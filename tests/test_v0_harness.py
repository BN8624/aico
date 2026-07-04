# AICO v0 dry-run 하네스의 필수 시나리오를 검증한다.
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import aico_v0.harness as harness
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


def valid_work_orders(count: int = 1) -> dict:
    return {
        "mission_interpretation": {"scenario": "unit"},
        "work_orders": [
            {
                "work_id": f"wo-{index + 1}",
                "role": "requirements_checker",
                "task": "Check deterministic acceptance criteria.",
                "input_scope": "mission.md",
                "output_schema": {"summary": "string"},
                "forbidden": [],
                "acceptance_condition": "Return schema-valid dry-run findings.",
                "can_edit_files": False,
                "can_run_shell": False,
                "references": [],
            }
            for index in range(count)
        ],
        "manager_self_check": {
            "mission_coverage_summary": "covered",
            "input_scope_rationale": "local",
            "duplicate_risk": "low",
            "known_gaps": [],
        },
    }


def normalized_artifacts(run_dir: Path) -> dict[str, object]:
    artifacts: dict[str, object] = {}
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        text = path.read_text(encoding="utf-8")
        if relative.endswith(".json"):
            artifacts[relative] = json.loads(text)
        elif relative.endswith(".jsonl"):
            rows = [json.loads(line) for line in text.splitlines() if line]
            for row in rows:
                row["timestamp"] = "<timestamp>"
            artifacts[relative] = rows
        else:
            artifacts[relative] = re.sub(r"run-[a-f0-9]+", "<run-id>", text)
    return artifacts


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
    assert not list(result.run_dir.rglob("*semantic_preflight*"))
    assert not list(result.run_dir.rglob("*repair*"))
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
    assert result.run_dir.is_dir()
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
    worker_results = read_jsonl(result.run_dir / "worker_results.jsonl")
    logs = read_jsonl(result.run_dir / "run_log.jsonl")
    assert len(worker_results) == 2
    assert [row["work_id"] for row in worker_results] == ["wo-1", "wo-2"]
    assert [event["event_type"] for event in logs].count("WORKER_COMPLETED") == 2
    assert not (result.run_dir / "manager_summary.json").exists()
    assert not (result.run_dir / "audit_report.json").exists()
    assert not (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()
    assert (result.run_dir / "ceo_report.md").exists()
    assert any(event["failure_type"] == "WORKER_BAD_OUTPUT" for event in logs if event["status"] == "failure")


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


def test_deterministic_preflight_direct_check_types(tmp_path: Path) -> None:
    passing = deterministic_preflight(valid_work_orders(1), run_dir=tmp_path)
    assert passing["status"] == "pass"
    assert set(passing["checks"]) == {
        "schema",
        "forbidden_keywords",
        "permission_flags",
        "path_scope",
        "secret_regex",
        "budget",
    }

    schema_error = valid_work_orders(1)
    del schema_error["work_orders"][0]["task"]
    assert deterministic_preflight(schema_error, run_dir=tmp_path)["failure_type"] == "SCHEMA_ERROR"

    forbidden = valid_work_orders(1)
    forbidden["work_orders"][0]["task"] = "Run shell command"
    assert deterministic_preflight(forbidden, run_dir=tmp_path)["failure_type"] == "MANAGER_BAD_PLAN"

    permission = valid_work_orders(1)
    permission["work_orders"][0]["can_edit_files"] = True
    assert deterministic_preflight(permission, run_dir=tmp_path)["failure_type"] == "SECURITY_BLOCKED"

    secret = valid_work_orders(1)
    secret["work_orders"][0]["task"] = "Check token=ghp_abcdefghijklmnopqrstuvwxyz123456"
    assert deterministic_preflight(secret, run_dir=tmp_path)["failure_type"] == "SECURITY_BLOCKED"

    outside = valid_work_orders(1)
    outside["work_orders"][0]["references"] = [str(tmp_path.parent / "outside-aico-reference.txt")]
    assert deterministic_preflight(outside, run_dir=tmp_path / "run")["failure_type"] == "SECURITY_BLOCKED"

    over_budget = valid_work_orders(5)
    assert deterministic_preflight(over_budget, run_dir=tmp_path)["failure_type"] == "BUDGET_EXCEEDED"


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_deterministic_preflight_allows_one_to_four_work_orders(tmp_path: Path, count: int) -> None:
    assert deterministic_preflight(valid_work_orders(count), run_dir=tmp_path)["status"] == "pass"


def test_more_than_four_work_orders_becomes_budget_exceeded(tmp_path: Path) -> None:
    audit = deterministic_preflight(valid_work_orders(5), run_dir=tmp_path)

    assert audit["status"] == "fail"
    assert audit["failure_type"] == "BUDGET_EXCEEDED"


def test_required_fixes_prevent_final_report_and_false_decision_becomes_fail(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="fail", run_id="required-fixes-fail", runs_root=tmp_path)
    audit = read_json(result.run_dir / "audit_report.json")

    assert audit["required_fixes"]
    assert audit["ceo_decision_needed"] is False
    assert result.status == "FAIL"
    assert result.failure_type == "AUDIT_FAIL"
    assert not (result.run_dir / "final_report.md").exists()


def test_required_fixes_with_decision_needed_becomes_needs_decision(tmp_path: Path) -> None:
    result = run_dry_run(
        mission_text=MISSION,
        scenario="required_fixes_needs_decision",
        run_id="required-fixes-decision",
        runs_root=tmp_path,
    )

    assert result.status == "NEEDS_DECISION"
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"
    assert read_json(result.run_dir / "audit_report.json")["required_fixes"]
    assert not (result.run_dir / "final_report.md").exists()


@pytest.mark.parametrize("scenario", ["manager_decision_only", "audit_decision_only"])
def test_single_source_ceo_decision_needed_becomes_needs_decision(tmp_path: Path, scenario: str) -> None:
    result = run_dry_run(mission_text=MISSION, scenario=scenario, run_id=scenario, runs_root=tmp_path)

    assert result.status == "NEEDS_DECISION"
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"
    assert not (result.run_dir / "final_report.md").exists()
    assert (result.run_dir / "failed_draft.md").exists()


def test_fail_without_draft_creates_no_failed_draft(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="fail_no_draft", run_id="fail-no-draft", runs_root=tmp_path)

    assert result.status == "FAIL"
    assert result.failure_type == "AUDIT_FAIL"
    assert not (result.run_dir / "final_report.md").exists()
    assert not (result.run_dir / "failed_draft.md").exists()


def test_worker_schema_error_becomes_schema_error(tmp_path: Path) -> None:
    result = run_dry_run(
        mission_text=MISSION,
        scenario="worker_schema_error",
        run_id="worker-schema-error",
        runs_root=tmp_path,
    )

    assert result.status == "FAIL"
    assert result.failure_type == "SCHEMA_ERROR"
    assert not (result.run_dir / "manager_summary.json").exists()
    assert not (result.run_dir / "audit_report.json").exists()


def test_schema_valid_empty_worker_output_becomes_worker_bad_output(tmp_path: Path) -> None:
    result = run_dry_run(
        mission_text=MISSION,
        scenario="worker_bad_output",
        run_id="worker-bad-output",
        runs_root=tmp_path,
    )

    assert result.status == "FAIL"
    assert result.failure_type == "WORKER_BAD_OUTPUT"
    assert not (result.run_dir / "manager_summary.json").exists()
    assert not (result.run_dir / "audit_report.json").exists()


def test_ceo_report_write_failure_logs_report_error_and_preserves_original_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_write_text = harness._write_text

    def fail_ceo_report(path: Path, text: str) -> None:
        if path.name == "ceo_report.md":
            raise OSError("simulated ceo report write failure")
        original_write_text(path, text)

    monkeypatch.setattr(harness, "_write_text", fail_ceo_report)

    result = run_dry_run(mission_text=MISSION, scenario="fail", run_id="report-error", runs_root=tmp_path)
    logs = read_jsonl(result.run_dir / "run_log.jsonl")

    assert result.failure_type == "AUDIT_FAIL"
    assert not (result.run_dir / "ceo_report.md").exists()
    assert any(event["failure_type"] == "AUDIT_FAIL" for event in logs if event["status"] == "failure")
    report_errors = [event for event in logs if event["failure_type"] == "REPORT_ERROR"]
    assert report_errors
    assert report_errors[0]["parent_event_id"] == "AUDIT_FAIL"


def test_secret_mission_and_raw_output_are_masked_or_blocked(tmp_path: Path) -> None:
    secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    blocked = run_dry_run(
        mission_text=f"Do not leak token={secret}",
        scenario="secret_raw_output",
        run_id="secret-mission",
        runs_root=tmp_path,
    )

    assert blocked.failure_type == "SECURITY_BLOCKED"
    assert secret not in all_run_text(blocked.run_dir)
    assert "[MASKED_SECRET]" in (blocked.run_dir / "mission.md").read_text(encoding="utf-8")

    masked = run_dry_run(
        mission_text=MISSION,
        scenario="secret_raw_output",
        run_id="secret-output",
        runs_root=tmp_path,
    )
    worker_results = read_jsonl(masked.run_dir / "worker_results.jsonl")
    worker_results_text = (masked.run_dir / "worker_results.jsonl").read_text(encoding="utf-8")

    assert secret not in all_run_text(masked.run_dir)
    assert "[MASKED_SECRET]" in worker_results_text
    assert all(row["raw_output_saved"] is False for row in worker_results)
    assert all("raw_output" not in row for row in worker_results)


def test_low_confidence_worker_results_are_not_sole_support_for_final_report(tmp_path: Path) -> None:
    result = run_dry_run(mission_text=MISSION, scenario="low_confidence", run_id="low-confidence", runs_root=tmp_path)
    worker_results = read_jsonl(result.run_dir / "worker_results.jsonl")
    summary = read_json(result.run_dir / "manager_summary.json")

    assert all(row["confidence"] < 0.5 for row in worker_results)
    assert summary["used_worker_results"] == []
    assert summary["rejected_worker_results"]
    assert not (result.run_dir / "final_report.md").exists()


def test_mission_path_is_copied_to_run_mission_md(tmp_path: Path) -> None:
    mission_path = tmp_path / "input-mission.md"
    mission_path.write_text("Mission from path has priority inside the run.", encoding="utf-8")

    result = run_dry_run(mission_path=mission_path, scenario="pass", run_id="mission-path", runs_root=tmp_path)
    summary = read_json(result.run_dir / "manager_summary.json")

    assert (result.run_dir / "mission.md").read_text(encoding="utf-8") == mission_path.read_text(encoding="utf-8")
    assert summary["mission_interpretation"]["mission_excerpt"].startswith("Mission from path")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_required_scenarios_produce_deterministic_artifacts(tmp_path: Path, scenario: str) -> None:
    first = run_dry_run(
        mission_text=None if scenario == "config_error" else MISSION,
        scenario=scenario,
        run_id=f"{scenario}-a",
        runs_root=tmp_path,
    )
    second = run_dry_run(
        mission_text=None if scenario == "config_error" else MISSION,
        scenario=scenario,
        run_id=f"{scenario}-b",
        runs_root=tmp_path,
    )

    assert normalized_artifacts(first.run_dir) == normalized_artifacts(second.run_dir)


def test_no_forbidden_external_capability_imports_exist() -> None:
    forbidden = (
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
        "webbrowser",
        "flask",
        "fastapi",
        "openai",
        "anthropic",
    )
    source = "\n".join(path.read_text(encoding="utf-8").lower() for path in Path("aico_v0").glob("*.py"))

    assert not any(name in source for name in forbidden)
