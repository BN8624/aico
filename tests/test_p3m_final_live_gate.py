# P3M final live-call gate skeleton이 실제 live call을 열지 않는지 검증한다.
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from aico_v0.artifact_safety import scan_artifacts
from aico_v0.final_live_gate import (
    FINAL_GATE_REQUIRED_GATES,
    FinalGateCheck,
    FinalLiveGateError,
    build_final_live_gate_result,
    validate_final_live_gate,
    validate_final_live_gate_result_payload,
    write_final_live_gate_result,
)
from aico_v0.key_loading_boundary import KeyLoadingBoundaryState, build_key_existence_summary
from aico_v0.key_registry import KeyRegistry
from aico_v0.live_smoke import FAILURE_TYPE_BY_SMOKE_CONDITION, FirstLiveSmokeApproval
from aico_v0.provider_allowlist import CandidateProviderEntry, ProviderAllowlistState, google_gemini_candidate_entry
from aico_v0.sdk_boundary import SDKBoundaryState

RAW_SECRET = "sk-" + "p3m-final-gate-secret"


def approval(**overrides: object) -> FirstLiveSmokeApproval:
    data = {
        "provider": "google_gemini",
        "model": "user-approved-model",
        "key_slot": "worker_1",
        "max_model_calls": 1,
        "max_retries_per_call": 0,
        "max_runtime_seconds": 60,
        "allow_raw_output": False,
        "approval_scope": "this_run_only",
        "approved_by_user": True,
        "approval_phrase": (
            "I approve AICO first live smoke for this run only:\n"
            "provider = google_gemini\n"
            "model = user-approved-model\n"
            "key_slot = worker_1\n"
            "max_model_calls = 1\n"
            "max_retries_per_call = 0\n"
            "max_runtime_seconds = 60\n"
            "allow_raw_output = false"
        ),
    }
    data.update(overrides)
    return FirstLiveSmokeApproval(**data)


def safe_flags(**overrides: str) -> dict[str, str]:
    data = {
        "AICO_ENABLE_REAL_PROVIDER": "true",
        "AICO_ALLOW_LIVE_CALLS": "true",
        "AICO_ALLOW_FIRST_LIVE_SMOKE": "true",
    }
    data.update(overrides)
    return data


def safe_budget(**overrides: int) -> dict[str, int]:
    data = {
        "max_model_calls": 1,
        "max_retries_per_call": 0,
        "max_consecutive_model_errors": 1,
        "max_runtime_seconds": 60,
    }
    data.update(overrides)
    return data


def key_summary(*, exists: bool = True, **overrides: object) -> dict[str, object]:
    summary = build_key_existence_summary(KeyRegistry({"worker_1": exists}), "worker_1").to_summary()
    summary.update(overrides)
    return summary


def safe_pre_scan():
    return scan_artifacts({"preflight": "provider=google_gemini key_slot=worker_1"})


def safe_kwargs(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "approval": approval(),
        "provider_allowlist_state": ProviderAllowlistState.candidate(google_gemini_candidate_entry()),
        "sdk_boundary": SDKBoundaryState(),
        "key_loading_boundary": KeyLoadingBoundaryState(),
        "key_existence_summary": key_summary(),
        "flags": safe_flags(),
        "budget": safe_budget(),
        "prompt_package": "Return a minimal JSON object matching the expected schema.",
        "expected_output_schema": {"status": "string", "message": "string"},
        "artifact_write_plan": ("run_log.jsonl", "ceo_report.md", "final_live_gate_result.json"),
        "artifact_safety_pre_scan": safe_pre_scan(),
        "live_call_allowed": False,
        "model_call_count": 0,
    }
    data.update(overrides)
    return data


def assert_result_failure(result, failure_type: str) -> None:
    assert result.overall_pass is False
    assert result.failure_type == failure_type
    assert result.live_call_allowed is False
    assert result.model_call_count == 0


def test_final_gate_pass_is_review_only() -> None:
    result = validate_final_live_gate(**safe_kwargs())

    assert result.overall_pass is True
    assert result.status == "ready_for_review"
    assert result.ready_for_review is True
    assert result.live_call_allowed is False
    assert result.model_call_count == 0
    assert result.provider == "google_gemini"
    assert result.key_slot == "worker_1"
    assert {gate.name for gate in result.gates} == set(FINAL_GATE_REQUIRED_GATES)
    assert all(gate.status == "pass" for gate in result.gates)


def test_final_gate_requires_approval_phrase_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(approval=None))

    assert_result_failure(result, "HUMAN_DECISION_REQUIRED")


def test_final_gate_requires_provider_allowlist_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(provider_allowlist_state=None))

    assert_result_failure(result, "CONFIG_ERROR")


def test_final_gate_requires_sdk_boundary_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(sdk_boundary=None))

    assert_result_failure(result, "CONFIG_ERROR")


def test_final_gate_requires_key_loading_boundary_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(key_loading_boundary=None))

    assert_result_failure(result, "CONFIG_ERROR")


def test_final_gate_requires_runtime_flags_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(flags=None))

    assert_result_failure(result, "CONFIG_ERROR")


def test_final_gate_requires_budget_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(budget=None))

    assert_result_failure(result, "CONFIG_ERROR")


def test_final_gate_requires_artifact_safety_pre_scan_gate() -> None:
    result = validate_final_live_gate(**safe_kwargs(artifact_safety_pre_scan=None))

    assert_result_failure(result, "CONFIG_ERROR")


def test_missing_required_gate_maps_to_config_error() -> None:
    gates = [FinalGateCheck(name=name, status="pass") for name in FINAL_GATE_REQUIRED_GATES if name != "budget_gate"]

    with pytest.raises(FinalLiveGateError) as exc_info:
        build_final_live_gate_result(approval=approval(), gates=gates)
    assert exc_info.value.failure_type == "CONFIG_ERROR"


def test_required_gate_not_run_maps_to_config_error() -> None:
    gates = [
        FinalGateCheck(name=name, status="not_run" if name == "budget_gate" else "pass")
        for name in FINAL_GATE_REQUIRED_GATES
    ]

    with pytest.raises(FinalLiveGateError) as exc_info:
        build_final_live_gate_result(approval=approval(), gates=gates)
    assert exc_info.value.failure_type == "CONFIG_ERROR"


def test_approval_missing_maps_to_human_decision_required() -> None:
    result = validate_final_live_gate(**safe_kwargs(approval=approval(approved_by_user=False)))

    assert_result_failure(result, "HUMAN_DECISION_REQUIRED")


def test_generic_approval_phrase_is_rejected() -> None:
    result = validate_final_live_gate(**safe_kwargs(approval=approval(approval_phrase="OK")))

    assert_result_failure(result, "HUMAN_DECISION_REQUIRED")


def test_allow_raw_output_true_maps_to_security_blocked() -> None:
    result = validate_final_live_gate(**safe_kwargs(approval=approval(allow_raw_output=True)))

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_provider_allowlist_empty_maps_to_config_error() -> None:
    result = validate_final_live_gate(**safe_kwargs(provider_allowlist_state=ProviderAllowlistState.empty()))

    assert_result_failure(result, "CONFIG_ERROR")


def test_provider_candidate_does_not_allow_live_call() -> None:
    result = validate_final_live_gate(**safe_kwargs())
    candidate_gate = next(gate for gate in result.gates if gate.name == "provider_candidate_gate")

    assert candidate_gate.status == "pass"
    assert result.live_call_allowed is False


@pytest.mark.parametrize(
    "entry",
    [
        CandidateProviderEntry(sdk_import_allowed=True),
        CandidateProviderEntry(key_loading_allowed=True),
        CandidateProviderEntry(live_calls_allowed=True),
        CandidateProviderEntry(endpoint_url="https://provider.example"),
    ],
)
def test_provider_candidate_unsafe_permissions_map_to_security_blocked(entry: CandidateProviderEntry) -> None:
    result = validate_final_live_gate(**safe_kwargs(provider_allowlist_state=ProviderAllowlistState("candidate", (entry,))))

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_sdk_import_allowed_true_maps_to_security_blocked() -> None:
    result = validate_final_live_gate(**safe_kwargs(sdk_boundary=SDKBoundaryState(sdk_import_allowed=True)))

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_key_loading_allowed_true_maps_to_security_blocked() -> None:
    result = validate_final_live_gate(
        **safe_kwargs(key_loading_boundary=KeyLoadingBoundaryState(key_loading_allowed=True))
    )

    assert_result_failure(result, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["approved", "active", "enabled", "live", "sdk_ready", "import_ready"])
def test_sdk_active_enabled_live_state_maps_to_security_blocked(state: str) -> None:
    result = validate_final_live_gate(**safe_kwargs(sdk_boundary=SDKBoundaryState(state=state)))

    assert_result_failure(result, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["approved", "active", "enabled", "live", "key_ready", "loaded", "value_loaded"])
def test_key_active_enabled_live_state_maps_to_security_blocked(state: str) -> None:
    result = validate_final_live_gate(**safe_kwargs(key_loading_boundary=KeyLoadingBoundaryState(state=state)))

    assert_result_failure(result, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "summary",
    [
        key_summary(value_loaded=True),
        key_summary(raw_key_present=True),
        key_summary(env_var_value="AICO_WORKER_1_API_KEY=actual-secret"),
    ],
)
def test_key_existence_unsafe_fields_map_to_security_blocked(summary: dict[str, object]) -> None:
    result = validate_final_live_gate(**safe_kwargs(key_existence_summary=summary))

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_runtime_flag_missing_maps_to_config_error() -> None:
    flags = safe_flags()
    flags.pop("AICO_ALLOW_FIRST_LIVE_SMOKE")
    result = validate_final_live_gate(**safe_kwargs(flags=flags))

    assert_result_failure(result, "CONFIG_ERROR")


def test_runtime_flag_false_maps_to_config_error() -> None:
    result = validate_final_live_gate(**safe_kwargs(flags=safe_flags(AICO_ALLOW_LIVE_CALLS="false")))

    assert_result_failure(result, "CONFIG_ERROR")


@pytest.mark.parametrize(
    "bad_approval",
    [
        approval(max_model_calls=2),
        approval(max_retries_per_call=1),
    ],
)
def test_approval_budget_attempt_to_loosen_policy_maps_to_security_blocked(
    bad_approval: FirstLiveSmokeApproval,
) -> None:
    result = validate_final_live_gate(**safe_kwargs(approval=bad_approval))

    assert_result_failure(result, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "budget",
    [
        safe_budget(max_model_calls=2),
        safe_budget(max_retries_per_call=1),
    ],
)
def test_budget_policy_attempt_to_loosen_maps_to_security_blocked(budget: dict[str, int]) -> None:
    result = validate_final_live_gate(**safe_kwargs(budget=budget))

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_model_call_count_greater_than_zero_maps_to_security_blocked() -> None:
    result = validate_final_live_gate(**safe_kwargs(model_call_count=1))

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_live_call_allowed_true_maps_to_security_blocked() -> None:
    result = validate_final_live_gate(**safe_kwargs(live_call_allowed=True))

    assert_result_failure(result, "SECURITY_BLOCKED")


@pytest.mark.parametrize("status", ["success", "live_success", "api_success", "provider_success"])
def test_success_like_status_maps_to_security_blocked(status: str) -> None:
    with pytest.raises(FinalLiveGateError) as exc_info:
        validate_final_live_gate(**safe_kwargs(result_status=status))
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


def test_artifact_safety_pre_scan_fail_maps_to_security_blocked() -> None:
    result = validate_final_live_gate(
        **safe_kwargs(artifact_safety_pre_scan=scan_artifacts({"pre": "Bearer abcdefghijklmnop"}))
    )

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_final_failure_priority_prefers_security_blocked() -> None:
    result = validate_final_live_gate(
        **safe_kwargs(
            approval=approval(allow_raw_output=True),
            flags=safe_flags(AICO_ALLOW_LIVE_CALLS="false"),
        )
    )

    assert_result_failure(result, "SECURITY_BLOCKED")


def test_final_failure_priority_handles_budget_exceeded() -> None:
    gates = [FinalGateCheck(name=name, status="pass") for name in FINAL_GATE_REQUIRED_GATES]
    gates[0] = FinalGateCheck("approval_phrase_gate", "fail", True, "BUDGET_EXCEEDED", "budget exceeded")
    result = build_final_live_gate_result(approval=approval(), gates=gates)

    assert_result_failure(result, "BUDGET_EXCEEDED")


def test_final_failure_priority_handles_report_error() -> None:
    gates = [FinalGateCheck(name=name, status="pass") for name in FINAL_GATE_REQUIRED_GATES]
    artifact_index = FINAL_GATE_REQUIRED_GATES.index("artifact_write_plan_gate")
    gates[artifact_index] = FinalGateCheck(
        "artifact_write_plan_gate",
        "fail",
        True,
        "REPORT_ERROR",
        "artifact write failure",
    )
    result = build_final_live_gate_result(approval=approval(), gates=gates)

    assert_result_failure(result, "REPORT_ERROR")


def test_final_gate_result_schema_has_no_raw_output_or_raw_key_fields() -> None:
    payload = validate_final_live_gate(**safe_kwargs()).to_summary()

    assert "raw_output" not in payload
    assert "raw_key" not in payload
    assert "env_var_value" not in payload
    assert "endpoint_url" not in payload
    assert payload["raw_output_saved"] is False
    assert payload["live_call_allowed"] is False
    assert payload["model_call_count"] == 0


@pytest.mark.parametrize(
    "payload_update",
    [
        {"provider": "https://provider.example"},
        {"model": RAW_SECRET},
        {"key_slot": RAW_SECRET},
        {"env_var_value": "AICO_WORKER_1_API_KEY=actual-secret"},
        {"raw_output": "unmasked"},
        {"raw_key": RAW_SECRET},
        {"endpoint_url": "https://provider.example"},
        {"live_call_allowed": True},
        {"model_call_count": 1},
    ],
)
def test_final_gate_result_payload_rejects_unsafe_fields(payload_update: dict[str, object]) -> None:
    payload = validate_final_live_gate(**safe_kwargs()).to_summary()
    payload.update(payload_update)

    with pytest.raises(FinalLiveGateError) as exc_info:
        validate_final_live_gate_result_payload(payload)
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


def test_final_gate_result_write_path_stays_inside_run_dir(tmp_path: Path) -> None:
    result = validate_final_live_gate(**safe_kwargs())
    path = write_final_live_gate_result(tmp_path, result)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path == (tmp_path / "final_live_gate_result.json").resolve()
    assert payload["status"] == "ready_for_review"
    assert payload["live_call_allowed"] is False


def test_final_gate_result_write_blocks_path_escape(tmp_path: Path) -> None:
    with pytest.raises(FinalLiveGateError) as exc_info:
        write_final_live_gate_result(tmp_path, validate_final_live_gate(**safe_kwargs()), artifact_name="../final_live_gate_result.json")
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


def test_final_gate_result_write_failure_maps_to_report_error(tmp_path: Path) -> None:
    with pytest.raises(FinalLiveGateError) as exc_info:
        write_final_live_gate_result(tmp_path, validate_final_live_gate(**safe_kwargs()), artifact_name="unknown.json")
    assert exc_info.value.failure_type == "REPORT_ERROR"


def test_final_gate_records_no_live_work() -> None:
    result = validate_final_live_gate(**safe_kwargs())

    assert result.actual_api_call_count == 0
    assert result.actual_llm_call_count == 0
    assert result.actual_key_value_read_count == 0
    assert result.actual_network_call_count == 0
    assert result.provider_sdk_imported is False
    assert result.live_smoke_executed is False


def test_p3m_failure_mapping_uses_existing_canonical_failure_types() -> None:
    expected = {
        "approval missing": "HUMAN_DECISION_REQUIRED",
        "approval ambiguous": "HUMAN_DECISION_REQUIRED",
        "required approval field missing": "HUMAN_DECISION_REQUIRED",
        "runtime flag missing": "CONFIG_ERROR",
        "runtime flag false": "CONFIG_ERROR",
        "provider allowlist missing": "CONFIG_ERROR",
        "provider allowlist empty": "CONFIG_ERROR",
        "SDK boundary missing": "CONFIG_ERROR",
        "key loading boundary missing": "CONFIG_ERROR",
        "unknown SDK import state": "CONFIG_ERROR",
        "unknown key loading state": "CONFIG_ERROR",
        "required gate not_run": "CONFIG_ERROR",
        "unknown gate status": "CONFIG_ERROR",
        "SDK import allowed true in P3M": "SECURITY_BLOCKED",
        "key loading allowed true in P3M": "SECURITY_BLOCKED",
        "model_call_count > 0 in P3M": "SECURITY_BLOCKED",
        "live_call_allowed true in P3M": "SECURITY_BLOCKED",
        "success-like status in P3M": "SECURITY_BLOCKED",
        "artifact write failure": "REPORT_ERROR",
    }

    for condition, failure_type in expected.items():
        assert FAILURE_TYPE_BY_SMOKE_CONDITION[condition] == failure_type


def test_default_pytest_does_not_execute_live_smoke() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "live_smoke" in pyproject
    assert "live_provider" in pyproject


def test_p3m_runtime_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
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


def test_agents_and_claude_remain_byte_identical_for_p3m() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
