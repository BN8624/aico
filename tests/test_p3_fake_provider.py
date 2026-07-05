# AICO P3A fake-provider 계층의 API worker 규칙을 검증한다.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aico_v0.p3_fake_provider import P3ABudget, run_p3a_fake_provider

MISSION = "Run P3A with fake provider only."
RAW_SECRET = "sk-p3a-fake-secret-value"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def all_run_text(run_dir: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in run_dir.rglob("*") if path.is_file())


def api_events(run_dir: Path) -> list[dict]:
    return [event for event in read_jsonl(run_dir / "run_log.jsonl") if event["event_type"] == "FAKE_PROVIDER_CALL"]


def key_slots(run_dir: Path) -> list[str]:
    return [event["key_slot"] for event in api_events(run_dir)]


def test_p3_document_priority_places_p3_above_v0() -> None:
    text = Path("AICO_P3_CANON.md").read_text(encoding="utf-8")

    assert text.index("2. AICO_P3_CANON.md") < text.index("3. AICO_V0_CANON.md")


def test_p3a_happy_path_uses_expected_slots_without_reserve(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="happy", run_id="happy", runs_root=tmp_path)
    slots = key_slots(result.run_dir)

    assert result.status == "PASS"
    assert result.failure_type is None
    assert result.fake_model_call_count == 6
    assert result.actual_api_call_count == 0
    assert result.actual_llm_call_count == 0
    assert slots == ["manager_1", "worker_1", "worker_2", "worker_3", "worker_4", "auditor_1"]
    assert "reserve_1" not in slots
    assert (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()


def test_raw_api_key_never_appears_and_key_slot_is_logged(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="security_leak",
        run_id="security-leak",
        runs_root=tmp_path,
    )
    logs = read_jsonl(result.run_dir / "run_log.jsonl")

    assert result.failure_type == "SECURITY_BLOCKED"
    assert RAW_SECRET not in all_run_text(result.run_dir)
    assert any(event["key_slot"] == "worker_1" for event in logs)
    assert all(event["key_slot"] != RAW_SECRET for event in logs)


@pytest.mark.parametrize(
    ("scenario", "failure_type"),
    [
        ("timeout", "MODEL_ERROR"),
        ("rate_limited_429", "MODEL_ERROR"),
        ("server_error_500", "MODEL_ERROR"),
        ("provider_unavailable", "MODEL_ERROR"),
        ("no_response", "MODEL_ERROR"),
        ("non_json_response", "SCHEMA_ERROR"),
        ("schema_invalid_json", "SCHEMA_ERROR"),
        ("schema_valid_empty", "WORKER_BAD_OUTPUT"),
    ],
)
def test_provider_failure_mapping(tmp_path: Path, scenario: str, failure_type: str) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario=scenario, run_id=scenario, runs_root=tmp_path)
    logs = read_jsonl(result.run_dir / "run_log.jsonl")

    assert result.status == "FAIL"
    assert result.failure_type == failure_type
    assert any(event["failure_type"] == failure_type for event in logs if event["status"] == "failure")
    assert not (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()


def test_no_provider_response_creates_no_worker_result_and_logs_model_error(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="no_response", run_id="no-response", runs_root=tmp_path)

    assert result.failure_type == "MODEL_ERROR"
    assert not (result.run_dir / "worker_results.jsonl").exists()
    assert any(event["failure_type"] == "MODEL_ERROR" for event in read_jsonl(result.run_dir / "run_log.jsonl"))


def test_security_leak_does_not_retry_or_use_reserve(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="security_leak",
        run_id="security-no-retry",
        runs_root=tmp_path,
    )

    assert result.failure_type == "SECURITY_BLOCKED"
    assert "reserve_1" not in key_slots(result.run_dir)


def test_reserve_is_used_only_after_worker_model_error(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="reserve_recovery",
        run_id="reserve-recovery",
        runs_root=tmp_path,
    )
    logs = read_jsonl(result.run_dir / "run_log.jsonl")

    assert result.status == "PASS"
    assert result.fake_model_call_count == 7
    assert "reserve_1" in key_slots(result.run_dir)
    reserve_event = next(event for event in logs if event["key_slot"] == "reserve_1")
    assert reserve_event["parent_event_id"] == "worker_2:MODEL_ERROR"
    worker_results = read_jsonl(result.run_dir / "worker_results.jsonl")
    assert any(row["payload"].get("recovered_from") == "worker_2" for row in worker_results)


def test_retry_and_reserve_calls_count_toward_max_model_calls(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="reserve_recovery",
        run_id="reserve-budget",
        runs_root=tmp_path,
        budget=P3ABudget(max_model_calls=6),
    )

    assert result.failure_type == "BUDGET_EXCEEDED"
    assert result.fake_model_call_count == 6
    assert "reserve_1" in key_slots(result.run_dir)
    assert not (result.run_dir / "audit_report.json").exists()


def test_max_model_calls_exceeded_becomes_budget_exceeded(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="happy",
        run_id="budget-exceeded",
        runs_root=tmp_path,
        budget=P3ABudget(max_model_calls=2),
    )

    assert result.failure_type == "BUDGET_EXCEEDED"
    assert result.fake_model_call_count == 2
    assert any(event["failure_type"] == "BUDGET_EXCEEDED" for event in read_jsonl(result.run_dir / "run_log.jsonl"))


def test_max_consecutive_model_errors_is_enforced(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="timeout",
        run_id="consecutive-model-errors",
        runs_root=tmp_path,
        budget=P3ABudget(max_consecutive_model_errors=1),
    )

    assert result.failure_type == "BUDGET_EXCEEDED"
    assert any(event["failure_type"] == "BUDGET_EXCEEDED" for event in read_jsonl(result.run_dir / "run_log.jsonl"))


def test_malformed_response_raw_output_is_not_saved_unmasked(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="non_json_response", run_id="non-json", runs_root=tmp_path)

    assert result.failure_type == "SCHEMA_ERROR"
    assert "not-json <<fixture>>" not in all_run_text(result.run_dir)


def test_masked_raw_output_and_raw_output_saved_defaults(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="happy", run_id="mask-defaults", runs_root=tmp_path)
    worker_results = read_jsonl(result.run_dir / "worker_results.jsonl")

    assert worker_results
    assert all("masked_raw_output" in row for row in worker_results)
    assert all(row["raw_output_saved"] is False for row in worker_results)
    assert all("raw_output" not in row for row in worker_results)


def test_final_report_and_failed_draft_remain_mutually_exclusive(tmp_path: Path) -> None:
    for scenario in ("happy", "timeout", "schema_valid_empty"):
        result = run_p3a_fake_provider(mission_text=MISSION, scenario=scenario, run_id=f"exclusive-{scenario}", runs_root=tmp_path)
        assert not ((result.run_dir / "final_report.md").exists() and (result.run_dir / "failed_draft.md").exists())


def test_ceo_report_exists_or_report_error_is_logged(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="timeout", run_id="ceo-report", runs_root=tmp_path)
    logs = read_jsonl(result.run_dir / "run_log.jsonl")

    assert (result.run_dir / "ceo_report.md").exists() or any(event["failure_type"] == "REPORT_ERROR" for event in logs)


def test_semantic_preflight_and_repair_loop_are_not_executed(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="happy", run_id="no-semantic-repair", runs_root=tmp_path)

    assert result.semantic_preflight_executed is False
    assert result.repair_loop_executed is False
    assert not list(result.run_dir.rglob("*semantic_preflight*"))
    assert not list(result.run_dir.rglob("*repair*"))


def test_worker_cannot_request_shell_or_file_edit(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(mission_text=MISSION, scenario="happy", run_id="permissions", runs_root=tmp_path)
    work_orders = read_json(result.run_dir / "work_orders.json")["work_orders"]

    assert all(order["can_edit_files"] is False for order in work_orders)
    assert all(order["can_run_shell"] is False for order in work_orders)


@pytest.mark.parametrize("mission", ["Use https://example.com", "run web search", "repo clone this project"])
def test_external_url_web_search_and_repo_clone_are_blocked(tmp_path: Path, mission: str) -> None:
    result = run_p3a_fake_provider(mission_text=mission, scenario="happy", run_id=mission.split()[0], runs_root=tmp_path)

    assert result.failure_type == "SECURITY_BLOCKED"
    assert not any(event["event_type"] == "FAKE_PROVIDER_CALL" for event in read_jsonl(result.run_dir / "run_log.jsonl"))


def test_unrecovered_api_failure_preserves_partial_worker_results_and_stops_downstream(tmp_path: Path) -> None:
    result = run_p3a_fake_provider(
        mission_text=MISSION,
        scenario="unrecovered_model_error",
        run_id="mid-flight",
        runs_root=tmp_path,
    )
    worker_results = read_jsonl(result.run_dir / "worker_results.jsonl")

    assert result.failure_type == "MODEL_ERROR"
    assert [row["work_id"] for row in worker_results] == ["wo-1", "wo-2"]
    assert not (result.run_dir / "manager_summary.json").exists()
    assert not (result.run_dir / "audit_report.json").exists()
    assert not (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()


def test_p3a_has_no_forbidden_external_capability_imports() -> None:
    source = Path("aico_v0/p3_fake_provider.py").read_text(encoding="utf-8").lower()
    forbidden = ("requests", "httpx", "urllib", "socket", "subprocess", "webbrowser", "openai", "anthropic")

    assert not any(name in source for name in forbidden)


def test_agents_and_claude_are_byte_identical() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
