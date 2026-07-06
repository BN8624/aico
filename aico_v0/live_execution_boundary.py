# P3R 단일 호출 실행 경계를 실제 호출 없이 검증하는 스켈레톤입니다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_safety import scan_artifacts, scan_value_for_unsafe_content
from .no_call_integration import (
    NO_CALL_INTEGRATION_ARTIFACT_NAME,
    P3QNoCallIntegrationError,
    P3Q_FAILURES,
    validate_no_call_integration,
)

CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME = "call_attempt_summary.json"

P3R_ALLOWED_BOUNDARY_STATUSES = frozenset({"prepared", "ready_for_review", "blocked", "fail"})
P3R_SUCCESS_LIKE_STATUSES = frozenset(
    {
        "success",
        "live_success",
        "api_success",
        "provider_success",
        "executed",
        "called",
        "completed_live_call",
    }
)
P3R_ALLOWED_CALL_ATTEMPT_STATES = frozenset(
    {
        "not_started",
        "precheck_ready",
        "precheck_failed",
        "blocked_before_call",
        "dry_run_ready",
        "dry_run_blocked",
        "no_execute_completed",
        "rollback_required",
        "review_required",
    }
)
P3R_FORBIDDEN_CALL_ATTEMPT_STATES = frozenset(
    {
        "executing",
        "executed",
        "called",
        "provider_called",
        "network_called",
        "sdk_imported",
        "key_loaded",
        "live_success",
        "api_success",
        "provider_success",
        "completed_live_call",
        "retrying",
        "fallback_started",
        "reserve_used",
        "second_call_started",
    }
)
P3R_ALLOWED_TRANSITIONS = {
    "not_started": frozenset({"precheck_ready", "precheck_failed"}),
    "precheck_ready": frozenset({"dry_run_ready", "precheck_failed", "blocked_before_call"}),
    "blocked_before_call": frozenset({"dry_run_blocked"}),
    "dry_run_ready": frozenset({"no_execute_completed"}),
    "dry_run_blocked": frozenset({"rollback_required", "review_required"}),
    "rollback_required": frozenset({"review_required"}),
}
P3R_FORBIDDEN_FIELDS = frozenset(
    {
        "approval_phrase",
        "raw_approval_phrase",
        "raw_output",
        "endpoint_url",
        "raw_key",
        "raw_key_value",
        "key_value",
        "env_var_value",
        "provider_response",
        "token_usage",
    }
)
P3R_FAILURES = {
    **P3Q_FAILURES,
    "success-like status in P3R": "SECURITY_BLOCKED",
    "live_call_allowed true in P3R": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3R": "SECURITY_BLOCKED",
    "forbidden call attempt state": "SECURITY_BLOCKED",
    "unknown call attempt state": "CONFIG_ERROR",
    "invalid call attempt transition": "CONFIG_ERROR",
    "provider response found": "SECURITY_BLOCKED",
    "token usage found": "SECURITY_BLOCKED",
    "retry_allowed true": "SECURITY_BLOCKED",
    "reserve_allowed true": "SECURITY_BLOCKED",
    "fallback_allowed true": "SECURITY_BLOCKED",
    "second_call_allowed true": "SECURITY_BLOCKED",
    "allowlist_widening_allowed true": "SECURITY_BLOCKED",
    "key_slot_change_allowed true": "SECURITY_BLOCKED",
    "raw_output_preservation_allowed true": "SECURITY_BLOCKED",
    "call_model attempted in P3R": "SECURITY_BLOCKED",
    "provider transport attempted in P3R": "SECURITY_BLOCKED",
    "approval package linkage missing": "CONFIG_ERROR",
    "final gate linkage missing": "CONFIG_ERROR",
    "no-call integration linkage missing": "CONFIG_ERROR",
    "run_id mismatch": "CONFIG_ERROR",
    "artifact path outside run_dir": "SECURITY_BLOCKED",
    "path traversal attempted": "SECURITY_BLOCKED",
    "artifact write failure": "REPORT_ERROR",
}


class P3RLiveExecutionBoundaryError(RuntimeError):
    def __init__(self, condition: str, *, failure_type: str | None = None) -> None:
        self.condition = condition
        self.failure_type = failure_type or P3R_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class CallAttemptStateMachineSummary:
    states: tuple[str, ...]
    current_state: str
    live_call_allowed: bool = False
    model_call_count: int = 0

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_call_attempt_state_machine(payload)
        return payload


@dataclass(frozen=True)
class RollbackPlanSummary:
    retry_allowed: bool = False
    reserve_allowed: bool = False
    fallback_allowed: bool = False
    second_call_allowed: bool = False
    allowlist_widening_allowed: bool = False
    key_slot_change_allowed: bool = False
    raw_output_preservation_allowed: bool = False
    review_required: bool = True
    rollback_plan_ref: str = "rollback_plan_summary"

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_rollback_plan(payload)
        return payload


@dataclass(frozen=True)
class LiveExecutionBoundarySummary:
    status: str
    ready_for_review: bool
    execution_boundary_state: str
    call_attempt_state: str
    live_call_allowed: bool
    model_call_count: int
    max_model_calls: int
    max_retries_per_call: int
    reserve_allowed: bool
    fallback_allowed: bool
    second_call_allowed: bool
    provider: str
    model: str
    key_slot: str
    approval_package_ref: str
    final_gate_result_ref: str
    no_call_integration_ref: str
    approval_phrase_hash: str
    artifact_safety_status: str
    rollback_plan_ref: str
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    run_id: str
    call_attempt_states: tuple[str, ...]
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_sdk_import_count: int = 0
    actual_network_call_count: int = 0
    actual_live_smoke_count: int = 0
    call_model_executed: bool = False
    provider_transport_called: bool = False

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_live_execution_boundary(payload)
        return payload


def build_call_attempt_state_machine(
    states: Sequence[str] | None = None,
    *,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
) -> CallAttemptStateMachineSummary:
    path = tuple(states or ("not_started", "precheck_ready", "dry_run_ready", "no_execute_completed"))
    summary = CallAttemptStateMachineSummary(
        states=path,
        current_state=path[-1],
        live_call_allowed=live_call_allowed,
        model_call_count=model_call_count,
    )
    summary.to_summary()
    return summary


def validate_call_attempt_state_machine(summary: Mapping[str, Any]) -> None:
    states = tuple(summary.get("states", ()))
    if not states:
        raise P3RLiveExecutionBoundaryError("unknown call attempt state")
    if summary.get("live_call_allowed") is not False:
        raise P3RLiveExecutionBoundaryError("live_call_allowed true in P3R")
    if summary.get("model_call_count") != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")
    for state in states:
        validate_call_attempt_state(str(state), live_call_allowed=False, model_call_count=0)
    for current, next_state in zip(states, states[1:]):
        if next_state not in P3R_ALLOWED_TRANSITIONS.get(current, frozenset()):
            raise P3RLiveExecutionBoundaryError("invalid call attempt transition")
    if summary.get("current_state") != states[-1]:
        raise P3RLiveExecutionBoundaryError("unknown call attempt state")


def validate_call_attempt_state(
    state: str,
    *,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
) -> None:
    if live_call_allowed is not False:
        raise P3RLiveExecutionBoundaryError("live_call_allowed true in P3R")
    if model_call_count != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")
    if state in P3R_FORBIDDEN_CALL_ATTEMPT_STATES:
        raise P3RLiveExecutionBoundaryError("forbidden call attempt state")
    if state not in P3R_ALLOWED_CALL_ATTEMPT_STATES:
        raise P3RLiveExecutionBoundaryError("unknown call attempt state")


def build_rollback_plan(**overrides: bool) -> RollbackPlanSummary:
    plan = RollbackPlanSummary(**overrides)
    plan.to_summary()
    return plan


def validate_rollback_plan(plan: Mapping[str, Any]) -> None:
    blocked_flags = {
        "retry_allowed": "retry_allowed true",
        "reserve_allowed": "reserve_allowed true",
        "fallback_allowed": "fallback_allowed true",
        "second_call_allowed": "second_call_allowed true",
        "allowlist_widening_allowed": "allowlist_widening_allowed true",
        "key_slot_change_allowed": "key_slot_change_allowed true",
        "raw_output_preservation_allowed": "raw_output_preservation_allowed true",
    }
    for field, condition in blocked_flags.items():
        if plan.get(field) is not False:
            raise P3RLiveExecutionBoundaryError(condition)
    if plan.get("review_required") is not True:
        raise P3RLiveExecutionBoundaryError("missing linkage required field")
    _reject_forbidden_payload(plan)


def build_live_execution_boundary(
    *,
    approval_package: Mapping[str, Any] | None,
    final_gate_result: Mapping[str, Any] | None,
    no_call_integration_summary: Mapping[str, Any] | None,
    status: str = "prepared",
    call_attempt_states: Sequence[str] | None = None,
    rollback_plan: RollbackPlanSummary | Mapping[str, Any] | None = None,
    max_model_calls: int = 1,
    max_retries_per_call: int = 0,
    reserve_allowed: bool = False,
    fallback_allowed: bool = False,
    second_call_allowed: bool = False,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
    raw_output_saved: bool = False,
    call_model_attempted: bool = False,
    provider_transport_attempted: bool = False,
) -> LiveExecutionBoundarySummary:
    validate_pre_call_safety(
        approval_package=approval_package,
        final_gate_result=final_gate_result,
        no_call_integration_summary=no_call_integration_summary,
        live_call_allowed=live_call_allowed,
        model_call_count=model_call_count,
        raw_output_saved=raw_output_saved,
        status=status,
        call_model_attempted=call_model_attempted,
        provider_transport_attempted=provider_transport_attempted,
    )
    if max_model_calls != 1:
        raise P3RLiveExecutionBoundaryError("live call attempted without all gates")
    if max_retries_per_call != 0:
        raise P3RLiveExecutionBoundaryError("retry attempted")
    if reserve_allowed is not False:
        raise P3RLiveExecutionBoundaryError("reserve_allowed true")
    if fallback_allowed is not False:
        raise P3RLiveExecutionBoundaryError("fallback_allowed true")
    if second_call_allowed is not False:
        raise P3RLiveExecutionBoundaryError("second_call_allowed true")
    state_machine = build_call_attempt_state_machine(call_attempt_states)
    rollback_payload = rollback_plan.to_summary() if isinstance(rollback_plan, RollbackPlanSummary) else dict(rollback_plan or build_rollback_plan().to_summary())
    validate_rollback_plan(rollback_payload)
    no_call = dict(no_call_integration_summary or {})
    summary = LiveExecutionBoundarySummary(
        status=status,
        ready_for_review=status == "ready_for_review",
        execution_boundary_state="single_call_no_execute_prepared",
        call_attempt_state=state_machine.current_state,
        live_call_allowed=False,
        model_call_count=0,
        max_model_calls=1,
        max_retries_per_call=0,
        reserve_allowed=False,
        fallback_allowed=False,
        second_call_allowed=False,
        provider=_string(no_call.get("provider")),
        model=_string(no_call.get("model")),
        key_slot=_string(no_call.get("key_slot")),
        approval_package_ref=_string(no_call.get("approval_package_ref")),
        final_gate_result_ref=_string(no_call.get("final_gate_result_ref")),
        no_call_integration_ref=NO_CALL_INTEGRATION_ARTIFACT_NAME,
        approval_phrase_hash=_string(no_call.get("approval_phrase_hash")),
        artifact_safety_status=_string(no_call.get("artifact_safety_status")),
        rollback_plan_ref=_string(rollback_payload.get("rollback_plan_ref")),
        failure_type=None,
        errors=(),
        raw_output_saved=False,
        run_id=_string(no_call.get("run_id")),
        call_attempt_states=state_machine.states,
    )
    summary.to_summary()
    return summary


def build_no_execute_dry_run(
    *,
    approval_package: Mapping[str, Any] | None,
    final_gate_result: Mapping[str, Any] | None,
    no_call_integration_summary: Mapping[str, Any] | None,
    status: str = "ready_for_review",
) -> LiveExecutionBoundarySummary:
    return build_live_execution_boundary(
        approval_package=approval_package,
        final_gate_result=final_gate_result,
        no_call_integration_summary=no_call_integration_summary,
        status=status,
        call_attempt_states=("not_started", "precheck_ready", "dry_run_ready", "no_execute_completed"),
    )


def validate_pre_call_safety(
    *,
    approval_package: Mapping[str, Any] | None,
    final_gate_result: Mapping[str, Any] | None,
    no_call_integration_summary: Mapping[str, Any] | None,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
    raw_output_saved: bool = False,
    status: str = "prepared",
    call_model_attempted: bool = False,
    provider_transport_attempted: bool = False,
) -> None:
    if approval_package is None:
        raise P3RLiveExecutionBoundaryError("approval package linkage missing")
    if final_gate_result is None:
        raise P3RLiveExecutionBoundaryError("final gate linkage missing")
    if no_call_integration_summary is None:
        raise P3RLiveExecutionBoundaryError("no-call integration linkage missing")
    _validate_no_execute_flags(
        status=status,
        live_call_allowed=live_call_allowed,
        model_call_count=model_call_count,
        raw_output_saved=raw_output_saved,
        call_model_attempted=call_model_attempted,
        provider_transport_attempted=provider_transport_attempted,
    )
    try:
        validate_no_call_integration(no_call_integration_summary)
    except P3QNoCallIntegrationError as exc:
        raise _translate_error(exc) from exc
    _validate_safe_payload("approval_package", approval_package)
    _validate_safe_payload("final_gate_result", final_gate_result)
    _validate_safe_payload("no_call_integration", no_call_integration_summary)
    run_ids = {
        _string(approval_package.get("run_id")),
        _string(final_gate_result.get("run_id")),
        _string(no_call_integration_summary.get("run_id")),
    }
    if len(run_ids) != 1:
        raise P3RLiveExecutionBoundaryError("run_id mismatch")
    if approval_package.get("live_call_allowed") is not False:
        raise P3RLiveExecutionBoundaryError("live_call_allowed true in P3R")
    if approval_package.get("model_call_count_before_execution") != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")
    if final_gate_result.get("live_call_allowed") is not False:
        raise P3RLiveExecutionBoundaryError("live_call_allowed true in P3R")
    if final_gate_result.get("model_call_count") != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")


def build_blocked_call_safety_summary(
    *,
    approval_package: Mapping[str, Any] | None,
    final_gate_result: Mapping[str, Any] | None,
    no_call_integration_summary: Mapping[str, Any] | None,
    call_model_attempted: bool = False,
    provider_transport_attempted: bool = False,
) -> LiveExecutionBoundarySummary:
    if call_model_attempted:
        raise P3RLiveExecutionBoundaryError("call_model attempted in P3R")
    if provider_transport_attempted:
        raise P3RLiveExecutionBoundaryError("provider transport attempted in P3R")
    return build_live_execution_boundary(
        approval_package=approval_package,
        final_gate_result=final_gate_result,
        no_call_integration_summary=no_call_integration_summary,
        status="blocked",
        call_attempt_states=("not_started", "precheck_ready", "blocked_before_call", "dry_run_blocked"),
    )


def validate_post_boundary_safety(summary: Mapping[str, Any]) -> None:
    validate_live_execution_boundary(summary)
    _validate_safe_payload("post_boundary", summary)


def validate_live_execution_boundary(summary: Mapping[str, Any]) -> None:
    required = {
        "status",
        "ready_for_review",
        "execution_boundary_state",
        "call_attempt_state",
        "live_call_allowed",
        "model_call_count",
        "max_model_calls",
        "max_retries_per_call",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "provider",
        "model",
        "key_slot",
        "approval_package_ref",
        "final_gate_result_ref",
        "no_call_integration_ref",
        "approval_phrase_hash",
        "artifact_safety_status",
        "rollback_plan_ref",
        "failure_type",
        "errors",
        "raw_output_saved",
        "run_id",
        "call_attempt_states",
    }
    if not required <= set(summary):
        raise P3RLiveExecutionBoundaryError("missing linkage required field")
    _validate_no_execute_flags(
        status=_string(summary.get("status")),
        live_call_allowed=summary.get("live_call_allowed"),
        model_call_count=summary.get("model_call_count"),
        raw_output_saved=summary.get("raw_output_saved"),
        call_model_attempted=summary.get("call_model_executed") is True,
        provider_transport_attempted=summary.get("provider_transport_called") is True,
    )
    if summary.get("max_model_calls") != 1:
        raise P3RLiveExecutionBoundaryError("live call attempted without all gates")
    if summary.get("max_retries_per_call") != 0:
        raise P3RLiveExecutionBoundaryError("retry attempted")
    for field, condition in (
        ("reserve_allowed", "reserve_allowed true"),
        ("fallback_allowed", "fallback_allowed true"),
        ("second_call_allowed", "second_call_allowed true"),
    ):
        if summary.get(field) is not False:
            raise P3RLiveExecutionBoundaryError(condition)
    validate_call_attempt_state_machine(
        {
            "states": tuple(summary.get("call_attempt_states", ())),
            "current_state": summary.get("call_attempt_state"),
            "live_call_allowed": summary.get("live_call_allowed"),
            "model_call_count": summary.get("model_call_count"),
        }
    )
    _validate_safe_payload("live_execution_boundary", summary)
    scan_result = scan_artifacts({CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME: dict(summary)})
    if not scan_result.ok:
        raise P3RLiveExecutionBoundaryError("raw key/token/env var value in approval", failure_type=scan_result.failure_type)


def write_call_attempt_summary(
    run_dir: Path,
    summary: LiveExecutionBoundarySummary | Mapping[str, Any],
    *,
    artifact_name: str = CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
) -> Path:
    payload = summary.to_summary() if isinstance(summary, LiveExecutionBoundarySummary) else dict(summary)
    validate_live_execution_boundary(payload)
    path = resolve_call_attempt_summary_path(run_dir, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3RLiveExecutionBoundaryError("artifact write failure") from exc
    return path


def resolve_call_attempt_summary_path(run_dir: Path, artifact_path: str | Path) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if ".." in requested.parts:
        raise P3RLiveExecutionBoundaryError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3RLiveExecutionBoundaryError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3RLiveExecutionBoundaryError("artifact path outside run_dir")
    if relative.as_posix() != CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME:
        raise P3RLiveExecutionBoundaryError("artifact write failure")
    return resolved


def call_attempt_summary_default_runtime_creation_enabled() -> bool:
    return False


def _validate_no_execute_flags(
    *,
    status: str,
    live_call_allowed: Any,
    model_call_count: Any,
    raw_output_saved: Any,
    call_model_attempted: bool,
    provider_transport_attempted: bool,
) -> None:
    if status in P3R_SUCCESS_LIKE_STATUSES:
        raise P3RLiveExecutionBoundaryError("success-like status in P3R")
    if status not in P3R_ALLOWED_BOUNDARY_STATUSES:
        raise P3RLiveExecutionBoundaryError("unknown gate status")
    if live_call_allowed is not False:
        raise P3RLiveExecutionBoundaryError("live_call_allowed true in P3R")
    if model_call_count != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")
    if raw_output_saved is not False:
        raise P3RLiveExecutionBoundaryError("raw_output_saved=True detected")
    if call_model_attempted:
        raise P3RLiveExecutionBoundaryError("call_model attempted in P3R")
    if provider_transport_attempted:
        raise P3RLiveExecutionBoundaryError("provider transport attempted in P3R")


def _validate_safe_payload(name: str, payload: Mapping[str, Any]) -> None:
    _reject_forbidden_payload(payload)
    if "status" in payload and payload["status"] in P3R_SUCCESS_LIKE_STATUSES:
        raise P3RLiveExecutionBoundaryError("success-like status in P3R")
    if payload.get("live_call_allowed") is True:
        raise P3RLiveExecutionBoundaryError("live_call_allowed true in P3R")
    if payload.get("model_call_count", 0) != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")
    if payload.get("model_call_count_before_execution", 0) != 0:
        raise P3RLiveExecutionBoundaryError("model_call_count > 0 in P3R")
    if payload.get("raw_output_saved") is True:
        raise P3RLiveExecutionBoundaryError("raw_output_saved=True detected")
    if "provider_response" in payload:
        raise P3RLiveExecutionBoundaryError("provider response found")
    if "token_usage" in payload:
        raise P3RLiveExecutionBoundaryError("token usage found")
    if scan_value_for_unsafe_content(dict(payload), value_path=name):
        raise P3RLiveExecutionBoundaryError("raw key/token/env var value in approval")


def _reject_forbidden_payload(payload: Mapping[str, Any]) -> None:
    forbidden = P3R_FORBIDDEN_FIELDS & set(payload)
    if "provider_response" in forbidden:
        raise P3RLiveExecutionBoundaryError("provider response found")
    if "token_usage" in forbidden:
        raise P3RLiveExecutionBoundaryError("token usage found")
    if forbidden:
        raise P3RLiveExecutionBoundaryError("raw key/token/env var value in approval")


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3RLiveExecutionBoundaryError("missing linkage required field")
    return value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _translate_error(exc: P3QNoCallIntegrationError) -> P3RLiveExecutionBoundaryError:
    return P3RLiveExecutionBoundaryError(exc.condition, failure_type=exc.failure_type)
