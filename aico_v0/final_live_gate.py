# P3M final live-call gate를 실제 호출 없이 종합 검증하는 skeleton이다.
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_safety import ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .key_loading_boundary import (
    KeyExistenceSummary,
    KeyLoadingBoundaryError,
    KeyLoadingBoundaryState,
    validate_key_existence_summary,
    validate_key_loading_boundary_state,
)
from .live_smoke import (
    FAILURE_TYPE_BY_SMOKE_CONDITION,
    FALSE_FLAG_VALUES,
    FORBIDDEN_LIVE_SMOKE_ARTIFACTS,
    REQUIRED_LIVE_SMOKE_FLAGS,
    TRUE_FLAG_VALUES,
    FirstLiveSmokeApproval,
)
from .live_smoke_artifacts import CANONICAL_FAILURE_TYPES
from .provider_allowlist import (
    ProviderAllowlistSkeletonError,
    ProviderAllowlistState,
    validate_allowlist_state,
)
from .sdk_boundary import SDKBoundaryError, SDKBoundaryState, validate_sdk_boundary_state

FINAL_GATE_REQUIRED_GATES = (
    "approval_phrase_gate",
    "provider_allowlist_gate",
    "provider_candidate_gate",
    "sdk_boundary_gate",
    "key_loading_boundary_gate",
    "key_existence_gate",
    "runtime_flags_gate",
    "budget_gate",
    "prompt_safety_gate",
    "expected_output_schema_gate",
    "artifact_write_plan_gate",
    "artifact_safety_pre_scan_gate",
    "live_call_disabled_gate",
)
FINAL_GATE_ALLOWED_STATUSES = frozenset(
    {"pass", "fail", "not_run", "not_applicable", "blocked", "prepared", "ready_for_review"}
)
FINAL_GATE_FORBIDDEN_STATUSES = frozenset(
    {"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"}
)
FINAL_GATE_ALLOWED_ARTIFACTS = frozenset(
    {
        "run_log.jsonl",
        "ceo_report.md",
        "live_smoke_result.json",
        "artifact_safety_report.json",
        "final_live_gate_result.json",
    }
)
FINAL_GATE_FAILURE_PRIORITY = (
    "SECURITY_BLOCKED",
    "BUDGET_EXCEEDED",
    "REPORT_ERROR",
    "CONFIG_ERROR",
    "HUMAN_DECISION_REQUIRED",
    "MODEL_ERROR",
    "SCHEMA_ERROR",
    "WORKER_BAD_OUTPUT",
)
FINAL_GATE_FAILURES = {
    **FAILURE_TYPE_BY_SMOKE_CONDITION,
}
_UNSAFE_PUBLIC_VALUE_PATTERN = re.compile(
    r"https?://|[A-Za-z0-9.-]+\.[A-Za-z]{2,}|sk-[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9._-]{10,}",
    re.IGNORECASE,
)


class FinalLiveGateError(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = FINAL_GATE_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class FinalGateCheck:
    name: str
    status: str
    required: bool = True
    failure_type: str | None = None
    message: str | None = None

    def to_summary(self) -> dict[str, object]:
        _validate_gate_status(self.status)
        _validate_failure_type(self.failure_type)
        return {
            "name": self.name,
            "status": self.status,
            "required": self.required,
            "failure_type": self.failure_type,
            "message": _mask_public_value(self.message),
        }


@dataclass(frozen=True)
class FinalLiveGateResult:
    status: str
    overall_pass: bool
    ready_for_review: bool
    live_call_allowed: bool
    model_call_count: int
    provider: str | None
    model: str | None
    key_slot: str | None
    gates: tuple[FinalGateCheck, ...]
    failure_type: str | None
    errors: tuple[str, ...]
    artifact_safety_status: str
    raw_output_saved: bool
    timestamp: str | None = None
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_network_call_count: int = 0
    provider_sdk_imported: bool = False
    live_smoke_executed: bool = False

    def to_summary(self) -> dict[str, object]:
        payload = {
            "status": self.status,
            "overall_pass": self.overall_pass,
            "ready_for_review": self.ready_for_review,
            "live_call_allowed": self.live_call_allowed,
            "model_call_count": self.model_call_count,
            "provider": self.provider,
            "model": self.model,
            "key_slot": self.key_slot,
            "gates": [gate.to_summary() for gate in self.gates],
            "failure_type": self.failure_type,
            "errors": [_mask_public_value(error) for error in self.errors],
            "artifact_safety_status": self.artifact_safety_status,
            "raw_output_saved": self.raw_output_saved,
            "timestamp": self.timestamp,
            "actual_api_call_count": self.actual_api_call_count,
            "actual_llm_call_count": self.actual_llm_call_count,
            "actual_key_value_read_count": self.actual_key_value_read_count,
            "actual_network_call_count": self.actual_network_call_count,
            "provider_sdk_imported": self.provider_sdk_imported,
            "live_smoke_executed": self.live_smoke_executed,
        }
        validate_final_live_gate_result_payload(payload)
        return payload


def validate_final_live_gate(
    *,
    approval: FirstLiveSmokeApproval | None,
    provider_allowlist_state: ProviderAllowlistState | None,
    sdk_boundary: SDKBoundaryState | None,
    key_loading_boundary: KeyLoadingBoundaryState | None,
    key_existence_summary: Mapping[str, object] | KeyExistenceSummary | None,
    flags: Mapping[str, str] | None,
    budget: Mapping[str, int] | None,
    prompt_package: Any,
    expected_output_schema: Any,
    artifact_write_plan: Sequence[str] | None,
    artifact_safety_pre_scan: ArtifactSafetyResult | None,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
    result_status: str | None = None,
    timestamp: str | None = None,
) -> FinalLiveGateResult:
    gates = (
        _approval_phrase_gate(approval),
        _provider_allowlist_gate(provider_allowlist_state),
        _provider_candidate_gate(provider_allowlist_state),
        _sdk_boundary_gate(sdk_boundary),
        _key_loading_boundary_gate(key_loading_boundary),
        _key_existence_gate(key_existence_summary),
        _runtime_flags_gate(flags),
        _budget_gate(budget, model_call_count=model_call_count),
        _scan_gate("prompt_safety_gate", prompt_package),
        _scan_gate("expected_output_schema_gate", expected_output_schema),
        _artifact_write_plan_gate(artifact_write_plan),
        _artifact_safety_pre_scan_gate(artifact_safety_pre_scan),
        _live_call_disabled_gate(live_call_allowed=live_call_allowed, model_call_count=model_call_count),
    )
    return build_final_live_gate_result(
        approval=approval,
        gates=gates,
        live_call_allowed=live_call_allowed,
        model_call_count=model_call_count,
        status=result_status,
        timestamp=timestamp,
    )


def build_final_live_gate_result(
    *,
    approval: FirstLiveSmokeApproval | None,
    gates: Sequence[FinalGateCheck],
    live_call_allowed: bool = False,
    model_call_count: int = 0,
    status: str | None = None,
    timestamp: str | None = None,
) -> FinalLiveGateResult:
    checked_gates = tuple(gates)
    _validate_required_gates(checked_gates)
    for gate in checked_gates:
        _validate_gate_status(gate.status)
        _validate_failure_type(gate.failure_type)

    if live_call_allowed:
        checked_gates += (_gate_fail("live_call_disabled_gate", "live_call_allowed true in P3M"),)
    if model_call_count > 0:
        checked_gates += (_gate_fail("budget_gate", "model_call_count > 0 in P3M"),)

    final_failure_type = choose_final_failure_type(checked_gates)
    overall_pass = final_failure_type is None
    final_status = status or ("ready_for_review" if overall_pass else "blocked")
    if final_status in FINAL_GATE_FORBIDDEN_STATUSES:
        raise FinalLiveGateError("success-like status in P3M")
    if final_status not in FINAL_GATE_ALLOWED_STATUSES:
        raise FinalLiveGateError("unknown gate status")

    result = FinalLiveGateResult(
        status=final_status,
        overall_pass=overall_pass,
        ready_for_review=overall_pass,
        live_call_allowed=False,
        model_call_count=0,
        provider=approval.provider if approval else None,
        model=approval.model if approval else None,
        key_slot=_single_key_slot(approval) if approval else None,
        gates=checked_gates,
        failure_type=final_failure_type,
        errors=tuple(gate.message or gate.name for gate in checked_gates if gate.failure_type),
        artifact_safety_status=_artifact_safety_status_from_gates(checked_gates),
        raw_output_saved=False,
        timestamp=timestamp,
    )
    result.to_summary()
    return result


def choose_final_failure_type(gates: Sequence[FinalGateCheck]) -> str | None:
    failures = {gate.failure_type for gate in gates if gate.failure_type}
    for failure_type in FINAL_GATE_FAILURE_PRIORITY:
        if failure_type in failures:
            return failure_type
    return None


def validate_final_live_gate_result_payload(payload: Mapping[str, Any]) -> None:
    forbidden_fields = {"raw_output", "raw_key", "raw_key_value", "env_var_value", "endpoint_url"}
    if forbidden_fields & set(payload):
        raise FinalLiveGateError("raw key found")
    if payload.get("live_call_allowed") is not False:
        raise FinalLiveGateError("live_call_allowed true in P3M")
    if payload.get("model_call_count") != 0:
        raise FinalLiveGateError("model_call_count > 0 in P3M")
    if payload.get("raw_output_saved") is not False:
        raise FinalLiveGateError("raw_output_saved=True detected")
    status = str(payload.get("status"))
    if status in FINAL_GATE_FORBIDDEN_STATUSES:
        raise FinalLiveGateError("success-like status in P3M")
    if status not in FINAL_GATE_ALLOWED_STATUSES:
        raise FinalLiveGateError("unknown gate status")
    _validate_failure_type(payload.get("failure_type"))
    for field in ("provider", "model", "key_slot"):
        value = payload.get(field)
        if isinstance(value, str) and _has_unsafe_public_value(value):
            raise FinalLiveGateError("raw key found")
    for gate in payload.get("gates", ()):
        if isinstance(gate, Mapping):
            _validate_gate_status(str(gate.get("status")))
            _validate_failure_type(gate.get("failure_type"))
            message = gate.get("message")
            if isinstance(message, str) and _has_unsafe_public_value(message):
                raise FinalLiveGateError("raw key found")
    for error in payload.get("errors", ()):
        if isinstance(error, str) and _has_unsafe_public_value(error):
            raise FinalLiveGateError("raw key found")


def write_final_live_gate_result(
    run_dir: Path,
    result: FinalLiveGateResult,
    *,
    artifact_name: str = "final_live_gate_result.json",
) -> Path:
    payload = result.to_summary()
    scan_result = scan_artifacts({"final_live_gate_result.json": payload})
    if not scan_result.ok:
        raise FinalLiveGateError(scan_result.findings[0].reason if scan_result.failure_type == "CONFIG_ERROR" else "raw key found")
    path = resolve_final_gate_artifact_path(run_dir, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise FinalLiveGateError("artifact write failure") from exc
    return path


def resolve_final_gate_artifact_path(run_dir: Path, artifact_path: str | Path) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if ".." in requested.parts:
        raise FinalLiveGateError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise FinalLiveGateError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise FinalLiveGateError("artifact path outside run_dir")
    relative_name = relative.as_posix()
    if relative.name in FORBIDDEN_LIVE_SMOKE_ARTIFACTS or relative_name in FORBIDDEN_LIVE_SMOKE_ARTIFACTS:
        raise FinalLiveGateError("forbidden artifact attempted")
    if relative_name not in FINAL_GATE_ALLOWED_ARTIFACTS:
        raise FinalLiveGateError("artifact write failure")
    return resolved


def _approval_phrase_gate(approval: FirstLiveSmokeApproval | None) -> FinalGateCheck:
    if approval is None or not approval.approved_by_user:
        return _gate_fail("approval_phrase_gate", "approval missing")
    if _approval_has_unsafe_content(approval):
        return _gate_fail("approval_phrase_gate", "raw key found")
    if approval.approval_phrase and approval.approval_phrase.strip().lower() in {"continue", "proceed", "go ahead", "ok"}:
        return _gate_fail("approval_phrase_gate", "approval ambiguous")
    if (
        not approval.provider
        or not approval.model
        or approval.key_slot is None
        or approval.max_model_calls is None
        or approval.max_retries_per_call is None
        or approval.max_runtime_seconds is None
        or approval.allow_raw_output is None
    ):
        return _gate_fail("approval_phrase_gate", "required approval field missing")
    if approval.allow_raw_output is not False:
        return _gate_fail("approval_phrase_gate", "allow_raw_output not false")
    key_slots = _key_slots_tuple(approval.key_slot)
    if len(key_slots) != 1:
        return _gate_fail("approval_phrase_gate", "required approval field missing")
    if approval.max_model_calls != 1:
        return _gate_fail("approval_phrase_gate", "live call attempted without all gates")
    if approval.max_retries_per_call != 0:
        return _gate_fail("approval_phrase_gate", "retry attempted")
    return _gate_pass("approval_phrase_gate")


def _provider_allowlist_gate(state: ProviderAllowlistState | None) -> FinalGateCheck:
    if state is None:
        return _gate_fail("provider_allowlist_gate", "provider allowlist missing")
    if state.state == "empty":
        return _gate_fail("provider_allowlist_gate", "provider allowlist empty")
    try:
        validate_allowlist_state(state)
    except ProviderAllowlistSkeletonError as exc:
        return _gate_fail("provider_allowlist_gate", exc.condition)
    return _gate_pass("provider_allowlist_gate")


def _provider_candidate_gate(state: ProviderAllowlistState | None) -> FinalGateCheck:
    if state is None:
        return _gate_fail("provider_candidate_gate", "provider allowlist missing")
    if state.state != "candidate":
        return _gate_fail("provider_candidate_gate", "provider allowlist empty")
    try:
        validate_allowlist_state(state)
    except ProviderAllowlistSkeletonError as exc:
        return _gate_fail("provider_candidate_gate", exc.condition)
    if state.authorizes_live_call or state.authorizes_sdk_import or state.authorizes_key_loading:
        return _gate_fail("provider_candidate_gate", "candidate interpreted as active")
    return _gate_pass("provider_candidate_gate")


def _sdk_boundary_gate(boundary: SDKBoundaryState | None) -> FinalGateCheck:
    if boundary is None:
        return _gate_fail("sdk_boundary_gate", "SDK boundary missing")
    if boundary.sdk_import_allowed is not False:
        return _gate_fail("sdk_boundary_gate", "SDK import allowed true in P3M")
    try:
        validate_sdk_boundary_state(boundary)
    except SDKBoundaryError as exc:
        return _gate_fail("sdk_boundary_gate", exc.condition)
    return _gate_pass("sdk_boundary_gate")


def _key_loading_boundary_gate(boundary: KeyLoadingBoundaryState | None) -> FinalGateCheck:
    if boundary is None:
        return _gate_fail("key_loading_boundary_gate", "key loading boundary missing")
    if boundary.key_loading_allowed is not False:
        return _gate_fail("key_loading_boundary_gate", "key loading allowed true in P3M")
    try:
        validate_key_loading_boundary_state(boundary)
    except KeyLoadingBoundaryError as exc:
        return _gate_fail("key_loading_boundary_gate", exc.condition)
    return _gate_pass("key_loading_boundary_gate")


def _key_existence_gate(summary: Mapping[str, object] | KeyExistenceSummary | None) -> FinalGateCheck:
    if summary is None:
        return _gate_fail("key_existence_gate", "key missing")
    data = summary.to_summary() if isinstance(summary, KeyExistenceSummary) else dict(summary)
    try:
        validate_key_existence_summary(data)
    except KeyLoadingBoundaryError as exc:
        return _gate_fail("key_existence_gate", exc.condition)
    if data.get("exists") is not True:
        return _gate_fail("key_existence_gate", "key missing")
    return _gate_pass("key_existence_gate")


def _runtime_flags_gate(flags: Mapping[str, str] | None) -> FinalGateCheck:
    if flags is None:
        return _gate_fail("runtime_flags_gate", "runtime flag missing")
    if scan_value_for_unsafe_content(flags, value_path="flags"):
        return _gate_fail("runtime_flags_gate", "raw key found")
    for flag_name in REQUIRED_LIVE_SMOKE_FLAGS:
        if flag_name not in flags:
            return _gate_fail("runtime_flags_gate", "runtime flag missing")
        normalized = flags[flag_name].strip().lower()
        if normalized in FALSE_FLAG_VALUES or normalized not in TRUE_FLAG_VALUES:
            return _gate_fail("runtime_flags_gate", "runtime flag false")
    return _gate_pass("runtime_flags_gate")


def _budget_gate(budget: Mapping[str, int] | None, *, model_call_count: int) -> FinalGateCheck:
    if budget is None:
        return _gate_fail("budget_gate", "budget missing")
    required = ("max_model_calls", "max_retries_per_call", "max_consecutive_model_errors", "max_runtime_seconds")
    if any(field not in budget for field in required):
        return _gate_fail("budget_gate", "budget missing")
    if model_call_count > 0:
        return _gate_fail("budget_gate", "model_call_count > 0 in P3M")
    if budget["max_model_calls"] != 1:
        return _gate_fail("budget_gate", "live call attempted without all gates")
    if budget["max_retries_per_call"] != 0:
        return _gate_fail("budget_gate", "retry attempted")
    if budget["max_consecutive_model_errors"] != 1 or budget["max_runtime_seconds"] <= 0:
        return _gate_fail("budget_gate", "budget invalid")
    return _gate_pass("budget_gate")


def _scan_gate(name: str, payload: Any) -> FinalGateCheck:
    if payload is None:
        return _gate_fail(name, "required gate not_run")
    scan = scan_artifacts({name: payload})
    if not scan.ok:
        condition = "artifact safety scan missing" if scan.failure_type == "CONFIG_ERROR" else "raw key found"
        return _gate_fail(name, condition)
    return _gate_pass(name)


def _artifact_write_plan_gate(plan: Sequence[str] | None) -> FinalGateCheck:
    if plan is None:
        return _gate_fail("artifact_write_plan_gate", "required gate not_run")
    for artifact_name in plan:
        if artifact_name in FORBIDDEN_LIVE_SMOKE_ARTIFACTS:
            return _gate_fail("artifact_write_plan_gate", "forbidden artifact attempted")
        if artifact_name not in FINAL_GATE_ALLOWED_ARTIFACTS:
            return _gate_fail("artifact_write_plan_gate", "artifact write failure")
    return _gate_pass("artifact_write_plan_gate")


def _artifact_safety_pre_scan_gate(scan: ArtifactSafetyResult | None) -> FinalGateCheck:
    if scan is None:
        return _gate_fail("artifact_safety_pre_scan_gate", "artifact safety scan missing")
    if not scan.ok:
        return _gate_fail(
            "artifact_safety_pre_scan_gate",
            "artifact safety scan missing" if scan.failure_type == "CONFIG_ERROR" else "artifact safety scan failed",
        )
    return _gate_pass("artifact_safety_pre_scan_gate")


def _live_call_disabled_gate(*, live_call_allowed: bool, model_call_count: int) -> FinalGateCheck:
    if live_call_allowed:
        return _gate_fail("live_call_disabled_gate", "live_call_allowed true in P3M")
    if model_call_count > 0:
        return _gate_fail("live_call_disabled_gate", "model_call_count > 0 in P3M")
    return _gate_pass("live_call_disabled_gate")


def _validate_required_gates(gates: Sequence[FinalGateCheck]) -> None:
    found = {gate.name for gate in gates}
    if not set(FINAL_GATE_REQUIRED_GATES) <= found:
        raise FinalLiveGateError("required gate not_run")
    for gate in gates:
        if gate.required and gate.status == "not_run":
            raise FinalLiveGateError("required gate not_run")


def _gate_pass(name: str) -> FinalGateCheck:
    return FinalGateCheck(name=name, status="pass", required=True)


def _gate_fail(name: str, condition: str) -> FinalGateCheck:
    return FinalGateCheck(
        name=name,
        status="fail",
        required=True,
        failure_type=FINAL_GATE_FAILURES[condition],
        message=condition,
    )


def _validate_gate_status(status: str) -> None:
    if status in FINAL_GATE_FORBIDDEN_STATUSES:
        raise FinalLiveGateError("success-like status in P3M")
    if status not in FINAL_GATE_ALLOWED_STATUSES:
        raise FinalLiveGateError("unknown gate status")


def _validate_failure_type(failure_type: object) -> None:
    if failure_type is not None and str(failure_type) not in CANONICAL_FAILURE_TYPES:
        raise FinalLiveGateError("unknown failure_type")


def _approval_has_unsafe_content(approval: FirstLiveSmokeApproval) -> bool:
    return bool(scan_value_for_unsafe_content(approval.__dict__, value_path="approval")) or _value_has_url(approval.__dict__)


def _value_has_url(value: Any) -> bool:
    if isinstance(value, str):
        return bool(re.search(r"https?://", value, re.IGNORECASE))
    if isinstance(value, Mapping):
        return any(_value_has_url(key) or _value_has_url(item) for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_value_has_url(item) for item in value)
    return False


def _key_slots_tuple(key_slot_value: str | tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if key_slot_value is None:
        return ()
    if isinstance(key_slot_value, str):
        return (key_slot_value,)
    return tuple(key_slot_value)


def _single_key_slot(approval: FirstLiveSmokeApproval) -> str | None:
    key_slots = _key_slots_tuple(approval.key_slot)
    if len(key_slots) != 1:
        return None
    return key_slots[0]


def _artifact_safety_status_from_gates(gates: Sequence[FinalGateCheck]) -> str:
    for gate in gates:
        if gate.name == "artifact_safety_pre_scan_gate":
            if gate.status == "pass":
                return "pass"
            if gate.failure_type == "CONFIG_ERROR":
                return "missing"
            return "fail"
    return "not_run"


def _has_unsafe_public_value(value: str) -> bool:
    return bool(_UNSAFE_PUBLIC_VALUE_PATTERN.search(value))


def _mask_public_value(value: str | None) -> str | None:
    if value is None:
        return None
    if _has_unsafe_public_value(value):
        return "[BLOCKED_VALUE]"
    return value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
