# P3P no-call 스켈레톤이 artifact safety와 offline pytest 정책을 유지하는지 검증한다.
from __future__ import annotations

from pathlib import Path

from aico_v0.activation_guards import assert_p3p_no_call_safety
from aico_v0.approval_package import build_approval_package
from aico_v0.approval_phrase import build_approval_phrase_hash, parse_approval_phrase
from aico_v0.artifact_safety import scan_artifacts

RAW_SECRET = "sk-" + "p3p-no-call-secret-value"


def approval_phrase() -> str:
    return "\n".join(
        [
            "I approve AICO first live smoke for this run only:",
            "provider = google_gemini",
            "model = user-approved-model",
            "key_slot = worker_1",
            "max_model_calls = 1",
            "max_retries_per_call = 0",
            "max_runtime_seconds = 60",
            "allow_raw_output = false",
        ]
    )


def safe_approval_package_payload() -> dict[str, object]:
    phrase = approval_phrase()
    parsed = parse_approval_phrase(phrase)
    digest = build_approval_phrase_hash(phrase)
    return build_approval_package(parsed=parsed, run_id="run-p3p-no-call", approval_phrase_hash=digest).to_summary()


def test_artifact_safety_accepts_safe_approval_package_and_no_call_summary() -> None:
    result = scan_artifacts(
        {
            "approval_package": safe_approval_package_payload(),
            "p3p_no_call_summary": assert_p3p_no_call_safety(),
        }
    )

    assert result.ok is True


def test_artifact_safety_rejects_approval_package_with_raw_key_or_endpoint() -> None:
    for unsafe_update in (
        {"model": RAW_SECRET},
        {"endpoint_url": "https://generativelanguage.googleapis.com"},
        {"raw_output": "unmasked"},
        {"raw_output_saved": True},
        {"live_call_allowed": True},
        {"model_call_count_before_execution": 1},
    ):
        payload = safe_approval_package_payload()
        payload.update(unsafe_update)
        result = scan_artifacts({"approval_package": payload})

        assert result.ok is False
        assert result.failure_type == "SECURITY_BLOCKED"


def test_p3p_no_call_summary_records_zero_work() -> None:
    summary = assert_p3p_no_call_safety()

    assert summary == {
        "live_call_allowed": False,
        "model_call_count": 0,
        "raw_output_saved": False,
        "actual_api_call_count": 0,
        "actual_llm_call_count": 0,
        "actual_key_value_read_count": 0,
        "actual_sdk_import_count": 0,
        "actual_network_call_count": 0,
        "actual_live_smoke_count": 0,
    }


def test_default_pytest_remains_offline_only_for_p3p() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "live_smoke" in pyproject
    assert "live_provider" in pyproject


def test_approval_package_is_not_created_in_workspace_by_default() -> None:
    assert not Path("approval_package.json").exists()
    assert not Path("runs/approval_package.json").exists()
