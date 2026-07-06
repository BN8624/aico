# P3U 명시 승인 gate가 armed-but-not-fired no-call 상태로만 동작하는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.explicit_approval_gate import (
    EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME,
    P3UExplicitApprovalGateError,
    aggregate_gate_failure_type,
    build_explicit_approval_gate,
    explicit_approval_gate_default_runtime_creation_enabled,
    validate_approval_phrase_ref,
    validate_explicit_approval_gate,
    validate_final_approval_linkage,
    validate_gate_no_call_invariants,
    validate_armed_state_artifact_ref,
    write_explicit_approval_gate,
)
from tests.test_p3t_final_live_approval_packet import p3t_inputs


def p3u_inputs(run_id: str = "run-p3u-001") -> dict[str, object]:
    inputs = p3t_inputs(run_id)
    packet = build_explicit_packet(inputs)
    return {**inputs, "final_live_approval_packet": packet}


def build_explicit_packet(inputs: dict[str, object]) -> dict[str, object]:
    from aico_v0.final_live_approval_packet import build_final_live_approval_packet

    return build_final_live_approval_packet(
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        approval_package_summary=inputs["approval_package"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        artifact_safety_summary=inputs["artifact_safety_summary"],
        runtime_flags_summary=inputs["runtime_flags_summary"],
        rollback_plan_summary=inputs["rollback_plan_summary"],
        test_evidence_summary=inputs["test_evidence_summary"],
        human_decision_summary=inputs["human_decision_summary"],
    ).to_summary()


def gate_summary(**overrides: object) -> dict[str, object]:
    inputs = p3u_inputs()
    gate = build_explicit_approval_gate(
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
    gate.update(overrides)
    return gate


def assert_failure(exc_info: pytest.ExceptionInfo[P3UExplicitApprovalGateError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_explicit_approval_gate_validates_safe_inputs() -> None:
    summary = gate_summary()

    assert summary["status"] == "armed_not_fired"
    assert summary["armed_state"] == "armed_not_fired"
    assert summary["armed"] is True
    assert summary["fired"] is False
    assert summary["created_for"] == "armed_but_not_fired_no_call"
    assert summary["final_live_approval_packet_ref"] == "final_live_approval_packet.json"
    assert summary["human_confirmation_checklist_ref"] == "human_confirmation_checklist.json"


def test_gate_allows_armed_true_only_when_fired_false() -> None:
    summary = gate_summary()

    assert summary["armed"] is True
    assert summary["fired"] is False
    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False


def test_gate_keeps_all_no_call_fields_closed() -> None:
    summary = gate_summary()

    assert summary["fired"] is False
    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["call_model_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["explicit_approval_required"] is True


@pytest.mark.parametrize("status", ["pending", "review_required", "not_granted"])
def test_gate_allows_only_non_granted_explicit_approval_status(status: str) -> None:
    inputs = p3u_inputs()
    gate = build_explicit_approval_gate(
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
        explicit_approval_status=status,
    ).to_summary()

    assert gate["explicit_approval_status"] == status
    assert gate["execution_allowed"] is False


@pytest.mark.parametrize("status", ["approved", "granted", "confirmed", "execution_approved", "live_approved", "armed_and_fired"])
def test_gate_rejects_approval_like_statuses(status: str) -> None:
    summary = gate_summary(explicit_approval_status=status)

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_explicit_approval_gate(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "status",
    ["success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call", "fired"],
)
def test_gate_rejects_success_like_status(status: str) -> None:
    summary = gate_summary(status=status)

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_explicit_approval_gate(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "update",
    [
        {"execution_allowed": True},
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"call_model_count": 1},
        {"fired": True},
        {"raw_output_saved": True},
        {"raw_output": "blocked"},
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"endpoint_url": "https://example.invalid"},
        {"raw_key": "sk-p3u-raw-key-value"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
        {"raw_approval_phrase": "I approve AICO first live smoke for this run only:"},
    ],
)
def test_gate_rejects_live_raw_secret_provider_and_approval_fields(update: dict[str, object]) -> None:
    summary = gate_summary()
    summary.update(update)

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_explicit_approval_gate(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_final_approval_packet_to_execution_boundary_linkage_validates_safe_matching_refs() -> None:
    inputs = p3u_inputs()

    validate_final_approval_linkage(
        final_live_approval_packet=inputs["final_live_approval_packet"],
        human_confirmation_checklist=inputs["human_decision_summary"],
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        live_execution_boundary=inputs["call_attempt_summary"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
    )


def test_linkage_rejects_missing_run_id() -> None:
    inputs = p3u_inputs()
    packet = dict(inputs["final_live_approval_packet"])
    packet.pop("run_id")

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_final_approval_linkage(
            final_live_approval_packet=packet,
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_linkage_rejects_missing_approval_phrase_hash() -> None:
    inputs = p3u_inputs()
    packet = dict(inputs["final_live_approval_packet"])
    packet.pop("approval_phrase_hash")

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_final_approval_linkage(
            final_live_approval_packet=packet,
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_linkage_rejects_run_id_mismatch() -> None:
    inputs = p3u_inputs()
    packet = dict(inputs["final_live_approval_packet"])
    packet["run_id"] = "other-run"

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_final_approval_linkage(
            final_live_approval_packet=packet,
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_linkage_rejects_approval_phrase_hash_mismatch() -> None:
    inputs = p3u_inputs()
    packet = dict(inputs["final_live_approval_packet"])
    packet["approval_phrase_hash"] = "0" * 64

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_final_approval_linkage(
            final_live_approval_packet=packet,
            human_confirmation_checklist=inputs["human_decision_summary"],
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            live_execution_boundary=inputs["call_attempt_summary"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_linkage_rejects_missing_artifact_reference() -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_armed_state_artifact_ref("")

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize("ref", ["C:/tmp/approval.txt", "../approval.txt", "https://example.invalid/approval.txt"])
def test_approval_phrase_ref_rejects_unsafe_refs(ref: str) -> None:
    with pytest.raises(Exception) as exc_info:
        validate_approval_phrase_ref(ref)

    assert getattr(exc_info.value, "failure_type") == "SECURITY_BLOCKED"


@pytest.mark.parametrize("ref", ["C:/tmp/gate.json", "../gate.json", "https://example.invalid/gate.json"])
def test_armed_state_artifact_ref_rejects_unsafe_refs(ref: str) -> None:
    with pytest.raises(Exception) as exc_info:
        validate_armed_state_artifact_ref(ref)

    assert getattr(exc_info.value, "failure_type") == "SECURITY_BLOCKED"


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
        {"budget_spent": True},
    ],
)
def test_gate_no_call_invariant_rejects_execution_markers(marker: dict[str, object]) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        validate_gate_no_call_invariants(marker)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_gate_failure_priority_prefers_security_blocked() -> None:
    assert aggregate_gate_failure_type(["CONFIG_ERROR", "SECURITY_BLOCKED", "REPORT_ERROR"]) == "SECURITY_BLOCKED"


def test_explicit_approval_gate_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    gate = gate_summary()
    path = write_explicit_approval_gate(tmp_path, gate, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME
    assert path.exists()


@pytest.mark.parametrize(
    "artifact_name",
    ["../explicit_approval_gate.json", "https://example.invalid/explicit_approval_gate.json"],
)
def test_explicit_approval_gate_write_helper_blocks_unsafe_paths(tmp_path: Path, artifact_name: str) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        write_explicit_approval_gate(
            tmp_path,
            gate_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name=artifact_name,
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_explicit_approval_gate_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        write_explicit_approval_gate(
            tmp_path,
            gate_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name=str(outside),
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_explicit_approval_gate_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        write_explicit_approval_gate(
            tmp_path,
            gate_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="unexpected.json",
        )

    assert_failure(exc_info, "REPORT_ERROR")


def test_explicit_approval_gate_write_requires_pre_and_post_scan(tmp_path: Path) -> None:
    with pytest.raises(P3UExplicitApprovalGateError) as pre_exc:
        write_explicit_approval_gate(tmp_path, gate_summary(), pre_scan=None, post_scan={"ok": True})
    with pytest.raises(P3UExplicitApprovalGateError) as post_exc:
        write_explicit_approval_gate(tmp_path, gate_summary(), pre_scan={"ok": True}, post_scan=None)

    assert_failure(pre_exc, "CONFIG_ERROR")
    assert_failure(post_exc, "CONFIG_ERROR")


def test_explicit_approval_gate_rejects_scan_failure() -> None:
    inputs = p3u_inputs()

    with pytest.raises(P3UExplicitApprovalGateError) as exc_info:
        build_explicit_approval_gate(
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
            artifact_safety_summary={"ok": False},
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_default_runtime_path_does_not_create_explicit_approval_gate(tmp_path: Path) -> None:
    assert explicit_approval_gate_default_runtime_creation_enabled() is False
    assert not (tmp_path / EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME).exists()
    assert not Path(EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME).exists()
