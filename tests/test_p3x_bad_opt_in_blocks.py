# P3X bad opt-in 경로가 provider 호출 없이 멈추는지 검증한다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.controlled_live_smoke import P3W_CONFIRM_PHRASE, build_p3w_live_smoke_config, run_controlled_single_call_live_smoke


def assert_zero_call_block(tmp_path: Path, **overrides: object) -> None:
    calls: list[int] = []
    base = {
        "provider": "google_gemini",
        "model": "gemma-4-31b-it",
        "key_slot": "worker_1",
        "confirm_phrase": P3W_CONFIRM_PHRASE,
        "live_smoke_opt_in": True,
        "run_id": "p3x-bad-opt-in",
    }
    base.update(overrides)
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(**base),
        env={},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(1) or "should not happen",
    )
    assert calls == []
    assert result.actual_provider_call_count == 0
    assert result.call_model_count_after == 0
    assert result.model_call_count_after == 0
    assert result.retry_count == 0
    assert result.reserve_used is False
    assert result.fallback_used is False
    assert result.second_call_attempted is False
    assert result.raw_output_saved is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"live_smoke_opt_in": False},
        {"confirm_phrase": "controlled-single-call "},
        {"confirm_phrase": "--execute"},
        {"confirm_phrase": "--live"},
        {"confirm_phrase": "--call-model"},
        {"provider": ""},
        {"model": ""},
        {"key_slot": ""},
    ],
)
def test_bad_opt_in_and_missing_required_fields_do_not_call_provider(tmp_path: Path, overrides: dict[str, object]) -> None:
    assert_zero_call_block(tmp_path, **overrides)


def test_live_smoke_env_opt_in_not_one_blocks(tmp_path: Path) -> None:
    calls: list[int] = []
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(
            env={
                "AICO_P3W_LIVE_SMOKE": "0",
                "AICO_P3W_PROVIDER": "google_gemini",
                "AICO_P3W_MODEL": "gemma-4-31b-it",
                "AICO_P3W_KEY_SLOT": "worker_1",
                "AICO_P3W_CONFIRM": P3W_CONFIRM_PHRASE,
            },
            run_id="p3x-bad-env-opt-in",
        ),
        env={},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(1) or "should not happen",
    )
    assert calls == []
    assert result.actual_provider_call_count == 0
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"
