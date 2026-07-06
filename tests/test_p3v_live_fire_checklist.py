# P3V live-fire 체크리스트가 still-no-call 상태만 허용하는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.explicit_approval_gate import ARMED_STATE_ARTIFACT_NAME, build_armed_but_not_fired_state
from aico_v0.live_fire_checklist import (
    EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME,
    LAST_STOP_GUARD_ARTIFACT_NAME,
    LIVE_FIRE_CHECKLIST_ARTIFACT_NAME,
    ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME,
    P3VLiveFireChecklistError,
    build_expected_live_artifacts,
    build_last_stop_guard,
    build_live_fire_checklist,
    build_one_shot_fire_plan,
    build_rollback_confirmation,
    live_fire_checklist_default_runtime_creation_enabled,
    validate_artifact_reference_consistency,
    validate_expected_live_artifacts,
    validate_live_fire_checklist,
    validate_still_no_call_invariants,
    write_live_fire_checklist,
)
from tests.test_p3u_explicit_approval_gate import p3u_inputs


def p3v_inputs(run_id: str = "run-p3v-001") -> dict[str, object]:
    inputs = p3u_inputs(run_id)
    state = build_armed_but_not_fired_state(run_id=run_id).to_summary()
    rollback = build_rollback_confirmation().to_summary()
    expected = build_expected_live_artifacts(run_id=run_id).to_summary()
    plan = build_one_shot_fire_plan(run_id=run_id).to_summary()
    guard = build_last_stop_guard(run_id=run_id).to_summary()
    return {
        **inputs,
        "explicit_approval_gate": build_explicit_gate(inputs),
        "armed_state": state,
        "rollback_confirmation": rollback,
        "expected_live_artifacts": expected,
        "one_shot_fire_plan": plan,
        "last_stop_guard": guard,
    }


def build_explicit_gate(inputs: dict[str, object]) -> dict[str, object]:
    from aico_v0.explicit_approval_gate import build_explicit_approval_gate

    return build_explicit_approval_gate(
        final_live_approval_packet=inputs["final_live_approval_packet"],
        human_confirmation_checklist=inputs["human_decision_summary"],
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        live_execution_boundary=inputs["call_attempt_summary"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        runtime_flags_summary=inputs["runtime_flags_summary"],
        test_evidence_summary=inputs["test_evidence_summary"],
        rollback_plan_summary=inputs["rollback_plan_summary"],
        human_decision_summary=inputs["human_decision_summary"],
        artifact_safety_summary={"ok": True},
    ).to_summary()


def checklist_summary(**overrides: object) -> dict[str, object]:
    inputs = p3v_inputs()
    checklist = build_live_fire_checklist(
        explicit_approval_gate=inputs["explicit_approval_gate"],
        armed_state=inputs["armed_state"],
        final_live_approval_packet=inputs["final_live_approval_packet"],
        human_confirmation_checklist=inputs["human_decision_summary"],
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        live_execution_boundary=inputs["call_attempt_summary"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        runtime_flags_summary=inputs["runtime_flags_summary"],
        test_evidence_summary=inputs["test_evidence_summary"],
        rollback_plan_summary=inputs["rollback_confirmation"],
        policy_lock_summary=inputs["rollback_confirmation"],
        last_stop_guard=inputs["last_stop_guard"],
        one_shot_fire_plan=inputs["one_shot_fire_plan"],
        expected_live_artifacts=inputs["expected_live_artifacts"],
        artifact_safety_summary={"ok": True},
    ).to_summary()
    checklist.update(overrides)
    return checklist


def assert_failure(exc_info: pytest.ExceptionInfo[P3VLiveFireChecklistError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_live_fire_checklist_validates_safe_inputs() -> None:
    summary = checklist_summary()

    assert summary["status"] == "fire_checklist_ready"
    assert summary["ready_for_final_review"] is True
    assert summary["fire_ready"] is True
    assert summary["armed"] is True
    assert summary["created_for"] == "live_fire_checklist_still_no_call"
    assert summary["one_shot_fire_plan_ref"] == ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME
    assert summary["expected_live_artifacts_ref"] == EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME


def test_checklist_allows_fire_ready_and_armed_only_while_not_fired() -> None:
    summary = checklist_summary()

    assert summary["fire_ready"] is True
    assert summary["armed"] is True
    assert summary["fired"] is False
    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False


def test_checklist_keeps_all_no_call_fields_closed() -> None:
    summary = checklist_summary()

    assert summary["fired"] is False
    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["call_model_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["no_retry_confirmed"] is True
    assert summary["no_reserve_confirmed"] is True
    assert summary["no_fallback_confirmed"] is True
    assert summary["no_second_call_confirmed"] is True


@pytest.mark.parametrize(
    "status",
    ["success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call", "fired"],
)
def test_checklist_rejects_success_like_status(status: str) -> None:
    summary = checklist_summary(status=status)

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_live_fire_checklist(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "update",
    [
        {"fired": True},
        {"execution_allowed": True},
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"call_model_count": 1},
        {"raw_output_saved": True},
        {"raw_output": "blocked"},
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"endpoint_url": "https://example.invalid"},
        {"raw_key": "sk-p3v-raw-key-value"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
        {"raw_approval_phrase": "I approve AICO first live smoke for this run only:"},
    ],
)
def test_checklist_rejects_live_secret_provider_and_approval_fields(update: dict[str, object]) -> None:
    summary = checklist_summary()
    summary.update(update)

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_live_fire_checklist(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_expected_observable_artifacts_validates_allowed_artifact_names() -> None:
    summary = build_expected_live_artifacts(run_id="run-p3v-artifacts").to_summary()

    assert set(summary["artifact_names"]) == {
        "live_smoke_result.json",
        "artifact_safety_report.json",
        "final_live_gate_result.json",
        "call_attempt_summary.json",
    }


@pytest.mark.parametrize(
    "update",
    [
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"raw_output": "blocked"},
    ],
)
def test_expected_observable_artifacts_rejects_raw_result_content(update: dict[str, object]) -> None:
    summary = build_expected_live_artifacts(run_id="run-p3v-artifacts").to_summary()
    summary.update(update)

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_expected_live_artifacts(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "ref",
    [
        "https://example.invalid/live_smoke_result.json",
        "C:/tmp/live_smoke_result.json",
        "../live_smoke_result.json",
    ],
)
def test_expected_observable_artifacts_rejects_unsafe_refs(ref: str) -> None:
    summary = build_expected_live_artifacts(run_id="run-p3v-artifacts", artifact_names=("live_smoke_result.json",)).to_summary()
    summary["artifact_refs"]["live_smoke_result.json"] = ref

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_expected_live_artifacts(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_artifact_reference_consistency_validates_safe_matching_refs() -> None:
    inputs = p3v_inputs()

    run_id = validate_artifact_reference_consistency(
        explicit_approval_gate=inputs["explicit_approval_gate"],
        armed_state=inputs["armed_state"],
        final_live_approval_packet=inputs["final_live_approval_packet"],
        human_confirmation_checklist=inputs["human_decision_summary"],
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        live_execution_boundary=inputs["call_attempt_summary"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
    )

    assert run_id == "run-p3v-001"


def test_artifact_reference_consistency_rejects_missing_required_ref() -> None:
    inputs = p3v_inputs()
    gate = dict(inputs["explicit_approval_gate"])
    gate.pop("final_gate_result_ref")

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_artifact_reference_consistency(
            explicit_approval_gate=gate,
            armed_state=inputs["armed_state"],
            final_live_approval_packet=inputs["final_live_approval_packet"],
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_artifact_reference_consistency_rejects_unsafe_ref() -> None:
    inputs = p3v_inputs()
    gate = dict(inputs["explicit_approval_gate"])
    gate["final_gate_result_ref"] = "../final_live_gate_result.json"

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_artifact_reference_consistency(
            explicit_approval_gate=gate,
            armed_state=inputs["armed_state"],
            final_live_approval_packet=inputs["final_live_approval_packet"],
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_artifact_reference_consistency_rejects_run_id_mismatch() -> None:
    inputs = p3v_inputs()
    armed_state = dict(inputs["armed_state"])
    armed_state["run_id"] = "other-run"

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_artifact_reference_consistency(
            explicit_approval_gate=inputs["explicit_approval_gate"],
            armed_state=armed_state,
            final_live_approval_packet=inputs["final_live_approval_packet"],
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_artifact_reference_consistency_rejects_approval_phrase_hash_mismatch() -> None:
    inputs = p3v_inputs()
    gate = dict(inputs["explicit_approval_gate"])
    gate["approval_phrase_hash"] = "0" * 64

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_artifact_reference_consistency(
            explicit_approval_gate=gate,
            armed_state=inputs["armed_state"],
            final_live_approval_packet=inputs["final_live_approval_packet"],
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_still_no_call_invariant_passes_safe_fire_ready_armed_state() -> None:
    validate_still_no_call_invariants({"fire_ready": True, "armed": True, "fired": False, "execution_allowed": False})


@pytest.mark.parametrize(
    "marker",
    [
        {"fired": True},
        {"sdk_imported": True},
        {"key_loaded": True},
        {"network_call": True},
        {"live_smoke_executed": True},
        {"call_model_executed": True},
        {"provider_activation": True},
        {"actual_live_result_present": True},
    ],
)
def test_still_no_call_invariant_rejects_execution_markers(marker: dict[str, object]) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        validate_still_no_call_invariants(marker)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_live_fire_checklist_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    path = write_live_fire_checklist(tmp_path, checklist_summary(), pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / LIVE_FIRE_CHECKLIST_ARTIFACT_NAME
    assert path.exists()


@pytest.mark.parametrize(
    "artifact_name",
    ["../live_fire_checklist.json", "https://example.invalid/live_fire_checklist.json"],
)
def test_live_fire_checklist_write_helper_blocks_unsafe_paths(tmp_path: Path, artifact_name: str) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        write_live_fire_checklist(tmp_path, checklist_summary(), pre_scan={"ok": True}, post_scan={"ok": True}, artifact_name=artifact_name)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_live_fire_checklist_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / LIVE_FIRE_CHECKLIST_ARTIFACT_NAME

    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        write_live_fire_checklist(tmp_path, checklist_summary(), pre_scan={"ok": True}, post_scan={"ok": True}, artifact_name=str(outside))

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_live_fire_checklist_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as exc_info:
        write_live_fire_checklist(tmp_path, checklist_summary(), pre_scan={"ok": True}, post_scan={"ok": True}, artifact_name="unexpected.json")

    assert_failure(exc_info, "REPORT_ERROR")


def test_live_fire_checklist_write_requires_pre_and_post_scan(tmp_path: Path) -> None:
    with pytest.raises(P3VLiveFireChecklistError) as pre_exc:
        write_live_fire_checklist(tmp_path, checklist_summary(), pre_scan=None, post_scan={"ok": True})
    with pytest.raises(P3VLiveFireChecklistError) as post_exc:
        write_live_fire_checklist(tmp_path, checklist_summary(), pre_scan={"ok": True}, post_scan=None)

    assert_failure(pre_exc, "CONFIG_ERROR")
    assert_failure(post_exc, "CONFIG_ERROR")


def test_default_runtime_path_does_not_create_live_fire_checklist(tmp_path: Path) -> None:
    assert live_fire_checklist_default_runtime_creation_enabled() is False
    assert not (tmp_path / LIVE_FIRE_CHECKLIST_ARTIFACT_NAME).exists()
    assert not Path(LIVE_FIRE_CHECKLIST_ARTIFACT_NAME).exists()
    assert not Path(ARMED_STATE_ARTIFACT_NAME).exists()
