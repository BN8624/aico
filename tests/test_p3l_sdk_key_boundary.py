# P3L SDK와 key-loading boundary skeleton이 실제 import/read를 열지 않는지 검증한다.
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from aico_v0.artifact_safety import scan_artifacts
from aico_v0.key_loading_boundary import (
    KEY_BOUNDARY_FAILURES,
    KeyLoadingBoundaryError,
    KeyLoadingBoundaryState,
    assert_key_value_read_disabled,
    build_key_existence_summary,
    build_key_loading_boundary_summary,
    validate_key_existence_summary,
    validate_key_loading_boundary_state,
)
from aico_v0.key_registry import KeyRegistry
from aico_v0.live_activation import block_candidate_provider_live_call, build_disabled_activation_result
from aico_v0.live_smoke import FAILURE_TYPE_BY_SMOKE_CONDITION, FirstLiveSmokeApproval
from aico_v0.live_smoke_artifacts import write_live_smoke_result
from aico_v0.provider_allowlist import google_gemini_candidate_entry, open_candidate_allowlist
from aico_v0.sdk_boundary import (
    SDK_BOUNDARY_FAILURES,
    SDKBoundaryError,
    SDKBoundaryState,
    assert_sdk_import_disabled,
    build_sdk_boundary_summary,
    validate_sdk_boundary_state,
    validate_sdk_boundary_summary,
)

RAW_SECRET = "sk-" + "p3l-boundary-secret-value"


def assert_sdk_blocked(exc_info: pytest.ExceptionInfo[SDKBoundaryError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def assert_key_blocked(exc_info: pytest.ExceptionInfo[KeyLoadingBoundaryError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def valid_approval() -> FirstLiveSmokeApproval:
    return FirstLiveSmokeApproval(
        provider="google_gemini",
        model="user-approved-model",
        key_slot="worker_1",
        max_model_calls=1,
        max_retries_per_call=0,
        max_runtime_seconds=60,
        allow_raw_output=False,
        approval_scope="this_run_only",
        approved_by_user=True,
    )


def safe_result_fields() -> dict[str, object]:
    return {
        "status": "disabled",
        "failure_type": "SECURITY_BLOCKED",
        "error": "first live smoke execution is disabled",
        "model_call_count": 0,
        "retry_count": 0,
        "reserve_used": False,
        "raw_output_saved": False,
        "masked_raw_output": None,
        "artifact_safety_status": "not_run",
    }


def test_default_sdk_boundary_state_is_disabled_or_not_approved() -> None:
    boundary = SDKBoundaryState()
    summary = build_sdk_boundary_summary(boundary)

    assert boundary.state == "disabled"
    assert boundary.authorizes_sdk_import is False
    assert summary["sdk_import_allowed"] is False
    assert summary["imports_provider_sdk"] is False
    assert summary["checks_sdk_availability"] is False


def test_sdk_candidate_only_is_not_approval() -> None:
    summary = build_sdk_boundary_summary(SDKBoundaryState(state="candidate_only"))

    assert summary["state"] == "candidate_only"
    assert summary["sdk_import_allowed"] is False
    assert summary["authorizes_live_call"] is False


@pytest.mark.parametrize("state", ["approved", "active", "enabled", "live", "sdk_ready", "import_ready"])
def test_sdk_approved_active_enabled_live_state_is_rejected(state: str) -> None:
    with pytest.raises(SDKBoundaryError) as exc_info:
        validate_sdk_boundary_state(SDKBoundaryState(state=state))
    assert_sdk_blocked(exc_info, "SECURITY_BLOCKED")


def test_unknown_sdk_state_maps_to_config_error() -> None:
    with pytest.raises(SDKBoundaryError) as exc_info:
        validate_sdk_boundary_state(SDKBoundaryState(state="mystery"))
    assert_sdk_blocked(exc_info, "CONFIG_ERROR")


def test_sdk_import_allowed_true_is_rejected() -> None:
    with pytest.raises(SDKBoundaryError) as exc_info:
        validate_sdk_boundary_state(SDKBoundaryState(sdk_import_allowed=True))
    assert_sdk_blocked(exc_info, "SECURITY_BLOCKED")


def test_sdk_boundary_helper_does_not_import_provider_sdk_or_network_modules() -> None:
    summary = build_sdk_boundary_summary()

    assert summary["imports_provider_sdk"] is False
    assert summary["imports_network_module"] is False
    with pytest.raises(SDKBoundaryError) as exc_info:
        assert_sdk_import_disabled()
    assert_sdk_blocked(exc_info, "SECURITY_BLOCKED")


def test_sdk_boundary_summary_contains_no_endpoint_url_or_raw_key() -> None:
    summary = build_sdk_boundary_summary()

    assert "endpoint_url" not in summary
    assert "api_key" not in summary
    assert RAW_SECRET not in repr(summary)
    with pytest.raises(SDKBoundaryError) as endpoint_exc:
        validate_sdk_boundary_summary({**summary, "endpoint_url": "https://provider.example"})
    assert_sdk_blocked(endpoint_exc, "SECURITY_BLOCKED")
    with pytest.raises(SDKBoundaryError) as raw_key_exc:
        validate_sdk_boundary_summary({**summary, "api_key": RAW_SECRET})
    assert_sdk_blocked(raw_key_exc, "SECURITY_BLOCKED")


def test_default_key_loading_boundary_state_is_disabled_or_not_approved() -> None:
    boundary = KeyLoadingBoundaryState()
    summary = build_key_loading_boundary_summary(boundary)

    assert boundary.state == "disabled"
    assert boundary.authorizes_key_loading is False
    assert summary["key_loading_allowed"] is False
    assert summary["reads_env_value"] is False
    assert summary["reads_raw_key"] is False


def test_key_existence_check_only_does_not_load_value() -> None:
    summary = build_key_loading_boundary_summary(KeyLoadingBoundaryState(state="existence_check_only"))

    assert summary["state"] == "existence_check_only"
    assert summary["key_loading_allowed"] is False
    assert summary["reads_raw_key"] is False


@pytest.mark.parametrize("state", ["approved", "active", "enabled", "live", "key_ready", "loaded", "value_loaded"])
def test_key_approved_active_enabled_live_state_is_rejected(state: str) -> None:
    with pytest.raises(KeyLoadingBoundaryError) as exc_info:
        validate_key_loading_boundary_state(KeyLoadingBoundaryState(state=state))
    assert_key_blocked(exc_info, "SECURITY_BLOCKED")


def test_unknown_key_loading_state_maps_to_config_error() -> None:
    with pytest.raises(KeyLoadingBoundaryError) as exc_info:
        validate_key_loading_boundary_state(KeyLoadingBoundaryState(state="mystery"))
    assert_key_blocked(exc_info, "CONFIG_ERROR")


def test_key_loading_allowed_true_is_rejected() -> None:
    with pytest.raises(KeyLoadingBoundaryError) as exc_info:
        validate_key_loading_boundary_state(KeyLoadingBoundaryState(key_loading_allowed=True))
    assert_key_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    ("summary", "failure_type"),
    [
        ({"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": True}, "SECURITY_BLOCKED"),
        ({"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": False, "raw_key_present": True}, "SECURITY_BLOCKED"),
        ({"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": False, "env_var_value": "actual-secret-value"}, "SECURITY_BLOCKED"),
        ({"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": "yes", "value_loaded": False}, "CONFIG_ERROR"),
    ],
)
def test_key_existence_summary_rejects_loaded_raw_or_env_value_fields(
    summary: dict[str, object],
    failure_type: str,
) -> None:
    with pytest.raises(KeyLoadingBoundaryError) as exc_info:
        validate_key_existence_summary(summary)
    assert_key_blocked(exc_info, failure_type)


def test_key_existence_summary_allows_env_var_name_and_boolean_exists_only() -> None:
    configured = build_key_existence_summary(KeyRegistry({"worker_1": True}), "worker_1").to_summary()
    missing = build_key_existence_summary(KeyRegistry({"worker_1": False}), "worker_1").to_summary()

    assert configured == {
        "key_slot": "worker_1",
        "env_var_name": "AICO_WORKER_1_API_KEY",
        "exists": True,
        "value_loaded": False,
        "failure_type": None,
        "error": None,
    }
    assert missing["exists"] is False
    assert missing["failure_type"] == "CONFIG_ERROR"
    assert "raw_key" not in configured
    assert "env_var_value" not in configured


def test_key_existence_skeleton_does_not_call_env_value_apis() -> None:
    source = Path("aico_v0/key_loading_boundary.py").read_text(encoding="utf-8")

    assert "getenv" not in source
    assert "environ.get" not in source
    with pytest.raises(KeyLoadingBoundaryError) as exc_info:
        assert_key_value_read_disabled()
    assert_key_blocked(exc_info, "SECURITY_BLOCKED")


def test_candidate_allowlist_does_not_authorize_sdk_key_or_live_call() -> None:
    entry = google_gemini_candidate_entry()
    state = open_candidate_allowlist()

    assert state.authorizes_sdk_import is False
    assert state.authorizes_key_loading is False
    assert state.authorizes_live_call is False
    assert entry.sdk_import_allowed is False
    assert entry.key_loading_allowed is False
    assert entry.live_calls_allowed is False


def test_provider_adapter_isolation_rule_keeps_raw_key_outside_boundary() -> None:
    sdk_summary = build_sdk_boundary_summary()
    key_summary = build_key_loading_boundary_summary()

    assert sdk_summary["boundary_location"] == "provider_adapter_internal_only"
    assert key_summary["boundary_location"] == "provider_adapter_internal_minimal_function_only"
    assert sdk_summary["imports_provider_sdk"] is False
    assert key_summary["reads_raw_key"] is False


def test_provider_result_cannot_contain_raw_key_or_raw_output() -> None:
    from aico_v0.provider_base import ProviderResult

    with pytest.raises(TypeError, match="raw_output"):
        ProviderResult("success", raw_output="unmasked")
    with pytest.raises(ValueError, match="raw_output_saved"):
        ProviderResult("success", raw_output_saved=True)
    result = ProviderResult("success", masked_raw_output="raw=" + RAW_SECRET)
    rendered = repr(result)

    assert "raw_output" not in result.__dict__
    assert RAW_SECRET not in rendered


@pytest.mark.parametrize(
    "artifact",
    [
        {"sdk_boundary_summary": {"provider": "google_gemini", "api_key": RAW_SECRET}},
        {"key_existence_summary": {"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": False, "env_var_value": "AICO_WORKER_1_API_KEY=actual-secret"}},
        {"sdk_boundary_summary": {"provider": "google_gemini", "endpoint_url": "https://provider.example"}},
        {"key_existence_summary": {"key_slot": "worker_1", "env_var_name": "AICO_WORKER_1_API_KEY", "exists": True, "value_loaded": True}},
    ],
)
def test_artifact_safety_rejects_unsafe_sdk_or_key_boundary_summary(artifact: dict[str, object]) -> None:
    result = scan_artifacts(artifact)

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"


def test_artifact_safety_accepts_safe_sdk_and_key_boundary_summaries() -> None:
    result = scan_artifacts(
        {
            "sdk_boundary_summary": build_sdk_boundary_summary(),
            "key_existence_summary": build_key_existence_summary(KeyRegistry({"worker_1": True}), "worker_1").to_summary(),
        }
    )

    assert result.ok is True


def test_live_call_remains_blocked_and_model_call_count_zero() -> None:
    entry = google_gemini_candidate_entry()
    activation_result = build_disabled_activation_result(entry.provider)

    assert activation_result.model_call_count == 0
    assert activation_result.actual_api_call_count == 0
    assert activation_result.actual_llm_call_count == 0
    assert activation_result.actual_key_value_read_count == 0
    assert activation_result.actual_network_call_count == 0
    with pytest.raises(Exception) as exc_info:
        block_candidate_provider_live_call(entry, state=open_candidate_allowlist())
    assert getattr(exc_info.value, "failure_type") == "SECURITY_BLOCKED"


def test_live_smoke_result_does_not_mark_success(tmp_path: Path) -> None:
    path = write_live_smoke_result(tmp_path, valid_approval(), **safe_result_fields())
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["status"] == "disabled"
    assert payload["model_call_count"] == 0
    assert payload["status"] not in {"success", "api_success", "provider_success", "live_success"}


def test_p3l_failure_mapping_uses_existing_canonical_failure_types() -> None:
    expected = {
        "unknown SDK import state": "CONFIG_ERROR",
        "unknown key loading state": "CONFIG_ERROR",
        "key missing": "CONFIG_ERROR",
        "SDK import before approved phase": "SECURITY_BLOCKED",
        "SDK import allowed true in P3L": "SECURITY_BLOCKED",
        "SDK boundary active/enabled/live": "SECURITY_BLOCKED",
        "provider SDK imported in runtime path": "SECURITY_BLOCKED",
        "network-capable SDK import in runtime path": "SECURITY_BLOCKED",
        "actual key read before approved phase": "SECURITY_BLOCKED",
        "key loading allowed true in P3L": "SECURITY_BLOCKED",
        "key boundary active/enabled/live": "SECURITY_BLOCKED",
        "raw key found": "SECURITY_BLOCKED",
        "env var value found": "SECURITY_BLOCKED",
        "value_loaded true": "SECURITY_BLOCKED",
        "raw_key_present field": "SECURITY_BLOCKED",
        "candidate interpreted as active": "SECURITY_BLOCKED",
        "live call attempted without all gates": "SECURITY_BLOCKED",
        "candidate provider live call attempted": "SECURITY_BLOCKED",
        "artifact write failure": "REPORT_ERROR",
    }

    for condition, failure_type in expected.items():
        assert FAILURE_TYPE_BY_SMOKE_CONDITION[condition] == failure_type
    assert SDK_BOUNDARY_FAILURES["unknown SDK import state"] == "CONFIG_ERROR"
    assert KEY_BOUNDARY_FAILURES["unknown key loading state"] == "CONFIG_ERROR"


def test_default_pytest_does_not_execute_live_smoke_in_p3l() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "live_smoke" in pyproject
    assert "live_provider" in pyproject


def test_p3l_runtime_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
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


def test_agents_and_claude_remain_byte_identical_for_p3l() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
