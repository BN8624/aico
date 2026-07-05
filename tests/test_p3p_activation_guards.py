# P3P 활성화 guard가 모든 실제 실행 전환을 차단하는지 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aico_v0.activation_guards import (
    P3PActivationGuardError,
    assert_p3p_no_call_safety,
    key_loading_activation_guard,
    live_call_activation_guard,
    provider_allowlist_activation_guard,
    sdk_import_activation_guard,
)
from aico_v0.key_loading_boundary import KeyLoadingBoundaryState
from aico_v0.provider_allowlist import CandidateProviderEntry, ProviderAllowlistState, google_gemini_candidate_entry
from aico_v0.sdk_boundary import SDKBoundaryState


def assert_blocked(exc_info: pytest.ExceptionInfo[P3PActivationGuardError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_provider_activation_guard_allows_candidate_only_as_prepared_not_activation() -> None:
    result = provider_allowlist_activation_guard(
        ProviderAllowlistState.candidate(google_gemini_candidate_entry())
    ).to_summary()

    assert result["status"] == "prepared"
    assert result["live_call_allowed"] is False
    assert result["model_call_count"] == 0
    assert result["provider_allowlist_activated"] is False


def test_provider_activation_guard_blocks_actual_activation() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        provider_allowlist_activation_guard(actual_activation_attempted=True)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "entry",
    [
        CandidateProviderEntry(live_calls_allowed=True),
        CandidateProviderEntry(sdk_import_allowed=True),
        CandidateProviderEntry(key_loading_allowed=True),
        CandidateProviderEntry(endpoint_url="https://provider.example"),
    ],
)
def test_provider_activation_guard_blocks_candidate_permission_opening(entry: CandidateProviderEntry) -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        provider_allowlist_activation_guard(ProviderAllowlistState("candidate", (entry,)))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_sdk_activation_guard_blocks_sdk_import_allowed_true() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        sdk_import_activation_guard(sdk_import_allowed=True)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["approved", "active", "enabled", "live", "sdk_ready", "import_ready"])
def test_sdk_activation_guard_blocks_active_enabled_live_states(state: str) -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        sdk_import_activation_guard(SDKBoundaryState(state=state))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_sdk_activation_guard_blocks_runtime_import_indicators() -> None:
    with pytest.raises(P3PActivationGuardError) as sdk_exc:
        sdk_import_activation_guard(provider_sdk_imported=True)
    assert_blocked(sdk_exc, "SECURITY_BLOCKED")
    with pytest.raises(P3PActivationGuardError) as network_exc:
        sdk_import_activation_guard(network_capable_imported=True)
    assert_blocked(network_exc, "SECURITY_BLOCKED")


def test_key_loading_guard_blocks_key_loading_allowed_true() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        key_loading_activation_guard(key_loading_allowed=True)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["approved", "active", "enabled", "live", "key_ready", "loaded", "value_loaded"])
def test_key_loading_guard_blocks_active_enabled_live_states(state: str) -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        key_loading_activation_guard(KeyLoadingBoundaryState(state=state))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "summary",
    [
        {"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": True},
        {
            "key_slot": "worker_1",
            "env_var_name": "AICO_WORKER_1_API_KEY",
            "exists": True,
            "value_loaded": False,
            "raw_key_present": True,
        },
        {
            "key_slot": "worker_1",
            "env_var_name": "AICO_WORKER_1_API_KEY",
            "exists": True,
            "value_loaded": False,
            "env_var_value": "AICO_WORKER_1_API_KEY=actual-secret",
        },
    ],
)
def test_key_loading_guard_blocks_loaded_raw_or_env_value_summary(summary: dict[str, object]) -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        key_loading_activation_guard(key_existence_summary=summary)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_key_loading_guard_blocks_actual_key_read_attempt() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        key_loading_activation_guard(actual_key_read_attempted=True)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_live_call_guard_blocks_live_call_allowed_true() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        live_call_activation_guard(live_call_allowed=True)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_live_call_guard_blocks_model_call_count_above_zero() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        live_call_activation_guard(model_call_count=1)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("status", ["success", "live_success", "api_success", "provider_success"])
def test_live_call_guard_blocks_success_like_status(status: str) -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        live_call_activation_guard(status=status)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_live_call_guard_blocks_call_model_attempt() -> None:
    with pytest.raises(P3PActivationGuardError) as exc_info:
        live_call_activation_guard(call_model_attempted=True)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_all_p3p_guards_keep_no_call_counters_zero() -> None:
    summary = assert_p3p_no_call_safety()

    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["actual_api_call_count"] == 0
    assert summary["actual_llm_call_count"] == 0
    assert summary["actual_key_value_read_count"] == 0
    assert summary["actual_sdk_import_count"] == 0
    assert summary["actual_network_call_count"] == 0
    assert summary["actual_live_smoke_count"] == 0


def test_p3p_runtime_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
    forbidden_roots = {"requests", "httpx", "socket", "google", "openai", "anthropic", "genai", "dotenv"}
    forbidden_exact = {"urllib.request", "os.environ"}
    imports: set[str] = set()
    for path in Path("aico_v0").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

    assert not any(name.split(".")[0] in forbidden_roots for name in imports)
    assert not any(name in forbidden_exact for name in imports)


def test_p3p_helpers_do_not_use_env_value_read_apis() -> None:
    for path in (Path("aico_v0/approval_phrase.py"), Path("aico_v0/approval_package.py"), Path("aico_v0/activation_guards.py")):
        source = path.read_text(encoding="utf-8")
        assert "getenv" not in source
        assert "environ.get" not in source


def test_agents_and_claude_remain_byte_identical_for_p3p() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
