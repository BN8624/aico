# P3X raw leak 주입이 artifact safety에서 차단되는지 검증한다.
from __future__ import annotations

import pytest

from aico_v0.controlled_live_smoke import P3W_EXPECTED_PHRASE, P3WLiveSmokeError
from aico_v0.negative_safety import build_p3x_safe_config, validate_p3x_bad_artifact, validate_p3x_negative_config


def assert_artifact_blocked(payload: dict[str, object]) -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_p3x_bad_artifact(payload)
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_output_saved": True},
        {"raw_output": "full raw output"},
        {"provider_response": {"text": "raw"}},
        {"raw_model_output": "full raw model output"},
        {"raw_response_body": "body"},
        {"raw_headers": {"x": "raw"}},
        {"token_usage": {"input": 1}},
        {"masked_output_summary": {"output_preview_masked": "x" * 81}},
    ],
)
def test_raw_output_response_usage_and_overlong_masked_summary_block(payload: dict[str, object]) -> None:
    assert_artifact_blocked(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_key": "sk-secretsecretsecret"},
        {"raw_key_value": "sk-secretsecretsecret"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretsecret"},
        {"note": "Bearer abcdefghijklmnopqrstuvwxyz"},
        {"private": "-----BEGIN PRIVATE KEY-----\\nsecret\\n-----END PRIVATE KEY-----"},
        {"google_key": "AIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"},
        {"dump": "env dump AICO_WORKER_1_API_KEY=secretsecret"},
        {"provider_config": {"api_key": "secretsecret"}},
        {"raw_approval_phrase": "I approve AICO first live smoke for this run only"},
        {"endpoint_url": "https://generativelanguage.googleapis.com"},
    ],
)
def test_raw_key_env_bearer_private_key_dump_approval_and_url_block(payload: dict[str, object]) -> None:
    assert_artifact_blocked(payload)


def test_safe_masked_summary_passes() -> None:
    validate_p3x_bad_artifact(
        {
            "phase": "P3X",
            "masked_output_summary": {
                "output_present": True,
                "output_length": len(P3W_EXPECTED_PHRASE),
                "output_preview_masked": P3W_EXPECTED_PHRASE,
                "secret_scan_passed": True,
                "raw_output_saved": False,
            },
        }
    )


def test_raw_output_saved_true_blocks_at_config_level() -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_p3x_negative_config(build_p3x_safe_config(raw_output_saved=True))
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"
