# P3T final live approval packet이 사람 검토용 no-call packet으로만 동작하는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.final_live_approval_packet import (
    FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
    HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
    P3TApprovalPacketError,
    aggregate_packet_failure_type,
    build_final_live_approval_packet,
    build_human_confirmation_checklist,
    build_no_call_evidence_summary,
    final_live_approval_packet_default_runtime_creation_enabled,
    validate_approval_phrase_ref,
    validate_final_live_approval_packet,
    validate_next_step_command_skeleton,
    validate_packet_artifact_ref,
    validate_packet_no_call_invariants,
    write_final_live_approval_packet,
)
from aico_v0.pre_live_package import PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME, assemble_pre_live_package

from tests.test_p3s_pre_live_package import p3s_inputs


def p3t_inputs(run_id: str = "run-p3t-001") -> dict[str, object]:
    p3s = p3s_inputs(run_id)
    manifest = assemble_pre_live_package(**p3s).to_summary()
    evidence = build_no_call_evidence_summary(run_id).to_summary()
    checklist = build_human_confirmation_checklist(run_id=run_id).to_summary()
    return {
        **p3s,
        "pre_live_package_manifest": manifest,
        "test_evidence_summary": evidence,
        "human_decision_summary": checklist,
        "artifact_safety_summary": {"ok": True},
    }


def packet_summary(**overrides: object) -> dict[str, object]:
    inputs = p3t_inputs()
    packet = build_final_live_approval_packet(
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
    packet.update(overrides)
    return packet


def assert_failure(exc_info: pytest.ExceptionInfo[P3TApprovalPacketError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_final_live_approval_packet_validates_safe_packet_inputs() -> None:
    summary = packet_summary()

    assert summary["status"] == "ready_for_human_review"
    assert summary["ready_for_human_review"] is True
    assert summary["human_confirmation_required"] is True
    assert summary["human_confirmation_status"] == "review_required"
    assert summary["created_for"] == "human_confirmation_only_no_call"
    assert summary["pre_live_package_manifest_ref"] == PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME
    assert summary["human_confirmation_checklist_ref"] == HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME
    assert summary["approval_package_ref"] == "approval_package.json"
    assert summary["next_step_command_skeleton"].endswith("--dry-run --no-execute --review-only")


def test_packet_keeps_all_no_call_fields_closed() -> None:
    summary = packet_summary()

    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["call_model_count"] == 0
    assert summary["raw_output_saved"] is False


@pytest.mark.parametrize("human_status", ["pending", "review_required", "not_granted"])
def test_packet_allows_only_non_granted_human_statuses(human_status: str) -> None:
    checklist = build_human_confirmation_checklist(run_id="run-p3t-001", human_confirmation_status=human_status).to_summary()
    inputs = p3t_inputs()
    packet = build_final_live_approval_packet(
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        approval_package_summary=inputs["approval_package"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        artifact_safety_summary=inputs["artifact_safety_summary"],
        runtime_flags_summary=inputs["runtime_flags_summary"],
        rollback_plan_summary=inputs["rollback_plan_summary"],
        test_evidence_summary=inputs["test_evidence_summary"],
        human_decision_summary=checklist,
    ).to_summary()

    assert packet["human_confirmation_status"] == human_status
    assert packet["execution_allowed"] is False


@pytest.mark.parametrize("human_status", ["approved", "granted", "confirmed", "execution_approved", "live_approved"])
def test_packet_rejects_granted_human_statuses(human_status: str) -> None:
    summary = packet_summary(human_confirmation_status=human_status)

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_final_live_approval_packet(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "status",
    ["success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"],
)
def test_packet_rejects_success_like_status(status: str) -> None:
    summary = packet_summary(status=status)

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_final_live_approval_packet(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "update",
    [
        {"execution_allowed": True},
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"call_model_count": 1},
        {"raw_output_saved": True},
        {"raw_output": "blocked"},
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"endpoint_url": "https://example.invalid"},
        {"raw_key": "sk-p3t-raw-key-value"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
        {"raw_approval_phrase": "I approve AICO first live smoke for this run only:"},
    ],
)
def test_packet_rejects_live_raw_secret_provider_and_approval_fields(update: dict[str, object]) -> None:
    summary = packet_summary()
    summary.update(update)

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_final_live_approval_packet(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "token",
    [
        "--execute",
        "--live",
        "--use-key",
        "--load-key",
        "--call-model",
        "--network",
        "--sdk-import",
        "--provider-activate",
        "--allowlist-activate",
        "--live-call-allowed",
    ],
)
def test_next_step_command_skeleton_rejects_live_tokens(token: str) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_next_step_command_skeleton(f"python -m aico_v0.live_smoke --dry-run --no-execute {token}")

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_next_step_command_skeleton_accepts_no_execute_review_only_command() -> None:
    validate_next_step_command_skeleton("python -m aico_v0.live_smoke --dry-run --no-execute --review-only")


@pytest.mark.parametrize("command", ["python -m aico_v0.live_smoke --review-only", "python -m aico_v0.live_smoke --no-execute"])
def test_next_step_command_skeleton_requires_no_execute_and_review_guard(command: str) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_next_step_command_skeleton(command)

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize("ref", ["C:/tmp/approval.txt", "../approval.txt", "https://example.invalid/approval.txt"])
def test_approval_phrase_ref_rejects_unsafe_refs(ref: str) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_approval_phrase_ref(ref)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_approval_phrase_ref_rejects_raw_phrase() -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_approval_phrase_ref("I approve AICO first live smoke for this run only:")

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("ref", ["C:/tmp/packet.json", "../packet.json", "https://example.invalid/packet.json"])
def test_packet_artifact_ref_rejects_unsafe_refs(ref: str) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_packet_artifact_ref(ref)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_missing_required_packet_ref_maps_config_error() -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_packet_artifact_ref("")

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize(
    "marker",
    [
        {"sdk_imported": True},
        {"key_loaded": True},
        {"network_call": True},
        {"live_smoke_executed": True},
        {"call_model_executed": True},
        {"provider_activation": True},
        {"retry_allowed": True},
        {"reserve_allowed": True},
        {"fallback_allowed": True},
        {"second_call_allowed": True},
    ],
)
def test_packet_no_call_invariant_rejects_execution_markers(marker: dict[str, object]) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_packet_no_call_invariants(marker)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_packet_failure_priority_prefers_security_blocked() -> None:
    assert aggregate_packet_failure_type(["CONFIG_ERROR", "SECURITY_BLOCKED", "REPORT_ERROR"]) == "SECURITY_BLOCKED"


def test_final_live_approval_packet_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    packet = build_final_live_approval_packet(
        pre_live_package_manifest=p3t_inputs()["pre_live_package_manifest"],
        approval_package_summary=p3t_inputs()["approval_package"],
        no_call_integration_summary=p3t_inputs()["no_call_integration_summary"],
        call_attempt_summary=p3t_inputs()["call_attempt_summary"],
        final_live_gate_result=p3t_inputs()["final_live_gate_result"],
        artifact_safety_summary={"ok": True},
        runtime_flags_summary=p3t_inputs()["runtime_flags_summary"],
        rollback_plan_summary=p3t_inputs()["rollback_plan_summary"],
        test_evidence_summary=p3t_inputs()["test_evidence_summary"],
        human_decision_summary=p3t_inputs()["human_decision_summary"],
    )
    path = write_final_live_approval_packet(tmp_path, packet, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME
    assert path.exists()


def test_final_live_approval_packet_write_helper_blocks_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        write_final_live_approval_packet(
            tmp_path,
            packet_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="../final_live_approval_packet.json",
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_final_live_approval_packet_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        write_final_live_approval_packet(
            tmp_path,
            packet_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name=str(outside),
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_final_live_approval_packet_write_helper_blocks_url_path(tmp_path: Path) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        write_final_live_approval_packet(
            tmp_path,
            packet_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="https://example.invalid/final_live_approval_packet.json",
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_final_live_approval_packet_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        write_final_live_approval_packet(
            tmp_path,
            packet_summary(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="unexpected.json",
        )

    assert_failure(exc_info, "REPORT_ERROR")


def test_final_live_approval_packet_write_requires_pre_and_post_scan(tmp_path: Path) -> None:
    with pytest.raises(P3TApprovalPacketError) as pre_exc:
        write_final_live_approval_packet(tmp_path, packet_summary(), pre_scan=None, post_scan={"ok": True})
    with pytest.raises(P3TApprovalPacketError) as post_exc:
        write_final_live_approval_packet(tmp_path, packet_summary(), pre_scan={"ok": True}, post_scan=None)

    assert_failure(pre_exc, "CONFIG_ERROR")
    assert_failure(post_exc, "CONFIG_ERROR")


def test_final_live_approval_packet_rejects_scan_failure() -> None:
    inputs = p3t_inputs()

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        build_final_live_approval_packet(
            pre_live_package_manifest=inputs["pre_live_package_manifest"],
            approval_package_summary=inputs["approval_package"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
            artifact_safety_summary={"ok": False},
            runtime_flags_summary=inputs["runtime_flags_summary"],
            rollback_plan_summary=inputs["rollback_plan_summary"],
            test_evidence_summary=inputs["test_evidence_summary"],
            human_decision_summary=inputs["human_decision_summary"],
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_default_runtime_path_does_not_create_final_live_approval_packet(tmp_path: Path) -> None:
    assert final_live_approval_packet_default_runtime_creation_enabled() is False
    assert not (tmp_path / FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME).exists()
    assert not Path(FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME).exists()
