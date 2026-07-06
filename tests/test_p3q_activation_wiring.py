# P3Q no-call 통합 경로가 모든 activation guard를 실제 권한 없이 연결하는지 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aico_v0.key_loading_boundary import KeyLoadingBoundaryState
from aico_v0.no_call_integration import P3QNoCallIntegrationError, build_no_call_integration_summary
from aico_v0.provider_allowlist import CandidateProviderEntry, ProviderAllowlistState
from aico_v0.sdk_boundary import SDKBoundaryState

from tests.test_p3q_no_call_integration import approval_package_payload, final_gate_payload, runtime_flags_summary


def build_summary(**overrides: object):
    return build_no_call_integration_summary(
        approval_package=approval_package_payload(),
        final_live_gate_result=final_gate_payload(),
        runtime_flags_summary=runtime_flags_summary(),
        artifact_safety_summary={"ok": True},
        **overrides,
    )


def assert_failure(exc_info: pytest.ExceptionInfo[P3QNoCallIntegrationError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_activation_guard_results_are_wired_into_integration_summary() -> None:
    summary = build_summary().to_summary()
    guard_names = {guard["guard_name"] for guard in summary["activation_guards"]}

    assert guard_names == {
        "provider_allowlist_activation_guard",
        "sdk_import_activation_guard",
        "key_loading_activation_guard",
        "live_call_activation_guard",
    }
    assert all(guard["live_call_allowed"] is False for guard in summary["activation_guards"])
    assert all(guard["model_call_count"] == 0 for guard in summary["activation_guards"])


def test_provider_actual_activation_maps_security_blocked() -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(provider_actual_activation_attempted=True)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "entry",
    [
        CandidateProviderEntry(live_calls_allowed=True),
        CandidateProviderEntry(sdk_import_allowed=True),
        CandidateProviderEntry(key_loading_allowed=True),
        CandidateProviderEntry(endpoint_url="blocked-endpoint"),
    ],
)
def test_provider_permission_openings_map_security_blocked(entry: CandidateProviderEntry) -> None:
    state = ProviderAllowlistState("candidate", (entry,))

    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(provider_allowlist_state=state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("provider", ["unknown_provider", "https://provider.invalid", "provider.invalid"])
def test_provider_unknown_or_url_maps_security_blocked(provider: str) -> None:
    state = ProviderAllowlistState("candidate", (CandidateProviderEntry(provider=provider),))

    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(provider_allowlist_state=state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["active", "enabled", "live"])
def test_sdk_active_enabled_live_state_maps_security_blocked(state: str) -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(sdk_boundary_state=SDKBoundaryState(state=state))

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_sdk_import_allowed_true_maps_security_blocked() -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(sdk_import_allowed=True)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_sdk_runtime_import_indicators_map_security_blocked() -> None:
    for kwargs in ({"provider_sdk_imported": True}, {"network_capable_imported": True}):
        with pytest.raises(P3QNoCallIntegrationError) as exc_info:
            build_summary(**kwargs)
        assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["active", "enabled", "live"])
def test_key_loading_active_enabled_live_state_maps_security_blocked(state: str) -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(key_loading_boundary_state=KeyLoadingBoundaryState(state=state))

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_key_loading_allowed_true_maps_security_blocked() -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(key_loading_allowed=True)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "key_summary",
    [
        {"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": True},
        {
            "key_slot": "worker_1",
            "env_var_name": "AICO_WORKER_1_API_KEY",
            "exists": True,
            "value_loaded": False,
            "raw_key_present": True,
        },
    ],
)
def test_key_loading_loaded_or_raw_summary_maps_security_blocked(key_summary: dict[str, object]) -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_summary(key_existence_summary=key_summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_live_call_guard_blocks_call_permission_and_model_count() -> None:
    for kwargs in ({"live_call_allowed": True}, {"model_call_count": 1}, {"call_model_attempted": True}):
        with pytest.raises(P3QNoCallIntegrationError) as exc_info:
            build_summary(**kwargs)
        assert_failure(exc_info, "SECURITY_BLOCKED")


def test_p3q_runtime_imports_no_provider_sdk_or_network_modules() -> None:
    path = Path("aico_v0/no_call_integration.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_roots = {"requests", "httpx", "socket", "google", "openai", "anthropic", "genai", "dotenv"}
    forbidden_exact = {"urllib.request", "os.environ"}
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any(name.split(".")[0] in forbidden_roots for name in imports)
    assert not any(name in forbidden_exact for name in imports)


def test_p3q_runtime_reads_no_env_value() -> None:
    source = Path("aico_v0/no_call_integration.py").read_text(encoding="utf-8")
    assert "getenv(" not in source
    assert "environ.get(" not in source

