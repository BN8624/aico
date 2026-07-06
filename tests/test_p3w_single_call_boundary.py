# P3W single-call provider boundary와 counter 불변식을 검증한다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.controlled_live_smoke import (
    P3W_CONFIRM_PHRASE,
    P3W_EXPECTED_PHRASE,
    P3WLiveSmokeError,
    build_call_attempt_summary,
    build_masked_output_summary,
    build_p3w_live_smoke_config,
    import_selected_provider_sdk,
    run_controlled_single_call_live_smoke,
    validate_call_attempt_summary,
)


def config(**overrides: object):
    data = {
        "provider": "google_gemini",
        "model": "gemini-live-smoke-test",
        "key_slot": "worker_1",
        "confirm_phrase": P3W_CONFIRM_PHRASE,
        "live_smoke_opt_in": True,
        "run_id": "p3w-call-test",
    }
    data.update(overrides)
    return build_p3w_live_smoke_config(**data)


def test_single_call_boundary_increments_count_zero_to_one(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []
    result = run_controlled_single_call_live_smoke(
        config=config(),
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append((model, mission)) or P3W_EXPECTED_PHRASE,
    )
    assert len(calls) == 1
    assert result.actual_provider_call_count == 1
    assert result.call_model_count_before == 0
    assert result.call_model_count_after == 1
    assert result.model_call_count_before == 0
    assert result.model_call_count_after == 1
    assert result.retry_count == 0
    assert result.reserve_used is False
    assert result.fallback_used is False
    assert result.second_call_attempted is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("call_model_count_after", 2),
        ("model_call_count_after", 2),
        ("retry_count", 1),
        ("reserve_used", True),
        ("fallback_used", True),
        ("second_call_attempted", True),
    ],
)
def test_call_attempt_summary_rejects_expanded_call_boundary(field: str, value: object) -> None:
    payload = build_call_attempt_summary(
        config=config(),
        key_fingerprint_masked="sha256:abcd1234...ffff",
        call_model_count_after=1,
        model_call_count_after=1,
        failure_type=None,
    )
    payload[field] = value
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_call_attempt_summary(payload)
    assert exc_info.value.failure_type in {"SECURITY_BLOCKED", "BUDGET_EXCEEDED"}


def test_provider_failure_does_not_retry_and_writes_safe_failure_artifact(tmp_path: Path) -> None:
    calls: list[int] = []

    def failing_provider(key: str, model: str, mission: str) -> str:
        calls.append(1)
        raise RuntimeError("provider failed without raw output")

    result = run_controlled_single_call_live_smoke(
        config=config(),
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
        provider_caller=failing_provider,
    )
    assert len(calls) == 1
    assert result.status == "single_call_failed_safely"
    assert result.failure_type == "MODEL_ERROR"
    assert result.call_model_count_after == 1
    assert result.model_call_count_after == 1
    assert result.retry_count == 0
    assert (tmp_path / "live_smoke_result.json").exists()


def test_masked_summary_builder_does_not_include_full_raw_output() -> None:
    raw = P3W_EXPECTED_PHRASE + " " + ("x" * 200)
    summary = build_masked_output_summary(raw)
    assert summary["output_present"] is True
    assert summary["output_length"] == len(raw)
    assert len(str(summary["output_preview_masked"])) <= 80
    assert summary["raw_output_saved"] is False
    assert raw not in str(summary)


def test_masked_summary_builder_secret_scans_preview() -> None:
    summary = build_masked_output_summary("sk-secretsecretsecret should not persist")
    assert summary["raw_output_saved"] is False
    assert "sk-secret" not in str(summary)


def test_sdk_boundary_allows_only_selected_provider_import(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModule:
        pass

    imported: list[str] = []

    def fake_import(name: str):
        imported.append(name)
        return FakeModule()

    monkeypatch.setattr("aico_v0.controlled_live_smoke.importlib.import_module", fake_import)
    assert import_selected_provider_sdk("google_gemini").__class__ is FakeModule
    assert imported == ["google.genai"]


def test_sdk_boundary_rejects_multiple_or_unknown_provider_sdk_imports() -> None:
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        import_selected_provider_sdk("unknown_provider")
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"
