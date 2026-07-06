# P3T 사람 확인 checklist와 no-call 증거 summary가 실행 승인으로 변하지 않는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.final_live_approval_packet import (
    HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
    P3TApprovalPacketError,
    build_human_confirmation_checklist,
    build_no_call_evidence_summary,
    human_confirmation_checklist_default_runtime_creation_enabled,
    validate_human_confirmation_checklist,
    validate_no_call_evidence_summary,
    write_human_confirmation_checklist,
)


def assert_failure(exc_info: pytest.ExceptionInfo[P3TApprovalPacketError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_human_confirmation_checklist_validates_required_items() -> None:
    summary = build_human_confirmation_checklist(run_id="run-p3t-human").to_summary()

    validate_human_confirmation_checklist(summary)

    assert summary["human_confirmation_required"] is True
    assert summary["human_confirmation_status"] == "review_required"
    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["call_model_count"] == 0


def test_human_confirmation_checklist_acknowledged_still_does_not_approve_execution() -> None:
    summary = build_human_confirmation_checklist(
        run_id="run-p3t-human",
        all_items_acknowledged=True,
    ).to_summary()

    assert summary["all_items_acknowledged"] is True
    assert summary["human_confirmation_status"] == "review_required"
    assert summary["execution_allowed"] is False
    assert summary["live_call_allowed"] is False


@pytest.mark.parametrize("status", ["approved", "granted", "confirmed", "execution_approved", "live_approved"])
def test_human_confirmation_checklist_rejects_granted_statuses(status: str) -> None:
    summary = build_human_confirmation_checklist(run_id="run-p3t-human").to_summary()
    summary["human_confirmation_status"] = status

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_human_confirmation_checklist(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_human_confirmation_checklist_rejects_missing_required_item() -> None:
    summary = build_human_confirmation_checklist(run_id="run-p3t-human").to_summary()
    summary["items"] = tuple(summary["items"][:-1])

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_human_confirmation_checklist(summary)

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize(
    "update",
    [
        {"execution_allowed": True},
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"call_model_count": 1},
        {"raw_output": "blocked"},
        {"raw_key": "sk-p3t-human-raw-key-value"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
    ],
)
def test_human_confirmation_checklist_rejects_live_and_raw_fields(update: dict[str, object]) -> None:
    summary = build_human_confirmation_checklist(run_id="run-p3t-human").to_summary()
    summary.update(update)

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_human_confirmation_checklist(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_no_call_evidence_validates_safe_evidence() -> None:
    summary = build_no_call_evidence_summary("run-p3t-evidence").to_summary()

    validate_no_call_evidence_summary(summary)

    assert summary["pytest_passed"] is True
    assert summary["targeted_tests_passed"] is True
    assert summary["actual_api_call_zero"] is True
    assert summary["actual_call_model_execution_zero"] is True


@pytest.mark.parametrize(
    "field",
    [
        "actual_api_call_zero",
        "actual_llm_call_zero",
        "actual_key_use_zero",
        "actual_env_value_read_zero",
        "actual_provider_sdk_import_zero",
        "actual_network_call_zero",
        "actual_live_smoke_zero",
        "actual_call_model_execution_zero",
        "live_call_allowed_false",
        "model_call_count_zero",
        "call_model_count_zero",
    ],
)
def test_no_call_evidence_rejects_actual_call_evidence_not_zero(field: str) -> None:
    summary = build_no_call_evidence_summary("run-p3t-evidence").to_summary()
    summary[field] = False

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_no_call_evidence_summary(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("field", ["pytest_passed", "targeted_tests_passed"])
def test_no_call_evidence_rejects_failed_required_evidence(field: str) -> None:
    summary = build_no_call_evidence_summary("run-p3t-evidence").to_summary()
    summary[field] = False

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_no_call_evidence_summary(summary)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_no_call_evidence_rejects_missing_critical_evidence() -> None:
    summary = build_no_call_evidence_summary("run-p3t-evidence").to_summary()
    summary.pop("runtime_forbidden_import_ast_passed")

    with pytest.raises(P3TApprovalPacketError) as exc_info:
        validate_no_call_evidence_summary(summary)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_human_confirmation_checklist_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    checklist = build_human_confirmation_checklist(run_id="run-p3t-human")

    path = write_human_confirmation_checklist(tmp_path, checklist, pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME
    assert path.exists()


@pytest.mark.parametrize(
    "artifact_name",
    ["../human_confirmation_checklist.json", "https://example.invalid/human_confirmation_checklist.json"],
)
def test_human_confirmation_checklist_write_helper_blocks_unsafe_paths(tmp_path: Path, artifact_name: str) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        write_human_confirmation_checklist(
            tmp_path,
            build_human_confirmation_checklist(run_id="run-p3t-human"),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name=artifact_name,
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_human_confirmation_checklist_write_helper_maps_write_failure(tmp_path: Path) -> None:
    with pytest.raises(P3TApprovalPacketError) as exc_info:
        write_human_confirmation_checklist(
            tmp_path,
            build_human_confirmation_checklist(run_id="run-p3t-human"),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="unexpected.json",
        )

    assert_failure(exc_info, "REPORT_ERROR")


def test_human_confirmation_checklist_write_helper_requires_scans(tmp_path: Path) -> None:
    checklist = build_human_confirmation_checklist(run_id="run-p3t-human")

    with pytest.raises(P3TApprovalPacketError) as pre_exc:
        write_human_confirmation_checklist(tmp_path, checklist, pre_scan=None, post_scan={"ok": True})
    with pytest.raises(P3TApprovalPacketError) as post_exc:
        write_human_confirmation_checklist(tmp_path, checklist, pre_scan={"ok": True}, post_scan=None)

    assert_failure(pre_exc, "CONFIG_ERROR")
    assert_failure(post_exc, "CONFIG_ERROR")


def test_default_runtime_path_does_not_create_human_confirmation_checklist(tmp_path: Path) -> None:
    assert human_confirmation_checklist_default_runtime_creation_enabled() is False
    assert not (tmp_path / HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME).exists()
    assert not Path(HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME).exists()
