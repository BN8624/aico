# P3R 호출 시도 상태 머신과 rollback 기본 정책을 검증합니다.
from __future__ import annotations

import pytest

from aico_v0.live_execution_boundary import (
    P3RLiveExecutionBoundaryError,
    build_call_attempt_state_machine,
    build_rollback_plan,
    validate_call_attempt_state,
    validate_call_attempt_state_machine,
    validate_rollback_plan,
)


def assert_failure(exc_info: pytest.ExceptionInfo[P3RLiveExecutionBoundaryError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_state_machine_allows_no_execute_path() -> None:
    summary = build_call_attempt_state_machine().to_summary()

    assert summary["states"] == ("not_started", "precheck_ready", "dry_run_ready", "no_execute_completed")
    assert summary["current_state"] == "no_execute_completed"
    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0


@pytest.mark.parametrize(
    "state",
    [
        "executing",
        "executed",
        "called",
        "provider_called",
        "network_called",
        "sdk_imported",
        "key_loaded",
        "retrying",
        "fallback_started",
        "reserve_used",
        "second_call_started",
        "live_success",
        "api_success",
        "provider_success",
        "completed_live_call",
    ],
)
def test_state_machine_rejects_forbidden_call_states(state: str) -> None:
    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_call_attempt_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_state_machine_rejects_unknown_state_as_config_error() -> None:
    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_call_attempt_state("unexpected_state")

    assert_failure(exc_info, "CONFIG_ERROR")


def test_state_machine_rejects_live_permission_or_model_count() -> None:
    for kwargs in ({"live_call_allowed": True}, {"model_call_count": 1}):
        with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
            validate_call_attempt_state("precheck_ready", **kwargs)
        assert_failure(exc_info, "SECURITY_BLOCKED")


def test_state_machine_rejects_invalid_transition() -> None:
    payload = {
        "states": ("not_started", "no_execute_completed"),
        "current_state": "no_execute_completed",
        "live_call_allowed": False,
        "model_call_count": 0,
    }

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_call_attempt_state_machine(payload)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_rollback_plan_validates_safe_defaults() -> None:
    plan = build_rollback_plan().to_summary()

    assert plan["retry_allowed"] is False
    assert plan["reserve_allowed"] is False
    assert plan["fallback_allowed"] is False
    assert plan["second_call_allowed"] is False
    assert plan["allowlist_widening_allowed"] is False
    assert plan["key_slot_change_allowed"] is False
    assert plan["raw_output_preservation_allowed"] is False
    assert plan["review_required"] is True


@pytest.mark.parametrize(
    "field",
    [
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "allowlist_widening_allowed",
        "key_slot_change_allowed",
        "raw_output_preservation_allowed",
    ],
)
def test_rollback_plan_rejects_policy_openings(field: str) -> None:
    plan = build_rollback_plan().to_summary()
    plan[field] = True

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_rollback_plan(plan)

    assert_failure(exc_info, "SECURITY_BLOCKED")
