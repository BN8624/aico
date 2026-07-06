# P3V last-stop guard와 one-shot fire plan이 실행 상태를 열지 않는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.live_fire_checklist import (
    EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME,
    LAST_STOP_GUARD_ARTIFACT_NAME,
    ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME,
    P3VLiveFireChecklistError,
    build_last_stop_guard,
    build_one_shot_fire_plan,
    build_rollback_confirmation,
    validate_fire_readiness_state,
    validate_fire_readiness_state_machine,
    validate_last_stop_guard,
    validate_one_shot_fire_plan,
    validate_rollback_confirmation,
    write_expected_live_artifacts,
    write_last_stop_guard,
    write_one_shot_fire_plan,
)
from tests.test_p3v_live_fire_checklist import assert_failure, p3v_inputs


def test_fire_readiness_state_allows_still_no_call_path() -> None:
    validate_fire_readiness_state_machine(
        {
            "states": ("checklist_ready", "last_stop_ready", "fire_plan_ready", "still_no_call"),
            "current_state": "still_no_call",
            "fired": False,
            "execution_allowed": False,
            "live_call_allowed": False,
            "model_call_count": 0,
            "call_model_count": 0,
        }
    )


@pytest.mark.parametrize("state", ["firing", "fired", "executing", "executed", "called"])
def test_fire_readiness_state_rejects_fire_and_execution_states(state: str) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_fire_readiness_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["provider_called", "network_called"])
def test_fire_readiness_state_rejects_provider_and_network_called_states(state: str) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_fire_readiness_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["sdk_imported", "key_loaded"])
def test_fire_readiness_state_rejects_sdk_and_key_states(state: str) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_fire_readiness_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("state", ["retrying", "fallback_started", "reserve_used", "second_call_started"])
def test_fire_readiness_state_rejects_retry_fallback_reserve_and_second_call_states(state: str) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_fire_readiness_state(state)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_fire_readiness_state_rejects_fire_command_issued() -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_fire_readiness_state("fire_command_issued")

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_unknown_fire_readiness_state_maps_config_error() -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_fire_readiness_state("unknown_state")

    assert_failure(exc_info, "CONFIG_ERROR")


def test_last_stop_guard_validates_required_safe_items() -> None:
    guard = build_last_stop_guard(run_id="run-p3v-guard").to_summary()

    assert guard["status"] == "still_no_call"
    assert guard["fire_ready"] is True
    assert guard["armed"] is True
    assert guard["fired"] is False


def test_last_stop_guard_rejects_missing_required_item() -> None:
    guard = build_last_stop_guard(run_id="run-p3v-guard").to_summary()
    del guard["required_items"]["rollback_policy_present"]

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_last_stop_guard(guard)

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize(
    "item",
    [
        "fired_false",
        "execution_allowed_false",
        "provider_not_activated",
        "sdk_not_imported",
        "key_not_loaded",
        "network_not_called",
        "call_model_not_called",
    ],
)
def test_last_stop_guard_rejects_actual_call_indicators(item: str) -> None:
    guard = build_last_stop_guard(run_id="run-p3v-guard").to_summary()
    guard["required_items"][item] = False

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_last_stop_guard(guard)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_last_stop_guard_rejects_actual_live_result_present() -> None:
    guard = build_last_stop_guard(run_id="run-p3v-guard").to_summary()
    guard["required_items"]["actual_live_result_absent"] = False

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_last_stop_guard(guard)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_one_shot_fire_plan_validates_no_execute_plan() -> None:
    plan = build_one_shot_fire_plan(run_id="run-p3v-plan").to_summary()

    assert plan["plan_type"] == "one_shot_fire_plan_no_execute"
    assert plan["fire_ready"] is True
    assert plan["fired"] is False
    assert plan["execution_allowed"] is False
    assert plan["live_call_allowed"] is False
    assert plan["max_model_calls"] == 1
    assert plan["model_call_count"] == 0
    assert plan["call_model_count"] == 0


@pytest.mark.parametrize(
    "token",
    ["--execute", "--live", "--fire", "--call-model", "--load-key", "--use-key", "--network", "--sdk-import"],
)
def test_one_shot_fire_plan_rejects_live_command_tokens(token: str) -> None:
    plan = build_one_shot_fire_plan(run_id="run-p3v-plan").to_summary()
    plan["command_skeleton"] = f"python -m aico_v0.live_smoke --dry-run --no-execute --review-only {token}"

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_one_shot_fire_plan(plan)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("field", ["retry_allowed", "reserve_allowed", "fallback_allowed", "second_call_allowed"])
def test_one_shot_fire_plan_rejects_call_expansion_flags(field: str) -> None:
    plan = build_one_shot_fire_plan(run_id="run-p3v-plan").to_summary()
    plan[field] = True

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_one_shot_fire_plan(plan)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_rollback_confirmation_validates_safe_defaults() -> None:
    rollback = build_rollback_confirmation().to_summary()

    assert rollback["retry_allowed"] is False
    assert rollback["reserve_allowed"] is False
    assert rollback["fallback_allowed"] is False
    assert rollback["second_call_allowed"] is False
    assert rollback["rollback_required_on_failure"] is True


@pytest.mark.parametrize(
    "field",
    ["preserve_raw_output", "allowlist_widening_allowed", "key_slot_change_allowed", "budget_reset_allowed"],
)
def test_rollback_confirmation_rejects_widening_flags(field: str) -> None:
    rollback = build_rollback_confirmation().to_summary()
    rollback[field] = True

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_rollback_confirmation(rollback)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_last_stop_guard_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    guard = build_last_stop_guard(run_id="run-p3v-guard")

    path = write_last_stop_guard(tmp_path, guard, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / LAST_STOP_GUARD_ARTIFACT_NAME
    assert path.exists()


def test_one_shot_fire_plan_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    plan = build_one_shot_fire_plan(run_id="run-p3v-plan")

    path = write_one_shot_fire_plan(tmp_path, plan, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME
    assert path.exists()


def test_expected_live_artifacts_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    expected = p3v_inputs()["expected_live_artifacts"]

    path = write_expected_live_artifacts(tmp_path, expected, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME
    assert path.exists()
