# AICO v0 dry-run 실행과 산출물 생성을 담당한다.
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fixtures import (
    FORBIDDEN_WORKER_ACTIONS,
    SCENARIOS,
    WORKER_ROLES,
    WORKER_TASKS,
    ScenarioFixture,
)

RUN_LOG_FIELDS = (
    "timestamp",
    "event_type",
    "actor",
    "model",
    "key_slot",
    "input_tokens",
    "output_tokens",
    "status",
    "failure_type",
    "error",
    "artifact_path",
    "parent_event_id",
)

FAILURE_TYPES = {
    "CONFIG_ERROR",
    "SCHEMA_ERROR",
    "MANAGER_BAD_PLAN",
    "WORKER_BAD_OUTPUT",
    "AUDIT_FAIL",
    "BUDGET_EXCEEDED",
    "HUMAN_DECISION_REQUIRED",
    "SECURITY_BLOCKED",
    "REPORT_ERROR",
    "UNKNOWN_ERROR",
}

WORKER_RESULT_REQUIRED_FIELDS = {
    "work_id",
    "role",
    "summary",
    "findings",
    "risks",
    "recommendations",
    "confidence",
    "payload",
    "masked_raw_output",
    "raw_output_saved",
    "mask_reason",
}

FORBIDDEN_KEYWORDS = (
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
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_ -]?key|token|credential|secret)\s*[:=]\s*[A-Za-z0-9_.-]{8,}"),
)


@dataclass(frozen=True)
class RunResult:
    run_id: str
    run_dir: Path
    status: str
    failure_type: str | None
    api_call_count: int = 0
    llm_call_count: int = 0
    semantic_preflight_executed: bool = False
    repair_loop_executed: bool = False


def run_dry_run(
    *,
    mission_text: str | None = None,
    mission_path: Path | None = None,
    scenario: str = "pass",
    run_id: str | None = None,
    runs_root: Path | str = Path("runs"),
) -> RunResult:
    if scenario != "config_error" and scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    resolved_run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
    run_dir = Path(runs_root) / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "run_log.jsonl"

    _append_log(log_path, "RUN_STARTED", "harness", "ok")

    mission = _load_mission(mission_text, mission_path)
    if mission is None:
        failure_type = "CONFIG_ERROR"
        _append_log(
            log_path,
            "RUN_FAILED",
            "harness",
            "failure",
            failure_type=failure_type,
            error="mission input/path is required",
        )
        _try_write_ceo_report(
            log_path,
            run_dir,
            status="FAIL",
            conclusion="Mission input or mission path was not provided.",
            final_artifact=None,
            warnings=[],
            failure_type=failure_type,
            decision_needed=False,
        )
        return RunResult(resolved_run_id, run_dir, "CONFIG_ERROR", failure_type)

    _write_text(run_dir / "mission.md", mission)
    _append_log(log_path, "MISSION_LOADED", "harness", "ok", artifact_path="mission.md")

    fixture = SCENARIOS[scenario]
    work_orders = _build_work_orders(mission, fixture)
    _write_json(run_dir / "work_orders.json", work_orders)
    _append_log(log_path, "WORK_ORDERS_CREATED", "manager", "ok", artifact_path="work_orders.json")

    preflight = deterministic_preflight(work_orders, run_dir=run_dir)
    _write_json(run_dir / "preflight_audit.json", preflight)
    if preflight["status"] != "pass":
        failure_type = preflight["failure_type"]
        _append_log(
            log_path,
            "PREFLIGHT_FAILED",
            "harness",
            "failure",
            failure_type=failure_type,
            error=preflight["error"],
            artifact_path="preflight_audit.json",
        )
        _try_write_ceo_report(
            log_path,
            run_dir,
            status="FAIL",
            conclusion=preflight["error"],
            final_artifact=None,
            warnings=[],
            failure_type=failure_type,
            decision_needed=False,
        )
        return RunResult(resolved_run_id, run_dir, "FAIL", failure_type)

    _append_log(log_path, "PREFLIGHT_PASSED", "harness", "ok", artifact_path="preflight_audit.json")

    worker_failure_type, worker_failure_error = _write_worker_results(run_dir, work_orders, fixture, log_path)
    if worker_failure_type is not None:
        failure_type = worker_failure_type
        _append_log(
            log_path,
            "RUN_FAILED",
            "worker_pool",
            "failure",
            failure_type=failure_type,
            error=worker_failure_error,
            artifact_path="worker_results.jsonl",
        )
        _try_write_ceo_report(
            log_path,
            run_dir,
            status="FAIL",
            conclusion=worker_failure_error or "worker failure",
            final_artifact=None,
            warnings=[],
            failure_type=failure_type,
            decision_needed=False,
        )
        return RunResult(resolved_run_id, run_dir, "FAIL", failure_type)

    manager_summary = _build_manager_summary(mission, work_orders, fixture)
    _write_json(run_dir / "manager_summary.json", manager_summary)
    _append_log(log_path, "MANAGER_SUMMARY_CREATED", "manager", "ok", artifact_path="manager_summary.json")

    audit_report = _build_audit_report(fixture, manager_summary)
    _write_json(run_dir / "audit_report.json", audit_report)
    _append_log(log_path, "AUDIT_COMPLETED", "auditor", "ok", artifact_path="audit_report.json")

    final_status, failure_type = _promote_reports(run_dir, preflight, manager_summary, audit_report, log_path)
    decision_needed = final_status == "NEEDS_DECISION"
    warnings = list(audit_report["warnings"])
    final_artifact = "final_report.md" if (run_dir / "final_report.md").exists() else None
    _try_write_ceo_report(
        log_path,
        run_dir,
        status=final_status,
        conclusion=_status_conclusion(final_status),
        final_artifact=final_artifact,
        warnings=warnings,
        failure_type=failure_type,
        decision_needed=decision_needed,
    )

    if failure_type is None:
        _append_log(log_path, "RUN_COMPLETED", "harness", "ok")
    else:
        _append_log(log_path, "RUN_FAILED", "harness", "failure", failure_type=failure_type)

    return RunResult(resolved_run_id, run_dir, final_status, failure_type)


def deterministic_preflight(work_orders_doc: dict[str, Any], *, run_dir: Path, max_workers: int = 4) -> dict[str, Any]:
    required_top = {"mission_interpretation", "work_orders", "manager_self_check"}
    missing_top = sorted(required_top - set(work_orders_doc))
    if missing_top:
        return _preflight_fail("SCHEMA_ERROR", f"Missing top-level fields: {', '.join(missing_top)}")

    work_orders = work_orders_doc.get("work_orders")
    if not isinstance(work_orders, list):
        return _preflight_fail("SCHEMA_ERROR", "work_orders must be a list")
    if len(work_orders) < 1:
        return _preflight_fail("MANAGER_BAD_PLAN", "work_orders must contain at least one WorkOrder")
    if len(work_orders) > max_workers:
        return _preflight_fail("BUDGET_EXCEEDED", "work_orders exceeds max_workers=4")

    manager_self_check = work_orders_doc.get("manager_self_check")
    if not isinstance(manager_self_check, dict):
        return _preflight_fail("SCHEMA_ERROR", "manager_self_check must be an object")
    for field in ("mission_coverage_summary", "input_scope_rationale", "duplicate_risk", "known_gaps"):
        if field not in manager_self_check:
            return _preflight_fail("SCHEMA_ERROR", f"manager_self_check.{field} is required")

    required_order_fields = {
        "work_id",
        "role",
        "task",
        "input_scope",
        "output_schema",
        "forbidden",
        "acceptance_condition",
    }
    for index, order in enumerate(work_orders):
        if not isinstance(order, dict):
            return _preflight_fail("SCHEMA_ERROR", f"WorkOrder {index} must be an object")
        missing = sorted(required_order_fields - set(order))
        if missing:
            return _preflight_fail("SCHEMA_ERROR", f"WorkOrder {index} missing fields: {', '.join(missing)}")
        if order.get("can_edit_files") is True or order.get("can_run_shell") is True:
            return _preflight_fail("SECURITY_BLOCKED", f"WorkOrder {order['work_id']} requested forbidden permissions")

        scan_text = "\n".join(str(order.get(field, "")) for field in ("role", "task", "input_scope", "acceptance_condition"))
        if _contains_forbidden_keyword(scan_text):
            return _preflight_fail("MANAGER_BAD_PLAN", f"WorkOrder {order['work_id']} contains forbidden task wording")
        if _contains_secret(scan_text):
            return _preflight_fail("SECURITY_BLOCKED", f"WorkOrder {order['work_id']} contains a secret-like value")
        if _contains_external_reference(order.get("references", []), run_dir):
            return _preflight_fail("SECURITY_BLOCKED", f"WorkOrder {order['work_id']} contains an out-of-scope reference")

    serialized = json.dumps(work_orders_doc, ensure_ascii=False)
    if _contains_secret(serialized):
        return _preflight_fail("SECURITY_BLOCKED", "work_orders.json contains a secret-like value")

    return {
        "status": "pass",
        "failure_type": None,
        "error": None,
        "checks": {
            "schema": "pass",
            "forbidden_keywords": "pass",
            "permission_flags": "pass",
            "path_scope": "pass",
            "secret_regex": "pass",
            "budget": "pass",
        },
    }


def _load_mission(mission_text: str | None, mission_path: Path | None) -> str | None:
    if mission_text is not None and mission_text.strip():
        return mission_text
    if mission_path is None:
        return None
    try:
        text = mission_path.read_text(encoding="utf-8")
    except OSError:
        return None
    return text if text.strip() else None


def _build_work_orders(mission: str, fixture: ScenarioFixture) -> dict[str, Any]:
    orders = []
    for index in range(fixture.work_order_count):
        role = WORKER_ROLES[index % len(WORKER_ROLES)]
        orders.append(
            {
                "work_id": f"wo-{index + 1}",
                "role": role,
                "task": WORKER_TASKS[index % len(WORKER_TASKS)],
                "input_scope": "mission.md and deterministic scenario fixture only",
                "output_schema": {
                    "summary": "string",
                    "findings": "array",
                    "risks": "array",
                    "recommendations": "array",
                    "confidence": "number",
                },
                "forbidden": list(FORBIDDEN_WORKER_ACTIONS),
                "acceptance_condition": "Return schema-valid dry-run findings without external calls.",
                "can_edit_files": False,
                "can_run_shell": False,
                "references": [],
            }
        )
    return {
        "mission_interpretation": {
            "scenario": fixture.name,
            "mission_excerpt": mission[:160],
            "api_calls_allowed": 0,
            "llm_calls_allowed": 0,
        },
        "work_orders": orders,
        "manager_self_check": {
            "mission_coverage_summary": "Mission is represented by deterministic dry-run work orders.",
            "input_scope_rationale": "Only mission.md and embedded scenario fixtures are used.",
            "duplicate_risk": "low",
            "known_gaps": [],
        },
    }


def _write_worker_results(
    run_dir: Path,
    work_orders_doc: dict[str, Any],
    fixture: ScenarioFixture,
    log_path: Path,
) -> tuple[str | None, str | None]:
    result_path = run_dir / "worker_results.jsonl"
    orders = work_orders_doc["work_orders"]
    allowed_count = fixture.mid_flight_after if fixture.mid_flight_after is not None else len(orders)
    with result_path.open("w", encoding="utf-8", newline="\n") as handle:
        for order in orders[:allowed_count]:
            result = {
                "work_id": order["work_id"],
                "role": order["role"],
                "summary": f"{order['role']} completed deterministic dry-run work.",
                "findings": [f"{order['work_id']} finding is fixture-derived."],
                "risks": [],
                "recommendations": ["Keep execution offline and deterministic."],
                "confidence": 0.4 if fixture.low_confidence else 0.9,
                "payload": {"scenario": fixture.name, "used_external_calls": False},
                "masked_raw_output": _mask_secrets(fixture.raw_output_text),
                "raw_output_saved": False,
                "mask_reason": "raw output is not persisted in v0",
            }
            if fixture.worker_result_mode == "schema_error":
                result.pop("summary")
            elif fixture.worker_result_mode == "bad_output":
                result["summary"] = ""
                result["findings"] = []
                result["recommendations"] = []
            validation_failure = _validate_worker_result(result)
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            if validation_failure is not None:
                return validation_failure
            _append_log(log_path, "WORKER_COMPLETED", "worker_pool", "ok", artifact_path="worker_results.jsonl")

    if fixture.mid_flight_after is not None:
        return ("WORKER_BAD_OUTPUT", "mid_flight_failure after partial worker completion")
    return (None, None)


def _build_manager_summary(
    mission: str,
    work_orders_doc: dict[str, Any],
    fixture: ScenarioFixture,
) -> dict[str, Any]:
    used = [order["work_id"] for order in work_orders_doc["work_orders"]]
    rejected: list[str] = []
    if fixture.low_confidence:
        rejected = used
        used = []
    return {
        "mission_interpretation": {
            "scenario": fixture.name,
            "mission_excerpt": mission[:160],
        },
        "used_worker_results": used,
        "rejected_worker_results": rejected,
        "draft_report": fixture.draft_report,
        "ceo_decision_needed": fixture.manager_ceo_decision_needed,
        "manager_self_check": work_orders_doc["manager_self_check"],
    }


def _build_audit_report(fixture: ScenarioFixture, manager_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": fixture.audit_status,
        "blocking": fixture.blocking,
        "required_fixes": list(fixture.required_fixes),
        "warnings": list(fixture.warnings),
        "ceo_decision_needed": fixture.audit_ceo_decision_needed or manager_summary["ceo_decision_needed"],
        "audit_summary": f"Deterministic audit result for {fixture.name}.",
    }


def _promote_reports(
    run_dir: Path,
    preflight: dict[str, Any],
    manager_summary: dict[str, Any],
    audit_report: dict[str, Any],
    log_path: Path,
) -> tuple[str, str | None]:
    decision_needed = bool(manager_summary["ceo_decision_needed"] or audit_report["ceo_decision_needed"])
    blocking = bool(audit_report["blocking"])
    required_fixes = bool(audit_report["required_fixes"])
    audit_status = audit_report["status"]

    can_promote = (
        preflight["status"] == "pass"
        and audit_status in {"pass", "conditional"}
        and not blocking
        and not required_fixes
        and not decision_needed
    )
    if can_promote:
        _write_text(run_dir / "final_report.md", manager_summary["draft_report"])
        _append_log(log_path, "FINAL_REPORT_CREATED", "harness", "ok", artifact_path="final_report.md")
        return ("CONDITIONAL" if audit_status == "conditional" else "PASS", None)

    status = "NEEDS_DECISION" if decision_needed else "FAIL"
    failure_type = "HUMAN_DECISION_REQUIRED" if decision_needed else "AUDIT_FAIL"
    draft = manager_summary.get("draft_report")
    if draft and status in {"FAIL", "NEEDS_DECISION"}:
        _write_text(run_dir / "failed_draft.md", draft)
        _append_log(log_path, "FAILED_DRAFT_CREATED", "harness", "ok", artifact_path="failed_draft.md")
    return status, failure_type


def _write_ceo_report(
    run_dir: Path,
    *,
    status: str,
    conclusion: str,
    final_artifact: str | None,
    warnings: list[str],
    failure_type: str | None,
    decision_needed: bool,
) -> None:
    warning_text = ", ".join(warnings) if warnings else "None"
    final_text = final_artifact or "None"
    failure_text = failure_type or "None"
    body = "\n".join(
        [
            f"상태: {status}",
            "",
            "## 결론",
            conclusion,
            "",
            "## 최종 산출물",
            final_text,
            "",
            "## 이번 실행에서 한 일",
            "Deterministic v0 dry-run artifacts were generated without API or LLM calls.",
            "",
            "## 핵심 결정",
            f"failure_type={failure_text}",
            "",
            "## 남은 위험",
            warning_text,
            "",
            "## 감사 결과",
            status,
            "",
            "## 대표 판단 필요 여부",
            "yes" if decision_needed else "no",
            "",
            "## 다음 행동",
            "Review generated artifacts and decide whether to proceed beyond v0.",
            "",
        ]
    )
    _write_text(run_dir / "ceo_report.md", body)


def _try_write_ceo_report(
    log_path: Path,
    run_dir: Path,
    *,
    status: str,
    conclusion: str,
    final_artifact: str | None,
    warnings: list[str],
    failure_type: str | None,
    decision_needed: bool,
) -> bool:
    try:
        _write_ceo_report(
            run_dir,
            status=status,
            conclusion=conclusion,
            final_artifact=final_artifact,
            warnings=warnings,
            failure_type=failure_type,
            decision_needed=decision_needed,
        )
    except Exception as exc:
        previous = failure_type or "NONE"
        _append_log(
            log_path,
            "REPORT_ERROR",
            "harness",
            "failure",
            failure_type="REPORT_ERROR",
            error=f"ceo_report.md write failed after {previous}: {exc}",
            artifact_path="ceo_report.md",
            parent_event_id=previous,
        )
        return False
    _append_log(log_path, "CEO_REPORT_CREATED", "harness", "ok", artifact_path="ceo_report.md")
    return True


def _validate_worker_result(result: dict[str, Any]) -> tuple[str, str] | None:
    missing = sorted(WORKER_RESULT_REQUIRED_FIELDS - set(result))
    if missing:
        return ("SCHEMA_ERROR", f"worker result missing fields: {', '.join(missing)}")
    if not isinstance(result["summary"], str) or not isinstance(result["findings"], list):
        return ("SCHEMA_ERROR", "worker result has invalid field types")
    if not isinstance(result["recommendations"], list) or not isinstance(result["confidence"], (int, float)):
        return ("SCHEMA_ERROR", "worker result has invalid field types")
    if not result["summary"].strip() or (not result["findings"] and not result["recommendations"]):
        return ("WORKER_BAD_OUTPUT", "worker result is schema-valid but empty or irrelevant")
    return None


def _status_conclusion(status: str) -> str:
    if status == "PASS":
        return "Dry-run completed and final_report.md was promoted."
    if status == "CONDITIONAL":
        return "Dry-run completed with non-blocking warnings."
    if status == "NEEDS_DECISION":
        return "Representative decision is required before promotion."
    return "Dry-run did not qualify for final_report.md promotion."


def _preflight_fail(failure_type: str, error: str) -> dict[str, Any]:
    if failure_type not in FAILURE_TYPES:
        failure_type = "UNKNOWN_ERROR"
    return {
        "status": "fail",
        "failure_type": failure_type,
        "error": error,
        "checks": {
            "schema": "unknown",
            "forbidden_keywords": "unknown",
            "permission_flags": "unknown",
            "path_scope": "unknown",
            "secret_regex": "unknown",
            "budget": "unknown",
        },
    }


def _append_log(
    log_path: Path,
    event_type: str,
    actor: str,
    status: str,
    *,
    failure_type: str | None = None,
    error: str | None = None,
    artifact_path: str | None = None,
    parent_event_id: str | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "actor": actor,
        "model": None,
        "key_slot": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "status": status,
        "failure_type": failure_type,
        "error": error,
        "artifact_path": artifact_path,
        "parent_event_id": parent_event_id,
    }
    if set(event) != set(RUN_LOG_FIELDS):
        raise RuntimeError("run log event fields drifted")
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    _write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.write_text(_mask_secrets(text), encoding="utf-8", newline="\n")


def _mask_secrets(text: str) -> str:
    masked = text
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub("[MASKED_SECRET]", masked)
    return masked


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _contains_forbidden_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in FORBIDDEN_KEYWORDS)


def _contains_external_reference(references: Any, run_dir: Path) -> bool:
    if not references:
        return False
    if not isinstance(references, list):
        return True
    workspace = Path.cwd().resolve()
    allowed_run_dir = run_dir.resolve()
    for reference in references:
        ref_text = str(reference)
        if ref_text.startswith(("http://", "https://", "git://")):
            return True
        try:
            resolved = Path(ref_text).resolve()
        except OSError:
            return True
        if not _is_relative_to(resolved, workspace) and not _is_relative_to(resolved, allowed_run_dir):
            return True
    return False


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True
