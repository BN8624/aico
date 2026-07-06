# P3S pre-live package manifest가 실제 호출 없이 안전한 요약만 허용하는지 검증합니다.
from __future__ import annotations

import pytest

from aico_v0.live_execution_boundary import build_no_execute_dry_run
from aico_v0.no_call_integration import build_no_call_integration_summary
from aico_v0.pre_live_package import (
    P3SPreLivePackageError,
    aggregate_package_failure_type,
    assemble_pre_live_package,
    build_pre_live_package_manifest,
    validate_consistency,
    validate_no_call_invariants,
    validate_package_item,
    validate_pre_live_package,
)

from tests.test_p3q_no_call_integration import (
    approval_package_payload,
    final_gate_payload,
    runtime_flags_summary,
)


def p3s_inputs(run_id: str = "run-p3s-001") -> dict[str, dict[str, object]]:
    approval = approval_package_payload(run_id)
    final_gate = final_gate_payload(run_id)
    final_gate["approval_phrase_hash"] = approval["approval_phrase_hash"]
    no_call = build_no_call_integration_summary(
        approval_package=approval,
        final_live_gate_result=final_gate,
        runtime_flags_summary=runtime_flags_summary(),
        artifact_safety_summary={"ok": True},
    ).to_summary()
    call_attempt = build_no_execute_dry_run(
        approval_package=approval,
        final_gate_result=final_gate,
        no_call_integration_summary=no_call,
    ).to_summary()
    return {
        "approval_package": approval,
        "final_live_gate_result": final_gate,
        "no_call_integration_summary": no_call,
        "call_attempt_summary": call_attempt,
        "runtime_flags_summary": runtime_flags_summary(),
        "rollback_plan_summary": {
            "retry_allowed": False,
            "reserve_allowed": False,
            "fallback_allowed": False,
            "second_call_allowed": False,
            "allowlist_widening_allowed": False,
            "key_slot_change_allowed": False,
            "raw_output_preservation_allowed": False,
            "review_required": True,
            "rollback_plan_ref": "rollback_plan_summary",
        },
    }


def manifest_summary(**overrides: object) -> dict[str, object]:
    inputs = p3s_inputs()
    manifest = build_pre_live_package_manifest(
        approval_package=inputs["approval_package"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        artifact_safety_summary={"ok": True},
        runtime_flags_summary=inputs["runtime_flags_summary"],
        rollback_plan_summary=inputs["rollback_plan_summary"],
        artifact_safety_post_scan={"ok": True},
        status="ready_for_review",
    ).to_summary()
    manifest.update(overrides)
    return manifest


def assert_failure(exc_info: pytest.ExceptionInfo[P3SPreLivePackageError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_pre_live_package_manifest_validates_safe_no_call_inputs() -> None:
    summary = manifest_summary()

    assert summary["status"] == "ready_for_review"
    assert summary["ready_for_review"] is True
    assert summary["created_for"] == "no_call_pre_live_package_only"
    assert summary["approval_package_ref"] == "approval_package.json"
    assert summary["no_call_integration_summary_ref"] == "no_call_integration_summary.json"
    assert summary["call_attempt_summary_ref"] == "call_attempt_summary.json"
    assert summary["final_gate_result_ref"] == "final_live_gate_result.json"
    assert {item["name"] for item in summary["package_items"]} >= {
        "approval_package",
        "no_call_integration_summary",
        "call_attempt_summary",
        "final_live_gate_result",
        "artifact_safety_report",
    }


def test_pre_live_package_keeps_no_call_fields_closed() -> None:
    summary = assemble_pre_live_package(**p3s_inputs()).to_summary()

    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["call_model_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["artifact_safety_pre_scan_status"] == "pass"
    assert summary["artifact_safety_post_scan_status"] == "pass"


@pytest.mark.parametrize(
    "status",
    ["success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"],
)
def test_pre_live_package_rejects_success_like_status(status: str) -> None:
    summary = manifest_summary(status=status)

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_pre_live_package(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "update",
    [
        {"live_call_allowed": True},
        {"model_call_count": 1},
        {"call_model_count": 1},
        {"raw_output_saved": True},
        {"raw_output": "blocked"},
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"endpoint_url": "https://example.invalid"},
        {"raw_key": "sk-p3s-raw-key-value"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
    ],
)
def test_pre_live_package_rejects_live_raw_provider_endpoint_and_secret_fields(update: dict[str, object]) -> None:
    summary = manifest_summary()
    summary.update(update)

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_pre_live_package(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "ref",
    ["../approval_package.json", "nested/../approval_package.json", "https://example.invalid/package.json", ""],
)
def test_package_item_rejects_unsafe_or_missing_refs(ref: str) -> None:
    item = dict(manifest_summary()["package_items"][0])
    item["ref"] = ref

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_package_item(item)

    assert exc_info.value.failure_type in {"SECURITY_BLOCKED", "CONFIG_ERROR"}


def test_pre_live_package_rejects_missing_required_item() -> None:
    summary = manifest_summary()
    summary["package_items"] = summary["package_items"][:-1]

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_pre_live_package(summary)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_package_rejects_required_item_not_scanned() -> None:
    summary = manifest_summary()
    item = dict(summary["package_items"][0])
    item["artifact_safety_status"] = "not_run"
    summary["package_items"][0] = item

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_pre_live_package(summary)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_package_rejects_required_item_scan_failure() -> None:
    summary = manifest_summary()
    item = dict(summary["package_items"][0])
    item["artifact_safety_status"] = "fail"
    summary["package_items"][0] = item

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_pre_live_package(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_pre_live_package_rejects_run_id_mismatch() -> None:
    inputs = p3s_inputs("run-a")
    inputs["final_live_gate_result"] = dict(inputs["final_live_gate_result"])
    inputs["final_live_gate_result"]["run_id"] = "run-b"

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_consistency(
            approval_package=inputs["approval_package"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_package_rejects_approval_phrase_hash_mismatch() -> None:
    inputs = p3s_inputs()
    inputs["final_live_gate_result"] = dict(inputs["final_live_gate_result"])
    inputs["final_live_gate_result"]["approval_phrase_hash"] = "a" * 64

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_consistency(
            approval_package=inputs["approval_package"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_package_rejects_missing_approval_phrase_hash() -> None:
    inputs = p3s_inputs()
    inputs["final_live_gate_result"] = dict(inputs["final_live_gate_result"])
    inputs["final_live_gate_result"].pop("approval_phrase_hash")

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_consistency(
            approval_package=inputs["approval_package"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_package_rejects_missing_artifact_reference() -> None:
    summary = manifest_summary(approval_package_ref="")

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_pre_live_package(summary)

    assert_failure(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize(
    "marker",
    [
        {"provider_sdk_imported": True},
        {"key_loaded": True},
        {"network_call": True},
        {"live_smoke_executed": True},
        {"retry_allowed": True},
        {"reserve_allowed": True},
        {"fallback_allowed": True},
        {"second_call_allowed": True},
        {"call_model_executed": True},
    ],
)
def test_no_call_invariants_reject_activation_execution_and_fallback_markers(marker: dict[str, object]) -> None:
    with pytest.raises(P3SPreLivePackageError) as exc_info:
        validate_no_call_invariants(marker)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_pre_live_failure_priority_prefers_security_blocked() -> None:
    assert aggregate_package_failure_type(["CONFIG_ERROR", "SECURITY_BLOCKED", "REPORT_ERROR"]) == "SECURITY_BLOCKED"
