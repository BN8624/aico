# P3T 최종 live 승인 packet을 실제 호출 없이 사람 검토용으로 조립하고 검증하는 스켈레톤입니다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifact_safety import ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .pre_live_package import (
    PRE_LIVE_FAILURE_PRIORITY,
    P3S_FAILURES,
    validate_approval_phrase_hash,
    validate_pre_live_package,
)

FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME = "final_live_approval_packet.json"
HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME = "human_confirmation_checklist.json"
FINAL_LIVE_APPROVAL_PACKET_SCHEMA_VERSION = "p3_final_live_approval_packet_v1"
HUMAN_CONFIRMATION_CHECKLIST_SCHEMA_VERSION = "p3_human_confirmation_checklist_v1"
NO_CALL_EVIDENCE_SCHEMA_VERSION = "p3_no_call_evidence_v1"
FINAL_LIVE_APPROVAL_PACKET_CREATED_FOR = "human_confirmation_only_no_call"
ALLOWED_PACKET_STATUSES = frozenset({"prepared", "ready_for_human_review", "blocked", "fail"})
SUCCESS_LIKE_STATUSES = frozenset(
    {"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"}
)
ALLOWED_HUMAN_CONFIRMATION_STATUSES = frozenset({"pending", "review_required", "not_granted"})
FORBIDDEN_HUMAN_CONFIRMATION_STATUSES = frozenset(
    {"approved", "granted", "confirmed", "execution_approved", "live_approved"}
)
REQUIRED_CHECKLIST_ITEMS = (
    "I understand this packet does not execute a live call.",
    "I understand live_call_allowed remains false.",
    "I understand model_call_count remains 0.",
    "I understand call_model_count remains 0.",
    "I understand no SDK import is approved.",
    "I understand no key loading is approved.",
    "I understand no provider activation is approved.",
    "I understand no network call is approved.",
    "I understand no live smoke is approved in P3T.",
    "I understand actual first call requires a later explicit approval phase.",
)
REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "pytest_passed",
        "targeted_tests_passed",
        "agents_claude_byte_identical",
        "runtime_forbidden_import_ast_passed",
        "forbidden_import_env_read_string_search_passed",
        "call_model_execution_path_string_check_passed",
        "default_runtime_artifact_creation_zero",
        "actual_api_call_zero",
        "actual_llm_call_zero",
        "actual_key_use_zero",
        "actual_env_value_read_zero",
        "actual_provider_sdk_import_zero",
        "actual_network_call_zero",
        "actual_live_smoke_zero",
        "actual_call_model_execution_zero",
        "live_call_allowed_false",
        "model_call_count_zero",
        "call_model_count_zero",
    }
)
ACTUAL_ZERO_EVIDENCE_FIELDS = frozenset(
    {
        "default_runtime_artifact_creation_zero",
        "actual_api_call_zero",
        "actual_llm_call_zero",
        "actual_key_use_zero",
        "actual_env_value_read_zero",
        "actual_provider_sdk_import_zero",
        "actual_network_call_zero",
        "actual_live_smoke_zero",
        "actual_call_model_execution_zero",
        "live_call_allowed_false",
        "model_call_count_zero",
        "call_model_count_zero",
    }
)
FORBIDDEN_PACKET_FIELDS = frozenset(
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
FORBIDDEN_COMMAND_TOKENS = frozenset(
    {
        "--execute",
        "--live",
        "--use-key",
        "--load-key",
        "--call-model",
        "--network",
        "--sdk-import",
        "--provider-activate",
        "--allowlist-activate",
        "--live-call-allowed",
    }
)
P3T_FAILURES = {
    **P3S_FAILURES,
    "approved human confirmation status in P3T": "SECURITY_BLOCKED",
    "success-like status in P3T": "SECURITY_BLOCKED",
    "execution_allowed true in P3T": "SECURITY_BLOCKED",
    "live_call_allowed true in P3T": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3T": "SECURITY_BLOCKED",
    "call_model_count > 0 in P3T": "SECURITY_BLOCKED",
    "missing required checklist item": "CONFIG_ERROR",
    "missing critical evidence": "CONFIG_ERROR",
    "evidence check failed": "CONFIG_ERROR",
    "actual call evidence not zero": "SECURITY_BLOCKED",
    "forbidden command token": "SECURITY_BLOCKED",
    "missing no-execute command guard": "CONFIG_ERROR",
    "missing required packet item": "CONFIG_ERROR",
    "approval_phrase_ref unsafe": "SECURITY_BLOCKED",
}


class P3TApprovalPacketError(RuntimeError):
    def __init__(self, condition: str, *, failure_type: str | None = None) -> None:
        self.condition = condition
        self.failure_type = failure_type or P3T_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class HumanConfirmationChecklist:
    schema_version: str
    run_id: str
    status: str
    human_confirmation_required: bool
    human_confirmation_status: str
    items: tuple[str, ...]
    all_items_acknowledged: bool
    execution_allowed: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    failure_type: str | None
    errors: tuple[str, ...]

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_human_confirmation_checklist(payload)
        return payload


@dataclass(frozen=True)
class NoCallEvidenceSummary:
    schema_version: str
    run_id: str
    pytest_passed: bool
    targeted_tests_passed: bool
    agents_claude_byte_identical: bool
    runtime_forbidden_import_ast_passed: bool
    forbidden_import_env_read_string_search_passed: bool
    call_model_execution_path_string_check_passed: bool
    default_runtime_artifact_creation_zero: bool
    actual_api_call_zero: bool
    actual_llm_call_zero: bool
    actual_key_use_zero: bool
    actual_env_value_read_zero: bool
    actual_provider_sdk_import_zero: bool
    actual_network_call_zero: bool
    actual_live_smoke_zero: bool
    actual_call_model_execution_zero: bool
    live_call_allowed_false: bool
    model_call_count_zero: bool
    call_model_count_zero: bool
    failure_type: str | None = None
    errors: tuple[str, ...] = ()

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_no_call_evidence_summary(payload)
        return payload


@dataclass(frozen=True)
class FinalLiveApprovalPacket:
    schema_version: str
    run_id: str
    status: str
    ready_for_human_review: bool
    human_confirmation_required: bool
    human_confirmation_status: str
    execution_allowed: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    approval_phrase_hash: str
    approval_phrase_ref: str
    pre_live_package_manifest_ref: str
    approval_package_ref: str
    no_call_integration_summary_ref: str
    call_attempt_summary_ref: str
    final_gate_result_ref: str
    no_call_evidence: dict[str, object]
    test_evidence: dict[str, object]
    next_step_command_skeleton: str
    human_confirmation_checklist_ref: str
    provider: str
    model: str
    key_slot: str
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    created_for: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_final_live_approval_packet(payload)
        return payload


def build_human_confirmation_checklist(
    *,
    run_id: str,
    status: str = "ready_for_human_review",
    human_confirmation_status: str = "review_required",
    items: Sequence[str] = REQUIRED_CHECKLIST_ITEMS,
    all_items_acknowledged: bool = False,
) -> HumanConfirmationChecklist:
    checklist = HumanConfirmationChecklist(
        schema_version=HUMAN_CONFIRMATION_CHECKLIST_SCHEMA_VERSION,
        run_id=run_id,
        status=status,
        human_confirmation_required=True,
        human_confirmation_status=human_confirmation_status,
        items=tuple(items),
        all_items_acknowledged=all_items_acknowledged,
        execution_allowed=False,
        live_call_allowed=False,
        model_call_count=0,
        call_model_count=0,
        failure_type=None,
        errors=(),
    )
    checklist.to_summary()
    return checklist


def build_no_call_evidence_summary(run_id: str, **overrides: bool) -> NoCallEvidenceSummary:
    data = {field: True for field in REQUIRED_EVIDENCE_FIELDS}
    data.update(overrides)
    summary = NoCallEvidenceSummary(
        schema_version=NO_CALL_EVIDENCE_SCHEMA_VERSION,
        run_id=run_id,
        **data,
    )
    summary.to_summary()
    return summary


def build_final_live_approval_packet(
    *,
    pre_live_package_manifest: Mapping[str, Any],
    approval_package_summary: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
    artifact_safety_summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    runtime_flags_summary: Mapping[str, Any],
    rollback_plan_summary: Mapping[str, Any],
    test_evidence_summary: NoCallEvidenceSummary | Mapping[str, Any],
    human_decision_summary: HumanConfirmationChecklist | Mapping[str, Any],
    next_step_command_skeleton: str = "python -m aico_v0.live_smoke --dry-run --no-execute --review-only",
    approval_phrase_ref: str = "approval_phrase_hash_only",
    status: str = "ready_for_human_review",
) -> FinalLiveApprovalPacket:
    validate_pre_live_package(pre_live_package_manifest)
    validate_packet_no_call_invariants(approval_package_summary)
    validate_packet_no_call_invariants(no_call_integration_summary)
    validate_packet_no_call_invariants(call_attempt_summary)
    validate_packet_no_call_invariants(final_live_gate_result)
    validate_packet_no_call_invariants(runtime_flags_summary)
    validate_packet_no_call_invariants(rollback_plan_summary)
    _artifact_scan_status(artifact_safety_summary, missing_condition="pre-scan missing")
    evidence = test_evidence_summary.to_summary() if isinstance(test_evidence_summary, NoCallEvidenceSummary) else dict(test_evidence_summary)
    checklist = human_decision_summary.to_summary() if isinstance(human_decision_summary, HumanConfirmationChecklist) else dict(human_decision_summary)
    validate_no_call_evidence_summary(evidence)
    validate_human_confirmation_checklist(checklist)
    validate_next_step_command_skeleton(next_step_command_skeleton)
    validate_approval_phrase_ref(approval_phrase_ref)
    run_id = _consistent_run_id(
        pre_live_package_manifest,
        approval_package_summary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
        evidence,
        checklist,
    )
    approval_hash = _consistent_approval_hash(
        pre_live_package_manifest,
        approval_package_summary,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    packet = FinalLiveApprovalPacket(
        schema_version=FINAL_LIVE_APPROVAL_PACKET_SCHEMA_VERSION,
        run_id=run_id,
        status=status,
        ready_for_human_review=status == "ready_for_human_review",
        human_confirmation_required=True,
        human_confirmation_status=_string(checklist["human_confirmation_status"]),
        execution_allowed=False,
        live_call_allowed=False,
        model_call_count=0,
        call_model_count=0,
        approval_phrase_hash=approval_hash,
        approval_phrase_ref=approval_phrase_ref,
        pre_live_package_manifest_ref="pre_live_package_manifest.json",
        approval_package_ref=_string(pre_live_package_manifest["approval_package_ref"]),
        no_call_integration_summary_ref=_string(pre_live_package_manifest["no_call_integration_summary_ref"]),
        call_attempt_summary_ref=_string(pre_live_package_manifest["call_attempt_summary_ref"]),
        final_gate_result_ref=_string(pre_live_package_manifest["final_gate_result_ref"]),
        no_call_evidence=evidence,
        test_evidence=evidence,
        next_step_command_skeleton=next_step_command_skeleton,
        human_confirmation_checklist_ref=HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
        provider=_string(pre_live_package_manifest["provider"]),
        model=_string(pre_live_package_manifest["model"]),
        key_slot=_string(pre_live_package_manifest["key_slot"]),
        failure_type=None,
        errors=(),
        raw_output_saved=False,
        created_for=FINAL_LIVE_APPROVAL_PACKET_CREATED_FOR,
    )
    packet.to_summary()
    return packet


def validate_final_live_approval_packet(packet: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "ready_for_human_review",
        "human_confirmation_required",
        "human_confirmation_status",
        "execution_allowed",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "approval_phrase_hash",
        "approval_phrase_ref",
        "pre_live_package_manifest_ref",
        "approval_package_ref",
        "no_call_integration_summary_ref",
        "call_attempt_summary_ref",
        "final_gate_result_ref",
        "no_call_evidence",
        "test_evidence",
        "next_step_command_skeleton",
        "human_confirmation_checklist_ref",
        "provider",
        "model",
        "key_slot",
        "failure_type",
        "errors",
        "raw_output_saved",
        "created_for",
    }
    if not required <= set(packet):
        raise P3TApprovalPacketError("missing required packet item")
    if packet["schema_version"] != FINAL_LIVE_APPROVAL_PACKET_SCHEMA_VERSION:
        raise P3TApprovalPacketError("missing required packet item")
    if packet["created_for"] != FINAL_LIVE_APPROVAL_PACKET_CREATED_FOR:
        raise P3TApprovalPacketError("execution_allowed true in P3T")
    _validate_packet_status(_string(packet["status"]))
    validate_human_confirmation_status(_string(packet["human_confirmation_status"]))
    if packet["human_confirmation_required"] is not True:
        raise P3TApprovalPacketError("missing required checklist item")
    validate_packet_no_call_invariants(packet)
    validate_approval_phrase_hash(_string(packet["approval_phrase_hash"]))
    validate_approval_phrase_ref(_string(packet["approval_phrase_ref"]))
    validate_packet_artifact_ref(_string(packet["pre_live_package_manifest_ref"]))
    validate_packet_artifact_ref(_string(packet["approval_package_ref"]))
    validate_packet_artifact_ref(_string(packet["no_call_integration_summary_ref"]))
    validate_packet_artifact_ref(_string(packet["call_attempt_summary_ref"]))
    validate_packet_artifact_ref(_string(packet["final_gate_result_ref"]))
    validate_packet_artifact_ref(_string(packet["human_confirmation_checklist_ref"]))
    validate_no_call_evidence_summary(_mapping(packet["no_call_evidence"]))
    validate_no_call_evidence_summary(_mapping(packet["test_evidence"]))
    validate_next_step_command_skeleton(_string(packet["next_step_command_skeleton"]))
    scan_result = scan_artifacts({FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME: dict(packet)})
    if not scan_result.ok:
        raise P3TApprovalPacketError("scan failed", failure_type=scan_result.failure_type)


def validate_human_confirmation_checklist(checklist: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "human_confirmation_required",
        "human_confirmation_status",
        "items",
        "all_items_acknowledged",
        "execution_allowed",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "failure_type",
        "errors",
    }
    if not required <= set(checklist):
        raise P3TApprovalPacketError("missing required checklist item")
    if checklist["schema_version"] != HUMAN_CONFIRMATION_CHECKLIST_SCHEMA_VERSION:
        raise P3TApprovalPacketError("missing required checklist item")
    _validate_packet_status(_string(checklist["status"]))
    validate_human_confirmation_status(_string(checklist["human_confirmation_status"]))
    if checklist["human_confirmation_required"] is not True:
        raise P3TApprovalPacketError("missing required checklist item")
    validate_packet_no_call_invariants(checklist)
    items = tuple(str(item) for item in checklist.get("items", ()))
    if not set(REQUIRED_CHECKLIST_ITEMS) <= set(items):
        raise P3TApprovalPacketError("missing required checklist item")
    scan_result = scan_artifacts({HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME: dict(checklist)})
    if not scan_result.ok:
        raise P3TApprovalPacketError("scan failed", failure_type=scan_result.failure_type)


def validate_no_call_evidence_summary(evidence: Mapping[str, Any]) -> None:
    if not REQUIRED_EVIDENCE_FIELDS <= set(evidence):
        raise P3TApprovalPacketError("missing critical evidence")
    if evidence.get("schema_version") != NO_CALL_EVIDENCE_SCHEMA_VERSION:
        raise P3TApprovalPacketError("missing critical evidence")
    validate_packet_no_call_invariants(evidence)
    for field in REQUIRED_EVIDENCE_FIELDS:
        if evidence.get(field) is not True:
            if field in ACTUAL_ZERO_EVIDENCE_FIELDS:
                raise P3TApprovalPacketError("actual call evidence not zero")
            raise P3TApprovalPacketError("evidence check failed")


def validate_next_step_command_skeleton(command: str) -> None:
    if not command or scan_value_for_unsafe_content(command, value_path="next_step_command_skeleton"):
        raise P3TApprovalPacketError("raw key/token/env var value in approval")
    tokens = command.split()
    if any(token in FORBIDDEN_COMMAND_TOKENS for token in tokens):
        raise P3TApprovalPacketError("forbidden command token")
    if "--no-execute" not in tokens:
        raise P3TApprovalPacketError("missing no-execute command guard")
    if "--dry-run" not in tokens and "--review-only" not in tokens:
        raise P3TApprovalPacketError("missing no-execute command guard")


def validate_approval_phrase_ref(ref: str) -> None:
    if "approval_phrase=" in ref or "I approve AICO first live smoke" in ref:
        raise P3TApprovalPacketError("raw approval phrase found")
    validate_packet_artifact_ref(ref, condition="approval_phrase_ref unsafe")


def validate_packet_artifact_ref(ref: str, *, condition: str = "unsafe artifact reference") -> None:
    if not ref:
        raise P3TApprovalPacketError("missing artifact reference")
    if _is_url_ref(ref):
        raise P3TApprovalPacketError(condition)
    requested = Path(ref)
    if requested.is_absolute():
        raise P3TApprovalPacketError(condition)
    if ".." in requested.parts:
        raise P3TApprovalPacketError("path traversal attempted")


def validate_human_confirmation_status(status: str) -> None:
    if status in FORBIDDEN_HUMAN_CONFIRMATION_STATUSES:
        raise P3TApprovalPacketError("approved human confirmation status in P3T")
    if status not in ALLOWED_HUMAN_CONFIRMATION_STATUSES:
        raise P3TApprovalPacketError("unknown gate status")


def validate_packet_no_call_invariants(payload: Mapping[str, Any]) -> None:
    _reject_forbidden_fields(payload)
    if "status" in payload:
        _reject_live_like_status(_string(payload["status"]))
    for field, condition in (
        ("execution_allowed", "execution_allowed true in P3T"),
        ("live_call_allowed", "live_call_allowed true in P3T"),
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
    ):
        if payload.get(field) is True:
            raise P3TApprovalPacketError(condition)
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
                raise P3TApprovalPacketError("call_model_count > 0 in P3T")
            if field == "actual_sdk_import_count":
                raise P3TApprovalPacketError("SDK import marker in P3S")
            if field in {"actual_key_value_read_count", "actual_env_value_read_count"}:
                raise P3TApprovalPacketError("key loaded marker in P3S")
            if field == "actual_network_call_count":
                raise P3TApprovalPacketError("network call marker in P3S")
            if field == "actual_live_smoke_count":
                raise P3TApprovalPacketError("live smoke marker in P3S")
            raise P3TApprovalPacketError("model_call_count > 0 in P3T")
    if scan_value_for_unsafe_content(dict(payload), value_path="final_live_approval_packet"):
        raise P3TApprovalPacketError("raw key/token/env var value in approval")


def write_final_live_approval_packet(
    run_dir: Path,
    packet: FinalLiveApprovalPacket | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = packet.to_summary() if isinstance(packet, FinalLiveApprovalPacket) else dict(packet)
    validate_final_live_approval_packet(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME)


def write_human_confirmation_checklist(
    run_dir: Path,
    checklist: HumanConfirmationChecklist | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = checklist.to_summary() if isinstance(checklist, HumanConfirmationChecklist) else dict(checklist)
    validate_human_confirmation_checklist(payload)
    return _write_json(run_dir, artifact_name, payload, expected_name=HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME)


def final_live_approval_packet_default_runtime_creation_enabled() -> bool:
    return False


def human_confirmation_checklist_default_runtime_creation_enabled() -> bool:
    return False


def aggregate_packet_failure_type(failure_types: Sequence[str | None]) -> str | None:
    present = {failure_type for failure_type in failure_types if failure_type}
    for failure_type in PRE_LIVE_FAILURE_PRIORITY:
        if failure_type in present:
            return failure_type
    return None


def _write_json(run_dir: Path, artifact_name: str | Path, payload: Mapping[str, Any], *, expected_name: str) -> Path:
    path = _resolve_packet_artifact_path(run_dir, artifact_name, expected_name=expected_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3TApprovalPacketError("artifact write failure") from exc
    return path


def _resolve_packet_artifact_path(run_dir: Path, artifact_path: str | Path, *, expected_name: str) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if _is_url_ref(str(artifact_path)):
        raise P3TApprovalPacketError("unsafe artifact reference")
    if ".." in requested.parts:
        raise P3TApprovalPacketError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3TApprovalPacketError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3TApprovalPacketError("artifact path outside run_dir")
    if relative.as_posix() != expected_name:
        raise P3TApprovalPacketError("artifact write failure")
    return resolved


def _consistent_run_id(*payloads: Mapping[str, Any]) -> str:
    run_ids = []
    for payload in payloads:
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise P3TApprovalPacketError("run_id mismatch")
        run_ids.append(run_id)
    if len(set(run_ids)) != 1:
        raise P3TApprovalPacketError("run_id mismatch")
    return run_ids[0]


def _consistent_approval_hash(*payloads: Mapping[str, Any]) -> str:
    hashes = []
    for payload in payloads:
        value = payload.get("approval_phrase_hash")
        if not isinstance(value, str) or not value:
            raise P3TApprovalPacketError("missing approval_phrase_hash")
        validate_approval_phrase_hash(value)
        hashes.append(value)
    if len(set(hashes)) != 1:
        raise P3TApprovalPacketError("approval_phrase_hash mismatch")
    return hashes[0]


def _artifact_scan_status(
    summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    *,
    missing_condition: str,
) -> str:
    if summary is None:
        raise P3TApprovalPacketError(missing_condition)
    if isinstance(summary, ArtifactSafetyResult):
        if not summary.ok:
            raise P3TApprovalPacketError("scan failed", failure_type=summary.failure_type)
        return "pass"
    _reject_forbidden_fields(summary)
    if scan_value_for_unsafe_content(dict(summary), value_path="artifact_safety_summary"):
        raise P3TApprovalPacketError("raw key/token/env var value in approval")
    if summary.get("ok") is True or summary.get("status") in {"pass", "ok"}:
        return "pass"
    if summary.get("ok") is False or summary.get("status") in {"fail", "failed", "blocked"}:
        raise P3TApprovalPacketError("scan failed")
    raise P3TApprovalPacketError(missing_condition)


def _validate_packet_status(status: str) -> None:
    _reject_live_like_status(status)
    if status not in ALLOWED_PACKET_STATUSES:
        raise P3TApprovalPacketError("unknown gate status")


def _reject_live_like_status(status: str) -> None:
    if status in SUCCESS_LIKE_STATUSES:
        raise P3TApprovalPacketError("success-like status in P3T")
    if status in FORBIDDEN_HUMAN_CONFIRMATION_STATUSES:
        raise P3TApprovalPacketError("approved human confirmation status in P3T")


def _reject_forbidden_fields(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if key in FORBIDDEN_PACKET_FIELDS:
            if key in {"approval_phrase", "raw_approval_phrase"}:
                raise P3TApprovalPacketError("raw approval phrase found")
            if key == "provider_response":
                raise P3TApprovalPacketError("provider response found")
            if key == "token_usage":
                raise P3TApprovalPacketError("token usage found")
            raise P3TApprovalPacketError("raw key/token/env var value in approval")
        if isinstance(value, Mapping):
            _reject_forbidden_fields(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_forbidden_fields(item)


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise P3TApprovalPacketError("missing required packet item")
    return value


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3TApprovalPacketError("missing required packet item")
    return value


def _is_url_ref(value: str) -> bool:
    return value.startswith(("http://", "https://")) or "://" in value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
