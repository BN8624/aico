# P3V live-fire 체크리스트를 실제 호출 없이 검증하는 스켈레톤입니다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_safety import ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .explicit_approval_gate import (
    ARMED_STATE_ARTIFACT_NAME,
    EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME,
    P3U_FAILURES,
    P3UExplicitApprovalGateError,
    validate_armed_but_not_fired_state,
    validate_explicit_approval_gate,
)
from .final_live_approval_packet import FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME, HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME
from .live_execution_boundary import CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME
from .no_call_integration import NO_CALL_INTEGRATION_ARTIFACT_NAME
from .pre_live_package import PRE_LIVE_FAILURE_PRIORITY, PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME, validate_approval_phrase_hash

LIVE_FIRE_CHECKLIST_ARTIFACT_NAME = "live_fire_checklist.json"
LAST_STOP_GUARD_ARTIFACT_NAME = "last_stop_guard.json"
ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME = "one_shot_fire_plan.json"
EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME = "expected_live_artifacts.json"

LIVE_FIRE_CHECKLIST_SCHEMA_VERSION = "p3_live_fire_checklist_v1"
LAST_STOP_GUARD_SCHEMA_VERSION = "p3_last_stop_guard_v1"
ONE_SHOT_FIRE_PLAN_SCHEMA_VERSION = "p3_one_shot_fire_plan_v1"
EXPECTED_LIVE_ARTIFACTS_SCHEMA_VERSION = "p3_expected_live_artifacts_v1"
ROLLBACK_CONFIRMATION_SCHEMA_VERSION = "p3_final_rollback_confirmation_v1"
LIVE_FIRE_CHECKLIST_CREATED_FOR = "live_fire_checklist_still_no_call"
ONE_SHOT_FIRE_PLAN_TYPE = "one_shot_fire_plan_no_execute"

P3V_ALLOWED_CHECKLIST_STATUSES = frozenset({"fire_checklist_ready", "still_no_call", "prepared", "ready_for_final_review", "blocked", "fail"})
P3V_ALLOWED_FIRE_PLAN_MODES = frozenset({"review_only", "no_execute", "still_no_call"})
P3V_ALLOWED_FIRE_STATES = frozenset({"not_ready", "checklist_ready", "last_stop_ready", "fire_plan_ready", "still_no_call", "review_required", "blocked"})
P3V_FORBIDDEN_FIRE_STATES = frozenset(
    {
        "firing",
        "fired",
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
        "armed_and_fired",
        "fire_command_issued",
    }
)
P3V_ALLOWED_FIRE_TRANSITIONS = {
    "not_ready": frozenset({"checklist_ready", "review_required", "blocked"}),
    "checklist_ready": frozenset({"last_stop_ready", "review_required", "blocked"}),
    "last_stop_ready": frozenset({"fire_plan_ready", "review_required", "blocked"}),
    "fire_plan_ready": frozenset({"still_no_call", "review_required", "blocked"}),
    "still_no_call": frozenset({"review_required", "blocked"}),
    "review_required": frozenset({"checklist_ready", "blocked"}),
}
P3V_SUCCESS_LIKE_STATUSES = frozenset({"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call", "fired"})
P3V_APPROVAL_LIKE_STATUSES = frozenset({"approved", "granted", "confirmed", "live_approved", "fire_approved", "execution_granted"})
P3V_FORBIDDEN_FIELDS = frozenset(
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
P3V_ALLOWED_EXPECTED_ARTIFACTS = frozenset(
    {"live_smoke_result.json", "artifact_safety_report.json", "final_live_gate_result.json", "call_attempt_summary.json"}
)
P3V_REQUIRED_LAST_STOP_ITEMS = (
    "explicit_approval_gate_present",
    "armed_state_present",
    "fire_ready_review_only",
    "fired_false",
    "execution_allowed_false",
    "live_call_allowed_false",
    "model_call_count_zero",
    "call_model_count_zero",
    "provider_not_activated",
    "sdk_not_imported",
    "key_not_loaded",
    "network_not_called",
    "call_model_not_called",
    "no_retry_confirmed",
    "no_reserve_confirmed",
    "no_fallback_confirmed",
    "no_second_call_confirmed",
    "rollback_policy_present",
    "expected_artifacts_defined",
    "actual_live_result_absent",
)
P3V_FORBIDDEN_COMMAND_TOKENS = frozenset(
    {
        "--execute",
        "--live",
        "--fire",
        "--call-model",
        "--load-key",
        "--use-key",
        "--network",
        "--sdk-import",
        "--provider-activate",
        "--allowlist-activate",
        "--confirm-live",
        "--live-call-allowed",
        "--armed-execute",
    }
)
P3V_FAILURES = {
    **P3U_FAILURES,
    "missing required checklist item": "CONFIG_ERROR",
    "missing required last-stop item": "CONFIG_ERROR",
    "missing required fire plan item": "CONFIG_ERROR",
    "missing required expected artifact item": "CONFIG_ERROR",
    "missing required rollback item": "CONFIG_ERROR",
    "missing required artifact reference": "CONFIG_ERROR",
    "success-like status in P3V": "SECURITY_BLOCKED",
    "approval-like status in P3V": "SECURITY_BLOCKED",
    "fired true in P3V": "SECURITY_BLOCKED",
    "execution_allowed true in P3V": "SECURITY_BLOCKED",
    "live_call_allowed true in P3V": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3V": "SECURITY_BLOCKED",
    "call_model_count > 0 in P3V": "SECURITY_BLOCKED",
    "forbidden fire readiness state": "SECURITY_BLOCKED",
    "unknown fire readiness state": "CONFIG_ERROR",
    "invalid fire readiness transition": "CONFIG_ERROR",
    "actual live result present": "SECURITY_BLOCKED",
    "fire command token found": "SECURITY_BLOCKED",
    "forbidden expected artifact": "SECURITY_BLOCKED",
    "unsafe expected artifact ref": "SECURITY_BLOCKED",
    "run_id mismatch": "CONFIG_ERROR",
    "approval_phrase_hash mismatch": "CONFIG_ERROR",
    "raw key/token/env var value in approval": "SECURITY_BLOCKED",
    "raw approval phrase found": "SECURITY_BLOCKED",
    "provider response found": "SECURITY_BLOCKED",
    "token usage found": "SECURITY_BLOCKED",
    "raw_output_saved=True detected": "SECURITY_BLOCKED",
    "scan failed": "SECURITY_BLOCKED",
    "pre-scan missing": "CONFIG_ERROR",
    "post-scan missing": "CONFIG_ERROR",
    "artifact write failure": "REPORT_ERROR",
    "unsafe artifact reference": "SECURITY_BLOCKED",
    "path traversal attempted": "SECURITY_BLOCKED",
    "artifact path outside run_dir": "SECURITY_BLOCKED",
    "missing approval_phrase_hash": "CONFIG_ERROR",
    "retry_allowed true": "SECURITY_BLOCKED",
    "reserve_allowed true": "SECURITY_BLOCKED",
    "fallback_allowed true": "SECURITY_BLOCKED",
    "second_call_allowed true": "SECURITY_BLOCKED",
    "allowlist_widening_allowed true": "SECURITY_BLOCKED",
    "key_slot_change_allowed true": "SECURITY_BLOCKED",
    "provider_rotation_allowed true": "SECURITY_BLOCKED",
    "budget_reset_allowed true": "SECURITY_BLOCKED",
    "budget_spent true": "SECURITY_BLOCKED",
    "SDK import marker in P3S": "SECURITY_BLOCKED",
    "key loaded marker in P3S": "SECURITY_BLOCKED",
    "network call marker in P3S": "SECURITY_BLOCKED",
    "live smoke marker in P3S": "SECURITY_BLOCKED",
    "call_model attempted in P3R": "SECURITY_BLOCKED",
    "candidate interpreted as active": "SECURITY_BLOCKED",
}


class P3VLiveFireChecklistError(RuntimeError):
    def __init__(self, condition: str, *, failure_type: str | None = None) -> None:
        self.condition = condition
        self.failure_type = failure_type or P3V_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class RollbackConfirmation:
    schema_version: str = ROLLBACK_CONFIRMATION_SCHEMA_VERSION
    retry_allowed: bool = False
    reserve_allowed: bool = False
    fallback_allowed: bool = False
    second_call_allowed: bool = False
    rollback_required_on_failure: bool = True
    preserve_raw_output: bool = False
    allowlist_widening_allowed: bool = False
    key_slot_change_allowed: bool = False
    provider_rotation_allowed: bool = False
    budget_reset_allowed: bool = False

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_rollback_confirmation(payload)
        return payload


@dataclass(frozen=True)
class ExpectedLiveArtifacts:
    schema_version: str
    run_id: str
    artifact_names: tuple[str, ...]
    artifact_refs: dict[str, str]
    raw_contents_saved: bool
    failure_type: str | None
    errors: tuple[str, ...]

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_expected_live_artifacts(payload)
        return payload


@dataclass(frozen=True)
class OneShotFirePlan:
    schema_version: str
    run_id: str
    plan_type: str
    fire_plan_mode: str
    fire_ready: bool
    fired: bool
    execution_allowed: bool
    live_call_allowed: bool
    max_model_calls: int
    model_call_count: int
    call_model_count: int
    max_retries_per_call: int
    retry_allowed: bool
    reserve_allowed: bool
    fallback_allowed: bool
    second_call_allowed: bool
    provider_rotation_allowed: bool
    key_rotation_allowed: bool
    rollback_policy_ref: str
    expected_live_artifacts_ref: str
    command_skeleton: str
    failure_type: str | None
    errors: tuple[str, ...]

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_one_shot_fire_plan(payload)
        return payload


@dataclass(frozen=True)
class LastStopGuard:
    schema_version: str
    run_id: str
    status: str
    required_items: dict[str, bool]
    fire_ready: bool
    armed: bool
    fired: bool
    execution_allowed: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    created_for: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_last_stop_guard(payload)
        return payload


@dataclass(frozen=True)
class LiveFireChecklist:
    schema_version: str
    run_id: str
    status: str
    ready_for_final_review: bool
    fire_ready: bool
    fire_readiness_states: tuple[str, ...]
    armed: bool
    fired: bool
    execution_allowed: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    last_stop_guard_status: str
    one_shot_fire_plan_ref: str
    expected_live_artifacts_ref: str
    explicit_approval_gate_ref: str
    armed_state_ref: str
    final_live_approval_packet_ref: str
    human_confirmation_checklist_ref: str
    pre_live_package_manifest_ref: str
    live_execution_boundary_ref: str
    no_call_integration_summary_ref: str
    call_attempt_summary_ref: str
    final_gate_result_ref: str
    approval_phrase_hash: str
    approval_phrase_ref: str
    provider: str
    model: str
    key_slot: str
    no_retry_confirmed: bool
    no_reserve_confirmed: bool
    no_fallback_confirmed: bool
    no_second_call_confirmed: bool
    rollback_policy_ref: str
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    created_for: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_live_fire_checklist(payload)
        return payload


def build_expected_live_artifacts(
    *,
    run_id: str,
    artifact_names: Sequence[str] = tuple(sorted(P3V_ALLOWED_EXPECTED_ARTIFACTS)),
    artifact_refs: Mapping[str, str] | None = None,
) -> ExpectedLiveArtifacts:
    refs = dict(artifact_refs or {name: name for name in artifact_names})
    summary = ExpectedLiveArtifacts(
        schema_version=EXPECTED_LIVE_ARTIFACTS_SCHEMA_VERSION,
        run_id=run_id,
        artifact_names=tuple(artifact_names),
        artifact_refs=refs,
        raw_contents_saved=False,
        failure_type=None,
        errors=(),
    )
    summary.to_summary()
    return summary


def build_rollback_confirmation(**overrides: object) -> RollbackConfirmation:
    confirmation = RollbackConfirmation(**overrides)
    confirmation.to_summary()
    return confirmation


def build_one_shot_fire_plan(
    *,
    run_id: str,
    rollback_policy_ref: str = "rollback_policy.json",
    expected_live_artifacts_ref: str = EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME,
    command_skeleton: str = "python -m aico_v0.live_smoke --dry-run --no-execute --review-only",
    fire_ready: bool = True,
    fire_plan_mode: str = "no_execute",
    **overrides: object,
) -> OneShotFirePlan:
    values = {
        "schema_version": ONE_SHOT_FIRE_PLAN_SCHEMA_VERSION,
        "run_id": run_id,
        "plan_type": ONE_SHOT_FIRE_PLAN_TYPE,
        "fire_plan_mode": fire_plan_mode,
        "fire_ready": fire_ready,
        "fired": False,
        "execution_allowed": False,
        "live_call_allowed": False,
        "max_model_calls": 1,
        "model_call_count": 0,
        "call_model_count": 0,
        "max_retries_per_call": 0,
        "retry_allowed": False,
        "reserve_allowed": False,
        "fallback_allowed": False,
        "second_call_allowed": False,
        "provider_rotation_allowed": False,
        "key_rotation_allowed": False,
        "rollback_policy_ref": rollback_policy_ref,
        "expected_live_artifacts_ref": expected_live_artifacts_ref,
        "command_skeleton": command_skeleton,
        "failure_type": None,
        "errors": (),
    }
    values.update(overrides)
    plan = OneShotFirePlan(**values)
    plan.to_summary()
    return plan


def build_last_stop_guard(
    *,
    run_id: str,
    fire_ready: bool = True,
    armed: bool = True,
    required_items: Mapping[str, bool] | None = None,
    **overrides: object,
) -> LastStopGuard:
    items = {name: True for name in P3V_REQUIRED_LAST_STOP_ITEMS}
    if required_items:
        items.update(required_items)
    values = {
        "schema_version": LAST_STOP_GUARD_SCHEMA_VERSION,
        "run_id": run_id,
        "status": "still_no_call",
        "required_items": items,
        "fire_ready": fire_ready,
        "armed": armed,
        "fired": False,
        "execution_allowed": False,
        "live_call_allowed": False,
        "model_call_count": 0,
        "call_model_count": 0,
        "failure_type": None,
        "errors": (),
        "raw_output_saved": False,
        "created_for": LIVE_FIRE_CHECKLIST_CREATED_FOR,
    }
    values.update(overrides)
    guard = LastStopGuard(**values)
    guard.to_summary()
    return guard


def build_live_fire_checklist(
    *,
    explicit_approval_gate: Mapping[str, Any],
    armed_state: Mapping[str, Any],
    final_live_approval_packet: Mapping[str, Any],
    human_confirmation_checklist: Mapping[str, Any],
    pre_live_package_manifest: Mapping[str, Any],
    live_execution_boundary: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
    runtime_flags_summary: Mapping[str, Any],
    test_evidence_summary: Mapping[str, Any],
    rollback_plan_summary: Mapping[str, Any],
    policy_lock_summary: Mapping[str, Any],
    last_stop_guard: Mapping[str, Any],
    one_shot_fire_plan: Mapping[str, Any],
    expected_live_artifacts: Mapping[str, Any],
    artifact_safety_summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    status: str = "fire_checklist_ready",
    fire_ready: bool = True,
    fire_readiness_states: Sequence[str] = ("checklist_ready", "last_stop_ready", "fire_plan_ready", "still_no_call"),
) -> LiveFireChecklist:
    validate_explicit_approval_gate(explicit_approval_gate)
    validate_armed_but_not_fired_state(armed_state)
    validate_last_stop_guard(last_stop_guard)
    validate_one_shot_fire_plan(one_shot_fire_plan)
    validate_expected_live_artifacts(expected_live_artifacts)
    validate_rollback_confirmation(rollback_plan_summary)
    validate_rollback_confirmation(policy_lock_summary)
    for payload in (runtime_flags_summary, test_evidence_summary, final_live_gate_result):
        validate_still_no_call_invariants(payload)
    _artifact_scan_status(artifact_safety_summary, missing_condition="pre-scan missing")
    run_id = validate_artifact_reference_consistency(
        explicit_approval_gate=explicit_approval_gate,
        armed_state=armed_state,
        final_live_approval_packet=final_live_approval_packet,
        human_confirmation_checklist=human_confirmation_checklist,
        pre_live_package_manifest=pre_live_package_manifest,
        live_execution_boundary=live_execution_boundary,
        no_call_integration_summary=no_call_integration_summary,
        call_attempt_summary=call_attempt_summary,
        final_live_gate_result=final_live_gate_result,
    )
    approval_hash = _consistent_approval_hash(
        explicit_approval_gate,
        final_live_approval_packet,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    validate_fire_readiness_state_machine(
        {
            "states": tuple(fire_readiness_states),
            "current_state": tuple(fire_readiness_states)[-1],
            "fired": False,
            "execution_allowed": False,
            "live_call_allowed": False,
            "model_call_count": 0,
            "call_model_count": 0,
        }
    )
    checklist = LiveFireChecklist(
        schema_version=LIVE_FIRE_CHECKLIST_SCHEMA_VERSION,
        run_id=run_id,
        status=status,
        ready_for_final_review=True,
        fire_ready=fire_ready,
        fire_readiness_states=tuple(fire_readiness_states),
        armed=bool(explicit_approval_gate.get("armed")),
        fired=False,
        execution_allowed=False,
        live_call_allowed=False,
        model_call_count=0,
        call_model_count=0,
        last_stop_guard_status=_string(last_stop_guard.get("status")),
        one_shot_fire_plan_ref=ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME,
        expected_live_artifacts_ref=EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME,
        explicit_approval_gate_ref=EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME,
        armed_state_ref=ARMED_STATE_ARTIFACT_NAME,
        final_live_approval_packet_ref=FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
        human_confirmation_checklist_ref=HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
        pre_live_package_manifest_ref=PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME,
        live_execution_boundary_ref=CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
        no_call_integration_summary_ref=NO_CALL_INTEGRATION_ARTIFACT_NAME,
        call_attempt_summary_ref=CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
        final_gate_result_ref=_string(pre_live_package_manifest.get("final_gate_result_ref")),
        approval_phrase_hash=approval_hash,
        approval_phrase_ref=_string(explicit_approval_gate.get("approval_phrase_ref")),
        provider=_string(final_live_approval_packet.get("provider")),
        model=_string(final_live_approval_packet.get("model")),
        key_slot=_string(final_live_approval_packet.get("key_slot")),
        no_retry_confirmed=True,
        no_reserve_confirmed=True,
        no_fallback_confirmed=True,
        no_second_call_confirmed=True,
        rollback_policy_ref="rollback_policy.json",
        failure_type=None,
        errors=(),
        raw_output_saved=False,
        created_for=LIVE_FIRE_CHECKLIST_CREATED_FOR,
    )
    checklist.to_summary()
    return checklist


def validate_live_fire_checklist(checklist: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "ready_for_final_review",
        "fire_ready",
        "fire_readiness_states",
        "armed",
        "fired",
        "execution_allowed",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "last_stop_guard_status",
        "one_shot_fire_plan_ref",
        "expected_live_artifacts_ref",
        "explicit_approval_gate_ref",
        "armed_state_ref",
        "final_live_approval_packet_ref",
        "human_confirmation_checklist_ref",
        "pre_live_package_manifest_ref",
        "live_execution_boundary_ref",
        "no_call_integration_summary_ref",
        "call_attempt_summary_ref",
        "final_gate_result_ref",
        "approval_phrase_hash",
        "approval_phrase_ref",
        "provider",
        "model",
        "key_slot",
        "no_retry_confirmed",
        "no_reserve_confirmed",
        "no_fallback_confirmed",
        "no_second_call_confirmed",
        "rollback_policy_ref",
        "failure_type",
        "errors",
        "raw_output_saved",
        "created_for",
    }
    if not required <= set(checklist):
        raise P3VLiveFireChecklistError("missing required checklist item")
    if checklist["schema_version"] != LIVE_FIRE_CHECKLIST_SCHEMA_VERSION:
        raise P3VLiveFireChecklistError("missing required checklist item")
    if checklist["created_for"] != LIVE_FIRE_CHECKLIST_CREATED_FOR:
        raise P3VLiveFireChecklistError("execution_allowed true in P3V")
    _validate_checklist_status(_string(checklist["status"]))
    validate_still_no_call_invariants(checklist)
    validate_fire_readiness_state_machine(
        {
            "states": tuple(checklist.get("fire_readiness_states", ())),
            "current_state": tuple(checklist.get("fire_readiness_states", ()))[-1] if checklist.get("fire_readiness_states") else None,
            "fired": checklist.get("fired"),
            "execution_allowed": checklist.get("execution_allowed"),
            "live_call_allowed": checklist.get("live_call_allowed"),
            "model_call_count": checklist.get("model_call_count"),
            "call_model_count": checklist.get("call_model_count"),
        }
    )
    validate_approval_phrase_hash(_string(checklist["approval_phrase_hash"]))
    for ref_field in (
        "one_shot_fire_plan_ref",
        "expected_live_artifacts_ref",
        "explicit_approval_gate_ref",
        "armed_state_ref",
        "final_live_approval_packet_ref",
        "human_confirmation_checklist_ref",
        "pre_live_package_manifest_ref",
        "live_execution_boundary_ref",
        "no_call_integration_summary_ref",
        "call_attempt_summary_ref",
        "final_gate_result_ref",
        "approval_phrase_ref",
        "rollback_policy_ref",
    ):
        validate_fire_artifact_ref(_string(checklist[ref_field]))
    for field in ("no_retry_confirmed", "no_reserve_confirmed", "no_fallback_confirmed", "no_second_call_confirmed"):
        if checklist[field] is not True:
            raise P3VLiveFireChecklistError("missing required checklist item")
    scan_result = scan_artifacts({LIVE_FIRE_CHECKLIST_ARTIFACT_NAME: dict(checklist)})
    if not scan_result.ok:
        raise P3VLiveFireChecklistError("scan failed", failure_type=scan_result.failure_type)


def validate_fire_readiness_state_machine(summary: Mapping[str, Any]) -> None:
    states = tuple(summary.get("states", ()))
    if not states:
        raise P3VLiveFireChecklistError("unknown fire readiness state")
    for state in states:
        validate_fire_readiness_state(
            str(state),
            fired=summary.get("fired"),
            execution_allowed=summary.get("execution_allowed"),
            live_call_allowed=summary.get("live_call_allowed"),
            model_call_count=summary.get("model_call_count"),
            call_model_count=summary.get("call_model_count"),
        )
    for current, next_state in zip(states, states[1:]):
        if next_state not in P3V_ALLOWED_FIRE_TRANSITIONS.get(current, frozenset()):
            raise P3VLiveFireChecklistError("invalid fire readiness transition")
    if summary.get("current_state") != states[-1]:
        raise P3VLiveFireChecklistError("unknown fire readiness state")


def validate_fire_readiness_state(
    state: str,
    *,
    fired: Any = False,
    execution_allowed: Any = False,
    live_call_allowed: Any = False,
    model_call_count: Any = 0,
    call_model_count: Any = 0,
) -> None:
    _validate_no_execute_flags(
        fired=fired,
        execution_allowed=execution_allowed,
        live_call_allowed=live_call_allowed,
        model_call_count=model_call_count,
        call_model_count=call_model_count,
    )
    if state in P3V_FORBIDDEN_FIRE_STATES:
        raise P3VLiveFireChecklistError("forbidden fire readiness state")
    if state not in P3V_ALLOWED_FIRE_STATES:
        raise P3VLiveFireChecklistError("unknown fire readiness state")


def validate_last_stop_guard(guard: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "required_items",
        "fire_ready",
        "armed",
        "fired",
        "execution_allowed",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "failure_type",
        "errors",
        "raw_output_saved",
        "created_for",
    }
    if not required <= set(guard):
        raise P3VLiveFireChecklistError("missing required last-stop item")
    if guard["schema_version"] != LAST_STOP_GUARD_SCHEMA_VERSION:
        raise P3VLiveFireChecklistError("missing required last-stop item")
    if guard["created_for"] != LIVE_FIRE_CHECKLIST_CREATED_FOR:
        raise P3VLiveFireChecklistError("execution_allowed true in P3V")
    _validate_checklist_status(_string(guard["status"]))
    validate_still_no_call_invariants(guard)
    items = guard.get("required_items")
    if not isinstance(items, Mapping):
        raise P3VLiveFireChecklistError("missing required last-stop item")
    missing = [item for item in P3V_REQUIRED_LAST_STOP_ITEMS if item not in items]
    if missing:
        raise P3VLiveFireChecklistError("missing required last-stop item")
    for item, value in items.items():
        if item not in P3V_REQUIRED_LAST_STOP_ITEMS:
            continue
        if value is not True:
            if item == "actual_live_result_absent":
                raise P3VLiveFireChecklistError("actual live result present")
            if item in {
                "fired_false",
                "execution_allowed_false",
                "live_call_allowed_false",
                "model_call_count_zero",
                "call_model_count_zero",
                "provider_not_activated",
                "sdk_not_imported",
                "key_not_loaded",
                "network_not_called",
                "call_model_not_called",
                "no_retry_confirmed",
                "no_reserve_confirmed",
                "no_fallback_confirmed",
                "no_second_call_confirmed",
            }:
                raise P3VLiveFireChecklistError("fired true in P3V")
            raise P3VLiveFireChecklistError("missing required last-stop item")
    scan_result = scan_artifacts({LAST_STOP_GUARD_ARTIFACT_NAME: dict(guard)})
    if not scan_result.ok:
        raise P3VLiveFireChecklistError("scan failed", failure_type=scan_result.failure_type)


def validate_one_shot_fire_plan(plan: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "plan_type",
        "fire_plan_mode",
        "fire_ready",
        "fired",
        "execution_allowed",
        "live_call_allowed",
        "max_model_calls",
        "model_call_count",
        "call_model_count",
        "max_retries_per_call",
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "provider_rotation_allowed",
        "key_rotation_allowed",
        "rollback_policy_ref",
        "expected_live_artifacts_ref",
        "command_skeleton",
        "failure_type",
        "errors",
    }
    if not required <= set(plan):
        raise P3VLiveFireChecklistError("missing required fire plan item")
    if plan["schema_version"] != ONE_SHOT_FIRE_PLAN_SCHEMA_VERSION or plan["plan_type"] != ONE_SHOT_FIRE_PLAN_TYPE:
        raise P3VLiveFireChecklistError("missing required fire plan item")
    if plan["fire_plan_mode"] not in P3V_ALLOWED_FIRE_PLAN_MODES:
        raise P3VLiveFireChecklistError("missing required fire plan item")
    validate_still_no_call_invariants(plan)
    if plan["max_model_calls"] != 1 or plan["max_retries_per_call"] != 0:
        raise P3VLiveFireChecklistError("model_call_count > 0 in P3V")
    _validate_command_skeleton(_string(plan["command_skeleton"]))
    validate_fire_artifact_ref(_string(plan["rollback_policy_ref"]))
    validate_fire_artifact_ref(_string(plan["expected_live_artifacts_ref"]))
    scan_result = scan_artifacts({ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME: dict(plan)})
    if not scan_result.ok:
        raise P3VLiveFireChecklistError("scan failed", failure_type=scan_result.failure_type)


def validate_expected_live_artifacts(summary: Mapping[str, Any]) -> None:
    required = {"schema_version", "run_id", "artifact_names", "artifact_refs", "raw_contents_saved", "failure_type", "errors"}
    if not required <= set(summary):
        raise P3VLiveFireChecklistError("missing required expected artifact item")
    if summary["schema_version"] != EXPECTED_LIVE_ARTIFACTS_SCHEMA_VERSION:
        raise P3VLiveFireChecklistError("missing required expected artifact item")
    if summary["raw_contents_saved"] is not False:
        raise P3VLiveFireChecklistError("raw key/token/env var value in approval")
    names = tuple(summary.get("artifact_names", ()))
    refs = summary.get("artifact_refs")
    if not names or not isinstance(refs, Mapping):
        raise P3VLiveFireChecklistError("missing required expected artifact item")
    for name in names:
        if name not in P3V_ALLOWED_EXPECTED_ARTIFACTS:
            raise P3VLiveFireChecklistError("forbidden expected artifact")
        validate_fire_artifact_ref(str(name))
        ref = refs.get(name)
        if not isinstance(ref, str):
            raise P3VLiveFireChecklistError("missing required expected artifact item")
        validate_fire_artifact_ref(ref, condition="unsafe expected artifact ref")
    _reject_forbidden_fields(summary)
    scan_result = scan_artifacts({EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME: dict(summary)})
    if not scan_result.ok:
        raise P3VLiveFireChecklistError("scan failed", failure_type=scan_result.failure_type)


def validate_rollback_confirmation(summary: Mapping[str, Any]) -> None:
    required = {
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "rollback_required_on_failure",
        "preserve_raw_output",
        "allowlist_widening_allowed",
        "key_slot_change_allowed",
        "provider_rotation_allowed",
        "budget_reset_allowed",
    }
    if not required <= set(summary):
        raise P3VLiveFireChecklistError("missing required rollback item")
    _reject_forbidden_fields(summary)
    for field in (
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "preserve_raw_output",
        "allowlist_widening_allowed",
        "key_slot_change_allowed",
        "provider_rotation_allowed",
        "budget_reset_allowed",
    ):
        if summary.get(field) is not False:
            if field == "preserve_raw_output":
                raise P3VLiveFireChecklistError("raw_output_saved=True detected")
            if field == "budget_reset_allowed":
                raise P3VLiveFireChecklistError("budget_reset_allowed true")
            raise P3VLiveFireChecklistError(f"{field} true")
    if summary.get("rollback_required_on_failure") is not True:
        raise P3VLiveFireChecklistError("missing required rollback item")


def validate_artifact_reference_consistency(
    *,
    explicit_approval_gate: Mapping[str, Any],
    armed_state: Mapping[str, Any],
    final_live_approval_packet: Mapping[str, Any],
    human_confirmation_checklist: Mapping[str, Any],
    pre_live_package_manifest: Mapping[str, Any],
    live_execution_boundary: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
) -> str:
    run_id = _consistent_run_id(
        explicit_approval_gate,
        armed_state,
        final_live_approval_packet,
        human_confirmation_checklist,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    _consistent_approval_hash(
        explicit_approval_gate,
        final_live_approval_packet,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    for payload, field in (
        (explicit_approval_gate, "final_live_approval_packet_ref"),
        (explicit_approval_gate, "pre_live_package_manifest_ref"),
        (explicit_approval_gate, "live_execution_boundary_ref"),
        (explicit_approval_gate, "no_call_integration_summary_ref"),
        (explicit_approval_gate, "call_attempt_summary_ref"),
        (explicit_approval_gate, "final_gate_result_ref"),
        (explicit_approval_gate, "approval_phrase_ref"),
        (final_live_approval_packet, "human_confirmation_checklist_ref"),
    ):
        validate_fire_artifact_ref(_string(payload.get(field)))
    return run_id


def validate_still_no_call_invariants(payload: Mapping[str, Any]) -> None:
    _reject_forbidden_fields(payload)
    if "status" in payload:
        _reject_live_like_status(_string(payload["status"]))
    for field, condition in (
        ("fired", "fired true in P3V"),
        ("executed", "fired true in P3V"),
        ("called", "fired true in P3V"),
        ("provider_called", "fired true in P3V"),
        ("network_called", "fired true in P3V"),
        ("execution_allowed", "execution_allowed true in P3V"),
        ("live_call_allowed", "live_call_allowed true in P3V"),
        ("raw_output_saved", "raw_output_saved=True detected"),
        ("provider_activation", "candidate interpreted as active"),
        ("provider_activated", "candidate interpreted as active"),
        ("sdk_import_activation", "SDK import marker in P3S"),
        ("sdk_imported", "SDK import marker in P3S"),
        ("key_loading_activation", "key loaded marker in P3S"),
        ("key_loaded", "key loaded marker in P3S"),
        ("network_call", "network call marker in P3S"),
        ("network_called", "network call marker in P3S"),
        ("live_smoke_executed", "live smoke marker in P3S"),
        ("call_model_executed", "call_model attempted in P3R"),
        ("call_model_called", "call_model attempted in P3R"),
        ("actual_live_result_present", "actual live result present"),
        ("retry_allowed", "retry_allowed true"),
        ("reserve_allowed", "reserve_allowed true"),
        ("fallback_allowed", "fallback_allowed true"),
        ("second_call_allowed", "second_call_allowed true"),
        ("budget_spent", "budget_spent true"),
    ):
        if payload.get(field) is True:
            raise P3VLiveFireChecklistError(condition)
    for field in (
        "model_call_count",
        "model_call_count_before_execution",
        "call_model_count",
        "actual_api_call_count",
        "actual_llm_call_count",
        "actual_key_value_read_count",
        "actual_env_value_read_count",
        "actual_sdk_import_count",
        "actual_network_call_count",
        "actual_live_smoke_count",
    ):
        if int(payload.get(field, 0) or 0) > 0:
            if field == "call_model_count":
                raise P3VLiveFireChecklistError("call_model_count > 0 in P3V")
            if field == "actual_sdk_import_count":
                raise P3VLiveFireChecklistError("SDK import marker in P3S")
            if field in {"actual_key_value_read_count", "actual_env_value_read_count"}:
                raise P3VLiveFireChecklistError("key loaded marker in P3S")
            if field == "actual_network_call_count":
                raise P3VLiveFireChecklistError("network call marker in P3S")
            if field == "actual_live_smoke_count":
                raise P3VLiveFireChecklistError("live smoke marker in P3S")
            raise P3VLiveFireChecklistError("model_call_count > 0 in P3V")
    if scan_value_for_unsafe_content(dict(payload), value_path="live_fire_checklist"):
        raise P3VLiveFireChecklistError("raw key/token/env var value in approval")


def write_live_fire_checklist(
    run_dir: Path,
    checklist: LiveFireChecklist | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = LIVE_FIRE_CHECKLIST_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = checklist.to_summary() if isinstance(checklist, LiveFireChecklist) else dict(checklist)
    validate_live_fire_checklist(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=LIVE_FIRE_CHECKLIST_ARTIFACT_NAME)


def write_last_stop_guard(
    run_dir: Path,
    guard: LastStopGuard | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = LAST_STOP_GUARD_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = guard.to_summary() if isinstance(guard, LastStopGuard) else dict(guard)
    validate_last_stop_guard(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=LAST_STOP_GUARD_ARTIFACT_NAME)


def write_one_shot_fire_plan(
    run_dir: Path,
    plan: OneShotFirePlan | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = plan.to_summary() if isinstance(plan, OneShotFirePlan) else dict(plan)
    validate_one_shot_fire_plan(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=ONE_SHOT_FIRE_PLAN_ARTIFACT_NAME)


def write_expected_live_artifacts(
    run_dir: Path,
    expected: ExpectedLiveArtifacts | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = expected.to_summary() if isinstance(expected, ExpectedLiveArtifacts) else dict(expected)
    validate_expected_live_artifacts(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=EXPECTED_LIVE_ARTIFACTS_ARTIFACT_NAME)


def live_fire_checklist_default_runtime_creation_enabled() -> bool:
    return False


def last_stop_guard_default_runtime_creation_enabled() -> bool:
    return False


def one_shot_fire_plan_default_runtime_creation_enabled() -> bool:
    return False


def expected_live_artifacts_default_runtime_creation_enabled() -> bool:
    return False


def aggregate_live_fire_failure_type(failure_types: Sequence[str | None]) -> str | None:
    present = {failure_type for failure_type in failure_types if failure_type}
    for failure_type in PRE_LIVE_FAILURE_PRIORITY:
        if failure_type in present:
            return failure_type
    return None


def validate_fire_artifact_ref(ref: str, *, condition: str = "unsafe artifact reference") -> None:
    if not ref:
        raise P3VLiveFireChecklistError("missing required artifact reference")
    if _is_url_ref(ref):
        raise P3VLiveFireChecklistError(condition)
    path = Path(ref)
    if path.is_absolute():
        raise P3VLiveFireChecklistError(condition)
    if ".." in path.parts:
        raise P3VLiveFireChecklistError(condition)


def _validate_checklist_status(status: str) -> None:
    _reject_live_like_status(status)
    if status not in P3V_ALLOWED_CHECKLIST_STATUSES:
        raise P3VLiveFireChecklistError("unknown fire readiness state")


def _reject_live_like_status(status: str) -> None:
    if status in P3V_SUCCESS_LIKE_STATUSES:
        raise P3VLiveFireChecklistError("success-like status in P3V")
    if status in P3V_APPROVAL_LIKE_STATUSES:
        raise P3VLiveFireChecklistError("approval-like status in P3V")
    if status in P3V_FORBIDDEN_FIRE_STATES:
        raise P3VLiveFireChecklistError("forbidden fire readiness state")


def _validate_no_execute_flags(
    *,
    fired: Any,
    execution_allowed: Any,
    live_call_allowed: Any,
    model_call_count: Any,
    call_model_count: Any,
) -> None:
    if fired is not False:
        raise P3VLiveFireChecklistError("fired true in P3V")
    if execution_allowed is not False:
        raise P3VLiveFireChecklistError("execution_allowed true in P3V")
    if live_call_allowed is not False:
        raise P3VLiveFireChecklistError("live_call_allowed true in P3V")
    if int(model_call_count or 0) > 0:
        raise P3VLiveFireChecklistError("model_call_count > 0 in P3V")
    if int(call_model_count or 0) > 0:
        raise P3VLiveFireChecklistError("call_model_count > 0 in P3V")


def _validate_command_skeleton(command: str) -> None:
    tokens = set(command.split())
    if not {"--no-execute", "--review-only"} <= tokens:
        raise P3VLiveFireChecklistError("fire command token found")
    if tokens & P3V_FORBIDDEN_COMMAND_TOKENS:
        raise P3VLiveFireChecklistError("fire command token found")
    if scan_value_for_unsafe_content(command, value_path="command_skeleton"):
        raise P3VLiveFireChecklistError("raw key/token/env var value in approval")


def _write_json(run_dir: Path, artifact_name: str | Path, payload: Mapping[str, Any], *, expected_name: str) -> Path:
    path = _resolve_live_fire_artifact_path(run_dir, artifact_name, expected_name=expected_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3VLiveFireChecklistError("artifact write failure") from exc
    return path


def _resolve_live_fire_artifact_path(run_dir: Path, artifact_path: str | Path, *, expected_name: str) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if _is_url_ref(str(artifact_path)):
        raise P3VLiveFireChecklistError("unsafe artifact reference")
    if ".." in requested.parts:
        raise P3VLiveFireChecklistError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3VLiveFireChecklistError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3VLiveFireChecklistError("artifact path outside run_dir")
    if relative.as_posix() != expected_name:
        raise P3VLiveFireChecklistError("artifact write failure")
    return resolved


def _consistent_run_id(*payloads: Mapping[str, Any]) -> str:
    run_ids = []
    for payload in payloads:
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise P3VLiveFireChecklistError("run_id mismatch")
        run_ids.append(run_id)
    if len(set(run_ids)) != 1:
        raise P3VLiveFireChecklistError("run_id mismatch")
    return run_ids[0]


def _consistent_approval_hash(*payloads: Mapping[str, Any]) -> str:
    hashes = []
    for payload in payloads:
        value = payload.get("approval_phrase_hash")
        if not isinstance(value, str) or not value:
            raise P3VLiveFireChecklistError("missing approval_phrase_hash")
        validate_approval_phrase_hash(value)
        hashes.append(value)
    if len(set(hashes)) != 1:
        raise P3VLiveFireChecklistError("approval_phrase_hash mismatch")
    return hashes[0]


def _artifact_scan_status(
    summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    *,
    missing_condition: str,
) -> str:
    if summary is None:
        raise P3VLiveFireChecklistError(missing_condition)
    if isinstance(summary, ArtifactSafetyResult):
        if not summary.ok:
            raise P3VLiveFireChecklistError("scan failed", failure_type=summary.failure_type)
        return "pass"
    _reject_forbidden_fields(summary)
    if scan_value_for_unsafe_content(dict(summary), value_path="artifact_safety_summary"):
        raise P3VLiveFireChecklistError("raw key/token/env var value in approval")
    if summary.get("ok") is True or summary.get("status") in {"pass", "ok"}:
        return "pass"
    if summary.get("ok") is False or summary.get("status") in {"fail", "failed", "blocked"}:
        raise P3VLiveFireChecklistError("scan failed")
    raise P3VLiveFireChecklistError(missing_condition)


def _reject_forbidden_fields(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if key in P3V_FORBIDDEN_FIELDS:
            if key in {"approval_phrase", "raw_approval_phrase"}:
                raise P3VLiveFireChecklistError("raw approval phrase found")
            if key == "provider_response":
                raise P3VLiveFireChecklistError("provider response found")
            if key == "token_usage":
                raise P3VLiveFireChecklistError("token usage found")
            raise P3VLiveFireChecklistError("raw key/token/env var value in approval")
        if isinstance(value, Mapping):
            _reject_forbidden_fields(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_forbidden_fields(item)


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3VLiveFireChecklistError("missing required artifact reference")
    return value


def _is_url_ref(value: str) -> bool:
    return value.startswith(("http://", "https://")) or "://" in value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
