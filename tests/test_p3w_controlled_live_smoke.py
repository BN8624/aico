# P3W controlled live smoke 설정과 opt-in 경계를 검증한다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.controlled_live_smoke import (
    P3W_CONFIRM_PHRASE,
    P3W_TOY_MISSION,
    P3WLiveSmokeError,
    build_p3w_live_smoke_config,
    build_toy_live_smoke_mission,
    p3w_default_runtime_creation_enabled,
    read_single_p3w_key_value,
    run_controlled_single_call_live_smoke,
    validate_p3w_live_smoke_config,
    validate_provider_model_key_slot_selection,
    validate_toy_live_smoke_mission,
)


def config(**overrides: object):
    data = {
        "provider": "google_gemini",
        "model": "gemini-live-smoke-test",
        "key_slot": "worker_1",
        "confirm_phrase": P3W_CONFIRM_PHRASE,
        "live_smoke_opt_in": True,
        "run_id": "p3w-test",
    }
    data.update(overrides)
    return build_p3w_live_smoke_config(**data)


def test_p3w_config_validates_one_provider_model_key_slot() -> None:
    validate_p3w_live_smoke_config(config())


@pytest.mark.parametrize(
    ("field", "value", "failure_type"),
    [
        ("provider", ["google_gemini", "other"], "CONFIG_ERROR"),
        ("model", ["gemini-a", "gemini-b"], "CONFIG_ERROR"),
        ("key_slot", ["worker_1", "worker_2"], "SECURITY_BLOCKED"),
    ],
)
def test_p3w_config_rejects_multiple_provider_model_or_key_slots(
    field: str, value: object, failure_type: str
) -> None:
    payload = config().to_summary()
    payload[field] = value
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_provider_model_key_slot_selection(payload)
    assert exc_info.value.failure_type == failure_type


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key_slot", "reserve_1"),
        ("fallback_provider", "google_gemini"),
        ("provider_rotation_allowed", True),
        ("key_rotation_allowed", True),
    ],
)
def test_p3w_config_rejects_reserve_fallback_and_rotation(field: str, value: object) -> None:
    payload = config().to_summary()
    payload[field] = value
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_provider_model_key_slot_selection(payload)
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


@pytest.mark.parametrize(
    ("field", "value", "failure_type"),
    [
        ("max_model_calls", 2, "BUDGET_EXCEEDED"),
        ("retry_allowed", True, "SECURITY_BLOCKED"),
        ("reserve_allowed", True, "SECURITY_BLOCKED"),
        ("fallback_allowed", True, "SECURITY_BLOCKED"),
        ("second_call_allowed", True, "SECURITY_BLOCKED"),
        ("worker_file_write_allowed", True, "SECURITY_BLOCKED"),
        ("worker_shell_allowed", True, "SECURITY_BLOCKED"),
        ("web_allowed", True, "SECURITY_BLOCKED"),
        ("repo_clone_allowed", True, "SECURITY_BLOCKED"),
        ("github_allowed", True, "SECURITY_BLOCKED"),
        ("parallel_allowed", True, "SECURITY_BLOCKED"),
    ],
)
def test_p3w_config_rejects_opened_permissions(field: str, value: object, failure_type: str) -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_p3w_live_smoke_config(config(**{field: value}))
    assert exc_info.value.failure_type == failure_type


def test_p3w_opt_in_missing_does_not_call_provider(tmp_path: Path) -> None:
    calls: list[str] = []
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(
            provider="google_gemini",
            model="gemini-live-smoke-test",
            key_slot="worker_1",
            live_smoke_opt_in=False,
        ),
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(key) or "should not happen",
    )
    assert calls == []
    assert result.actual_provider_call_count == 0
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"


def test_p3w_bad_confirm_phrase_does_not_call_provider(tmp_path: Path) -> None:
    calls: list[str] = []
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(
            provider="google_gemini",
            model="gemini-live-smoke-test",
            key_slot="worker_1",
            confirm_phrase="go",
            live_smoke_opt_in=True,
        ),
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(key) or "should not happen",
    )
    assert calls == []
    assert result.actual_provider_call_count == 0
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"


@pytest.mark.parametrize("missing", ["provider", "model", "key_slot"])
def test_p3w_missing_provider_model_or_key_slot_does_not_call_provider(tmp_path: Path, missing: str) -> None:
    calls: list[str] = []
    kwargs = {"provider": "google_gemini", "model": "gemini-live-smoke-test", "key_slot": "worker_1"}
    kwargs[missing] = ""
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(
            **kwargs,
            confirm_phrase=P3W_CONFIRM_PHRASE,
            live_smoke_opt_in=True,
        ),
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(key) or "should not happen",
    )
    assert calls == []
    assert result.actual_provider_call_count == 0
    assert result.failure_type == "CONFIG_ERROR"


def test_key_loading_boundary_reads_only_one_key_slot_in_controlled_mode() -> None:
    loaded = read_single_p3w_key_value("worker_1", env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"})
    assert loaded.key_slot == "worker_1"
    assert loaded.key_value == "test-key-for-fake-provider"
    assert loaded.key_fingerprint_masked.startswith("sha256:")
    assert "test-key" not in loaded.key_fingerprint_masked


def test_key_loading_boundary_does_not_serialize_raw_key() -> None:
    loaded = read_single_p3w_key_value("worker_1", env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"})
    assert "test-key-for-fake-provider" not in repr(loaded.key_fingerprint_masked)


@pytest.mark.parametrize("slot", ["reserve_1", ("worker_1", "worker_2")])
def test_key_loading_boundary_rejects_reserve_or_multiple_key_reads(slot: object) -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        read_single_p3w_key_value(slot, env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"})  # type: ignore[arg-type]
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


def test_toy_mission_validator_accepts_tiny_text_mission() -> None:
    assert build_toy_live_smoke_mission() == P3W_TOY_MISSION
    validate_toy_live_smoke_mission(P3W_TOY_MISSION)


@pytest.mark.parametrize(
    "mission",
    [
        "Edit a file.",
        "Run a shell command.",
        "Search the web.",
        "Read a secret env key.",
    ],
)
def test_toy_mission_validator_rejects_forbidden_missions(mission: str) -> None:
    with pytest.raises(P3WLiveSmokeError):
        validate_toy_live_smoke_mission(mission)


def test_default_runtime_path_does_not_create_p3w_live_smoke(tmp_path: Path) -> None:
    assert p3w_default_runtime_creation_enabled() is False
    assert not (tmp_path / "call_attempt_summary.json").exists()
    assert not (tmp_path / "live_smoke_result.json").exists()
    assert not (tmp_path / "artifact_safety_report.json").exists()
