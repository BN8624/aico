# P3U armed-but-not-fired 상태와 one-shot policy lock이 실행 상태로 전환되지 않는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.explicit_approval_gate import (
    ARMED_STATE_ARTIFACT_NAME,
    P3UExplicitApprovalGateError,
    armed_state_default_runtime_creation_enabled,
    build_armed_but_not_fired_state,
    build_one_shot_budget_lock,
    build_single_call_policy_lock,
    validate_armed_but_not_fired_state,
    validate_armed_state,
    validate_armed_state_machine,
    validate_one_shot_budget_lock,
    validate_policy_lock,
    write_armed_state,
)


def assert_failure(exc_info: pytest.ExceptionInfo[P3UExplicitApprovalGateError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_armed_state_allows_pre_armed_review_to_armed_not_fired() -> None:
    state = build_armed_but_not_fired_state(run_id="run-p3u-armed").to_summary()

    assert state["armed_states"] == ("pre_armed_review", "armed_not_fired")
    assert state["armed_state"] == "armed_not_fired"
    assert state["armed"] is True
    assert state["fired"] is False
    assert state["execution_allowed"] is False
    assert state["live_call_allowed"] is False
    assert state["model_call_count"] == 0
    assert state["call_model_count"] == 0


@pytest.mark.parametrize(
    "state",
    ["firing", "fired", "executing", "executed", "called", "provider_called", "network_called"],
)
def test_armed_state_rejects_firing_and_execution_states(state: str) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["sdk_imported", "key_loaded"])
def test_armed_state_rejects_sdk_and_key_states(state: str) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["retrying", "fallback_started", "reserve_used", "second_call_started"])
def test_armed_state_rejects_retry_fallback_reserve_and_second_call_states(state: str) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["live_success", "api_success", "provider_success", "completed_live_call", "armed_and_fired"])
def test_armed_state_rejects_success_like_states(state: str) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_unknown_armed_state_maps_config_error() -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state("unknown_state")

    assert_failure(exc_info, "CONFIG_ERROR")


def test_armed_state_machine_rejects_invalid_transition() -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state_machine(
            {
                "states": ("not_armed", "armed_not_fired"),
                "current_state": "armed_not_fired",
                "execution_allowed": False,
                "live_call_allowed": False,
                "model_call_count": 0,
                "call_model_count": 0,
            }
        )

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize(
    "update",
    [
        {"fired": True},
        {"execution_allowed": True},
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"call_model_count": 1},
        {"raw_output_saved": True},
    ],
)
def test_armed_state_summary_rejects_execution_flags(update: dict[str, object]) -> None:
    state = build_armed_but_not_fired_state(run_id="run-p3u-armed").to_summary()
    state.update(update)

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_but_not_fired_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_one_shot_budget_lock_validates_safe_defaults() -> None:
    lock = build_one_shot_budget_lock().to_summary()

    assert lock["max_model_calls"] == 1
    assert lock["model_call_count"] == 0
    assert lock["budget_locked"] is True
    assert lock["budget_spent"] is False


@pytest.mark.parametrize(
    "field",
    [
        "budget_spent",
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "budget_reset_allowed",
        "budget_widening_allowed",
    ],
)
def test_one_shot_budget_lock_rejects_widening_and_spent_flags(field: str) -> None:
    lock = build_one_shot_budget_lock().to_summary()
    lock[field] = True

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_one_shot_budget_lock(lock)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_policy_locks_validate_safe_defaults() -> None:
    lock = build_single_call_policy_lock().to_summary()

    assert lock["single_call_only"] is True
    assert lock["retry_allowed"] is False
    assert lock["reserve_allowed"] is False
    assert lock["fallback_allowed"] is False
    assert lock["second_call_allowed"] is False


@pytest.mark.parametrize(
    "field",
    [
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "provider_rotation_allowed",
        "key_rotation_allowed",
        "policy_widening_allowed",
    ],
)
def test_policy_locks_reject_widening_and_call_expansion_flags(field: str) -> None:
    lock = build_single_call_policy_lock().to_summary()
    lock[field] = True

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_policy_lock(lock)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_armed_state_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    state = build_armed_but_not_fired_state(run_id="run-p3u-armed")

    path = write_armed_state(tmp_path, state, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / ARMED_STATE_ARTIFACT_NAME
    assert path.exists()


@pytest.mark.parametrize("artifact_name", ["../armed_state.json", "https://example.invalid/armed_state.json"])
def test_armed_state_write_helper_blocks_unsafe_paths(tmp_path: Path, artifact_name: str) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        write_armed_state(
            tmp_path,
            build_armed_but_not_fired_state(run_id="run-p3u-armed"),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name=artifact_name,
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_armed_state_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        write_armed_state(
            tmp_path,
            build_armed_but_not_fired_state(run_id="run-p3u-armed"),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="unexpected.json",
        )

    assert_failure(exc_info, "REPORT_ERROR")


def test_armed_state_write_requires_pre_and_post_scan(tmp_path: Path) -> None:
    state = build_armed_but_not_fired_state(run_id="run-p3u-armed")

    with pytest.raises(P3UExplicitApprovalGateError) as pre_exc:
        write_armed_state(tmp_path, state, pre_scan=None, post_scan={"ok": True})
    with pytest.raises(P3UExplicitApprovalGateError) as post_exc:
        write_armed_state(tmp_path, state, pre_scan={"ok": True}, post_scan=None)

    assert_failure(pre_exc, "CONFIG_ERROR")
    assert_failure(post_exc, "CONFIG_ERROR")


def test_default_runtime_path_does_not_create_armed_state(tmp_path: Path) -> None:
    assert armed_state_default_runtime_creation_enabled() is False
    assert not (tmp_path / ARMED_STATE_ARTIFACT_NAME).exists()
    assert not Path(ARMED_STATE_ARTIFACT_NAME).exists()
