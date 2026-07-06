# P3U 명시 승인 gate를 실제 호출 없이 armed-but-not-fired 상태로만 검증하는 스켈레톤입니다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_safety import ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .final_live_approval_packet import (
    FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
    HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
    P3TApprovalPacketError,
    P3T_FAILURES,
    validate_approval_phrase_ref,
    validate_final_live_approval_packet,
    validate_human_confirmation_checklist,
    validate_no_call_evidence_summary,
    validate_packet_artifact_ref,
    validate_packet_no_call_invariants,
)
from .live_execution_boundary import CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME, validate_live_execution_boundary
from .no_call_integration import NO_CALL_INTEGRATION_ARTIFACT_NAME, validate_no_call_integration
from .pre_live_package import PRE_LIVE_FAILURE_PRIORITY, PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME, validate_approval_phrase_hash, validate_pre_live_package

EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME = "explicit_approval_gate.json"
ARMED_STATE_ARTIFACT_NAME = "armed_state.json"
EXPLICIT_APPROVAL_GATE_SCHEMA_VERSION = "p3_explicit_approval_gate_v1"
ARMED_STATE_SCHEMA_VERSION = "p3_armed_but_not_fired_state_v1"
ONE_SHOT_BUDGET_LOCK_SCHEMA_VERSION = "p3_one_shot_budget_lock_v1"
POLICY_LOCK_SCHEMA_VERSION = "p3_single_call_policy_lock_v1"
EXPLICIT_APPROVAL_GATE_CREATED_FOR = "armed_but_not_fired_no_call"

P3U_ALLOWED_GATE_STATUSES = frozenset({"armed_not_fired", "prepared", "ready_for_human_review", "blocked", "fail"})
P3U_ALLOWED_APPROVAL_STATUSES = frozenset({"pending", "review_required", "not_granted"})
P3U_FORBIDDEN_APPROVAL_STATUSES = frozenset(
    {"approved", "granted", "confirmed", "execution_approved", "live_approved", "armed_and_fired"}
)
P3U_SUCCESS_LIKE_STATUSES = frozenset(
    {"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call", "fired"}
)
P3U_ALLOWED_ARMED_STATES = frozenset(
    {"not_armed", "pre_armed_review", "armed_not_fired", "armed_blocked", "disarmed", "review_required"}
)
P3U_FORBIDDEN_ARMED_STATES = frozenset(
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
    }
)
P3U_ALLOWED_ARMED_TRANSITIONS = {
    "not_armed": frozenset({"pre_armed_review", "review_required", "disarmed"}),
    "pre_armed_review": frozenset({"armed_not_fired", "armed_blocked", "review_required", "disarmed"}),
    "armed_not_fired": frozenset({"armed_blocked", "review_required", "disarmed"}),
    "armed_blocked": frozenset({"review_required", "disarmed"}),
    "review_required": frozenset({"pre_armed_review", "disarmed"}),
}
P3U_FORBIDDEN_FIELDS = frozenset(
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
P3U_FAILURES = {
    **P3T_FAILURES,
    "approved explicit approval status in P3U": "SECURITY_BLOCKED",
    "success-like status in P3U": "SECURITY_BLOCKED",
    "fired true in P3U": "SECURITY_BLOCKED",
    "execution_allowed true in P3U": "SECURITY_BLOCKED",
    "live_call_allowed true in P3U": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3U": "SECURITY_BLOCKED",
    "call_model_count > 0 in P3U": "SECURITY_BLOCKED",
    "forbidden armed state": "SECURITY_BLOCKED",
    "unknown armed state": "CONFIG_ERROR",
    "invalid armed transition": "CONFIG_ERROR",
    "missing required gate item": "CONFIG_ERROR",
    "missing required armed state item": "CONFIG_ERROR",
    "budget_spent true": "SECURITY_BLOCKED",
    "budget_reset_allowed true": "SECURITY_BLOCKED",
    "budget_widening_allowed true": "SECURITY_BLOCKED",
    "provider_rotation_allowed true": "SECURITY_BLOCKED",
    "key_rotation_allowed true": "SECURITY_BLOCKED",
    "policy_widening_allowed true": "SECURITY_BLOCKED",
    "missing policy lock item": "CONFIG_ERROR",
}


class P3UExplicitApprovalGateError(RuntimeError):
    def __init__(self, condition: str, *, failure_type: str | None = None) -> None:
        self.condition = condition
        self.failure_type = failure_type or P3U_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class OneShotBudgetLock:
    schema_version: str = ONE_SHOT_BUDGET_LOCK_SCHEMA_VERSION
    max_model_calls: int = 1
    model_call_count: int = 0
    budget_locked: bool = True
    budget_spent: bool = False
    retry_allowed: bool = False
    reserve_allowed: bool = False
    fallback_allowed: bool = False
    second_call_allowed: bool = False
    budget_reset_allowed: bool = False
    budget_widening_allowed: bool = False

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_one_shot_budget_lock(payload)
        return payload


@dataclass(frozen=True)
class SingleCallPolicyLock:
    schema_version: str = POLICY_LOCK_SCHEMA_VERSION
    single_call_only: bool = True
    retry_allowed: bool = False
    reserve_allowed: bool = False
    fallback_allowed: bool = False
    second_call_allowed: bool = False
    provider_rotation_allowed: bool = False
    key_rotation_allowed: bool = False
    policy_widening_allowed: bool = False

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_policy_lock(payload)
        return payload


@dataclass(frozen=True)
class ArmedButNotFiredState:
    schema_version: str
    run_id: str
    armed_state: str
    armed_states: tuple[str, ...]
    armed: bool
    fired: bool
    execution_allowed: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    raw_output_saved: bool
    explicit_approval_status: str
    human_confirmation_status: str
    failure_type: str | None
    errors: tuple[str, ...]
    created_for: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_armed_but_not_fired_state(payload)
        return payload


@dataclass(frozen=True)
class ExplicitApprovalGate:
    schema_version: str
    run_id: str
    status: str
    ready_for_human_review: bool
    armed_state: str
    armed: bool
    fired: bool
    execution_allowed: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    human_confirmation_required: bool
    human_confirmation_status: str
    explicit_approval_required: bool
    explicit_approval_status: str
    approval_phrase_hash: str
    approval_phrase_ref: str
    final_live_approval_packet_ref: str
    human_confirmation_checklist_ref: str
    pre_live_package_manifest_ref: str
    live_execution_boundary_ref: str
    no_call_integration_summary_ref: str
    call_attempt_summary_ref: str
    final_gate_result_ref: str
    one_shot_budget_lock: dict[str, object]
    single_call_policy_lock: dict[str, object]
    no_retry_policy_lock: dict[str, object]
    no_reserve_policy_lock: dict[str, object]
    no_fallback_policy_lock: dict[str, object]
    no_second_call_policy_lock: dict[str, object]
    provider: str
    model: str
    key_slot: str
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    created_for: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_explicit_approval_gate(payload)
        return payload


def build_one_shot_budget_lock(**overrides: object) -> OneShotBudgetLock:
    lock = OneShotBudgetLock(**overrides)
    lock.to_summary()
    return lock


def build_single_call_policy_lock(**overrides: object) -> SingleCallPolicyLock:
    lock = SingleCallPolicyLock(**overrides)
    lock.to_summary()
    return lock


def build_armed_but_not_fired_state(
    *,
    run_id: str,
    explicit_approval_status: str = "review_required",
    human_confirmation_status: str = "review_required",
    armed_states: Sequence[str] = ("pre_armed_review", "armed_not_fired"),
    armed: bool = True,
) -> ArmedButNotFiredState:
    state = ArmedButNotFiredState(
        schema_version=ARMED_STATE_SCHEMA_VERSION,
        run_id=run_id,
        armed_state=tuple(armed_states)[-1],
        armed_states=tuple(armed_states),
        armed=armed,
        fired=False,
        execution_allowed=False,
        live_call_allowed=False,
        model_call_count=0,
        call_model_count=0,
        raw_output_saved=False,
        explicit_approval_status=explicit_approval_status,
        human_confirmation_status=human_confirmation_status,
        failure_type=None,
        errors=(),
        created_for=EXPLICIT_APPROVAL_GATE_CREATED_FOR,
    )
    state.to_summary()
    return state


def build_explicit_approval_gate(
    *,
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
    human_decision_summary: Mapping[str, Any],
    artifact_safety_summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    status: str = "armed_not_fired",
    explicit_approval_status: str = "review_required",
    armed: bool = True,
    approval_phrase_ref: str = "approval_phrase_hash_only",
) -> ExplicitApprovalGate:
    validate_final_live_approval_packet(final_live_approval_packet)
    validate_human_confirmation_checklist(human_confirmation_checklist)
    validate_pre_live_package(pre_live_package_manifest)
    validate_live_execution_boundary(live_execution_boundary)
    validate_no_call_integration(no_call_integration_summary)
    validate_live_execution_boundary(call_attempt_summary)
    validate_no_call_evidence_summary(test_evidence_summary)
    validate_human_confirmation_checklist(human_decision_summary)
    for payload in (runtime_flags_summary, rollback_plan_summary, final_live_gate_result):
        validate_gate_no_call_invariants(payload)
    _artifact_scan_status(artifact_safety_summary, missing_condition="pre-scan missing")
    validate_explicit_approval_status(explicit_approval_status)
    validate_approval_phrase_ref(approval_phrase_ref)
    run_id = _consistent_run_id(
        final_live_approval_packet,
        human_confirmation_checklist,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
        test_evidence_summary,
        human_decision_summary,
    )
    approval_hash = _consistent_approval_hash(
        final_live_approval_packet,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    budget_lock = build_one_shot_budget_lock().to_summary()
    policy_lock = build_single_call_policy_lock().to_summary()
    armed_state = build_armed_but_not_fired_state(
        run_id=run_id,
        explicit_approval_status=explicit_approval_status,
        human_confirmation_status=_string(human_confirmation_checklist.get("human_confirmation_status")),
        armed=armed,
    )
    gate = ExplicitApprovalGate(
        schema_version=EXPLICIT_APPROVAL_GATE_SCHEMA_VERSION,
        run_id=run_id,
        status=status,
        ready_for_human_review=True,
        armed_state=armed_state.armed_state,
        armed=armed_state.armed,
        fired=False,
        execution_allowed=False,
        live_call_allowed=False,
        model_call_count=0,
        call_model_count=0,
        human_confirmation_required=True,
        human_confirmation_status=armed_state.human_confirmation_status,
        explicit_approval_required=True,
        explicit_approval_status=explicit_approval_status,
        approval_phrase_hash=approval_hash,
        approval_phrase_ref=approval_phrase_ref,
        final_live_approval_packet_ref=FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
        human_confirmation_checklist_ref=HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
        pre_live_package_manifest_ref=PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME,
        live_execution_boundary_ref=CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
        no_call_integration_summary_ref=NO_CALL_INTEGRATION_ARTIFACT_NAME,
        call_attempt_summary_ref=CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
        final_gate_result_ref=_string(pre_live_package_manifest.get("final_gate_result_ref")),
        one_shot_budget_lock=budget_lock,
        single_call_policy_lock=policy_lock,
        no_retry_policy_lock=policy_lock,
        no_reserve_policy_lock=policy_lock,
        no_fallback_policy_lock=policy_lock,
        no_second_call_policy_lock=policy_lock,
        provider=_string(final_live_approval_packet.get("provider")),
        model=_string(final_live_approval_packet.get("model")),
        key_slot=_string(final_live_approval_packet.get("key_slot")),
        failure_type=None,
        errors=(),
        raw_output_saved=False,
        created_for=EXPLICIT_APPROVAL_GATE_CREATED_FOR,
    )
    gate.to_summary()
    return gate


def validate_explicit_approval_gate(gate: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "ready_for_human_review",
        "armed_state",
        "armed",
        "fired",
        "execution_allowed",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "human_confirmation_required",
        "human_confirmation_status",
        "explicit_approval_required",
        "explicit_approval_status",
        "approval_phrase_hash",
        "approval_phrase_ref",
        "final_live_approval_packet_ref",
        "human_confirmation_checklist_ref",
        "pre_live_package_manifest_ref",
        "live_execution_boundary_ref",
        "no_call_integration_summary_ref",
        "call_attempt_summary_ref",
        "final_gate_result_ref",
        "one_shot_budget_lock",
        "single_call_policy_lock",
        "no_retry_policy_lock",
        "no_reserve_policy_lock",
        "no_fallback_policy_lock",
        "no_second_call_policy_lock",
        "provider",
        "model",
        "key_slot",
        "failure_type",
        "errors",
        "raw_output_saved",
        "created_for",
    }
    if not required <= set(gate):
        raise P3UExplicitApprovalGateError("missing required gate item")
    if gate["schema_version"] != EXPLICIT_APPROVAL_GATE_SCHEMA_VERSION:
        raise P3UExplicitApprovalGateError("missing required gate item")
    if gate["created_for"] != EXPLICIT_APPROVAL_GATE_CREATED_FOR:
        raise P3UExplicitApprovalGateError("execution_allowed true in P3U")
    _validate_gate_status(_string(gate["status"]))
    validate_explicit_approval_status(_string(gate["explicit_approval_status"]))
    validate_explicit_approval_status(_string(gate["human_confirmation_status"]))
    validate_gate_no_call_invariants(gate)
    validate_armed_state(_string(gate["armed_state"]), execution_allowed=False, live_call_allowed=False, model_call_count=0, call_model_count=0)
    validate_approval_phrase_hash(_string(gate["approval_phrase_hash"]))
    validate_approval_phrase_ref(_string(gate["approval_phrase_ref"]))
    for ref_field in (
        "final_live_approval_packet_ref",
        "human_confirmation_checklist_ref",
        "pre_live_package_manifest_ref",
        "live_execution_boundary_ref",
        "no_call_integration_summary_ref",
        "call_attempt_summary_ref",
        "final_gate_result_ref",
    ):
        validate_armed_state_artifact_ref(_string(gate[ref_field]))
    validate_one_shot_budget_lock(_mapping(gate["one_shot_budget_lock"]))
    for field in (
        "single_call_policy_lock",
        "no_retry_policy_lock",
        "no_reserve_policy_lock",
        "no_fallback_policy_lock",
        "no_second_call_policy_lock",
    ):
        validate_policy_lock(_mapping(gate[field]))
    scan_result = scan_artifacts({EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME: dict(gate)})
    if not scan_result.ok:
        raise P3UExplicitApprovalGateError("scan failed", failure_type=scan_result.failure_type)


def validate_armed_but_not_fired_state(summary: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "armed_state",
        "armed_states",
        "armed",
        "fired",
        "execution_allowed",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "raw_output_saved",
        "explicit_approval_status",
        "human_confirmation_status",
        "failure_type",
        "errors",
        "created_for",
    }
    if not required <= set(summary):
        raise P3UExplicitApprovalGateError("missing required armed state item")
    if summary["schema_version"] != ARMED_STATE_SCHEMA_VERSION:
        raise P3UExplicitApprovalGateError("missing required armed state item")
    if summary["created_for"] != EXPLICIT_APPROVAL_GATE_CREATED_FOR:
        raise P3UExplicitApprovalGateError("execution_allowed true in P3U")
    validate_explicit_approval_status(_string(summary["explicit_approval_status"]))
    validate_explicit_approval_status(_string(summary["human_confirmation_status"]))
    validate_gate_no_call_invariants(summary)
    validate_armed_state_machine(
        {
            "states": tuple(summary.get("armed_states", ())),
            "current_state": summary.get("armed_state"),
            "execution_allowed": summary.get("execution_allowed"),
            "live_call_allowed": summary.get("live_call_allowed"),
            "model_call_count": summary.get("model_call_count"),
            "call_model_count": summary.get("call_model_count"),
        }
    )
    scan_result = scan_artifacts({ARMED_STATE_ARTIFACT_NAME: dict(summary)})
    if not scan_result.ok:
        raise P3UExplicitApprovalGateError("scan failed", failure_type=scan_result.failure_type)


def validate_armed_state_machine(summary: Mapping[str, Any]) -> None:
    states = tuple(summary.get("states", ()))
    if not states:
        raise P3UExplicitApprovalGateError("unknown armed state")
    for state in states:
        validate_armed_state(
            str(state),
            execution_allowed=summary.get("execution_allowed"),
            live_call_allowed=summary.get("live_call_allowed"),
            model_call_count=summary.get("model_call_count"),
            call_model_count=summary.get("call_model_count"),
        )
    for current, next_state in zip(states, states[1:]):
        if next_state not in P3U_ALLOWED_ARMED_TRANSITIONS.get(current, frozenset()):
            raise P3UExplicitApprovalGateError("invalid armed transition")
    if summary.get("current_state") != states[-1]:
        raise P3UExplicitApprovalGateError("unknown armed state")


def validate_armed_state(
    state: str,
    *,
    execution_allowed: Any = False,
    live_call_allowed: Any = False,
    model_call_count: Any = 0,
    call_model_count: Any = 0,
) -> None:
    if execution_allowed is not False:
        raise P3UExplicitApprovalGateError("execution_allowed true in P3U")
    if live_call_allowed is not False:
        raise P3UExplicitApprovalGateError("live_call_allowed true in P3U")
    if int(model_call_count or 0) > 0:
        raise P3UExplicitApprovalGateError("model_call_count > 0 in P3U")
    if int(call_model_count or 0) > 0:
        raise P3UExplicitApprovalGateError("call_model_count > 0 in P3U")
    if state in P3U_FORBIDDEN_ARMED_STATES:
        raise P3UExplicitApprovalGateError("forbidden armed state")
    if state not in P3U_ALLOWED_ARMED_STATES:
        raise P3UExplicitApprovalGateError("unknown armed state")


def validate_one_shot_budget_lock(lock: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "max_model_calls",
        "model_call_count",
        "budget_locked",
        "budget_spent",
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "budget_reset_allowed",
        "budget_widening_allowed",
    }
    if not required <= set(lock):
        raise P3UExplicitApprovalGateError("missing policy lock item")
    if lock["schema_version"] != ONE_SHOT_BUDGET_LOCK_SCHEMA_VERSION:
        raise P3UExplicitApprovalGateError("missing policy lock item")
    if lock["max_model_calls"] != 1:
        raise P3UExplicitApprovalGateError("model_call_count > 0 in P3U")
    if lock["model_call_count"] != 0:
        raise P3UExplicitApprovalGateError("model_call_count > 0 in P3U")
    if lock["budget_locked"] is not True:
        raise P3UExplicitApprovalGateError("missing policy lock item")
    for field, condition in (
        ("budget_spent", "budget_spent true"),
        ("retry_allowed", "retry_allowed true"),
        ("reserve_allowed", "reserve_allowed true"),
        ("fallback_allowed", "fallback_allowed true"),
        ("second_call_allowed", "second_call_allowed true"),
        ("budget_reset_allowed", "budget_reset_allowed true"),
        ("budget_widening_allowed", "budget_widening_allowed true"),
    ):
        if lock.get(field) is not False:
            raise P3UExplicitApprovalGateError(condition)
    _reject_forbidden_fields(lock)


def validate_policy_lock(lock: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "single_call_only",
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "provider_rotation_allowed",
        "key_rotation_allowed",
        "policy_widening_allowed",
    }
    if not required <= set(lock):
        raise P3UExplicitApprovalGateError("missing policy lock item")
    if lock["schema_version"] != POLICY_LOCK_SCHEMA_VERSION:
        raise P3UExplicitApprovalGateError("missing policy lock item")
    if lock["single_call_only"] is not True:
        raise P3UExplicitApprovalGateError("missing policy lock item")
    for field, condition in (
        ("retry_allowed", "retry_allowed true"),
        ("reserve_allowed", "reserve_allowed true"),
        ("fallback_allowed", "fallback_allowed true"),
        ("second_call_allowed", "second_call_allowed true"),
        ("provider_rotation_allowed", "provider_rotation_allowed true"),
        ("key_rotation_allowed", "key_rotation_allowed true"),
        ("policy_widening_allowed", "policy_widening_allowed true"),
    ):
        if lock.get(field) is not False:
            raise P3UExplicitApprovalGateError(condition)
    _reject_forbidden_fields(lock)


def validate_final_approval_linkage(
    *,
    final_live_approval_packet: Mapping[str, Any],
    human_confirmation_checklist: Mapping[str, Any],
    pre_live_package_manifest: Mapping[str, Any],
    live_execution_boundary: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
) -> None:
    _consistent_run_id(
        final_live_approval_packet,
        human_confirmation_checklist,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    _consistent_approval_hash(
        final_live_approval_packet,
        pre_live_package_manifest,
        live_execution_boundary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    for ref in (
        final_live_approval_packet.get("pre_live_package_manifest_ref"),
        final_live_approval_packet.get("human_confirmation_checklist_ref"),
        final_live_approval_packet.get("approval_package_ref"),
        final_live_approval_packet.get("no_call_integration_summary_ref"),
        final_live_approval_packet.get("call_attempt_summary_ref"),
        final_live_approval_packet.get("final_gate_result_ref"),
    ):
        validate_armed_state_artifact_ref(_string(ref))


def validate_gate_no_call_invariants(payload: Mapping[str, Any]) -> None:
    _reject_forbidden_fields(payload)
    if "status" in payload:
        _reject_live_like_status(_string(payload["status"]))
    for field, condition in (
        ("fired", "fired true in P3U"),
        ("executed", "fired true in P3U"),
        ("called", "fired true in P3U"),
        ("provider_called", "fired true in P3U"),
        ("network_called", "fired true in P3U"),
        ("execution_allowed", "execution_allowed true in P3U"),
        ("live_call_allowed", "live_call_allowed true in P3U"),
        ("raw_output_saved", "raw_output_saved=True detected"),
        ("provider_activation", "candidate interpreted as active"),
        ("provider_allowlist_activated", "candidate interpreted as active"),
        ("sdk_import_activation", "SDK import marker in P3S"),
        ("sdk_imported", "SDK import marker in P3S"),
        ("key_loading_activation", "key loaded marker in P3S"),
        ("key_loaded", "key loaded marker in P3S"),
        ("network_call", "network call marker in P3S"),
        ("live_smoke_executed", "live smoke marker in P3S"),
        ("call_model_executed", "call_model attempted in P3R"),
        ("retry_allowed", "retry_allowed true"),
        ("reserve_allowed", "reserve_allowed true"),
        ("fallback_allowed", "fallback_allowed true"),
        ("second_call_allowed", "second_call_allowed true"),
        ("budget_spent", "budget_spent true"),
    ):
        if payload.get(field) is True:
            raise P3UExplicitApprovalGateError(condition)
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
                raise P3UExplicitApprovalGateError("call_model_count > 0 in P3U")
            if field == "actual_sdk_import_count":
                raise P3UExplicitApprovalGateError("SDK import marker in P3S")
            if field in {"actual_key_value_read_count", "actual_env_value_read_count"}:
                raise P3UExplicitApprovalGateError("key loaded marker in P3S")
            if field == "actual_network_call_count":
                raise P3UExplicitApprovalGateError("network call marker in P3S")
            if field == "actual_live_smoke_count":
                raise P3UExplicitApprovalGateError("live smoke marker in P3S")
            raise P3UExplicitApprovalGateError("model_call_count > 0 in P3U")
    if scan_value_for_unsafe_content(dict(payload), value_path="explicit_approval_gate"):
        raise P3UExplicitApprovalGateError("raw key/token/env var value in approval")


def validate_explicit_approval_status(status: str) -> None:
    if status in P3U_FORBIDDEN_APPROVAL_STATUSES:
        raise P3UExplicitApprovalGateError("approved explicit approval status in P3U")
    if status not in P3U_ALLOWED_APPROVAL_STATUSES:
        raise P3UExplicitApprovalGateError("unknown gate status")


def validate_armed_state_artifact_ref(ref: str) -> None:
    try:
        validate_packet_artifact_ref(ref)
    except P3TApprovalPacketError as exc:
        raise P3UExplicitApprovalGateError(exc.condition, failure_type=exc.failure_type) from exc


def write_explicit_approval_gate(
    run_dir: Path,
    gate: ExplicitApprovalGate | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = gate.to_summary() if isinstance(gate, ExplicitApprovalGate) else dict(gate)
    validate_explicit_approval_gate(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=EXPLICIT_APPROVAL_GATE_ARTIFACT_NAME)


def write_armed_state(
    run_dir: Path,
    state: ArmedButNotFiredState | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = ARMED_STATE_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = state.to_summary() if isinstance(state, ArmedButNotFiredState) else dict(state)
    validate_armed_but_not_fired_state(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=ARMED_STATE_ARTIFACT_NAME)


def explicit_approval_gate_default_runtime_creation_enabled() -> bool:
    return False


def armed_state_default_runtime_creation_enabled() -> bool:
    return False


def aggregate_gate_failure_type(failure_types: Sequence[str | None]) -> str | None:
    present = {failure_type for failure_type in failure_types if failure_type}
    for failure_type in PRE_LIVE_FAILURE_PRIORITY:
        if failure_type in present:
            return failure_type
    return None


def _write_json(run_dir: Path, artifact_name: str | Path, payload: Mapping[str, Any], *, expected_name: str) -> Path:
    path = _resolve_gate_artifact_path(run_dir, artifact_name, expected_name=expected_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3UExplicitApprovalGateError("artifact write failure") from exc
    return path


def _resolve_gate_artifact_path(run_dir: Path, artifact_path: str | Path, *, expected_name: str) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if _is_url_ref(str(artifact_path)):
        raise P3UExplicitApprovalGateError("unsafe artifact reference")
    if ".." in requested.parts:
        raise P3UExplicitApprovalGateError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3UExplicitApprovalGateError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3UExplicitApprovalGateError("artifact path outside run_dir")
    if relative.as_posix() != expected_name:
        raise P3UExplicitApprovalGateError("artifact write failure")
    return resolved


def _consistent_run_id(*payloads: Mapping[str, Any]) -> str:
    run_ids = []
    for payload in payloads:
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise P3UExplicitApprovalGateError("run_id mismatch")
        run_ids.append(run_id)
    if len(set(run_ids)) != 1:
        raise P3UExplicitApprovalGateError("run_id mismatch")
    return run_ids[0]


def _consistent_approval_hash(*payloads: Mapping[str, Any]) -> str:
    hashes = []
    for payload in payloads:
        value = payload.get("approval_phrase_hash")
        if not isinstance(value, str) or not value:
            raise P3UExplicitApprovalGateError("missing approval_phrase_hash")
        validate_approval_phrase_hash(value)
        hashes.append(value)
    if len(set(hashes)) != 1:
        raise P3UExplicitApprovalGateError("approval_phrase_hash mismatch")
    return hashes[0]


def _artifact_scan_status(
    summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    *,
    missing_condition: str,
) -> str:
    if summary is None:
        raise P3UExplicitApprovalGateError(missing_condition)
    if isinstance(summary, ArtifactSafetyResult):
        if not summary.ok:
            raise P3UExplicitApprovalGateError("scan failed", failure_type=summary.failure_type)
        return "pass"
    _reject_forbidden_fields(summary)
    if scan_value_for_unsafe_content(dict(summary), value_path="artifact_safety_summary"):
        raise P3UExplicitApprovalGateError("raw key/token/env var value in approval")
    if summary.get("ok") is True or summary.get("status") in {"pass", "ok"}:
        return "pass"
    if summary.get("ok") is False or summary.get("status") in {"fail", "failed", "blocked"}:
        raise P3UExplicitApprovalGateError("scan failed")
    raise P3UExplicitApprovalGateError(missing_condition)


def _validate_gate_status(status: str) -> None:
    _reject_live_like_status(status)
    if status not in P3U_ALLOWED_GATE_STATUSES:
        raise P3UExplicitApprovalGateError("unknown gate status")


def _reject_live_like_status(status: str) -> None:
    if status in P3U_SUCCESS_LIKE_STATUSES:
        raise P3UExplicitApprovalGateError("success-like status in P3U")
    if status in P3U_FORBIDDEN_APPROVAL_STATUSES:
        raise P3UExplicitApprovalGateError("approved explicit approval status in P3U")
    if status in P3U_FORBIDDEN_ARMED_STATES:
        raise P3UExplicitApprovalGateError("forbidden armed state")


def _reject_forbidden_fields(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if key in P3U_FORBIDDEN_FIELDS:
            if key in {"approval_phrase", "raw_approval_phrase"}:
                raise P3UExplicitApprovalGateError("raw approval phrase found")
            if key == "provider_response":
                raise P3UExplicitApprovalGateError("provider response found")
            if key == "token_usage":
                raise P3UExplicitApprovalGateError("token usage found")
            raise P3UExplicitApprovalGateError("raw key/token/env var value in approval")
        if isinstance(value, Mapping):
            _reject_forbidden_fields(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_forbidden_fields(item)


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise P3UExplicitApprovalGateError("missing required gate item")
    return value


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3UExplicitApprovalGateError("missing artifact reference")
    return value


def _is_url_ref(value: str) -> bool:
    return value.startswith(("http://", "https://")) or "://" in value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
