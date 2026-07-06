# P3R 실행 경계가 실제 호출 없이 안전한 summary만 허용하는지 검증합니다.
from __future__ import annotations

import pytest

from aico_v0.live_execution_boundary import (
    P3RLiveExecutionBoundaryError,
    build_live_execution_boundary,
    build_no_execute_dry_run,
    validate_live_execution_boundary,
    validate_pre_call_safety,
)

from tests.test_p3q_no_call_integration import (
    approval_package_payload,
    final_gate_payload,
    runtime_flags_summary,
)
from aico_v0.no_call_integration import build_no_call_integration_summary


def no_call_summary(run_id: str = "run-p3r-001", **overrides: object) -> dict[str, object]:
    return build_no_call_integration_summary(
        approval_package=approval_package_payload(run_id),
        final_live_gate_result=final_gate_payload(run_id),
        runtime_flags_summary=runtime_flags_summary(),
        artifact_safety_summary={"ok": True},
        **overrides,
    ).to_summary()


def safe_inputs(run_id: str = "run-p3r-001") -> dict[str, dict[str, object]]:
    return {
        "approval_package": approval_package_payload(run_id),
        "final_gate_result": final_gate_payload(run_id),
        "no_call_integration_summary": no_call_summary(run_id),
    }


def assert_failure(exc_info: pytest.ExceptionInfo[P3RLiveExecutionBoundaryError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_live_execution_boundary_validates_safe_no_call_inputs() -> None:
    summary = build_no_execute_dry_run(**safe_inputs()).to_summary()

    assert summary["status"] == "ready_for_review"
    assert summary["ready_for_review"] is True
    assert summary["execution_boundary_state"] == "single_call_no_execute_prepared"
    assert summary["call_attempt_state"] == "no_execute_completed"
    assert summary["provider"] == "google_gemini"
    assert summary["model"] == "gemini_flash"
    assert summary["key_slot"] == "worker_1"
    assert summary["approval_package_ref"] == "approval_package.json"
    assert summary["final_gate_result_ref"] == "final_live_gate_result.json"
    assert summary["no_call_integration_ref"] == "no_call_integration_summary.json"


def test_boundary_keeps_no_execute_counters_and_raw_output_closed() -> None:
    summary = build_live_execution_boundary(**safe_inputs()).to_summary()

    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["max_model_calls"] == 1
    assert summary["max_retries_per_call"] == 0
    assert summary["reserve_allowed"] is False
    assert summary["fallback_allowed"] is False
    assert summary["second_call_allowed"] is False
    assert summary["actual_api_call_count"] == 0
    assert summary["actual_llm_call_count"] == 0
    assert summary["actual_key_value_read_count"] == 0
    assert summary["actual_sdk_import_count"] == 0
    assert summary["actual_network_call_count"] == 0
    assert summary["actual_live_smoke_count"] == 0


@pytest.mark.parametrize(
    "update",
    [
        {"status": "success"},
        {"status": "live_success"},
        {"status": "api_success"},
        {"status": "provider_success"},
        {"status": "executed"},
        {"status": "called"},
        {"status": "completed_live_call"},
    ],
)
def test_boundary_rejects_success_like_status(update: dict[str, object]) -> None:
    summary = build_live_execution_boundary(**safe_inputs()).to_summary()
    summary.update(update)

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_live_execution_boundary(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "update",
    [
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"raw_output_saved": True},
        {"raw_output": "blocked"},
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"endpoint_url": "https://example.invalid"},
        {"raw_key": "sk-p3r-raw-key-value"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
    ],
)
def test_boundary_rejects_live_raw_provider_and_endpoint_fields(update: dict[str, object]) -> None:
    summary = build_live_execution_boundary(**safe_inputs()).to_summary()
    summary.update(update)

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_live_execution_boundary(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_pre_call_safety_validates_safe_linkage() -> None:
    validate_pre_call_safety(**safe_inputs())


def test_pre_call_safety_rejects_run_id_mismatch() -> None:
    inputs = safe_inputs("run-a")
    inputs["final_gate_result"] = final_gate_payload("run-b")

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_pre_call_safety(**inputs)

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize(
    ("missing_field", "condition"),
    [
        ("approval_package", "approval package linkage missing"),
        ("final_gate_result", "final gate linkage missing"),
        ("no_call_integration_summary", "no-call integration linkage missing"),
    ],
)
def test_pre_call_safety_rejects_missing_required_linkage(missing_field: str, condition: str) -> None:
    inputs: dict[str, object] = safe_inputs()
    inputs[missing_field] = None

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_pre_call_safety(**inputs)

    assert exc_info.value.condition == condition
    assert_failure(exc_info, "CONFIG_ERROR")
