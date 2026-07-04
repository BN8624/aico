# AICO v0 dry-run 하네스의 필수 시나리오를 검증한다.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aico_v0.harness import deterministic_preflight, run_dry_run


MISSION = "Build an offline AICO v0 dry-run harness with deterministic fixtures."
SCENARIOS = (
    "pass",
    "conditional",
    "fail",
    "needs_decision",
    "config_error",
    "budget_exceeded",
    "mid_flight_failure",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def all_run_text(run_dir: Path) -> str:
    chunks = []
    for path in run_dir.rglob("*"):
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_required_document_set_exists_and_agent_docs_are_identical() -> None:
    required = [
        "AICO_MASTER_CANON.md",
        "AICO_V0_CANON.md",
        "AGENTS.md",
        "CLAUDE.md",
        "HANDOFF.md",
        "CONTEXT_NOTES.md",
    ]
    for name in required:
        assert Path(name).is_file(), name
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_required_scenarios_are_deterministic_and_offline(tmp_path: Path, scenario: str) -> None:
    result = run_dry_run(
        mission_text=None if scenario == "config_error" else MISSION,
        scenario=scenario,
        run_id=f"test-{scenario}",
        runs_root=tmp_path,
    )

    assert result.run_dir.is_dir()
    assert result.api_call_count == 0
    assert result.llm_call_count == 0
    assert result.semantic_preflight_executed is False
    assert result.repair_loop_executed is False
    assert (result.run_dir / "run_log.jsonl").is_file()
    assert "MODEL_ERROR" not in all_run_text(result.run_dir)
    assert "sk-test-secret-should-not-appear" not in all_run_text(result.run_dir)

    logs = read_jsonl(result.run_dir / "run_log.jsonl")
    assert all(event["model"] is None for event in logs)
    assert all(event["key_slot"] is None for event in logs)
    assert all(event["input_tokens"] == 0 and event["output_tokens"] == 0 for event in logs)

    final_exists = (result.run_dir / "final_report.md").exists()
    failed_exists = (result.run_dir / "failed_draft.md").exists()
    assert not (final_exists and failed_exists)

    if result.failure_type is not None:
        failure_events = [event for event in logs if event["status"] == "failure"]
        assert failure_events
        assert all(event["failure_type"] for event in failure_events)
        assert (result.run_dir / "ceo_report.md").exists() or any(
            event["failure_type"] == "REPORT_ERROR" for event in logs
        )


def test_pass_scenario_creates_final_report(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="pass", run_id="pass", runs_root=tmp_path)

    assert result.status == "PASS"
    assert result.failure_type is None
    assert (result.run_dir / "final_report.md").is_file()
    assert not (result.run_dir / "failed_draft.md").exists()
    assert len(read_json(result.run_dir / "work_orders.json")["work_orders"]) == 4


def test_conditional_scenario_creates_final_report_and_warning(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="conditional", run_id="conditional", runs_root=tmp_path)

    assert result.status == "CONDITIONAL"
    assert result.failure_type is None
    assert (result.run_dir / "final_report.md").is_file()
    assert "Minor non-blocking review note exists." in (result.run_dir / "ceo_report.md").read_text(encoding="utf-8")


def test_fail_scenario_creates_failed_draft_only(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="fail", run_id="fail", runs_root=tmp_path)

    assert result.status == "FAIL"
    assert result.failure_type == "AUDIT_FAIL"
    assert not (result.run_dir / "final_report.md").exists()
    assert (result.run_dir / "failed_draft.md").is_file()


def test_needs_decision_scenario_creates_ceo_report_and_no_final(tmp_path: Path) -> None:
    result = run_dry_run(
        mission_text=MISSION,
        scenario="needs_decision",
        run_id="needs-decision",
        runs_root=tmp_path,
    )

    assert result.status == "NEEDS_DECISION"
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"
    assert not (result.run_dir / "final_report.md").exists()
    assert (result.run_dir / "failed_draft.md").is_file()
    assert "대표 판단 필요 여부" in (result.run_dir / "ceo_report.md").read_text(encoding="utf-8")


def test_config_error_creates_only_failure_reports(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=None, scenario="config_error", run_id="config-error", runs_root=tmp_path)

    assert result.status == "CONFIG_ERROR"
    assert result.failure_type == "CONFIG_ERROR"
    assert (result.run_dir / "ceo_report.md").is_file()
    assert not (result.run_dir / "work_orders.json").exists()
    assert not (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()


def test_budget_exceeded_stops_after_preflight(tmp_path: Path) -> None:
    result = run_dry_run(
        mission_text=MISSION,
        scenario="budget_exceeded",
        run_id="budget-exceeded",
        runs_root=tmp_path,
    )

    assert result.failure_type == "BUDGET_EXCEEDED"
    assert read_json(result.run_dir / "preflight_audit.json")["failure_type"] == "BUDGET_EXCEEDED"
    assert not (result.run_dir / "worker_results.jsonl").exists()
    assert not (result.run_dir / "manager_summary.json").exists()
    assert not (result.run_dir / "audit_report.json").exists()


def test_mid_flight_failure_preserves_partial_worker_results(tmp_path: Path) -> None:
    result = run_dry_run(
        mission_text=MISSION,
        scenario="mid_flight_failure",
        run_id="mid-flight",
        runs_root=tmp_path,
    )

    assert result.failure_type == "WORKER_BAD_OUTPUT"
    assert len(read_jsonl(result.run_dir / "worker_results.jsonl")) == 2
    assert not (result.run_dir / "manager_summary.json").exists()
    assert not (result.run_dir / "audit_report.json").exists()
    assert not (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()


def test_invalid_work_order_fails_preflight_without_semantic_checks(tmp_path: Path) -> None:
    doc = {
        "mission_interpretation": {},
        "work_orders": [
            {
                "work_id": "wo-1",
                "role": "requirements_checker",
                "task": "Please run shell commands",
                "input_scope": "mission.md",
                "output_schema": {},
                "forbidden": [],
                "acceptance_condition": "schema-valid output",
                "can_edit_files": False,
                "can_run_shell": False,
                "references": [],
            }
        ],
        "manager_self_check": {
            "mission_coverage_summary": "covered",
            "input_scope_rationale": "local",
            "duplicate_risk": "low",
            "known_gaps": [],
        },
    }

    audit = deterministic_preflight(doc, run_dir=tmp_path)

    assert audit["status"] == "fail"
    assert audit["failure_type"] == "MANAGER_BAD_PLAN"


def test_worker_permission_flags_are_blocked(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="pass", run_id="permissions", runs_root=tmp_path)
    work_orders = read_json(result.run_dir / "work_orders.json")["work_orders"]

    assert all(order["can_edit_files"] is False for order in work_orders)
    assert all(order["can_run_shell"] is False for order in work_orders)
