# AICO v0 deterministic scenario fixture를 정의한다.
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioFixture:
    name: str
    audit_status: str
    work_order_count: int = 4
    warnings: tuple[str, ...] = ()
    required_fixes: tuple[str, ...] = ()
    manager_ceo_decision_needed: bool = False
    audit_ceo_decision_needed: bool = False
    draft_report: str = "AICO v0 dry-run draft report."
    blocking: bool = False
    mid_flight_after: int | None = None
    worker_result_mode: str = "valid"
    raw_output_text: str = "deterministic mock output"
    low_confidence: bool = False


SCENARIOS: dict[str, ScenarioFixture] = {
    "pass": ScenarioFixture(
        name="pass",
        audit_status="pass",
        draft_report="All deterministic dry-run checks passed.",
    ),
    "conditional": ScenarioFixture(
        name="conditional",
        audit_status="conditional",
        warnings=("Minor non-blocking review note exists.",),
        draft_report="Dry-run passed with non-blocking warnings.",
    ),
    "fail": ScenarioFixture(
        name="fail",
        audit_status="fail",
        required_fixes=("Resolve the deterministic audit blocker.",),
        blocking=True,
        draft_report="Draft retained for failed audit review.",
    ),
    "needs_decision": ScenarioFixture(
        name="needs_decision",
        audit_status="conditional",
        manager_ceo_decision_needed=True,
        audit_ceo_decision_needed=True,
        warnings=("Representative decision is required before promotion.",),
        draft_report="Draft retained for representative decision.",
    ),
    "budget_exceeded": ScenarioFixture(
        name="budget_exceeded",
        audit_status="fail",
        work_order_count=5,
        draft_report="",
    ),
    "mid_flight_failure": ScenarioFixture(
        name="mid_flight_failure",
        audit_status="fail",
        mid_flight_after=2,
        draft_report="",
    ),
    "fail_no_draft": ScenarioFixture(
        name="fail_no_draft",
        audit_status="fail",
        required_fixes=("Resolve the deterministic audit blocker.",),
        blocking=True,
        draft_report="",
    ),
    "required_fixes_needs_decision": ScenarioFixture(
        name="required_fixes_needs_decision",
        audit_status="fail",
        required_fixes=("Resolve the blocker after representative decision.",),
        audit_ceo_decision_needed=True,
        blocking=True,
        draft_report="Draft retained for required fix decision.",
    ),
    "manager_decision_only": ScenarioFixture(
        name="manager_decision_only",
        audit_status="conditional",
        manager_ceo_decision_needed=True,
        draft_report="Draft retained for manager decision.",
    ),
    "audit_decision_only": ScenarioFixture(
        name="audit_decision_only",
        audit_status="conditional",
        audit_ceo_decision_needed=True,
        draft_report="Draft retained for audit decision.",
    ),
    "worker_schema_error": ScenarioFixture(
        name="worker_schema_error",
        audit_status="fail",
        worker_result_mode="schema_error",
        draft_report="",
    ),
    "worker_bad_output": ScenarioFixture(
        name="worker_bad_output",
        audit_status="fail",
        worker_result_mode="bad_output",
        draft_report="",
    ),
    "secret_raw_output": ScenarioFixture(
        name="secret_raw_output",
        audit_status="pass",
        raw_output_text="token=ghp_abcdefghijklmnopqrstuvwxyz123456",
        draft_report="Secret raw output was masked before persistence.",
    ),
    "low_confidence": ScenarioFixture(
        name="low_confidence",
        audit_status="fail",
        required_fixes=("Low confidence worker output cannot support promotion.",),
        low_confidence=True,
        draft_report="Low confidence draft is not promoted.",
    ),
}

SCENARIO_NAMES = tuple(["config_error", *SCENARIOS.keys()])

WORKER_ROLES = (
    "requirements_checker",
    "risk_finder",
    "structure_planner",
    "report_reviewer",
)

WORKER_TASKS = (
    "Check whether the mission has enough concrete acceptance criteria.",
    "Identify deterministic risks that can be represented without external calls.",
    "Plan the artifact structure for the dry-run output.",
    "Review report promotion rules against the fixture result.",
)

FORBIDDEN_WORKER_ACTIONS = (
    "final answer",
    "final_report",
    "최종 결론",
    "전체 계획 재작성",
    "알아서",
    "파일 수정",
    "file edit",
    "shell",
    "shell 실행",
    "mission 수정",
    "secret/API key 포함",
)
