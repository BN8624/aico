# AICO P3A fake-provider API worker 계층을 구현한다.
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .harness import deterministic_preflight

KEY_SLOTS = (
    "manager_1",
    "worker_1",
    "worker_2",
    "worker_3",
    "worker_4",
    "auditor_1",
    "reserve_1",
)

WORKER_SLOTS = ("worker_1", "worker_2", "worker_3", "worker_4")
WORKER_ROLES = ("requirements_checker", "risk_finder", "structure_planner", "report_reviewer")

FAILURE_BY_PROVIDER_STATUS = {
    "timeout": "MODEL_ERROR",
    "rate_limited_429": "MODEL_ERROR",
    "server_error_500": "MODEL_ERROR",
    "provider_unavailable": "MODEL_ERROR",
    "no_response": "MODEL_ERROR",
    "non_json_response": "SCHEMA_ERROR",
    "schema_invalid_json": "SCHEMA_ERROR",
    "schema_valid_empty": "WORKER_BAD_OUTPUT",
    "security_leak": "SECURITY_BLOCKED",
}

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_ -]?key|token|credential|secret)\s*[:=]\s*[A-Za-z0-9_.-]{8,}"),
)

FORBIDDEN_REFERENCE_MARKERS = ("http://", "https://", "git://", "web search", "repo clone")


@dataclass(frozen=True)
class ProviderResult:
    status: str
    content: Any = None
    raw_output: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None


class Provider(Protocol):
    def call_model(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> ProviderResult:
        ...


@dataclass(frozen=True)
class P3ABudget:
    max_workers: int = 4
    max_repair_loops: int = 0
    max_model_calls: int = 7
    max_retries_per_call: int = 1
    max_consecutive_model_errors: int = 2
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_runtime_seconds: int | None = None


@dataclass(frozen=True)
class P3ARunResult:
    run_id: str
    run_dir: Path
    status: str
    failure_type: str | None
    fake_model_call_count: int
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    semantic_preflight_executed: bool = False
    repair_loop_executed: bool = False


class FakeProvider:
    def __init__(self, scenario: str = "happy") -> None:
        self.scenario = scenario
        self.calls: list[dict[str, Any]] = []

    def call_model(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> ProviderResult:
        if key_slot not in KEY_SLOTS:
            return ProviderResult("security_leak", error="invalid key slot")
        call_number = 1 + sum(1 for call in self.calls if call["key_slot"] == key_slot)
        self.calls.append({"key_slot": key_slot, "call_number": call_number, "scenario": scenario})

        if key_slot == "manager_1":
            return ProviderResult(
                "success",
                content={"plan": "deterministic p3a manager plan"},
                raw_output='{"plan":"deterministic p3a manager plan"}',
                input_tokens=12,
                output_tokens=8,
            )
        if key_slot == "auditor_1":
            return ProviderResult(
                "success",
                content={"status": "pass", "warnings": [], "required_fixes": [], "ceo_decision_needed": False},
                raw_output='{"status":"pass","warnings":[],"required_fixes":[],"ceo_decision_needed":false}',
                input_tokens=18,
                output_tokens=10,
            )

        status = self._worker_status(key_slot, call_number)
        return self._worker_result(key_slot, expected_schema, status)

    def _worker_status(self, key_slot: str, call_number: int) -> str:
        if key_slot == "reserve_1":
            return "success" if self.scenario == "reserve_recovery" else self._scenario_failure_status()
        if key_slot != "worker_1" and self.scenario not in {"reserve_recovery", "unrecovered_model_error"}:
            return "success"
        if self.scenario == "reserve_recovery":
            return "timeout" if key_slot == "worker_2" and call_number == 1 else "success"
        if self.scenario == "unrecovered_model_error":
            return "timeout" if key_slot == "worker_3" else "success"
        return self._scenario_failure_status() if key_slot == "worker_1" else "success"

    def _scenario_failure_status(self) -> str:
        return {
            "timeout": "timeout",
            "rate_limited_429": "rate_limited_429",
            "server_error_500": "server_error_500",
            "provider_unavailable": "provider_unavailable",
            "no_response": "no_response",
            "non_json_response": "non_json_response",
            "schema_invalid_json": "schema_invalid_json",
            "schema_valid_empty": "schema_valid_empty",
            "security_leak": "security_leak",
            "unrecovered_model_error": "timeout",
        }.get(self.scenario, "success")

    def _worker_result(self, key_slot: str, expected_schema: dict[str, Any], status: str) -> ProviderResult:
        work_id = expected_schema.get("work_id", "wo-reserve")
        role = expected_schema.get("role", "reserve_worker")
        if status == "success":
            raw = json.dumps({"summary": f"{role} completed via {key_slot}", "findings": ["fixture finding"]})
            return ProviderResult(
                "success",
                content=_valid_worker_payload(work_id, role, raw),
                raw_output=raw,
                input_tokens=24,
                output_tokens=16,
            )
        if status == "non_json_response":
            return ProviderResult(status, raw_output="not-json <<fixture>>", input_tokens=24, output_tokens=None)
        if status == "schema_invalid_json":
            return ProviderResult(status, content={"summary": "missing required fields"}, raw_output='{"summary":"missing"}')
        if status == "schema_valid_empty":
            empty = _valid_worker_payload(work_id, role, '{"summary":""}')
            empty["summary"] = ""
            empty["findings"] = []
            empty["recommendations"] = []
            return ProviderResult(status, content=empty, raw_output='{"summary":"","findings":[]}')
        if status == "security_leak":
            leaked = _valid_worker_payload(work_id, role, "token=sk-p3a-fake-secret-value")
            leaked["payload"] = {"leak": "sk-p3a-fake-secret-value"}
            return ProviderResult(status, content=leaked, raw_output="token=sk-p3a-fake-secret-value")
        return ProviderResult(status, raw_output=None, input_tokens=24, output_tokens=None, error=status)


def run_p3a_fake_provider(
    *,
    mission_text: str,
    scenario: str = "happy",
    run_id: str | None = None,
    runs_root: Path | str = Path("runs"),
    provider: Provider | None = None,
    budget: P3ABudget | None = None,
    model: str = "fake-p3a-model",
) -> P3ARunResult:
    active_budget = budget or P3ABudget()
    fake_provider = provider or FakeProvider(scenario)
    resolved_run_id = run_id or f"p3a-{uuid.uuid4().hex[:12]}"
    run_dir = Path(runs_root) / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "run_log.jsonl"
    state = {"model_calls": 0, "consecutive_model_errors": 0}

    _append_log(log_path, "RUN_STARTED", "harness", "ok")
    _write_text(run_dir / "mission.md", mission_text)

    if _contains_forbidden_reference(mission_text):
        return _finish_failure(
            run_dir,
            log_path,
            "SECURITY_BLOCKED",
            "mission requested forbidden external access",
            state,
        )

    manager_result = _call_provider(
        fake_provider,
        log_path,
        state,
        active_budget,
        key_slot="manager_1",
        actor="manager",
        model=model,
        prompt="Create P3A work orders.",
        expected_schema={"kind": "manager_plan"},
        scenario=scenario,
    )
    if manager_result[0] is not None:
        return _finish_failure(run_dir, log_path, manager_result[0], manager_result[1], state)

    work_orders = _build_work_orders()
    _write_json(run_dir / "work_orders.json", work_orders)
    preflight = deterministic_preflight(work_orders, run_dir=run_dir)
    _write_json(run_dir / "preflight_audit.json", preflight)
    if preflight["status"] != "pass":
        return _finish_failure(run_dir, log_path, preflight["failure_type"], preflight["error"], state)

    worker_results_path = run_dir / "worker_results.jsonl"
    completed_work_ids: list[str] = []
    for index, order in enumerate(work_orders["work_orders"]):
        key_slot = WORKER_SLOTS[index]
        failure_type, error, payload = _call_worker(
            fake_provider,
            log_path,
            state,
            active_budget,
            key_slot,
            order,
            scenario,
            model,
        )
        if failure_type is not None:
            _append_log(
                log_path,
                "RUN_FAILED",
                "worker_pool",
                "failure",
                failure_type=failure_type,
                error=error,
                artifact_path="worker_results.jsonl",
            )
            return _finish_failure(run_dir, log_path, failure_type, error, state)
        _append_jsonl(worker_results_path, payload)
        completed_work_ids.append(order["work_id"])

    manager_summary = {
        "used_worker_results": completed_work_ids,
        "rejected_worker_results": [],
        "draft_report": "P3A fake-provider final draft.",
        "ceo_decision_needed": False,
        "manager_self_check": work_orders["manager_self_check"],
    }
    _write_json(run_dir / "manager_summary.json", manager_summary)

    auditor_result = _call_provider(
        fake_provider,
        log_path,
        state,
        active_budget,
        key_slot="auditor_1",
        actor="auditor",
        model=model,
        prompt="Audit P3A worker results.",
        expected_schema={"kind": "audit_report"},
        scenario=scenario,
    )
    if auditor_result[0] is not None:
        return _finish_failure(run_dir, log_path, auditor_result[0], auditor_result[1], state)

    audit_report = {
        "status": "pass",
        "blocking": False,
        "required_fixes": [],
        "warnings": [],
        "ceo_decision_needed": False,
        "audit_summary": "P3A fake-provider audit passed.",
    }
    _write_json(run_dir / "audit_report.json", audit_report)
    _write_text(run_dir / "final_report.md", manager_summary["draft_report"])
    _try_write_ceo_report(run_dir, log_path, "PASS", "P3A fake-provider run passed.", None)
    _append_log(log_path, "RUN_COMPLETED", "harness", "ok")
    return P3ARunResult(resolved_run_id, run_dir, "PASS", None, state["model_calls"])


def _call_worker(
    provider: Provider,
    log_path: Path,
    state: dict[str, int],
    budget: P3ABudget,
    key_slot: str,
    order: dict[str, Any],
    scenario: str,
    model: str,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    failure_type, error, content = _call_provider(
        provider,
        log_path,
        state,
        budget,
        key_slot=key_slot,
        actor=key_slot,
        model=model,
        prompt=f"Execute {order['work_id']}",
        expected_schema=order,
        scenario=scenario,
    )
    if failure_type is None:
        return _validate_worker_payload(content)
    if failure_type != "MODEL_ERROR":
        return (failure_type, error, None)

    if state["consecutive_model_errors"] > budget.max_consecutive_model_errors:
        return ("BUDGET_EXCEEDED", "max_consecutive_model_errors exceeded", None)
    if budget.max_retries_per_call < 1:
        return (failure_type, error, None)

    reserve_failure, reserve_error, reserve_content = _call_provider(
        provider,
        log_path,
        state,
        budget,
        key_slot="reserve_1",
        actor="reserve_1",
        model=model,
        prompt=f"Recover {order['work_id']}",
        expected_schema=order,
        scenario=scenario,
        parent_event_id=f"{key_slot}:MODEL_ERROR",
    )
    if reserve_failure is not None:
        if reserve_failure == "MODEL_ERROR" and state["consecutive_model_errors"] > budget.max_consecutive_model_errors:
            return ("BUDGET_EXCEEDED", "max_consecutive_model_errors exceeded", None)
        return (reserve_failure, reserve_error, None)
    return _validate_worker_payload(reserve_content, recovered_from=key_slot)


def _call_provider(
    provider: Provider,
    log_path: Path,
    state: dict[str, int],
    budget: P3ABudget,
    *,
    key_slot: str,
    actor: str,
    model: str,
    prompt: str,
    expected_schema: dict[str, Any],
    scenario: str,
    parent_event_id: str | None = None,
) -> tuple[str | None, str | None, Any | None]:
    if state["model_calls"] >= budget.max_model_calls:
        _append_log(
            log_path,
            "BUDGET_EXCEEDED",
            actor,
            "failure",
            model=model,
            key_slot=key_slot,
            failure_type="BUDGET_EXCEEDED",
            error="max_model_calls exceeded",
            parent_event_id=parent_event_id,
        )
        return ("BUDGET_EXCEEDED", "max_model_calls exceeded", None)
    if _contains_secret(prompt):
        _append_log(
            log_path,
            "SECURITY_BLOCKED",
            actor,
            "failure",
            model=model,
            key_slot=key_slot,
            failure_type="SECURITY_BLOCKED",
            error="prompt contained a secret-like value",
            parent_event_id=parent_event_id,
        )
        return ("SECURITY_BLOCKED", "prompt contained a secret-like value", None)

    state["model_calls"] += 1
    result = provider.call_model(key_slot, model, prompt, expected_schema, scenario)
    failure_type = FAILURE_BY_PROVIDER_STATUS.get(result.status)
    if result.status == "success":
        state["consecutive_model_errors"] = 0
        _append_log(
            log_path,
            "FAKE_PROVIDER_CALL",
            actor,
            "ok",
            model=model,
            key_slot=key_slot,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            parent_event_id=parent_event_id,
        )
        return (None, None, result.content)

    error = _provider_error_message(result)
    if failure_type == "MODEL_ERROR":
        state["consecutive_model_errors"] += 1
    _append_log(
        log_path,
        "FAKE_PROVIDER_CALL",
        actor,
        "failure",
        model=model,
        key_slot=key_slot,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        failure_type=failure_type,
        error=error,
        artifact_path="worker_results.jsonl" if actor.startswith(("worker_", "reserve_")) else None,
        parent_event_id=parent_event_id,
    )
    if result.raw_output and _contains_secret(result.raw_output):
        return ("SECURITY_BLOCKED", "provider output contained a secret-like value", None)
    return (failure_type, error, None)


def _validate_worker_payload(
    payload: Any,
    *,
    recovered_from: str | None = None,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    if not isinstance(payload, dict):
        return ("SCHEMA_ERROR", "worker payload was not an object", None)
    required = {
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
    missing = sorted(required - set(payload))
    if missing:
        return ("SCHEMA_ERROR", f"worker payload missing fields: {', '.join(missing)}", None)
    if not isinstance(payload["summary"], str) or not isinstance(payload["findings"], list):
        return ("SCHEMA_ERROR", "worker payload field type mismatch", None)
    if not payload["summary"].strip() or (not payload["findings"] and not payload["recommendations"]):
        return ("WORKER_BAD_OUTPUT", "schema-valid worker output was empty", None)
    if _contains_secret(json.dumps(payload, ensure_ascii=False)):
        return ("SECURITY_BLOCKED", "worker payload contained a secret-like value", None)
    if recovered_from:
        payload = dict(payload)
        payload["payload"] = dict(payload["payload"])
        payload["payload"]["recovered_from"] = recovered_from
        payload["payload"]["key_slot"] = "reserve_1"
    return (None, None, payload)


def _build_work_orders() -> dict[str, Any]:
    work_orders = []
    for index, role in enumerate(WORKER_ROLES):
        work_orders.append(
            {
                "work_id": f"wo-{index + 1}",
                "role": role,
                "task": f"Run bounded P3A fake-provider task for {role}.",
                "input_scope": "mission.md and P3A fake provider fixture only",
                "output_schema": {"summary": "string", "findings": "array", "confidence": "number"},
                "forbidden": ["file edit", "shell", "web search", "repo clone", "external URL"],
                "acceptance_condition": "Return schema-valid findings without external calls.",
                "can_edit_files": False,
                "can_run_shell": False,
                "references": [],
            }
        )
    return {
        "mission_interpretation": {"scenario": "p3a_fake_provider"},
        "work_orders": work_orders,
        "manager_self_check": {
            "mission_coverage_summary": "P3A fake-provider run covers four bounded worker tasks.",
            "input_scope_rationale": "Only mission.md and fake provider fixtures are used.",
            "duplicate_risk": "low",
            "known_gaps": [],
        },
    }


def _valid_worker_payload(work_id: str, role: str, raw_output: str) -> dict[str, Any]:
    return {
        "work_id": work_id,
        "role": role,
        "summary": f"{role} completed P3A fake-provider work.",
        "findings": [f"{work_id} fixture finding"],
        "risks": [],
        "recommendations": ["Keep P3A on fake provider until real API work is explicitly requested."],
        "confidence": 0.9,
        "payload": {"key_slot": role},
        "masked_raw_output": _mask_secrets(raw_output),
        "raw_output_saved": False,
        "mask_reason": "raw output is never saved unmasked in P3A",
    }


def _finish_failure(
    run_dir: Path,
    log_path: Path,
    failure_type: str,
    error: str | None,
    state: dict[str, int],
) -> P3ARunResult:
    _try_write_ceo_report(run_dir, log_path, "FAIL", error or failure_type, failure_type)
    return P3ARunResult(run_dir.name, run_dir, "FAIL", failure_type, state["model_calls"])


def _try_write_ceo_report(
    run_dir: Path,
    log_path: Path,
    status: str,
    conclusion: str,
    failure_type: str | None,
) -> None:
    try:
        _write_text(
            run_dir / "ceo_report.md",
            "\n".join(
                [
                    f"상태: {status}",
                    "",
                    "## 결론",
                    conclusion,
                    "",
                    "## 핵심 결정",
                    f"failure_type={failure_type or 'None'}",
                    "",
                    "## 다음 행동",
                    "Review P3A fake-provider artifacts before real provider work.",
                    "",
                ]
            ),
        )
        _append_log(log_path, "CEO_REPORT_CREATED", "harness", "ok", artifact_path="ceo_report.md")
    except Exception as exc:
        _append_log(
            log_path,
            "REPORT_ERROR",
            "harness",
            "failure",
            failure_type="REPORT_ERROR",
            error=f"ceo_report.md write failed after {failure_type}: {exc}",
            artifact_path="ceo_report.md",
            parent_event_id=failure_type,
        )


def _provider_error_message(result: ProviderResult) -> str:
    return {
        "timeout": "provider timeout",
        "rate_limited_429": "provider returned 429",
        "server_error_500": "provider returned 500",
        "provider_unavailable": "provider unavailable",
        "no_response": "provider returned no response",
        "non_json_response": "provider response was not JSON",
        "schema_invalid_json": "provider response failed worker schema",
        "schema_valid_empty": "provider response was empty",
        "security_leak": "provider response contained a secret-like value",
    }.get(result.status, result.error or result.status)


def _append_log(
    log_path: Path,
    event_type: str,
    actor: str,
    status: str,
    *,
    model: str | None = None,
    key_slot: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    failure_type: str | None = None,
    error: str | None = None,
    artifact_path: str | None = None,
    parent_event_id: str | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "actor": actor,
        "model": model,
        "key_slot": key_slot,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "status": status,
        "failure_type": failure_type,
        "error": _mask_secrets(error) if error else None,
        "artifact_path": artifact_path,
        "parent_event_id": parent_event_id,
    }
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


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


def _contains_forbidden_reference(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in FORBIDDEN_REFERENCE_MARKERS)
