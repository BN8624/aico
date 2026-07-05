# P3E artifact safety scanner가 raw secret과 raw output 흔적을 차단하는지 검증한다.
from __future__ import annotations

from aico_v0.artifact_safety import scan_artifact_text, scan_artifacts

RAW_KEY = "sk-" + "p3e-artifact-secret-value"


def assert_blocked(text: str, reason_fragment: str) -> None:
    result = scan_artifact_text("artifact.md", text)

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"
    assert any(reason_fragment in finding.reason for finding in result.findings)


def test_artifact_safety_scan_detects_raw_key_like_value() -> None:
    assert_blocked(f"secret={RAW_KEY}", "raw key-like")


def test_artifact_safety_scan_detects_env_var_value_pattern() -> None:
    assert_blocked("AICO_WORKER_1_API_KEY=actual-secret-value", "env var value")


def test_artifact_safety_scan_detects_bearer_token_pattern() -> None:
    assert_blocked("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "bearer token")


def test_artifact_safety_scan_detects_private_key_block() -> None:
    assert_blocked("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----", "private key")


def test_artifact_safety_scan_detects_unmasked_raw_provider_output_marker() -> None:
    assert_blocked("raw_provider_output: provider text", "raw provider output")


def test_artifact_safety_scan_detects_raw_output_saved_true() -> None:
    result = scan_artifacts({"worker_results.jsonl": {"raw_output_saved": True}})

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"
    assert any("raw_output_saved=True" in finding.reason for finding in result.findings)


def test_artifact_safety_scan_detects_raw_output_field() -> None:
    result = scan_artifacts({"worker_results.jsonl": {"raw_output": "unmasked"}})

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"
    assert any("raw_output field" in finding.reason for finding in result.findings)


def test_artifact_safety_scan_passes_masked_raw_output_and_safe_metadata() -> None:
    result = scan_artifacts(
        {
            "worker_results.jsonl": {
                "masked_raw_output": "[MASKED_SECRET]",
                "mask_reason": "secret masked",
                "raw_output_saved": False,
                "key_slot": "worker_1",
                "env_var_name": "AICO_WORKER_1_API_KEY",
            }
        }
    )

    assert result.ok is True
    assert result.failure_type is None


def test_artifact_safety_scan_rejects_final_report_with_raw_secret() -> None:
    result = scan_artifacts({"final_report.md": f"raw {RAW_KEY}"})

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"


def test_artifact_safety_scan_rejects_failed_draft_with_raw_secret() -> None:
    result = scan_artifacts({"failed_draft.md": f"raw {RAW_KEY}"})

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"


def test_artifact_safety_scan_detects_final_and_failed_draft_coexistence_as_report_error() -> None:
    result = scan_artifacts({"final_report.md": "safe", "failed_draft.md": "safe"})

    assert result.ok is False
    assert result.failure_type == "REPORT_ERROR"
    assert any("both generated" in finding.reason for finding in result.findings)


def test_artifact_safety_scan_missing_becomes_config_error() -> None:
    result = scan_artifacts(None)

    assert result.ok is False
    assert result.failure_type == "CONFIG_ERROR"


def test_artifact_safety_scan_result_is_run_log_ready() -> None:
    result = scan_artifacts({"final_report.md": "safe"})
    event = result.to_run_log_event()

    assert event["event_type"] == "ARTIFACT_SAFETY_SCAN"
    assert event["status"] == "ok"
    assert event["failure_type"] is None
