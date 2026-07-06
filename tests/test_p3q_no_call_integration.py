# P3Q no-call 통합 요약이 실제 호출 권한을 열지 않는지 검증한다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.approval_package import build_approval_package
from aico_v0.approval_phrase import build_approval_phrase_hash, parse_approval_phrase
from aico_v0.artifact_safety import scan_artifacts
from aico_v0.no_call_integration import (
    NO_CALL_INTEGRATION_ARTIFACT_NAME,
    P3QNoCallIntegrationError,
    build_no_call_integration_summary,
    no_call_integration_default_runtime_creation_enabled,
    validate_no_call_integration,
    write_no_call_integration_summary,
)


def approval_phrase(**overrides: str) -> str:
    fields = {
        "provider": "google_gemini",
        "model": "gemini_flash",
        "key_slot": "worker_1",
        "max_model_calls": "1",
        "max_retries_per_call": "0",
        "max_runtime_seconds": "60",
        "allow_raw_output": "false",
    }
    fields.update(overrides)
    return "\n".join(
        [
            "I approve AICO first live smoke for this run only:",
            f"provider = {fields['provider']}",
            f"model = {fields['model']}",
            f"key_slot = {fields['key_slot']}",
            f"max_model_calls = {fields['max_model_calls']}",
            f"max_retries_per_call = {fields['max_retries_per_call']}",
            f"max_runtime_seconds = {fields['max_runtime_seconds']}",
            f"allow_raw_output = {fields['allow_raw_output']}",
        ]
    )


def approval_package_payload(run_id: str = "run-p3q-001") -> dict[str, object]:
    phrase = approval_phrase()
    parsed = parse_approval_phrase(phrase)
    digest = build_approval_phrase_hash(phrase)
    return build_approval_package(parsed=parsed, run_id=run_id, approval_phrase_hash=digest).to_summary()


def final_gate_payload(run_id: str = "run-p3q-001", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "run_id": run_id,
        "status": "ready_for_review",
        "live_call_allowed": False,
        "model_call_count": 0,
        "raw_output_saved": False,
        "errors": [],
    }
    payload.update(overrides)
    return payload


def runtime_flags_summary() -> dict[str, object]:
    return {
        "AICO_ENABLE_REAL_PROVIDER": "true",
        "AICO_ALLOW_LIVE_CALLS": "true",
        "AICO_ALLOW_FIRST_LIVE_SMOKE": "true",
        "source": "injected_metadata_only",
    }


def safe_summary(**overrides: object):
    return build_no_call_integration_summary(
        approval_package=approval_package_payload(),
        final_live_gate_result=final_gate_payload(),
        runtime_flags_summary=runtime_flags_summary(),
        artifact_safety_summary={"ok": True},
        **overrides,
    )


def assert_failure(exc_info: pytest.ExceptionInfo[P3QNoCallIntegrationError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_no_call_integration_validates_safe_approval_package_and_final_gate_linkage() -> None:
    summary = safe_summary(status="ready_for_review").to_summary()

    assert summary["status"] == "ready_for_review"
    assert summary["ready_for_review"] is True
    assert summary["approval_package_ref"] == "approval_package.json"
    assert summary["final_gate_result_ref"] == "final_live_gate_result.json"
    assert summary["provider"] == "google_gemini"
    assert summary["model"] == "gemini_flash"
    assert summary["key_slot"] == "worker_1"
    assert summary["artifact_safety_status"] == "pass"
    assert len(summary["activation_guards"]) == 4


def test_no_call_integration_keeps_all_no_call_fields_false_or_zero() -> None:
    summary = safe_summary().to_summary()

    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["actual_api_call_count"] == 0
    assert summary["actual_llm_call_count"] == 0
    assert summary["actual_key_value_read_count"] == 0
    assert summary["actual_sdk_import_count"] == 0
    assert summary["actual_network_call_count"] == 0
    assert summary["actual_live_smoke_count"] == 0


@pytest.mark.parametrize(
    ("payload_update", "failure_type"),
    [
        ({"status": "success"}, "SECURITY_BLOCKED"),
        ({"status": "api_success"}, "SECURITY_BLOCKED"),
        ({"live_call_allowed": True}, "SECURITY_BLOCKED"),
        ({"model_call_count": 1}, "SECURITY_BLOCKED"),
        ({"raw_output_saved": True}, "SECURITY_BLOCKED"),
        ({"raw_output": "blocked"}, "SECURITY_BLOCKED"),
        ({"raw_key": "sk-p3q-raw-key-value"}, "SECURITY_BLOCKED"),
        ({"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"}, "SECURITY_BLOCKED"),
        ({"endpoint_url": "https://example.invalid"}, "SECURITY_BLOCKED"),
        ({"approval_phrase": approval_phrase()}, "SECURITY_BLOCKED"),
    ],
)
def test_no_call_integration_rejects_live_or_raw_fields(payload_update: dict[str, object], failure_type: str) -> None:
    payload = safe_summary().to_summary()
    payload.update(payload_update)

    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        validate_no_call_integration(payload)

    assert_failure(exc_info, failure_type)


@pytest.mark.parametrize("field", ["approval_package_ref", "final_gate_result_ref", "approval_phrase_hash"])
def test_no_call_integration_rejects_missing_linkage_fields(field: str) -> None:
    payload = safe_summary().to_summary()
    payload.pop(field)

    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        validate_no_call_integration(payload)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_no_call_integration_rejects_run_id_mismatch() -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_no_call_integration_summary(
            approval_package=approval_package_payload("run-a"),
            final_live_gate_result=final_gate_payload("run-b"),
            runtime_flags_summary=runtime_flags_summary(),
            artifact_safety_summary={"ok": True},
        )

    assert_failure(exc_info, "CONFIG_ERROR")


def test_no_call_integration_artifact_safety_accepts_safe_summary() -> None:
    summary = safe_summary().to_summary()
    scan = scan_artifacts({NO_CALL_INTEGRATION_ARTIFACT_NAME: summary})

    assert scan.ok


def test_no_call_integration_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    summary = safe_summary()
    path = write_no_call_integration_summary(tmp_path, summary)

    assert path == tmp_path / NO_CALL_INTEGRATION_ARTIFACT_NAME
    assert path.exists()
    assert no_call_integration_default_runtime_creation_enabled() is False


def test_no_call_integration_default_runtime_path_creates_no_artifacts(tmp_path: Path) -> None:
    assert no_call_integration_default_runtime_creation_enabled() is False
    assert not (tmp_path / NO_CALL_INTEGRATION_ARTIFACT_NAME).exists()
    assert not (tmp_path / "approval_package.json").exists()

