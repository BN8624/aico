# P3W live smoke 산출물 safety schema를 검증한다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.controlled_live_smoke import (
    P3W_CONFIRM_PHRASE,
    P3W_EXPECTED_PHRASE,
    P3WLiveSmokeError,
    build_artifact_safety_report,
    build_call_attempt_summary,
    build_live_smoke_result,
    build_masked_output_summary,
    build_p3w_live_smoke_config,
    scan_p3w_artifacts,
    validate_live_smoke_result,
    write_artifact_safety_report,
    write_call_attempt_summary,
    write_live_smoke_result,
)


def config():
    return build_p3w_live_smoke_config(
        provider="google_gemini",
        model="gemini-live-smoke-test",
        key_slot="worker_1",
        confirm_phrase=P3W_CONFIRM_PHRASE,
        live_smoke_opt_in=True,
        run_id="p3w-artifact-test",
    )


def call_attempt(**overrides: object) -> dict[str, object]:
    payload = build_call_attempt_summary(
        config=config(),
        key_fingerprint_masked="sha256:abcd1234...ffff",
        call_model_count_after=1,
        model_call_count_after=1,
        failure_type=None,
    )
    payload.update(overrides)
    return payload


def live_result(**overrides: object) -> dict[str, object]:
    payload = build_live_smoke_result(
        config=config(),
        status="single_call_completed",
        call_model_count=1,
        model_call_count=1,
        failure_type=None,
        errors=(),
        masked_output_summary=build_masked_output_summary(P3W_EXPECTED_PHRASE),
    )
    payload.update(overrides)
    return payload


def test_call_attempt_summary_validates_safe_single_call_artifact() -> None:
    assert scan_p3w_artifacts({"call_attempt_summary.json": call_attempt()}).ok


@pytest.mark.parametrize(
    "update",
    [
        {"raw_key": "sk-secretsecretsecret"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretsecret"},
        {"raw_output": "full raw output"},
        {"provider_response": {"text": "raw"}},
        {"token_usage": {"input": 1}},
        {"endpoint_url": "https://generativelanguage.googleapis.com"},
    ],
)
def test_call_attempt_summary_rejects_raw_secret_output_response_usage_and_endpoint(update: dict[str, object]) -> None:
    scan = scan_p3w_artifacts({"call_attempt_summary.json": call_attempt(**update)})
    assert scan.ok is False
    assert scan.failure_type == "SECURITY_BLOCKED"


def test_live_smoke_result_validates_single_call_completed_and_failed_safely() -> None:
    validate_live_smoke_result(live_result(status="single_call_completed"))
    validate_live_smoke_result(live_result(status="single_call_failed_safely", failure_type="MODEL_ERROR"))


@pytest.mark.parametrize(
    "status",
    ["live_success", "provider_success", "api_success", "retry_success", "fallback_success", "reserve_success"],
)
def test_live_smoke_result_rejects_forbidden_success_statuses(status: str) -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_live_smoke_result(live_result(status=status))
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


@pytest.mark.parametrize(
    "update",
    [
        {"raw_key": "sk-secretsecretsecret"},
        {"raw_output": "full raw output"},
        {"provider_response": {"text": "raw"}},
        {"token_usage": {"input": 1}},
        {"call_model_count": 2},
        {"model_call_count": 2},
        {"retry_count": 1},
        {"reserve_used": True},
        {"fallback_used": True},
        {"second_call_attempted": True},
    ],
)
def test_artifact_safety_report_detects_forbidden_p3w_values(update: dict[str, object]) -> None:
    scan = scan_p3w_artifacts({"live_smoke_result.json": live_result(**update)})
    assert scan.ok is False
    assert scan.failure_type == "SECURITY_BLOCKED"


def test_post_call_scan_failure_maps_security_blocked() -> None:
    scan = scan_p3w_artifacts({"live_smoke_result.json": live_result(raw_output="raw")})
    report = build_artifact_safety_report(scan)
    assert report["status"] == "fail"
    assert report["failure_type"] == "SECURITY_BLOCKED"


def test_p3w_write_helpers_stay_inside_run_dir(tmp_path: Path) -> None:
    call_path = write_call_attempt_summary(tmp_path, call_attempt())
    live_path = write_live_smoke_result(tmp_path, live_result())
    report_path = write_artifact_safety_report(tmp_path, build_artifact_safety_report(scan_p3w_artifacts({})))
    assert call_path.parent == tmp_path.resolve()
    assert live_path.parent == tmp_path.resolve()
    assert report_path.parent == tmp_path.resolve()


def test_artifact_write_failure_maps_report_error(tmp_path: Path) -> None:
    blocked_file = tmp_path / "not-a-dir"
    blocked_file.write_text("", encoding="utf-8")
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        write_call_attempt_summary(blocked_file, call_attempt())
    assert exc_info.value.failure_type == "REPORT_ERROR"
