# P3G first live smoke 실행 전용 승인과 산출물 스켈레톤을 검증한다.
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .artifact_safety import ArtifactSafetyResult, scan_value_for_unsafe_content
from .key_registry import KeyRegistry
from .provider_allowlist import KNOWN_PROVIDER_CANDIDATES, ProviderAllowlist
from .provider_base import KEY_SLOTS, mask_secrets


FAILURE_TYPE_BY_SMOKE_CONDITION = {
    "explicit approval missing": "HUMAN_DECISION_REQUIRED",
    "approval phrase ambiguous": "HUMAN_DECISION_REQUIRED",
    "required approval field missing": "HUMAN_DECISION_REQUIRED",
    "runtime flag missing": "CONFIG_ERROR",
    "runtime flag false": "CONFIG_ERROR",
    "provider allowlist missing": "CONFIG_ERROR",
    "provider allowlist empty": "CONFIG_ERROR",
    "key missing": "CONFIG_ERROR",
    "budget missing": "CONFIG_ERROR",
    "budget invalid": "CONFIG_ERROR",
    "artifact safety scan missing": "CONFIG_ERROR",
    "artifact safety scan failed": "SECURITY_BLOCKED",
    "unknown provider requested": "SECURITY_BLOCKED",
    "provider not in allowlist": "SECURITY_BLOCKED",
    "unknown endpoint requested": "SECURITY_BLOCKED",
    "arbitrary URL requested": "SECURITY_BLOCKED",
    "raw key found": "SECURITY_BLOCKED",
    "env var value found": "SECURITY_BLOCKED",
    "unmasked raw provider output found": "SECURITY_BLOCKED",
    "raw_output_saved=True detected": "SECURITY_BLOCKED",
    "allow_raw_output not false": "SECURITY_BLOCKED",
    "network call in default tests": "SECURITY_BLOCKED",
    "live call attempted without all gates": "SECURITY_BLOCKED",
    "retry attempted": "SECURITY_BLOCKED",
    "reserve attempted": "SECURITY_BLOCKED",
    "second model call attempted": "SECURITY_BLOCKED",
    "budget exceeded": "BUDGET_EXCEEDED",
    "timeout": "MODEL_ERROR",
    "429": "MODEL_ERROR",
    "500": "MODEL_ERROR",
    "provider unavailable": "MODEL_ERROR",
    "no response": "MODEL_ERROR",
    "non-json response": "SCHEMA_ERROR",
    "schema-invalid json": "SCHEMA_ERROR",
    "schema-valid empty response": "WORKER_BAD_OUTPUT",
    "ceo_report generation failed": "REPORT_ERROR",
    "artifact write failure": "REPORT_ERROR",
}

REQUIRED_LIVE_SMOKE_FLAGS = (
    "AICO_ENABLE_REAL_PROVIDER",
    "AICO_ALLOW_LIVE_CALLS",
    "AICO_ALLOW_FIRST_LIVE_SMOKE",
)
TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_FLAG_VALUES = frozenset({"0", "false", "no", "off", ""})
AMBIGUOUS_APPROVAL_PHRASES = frozenset({"continue", "proceed", "go ahead", "진행해", "계속해", "해봐", "다음 단계로 가", "승인", "ok"})
URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
ENV_VAR_NAME_PATTERN = re.compile(r"^AICO_[A-Z0-9_]*API_KEY$")

ALLOWED_LIVE_SMOKE_ARTIFACTS = frozenset(
    {
        "run_log.jsonl",
        "ceo_report.md",
        "live_smoke_result.json",
        "artifact_safety_report.json",
    }
)
FORBIDDEN_LIVE_SMOKE_ARTIFACTS = frozenset(
    {
        "final_report.md",
        "failed_draft.md",
        "manager_summary.json",
        "audit_report.json",
        "worker_results.jsonl",
    }
)


@dataclass(frozen=True)
class FirstLiveSmokeApproval:
    provider: str | None = None
    model: str | None = None
    key_slot: str | tuple[str, ...] | list[str] | None = None
    max_model_calls: int | None = None
    max_retries_per_call: int | None = None
    max_runtime_seconds: int | None = None
    allow_raw_output: bool | None = None
    approval_scope: str = "this_run_only"
    approved_by_user: bool = False
    approval_phrase: str | None = None
    endpoint: str | None = None
    run_id: str | None = None
    reason: str | None = None
    metadata: Mapping[str, object] | None = None

    def __repr__(self) -> str:
        safe_fields = {key: _mask_value(value) for key, value in asdict(self).items()}
        rendered = ", ".join(f"{key}={safe_fields[key]!r}" for key in safe_fields)
        return f"FirstLiveSmokeApproval({rendered})"


@dataclass(frozen=True)
class FirstLiveSmokeValidationResult:
    ok: bool
    condition: str | None
    failure_type: str | None
    error: str | None = None


@dataclass(frozen=True)
class DisabledLiveSmokeRunResult:
    status: str
    failure_type: str
    error: str
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_network_call_count: int = 0
    provider_sdk_imported: bool = False
    live_smoke_executed: bool = False


def validate_first_live_smoke_request(
    *,
    approval: FirstLiveSmokeApproval | None,
    flags: Mapping[str, str] | None,
    provider_allowlist: ProviderAllowlist | None,
    key_registry: KeyRegistry | None,
    pre_artifact_scan: ArtifactSafetyResult | None,
    post_artifact_scan: ArtifactSafetyResult | None,
    attempted_model_calls: int = 0,
    retry_attempted: bool = False,
    reserve_attempted: bool = False,
    fallback_provider_attempted: bool = False,
    second_model_call_attempted: bool = False,
) -> FirstLiveSmokeValidationResult:
    for condition in _request_conditions(
        approval=approval,
        flags=flags,
        provider_allowlist=provider_allowlist,
        key_registry=key_registry,
        pre_artifact_scan=pre_artifact_scan,
        post_artifact_scan=post_artifact_scan,
        attempted_model_calls=attempted_model_calls,
        retry_attempted=retry_attempted,
        reserve_attempted=reserve_attempted,
        fallback_provider_attempted=fallback_provider_attempted,
        second_model_call_attempted=second_model_call_attempted,
    ):
        return _failure(condition)
    return FirstLiveSmokeValidationResult(True, None, None)


def validate_first_live_smoke_approval(approval: FirstLiveSmokeApproval | None) -> FirstLiveSmokeValidationResult:
    for condition in _approval_conditions(approval):
        return _failure(condition)
    return FirstLiveSmokeValidationResult(True, None, None)


def build_live_smoke_result(
    *,
    approval: FirstLiveSmokeApproval,
    status: str,
    failure_type: str | None = None,
    error: str | None = None,
    model_call_count: int = 0,
    retry_count: int = 0,
    reserve_used: bool = False,
    raw_output_saved: bool = False,
    masked_raw_output: str | None = None,
    artifact_safety_status: str = "not_run",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    timestamp: str | None = None,
    parent_event_id: str | None = None,
) -> dict[str, object]:
    if raw_output_saved:
        raise ValueError("raw_output_saved must remain false for first live smoke")
    key_slot = _single_key_slot(approval)
    if key_slot is None:
        key_slot = ""
    return {
        "status": status,
        "provider": approval.provider,
        "model": approval.model,
        "key_slot": key_slot,
        "model_call_count": model_call_count,
        "max_model_calls": 1,
        "retry_count": retry_count,
        "max_retries_per_call": 0,
        "reserve_used": reserve_used,
        "raw_output_saved": False,
        "masked_raw_output": _mask_value(masked_raw_output),
        "failure_type": failure_type,
        "error": _mask_value(error),
        "artifact_safety_status": artifact_safety_status,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "run_id": approval.run_id,
        "timestamp": timestamp,
        "parent_event_id": parent_event_id,
    }


def build_artifact_safety_report(
    scan_result: ArtifactSafetyResult | None,
    *,
    scanned_artifacts: tuple[str, ...] = (),
) -> dict[str, object]:
    if scan_result is None:
        return {
            "status": "missing",
            "scanned_artifacts": list(scanned_artifacts),
            "findings": [],
            "failure_type": "CONFIG_ERROR",
            "summary": "artifact safety scan missing",
        }
    findings = [
        {
            "artifact_path": _mask_value(finding.artifact_path),
            "finding_type": _mask_value(finding.reason),
            "severity": "high",
            "failure_type": finding.failure_type,
            "message": _mask_value(finding.reason),
        }
        for finding in scan_result.findings
    ]
    return {
        "status": "pass" if scan_result.ok else "fail",
        "scanned_artifacts": [_mask_value(path) for path in scanned_artifacts],
        "findings": findings,
        "failure_type": scan_result.failure_type,
        "summary": "artifact safety scan passed" if scan_result.ok else "artifact safety scan failed",
    }


def validate_live_smoke_artifact_names(artifact_names: set[str]) -> FirstLiveSmokeValidationResult:
    if artifact_names & FORBIDDEN_LIVE_SMOKE_ARTIFACTS:
        return _failure("live call attempted without all gates")
    if not artifact_names <= ALLOWED_LIVE_SMOKE_ARTIFACTS:
        return _failure("artifact write failure")
    return FirstLiveSmokeValidationResult(True, None, None)


def run_first_live_smoke_disabled(*args: object, **kwargs: object) -> DisabledLiveSmokeRunResult:
    return DisabledLiveSmokeRunResult(
        status="blocked",
        failure_type="SECURITY_BLOCKED",
        error="first live smoke execution is disabled in P3G skeleton",
    )


def _request_conditions(
    *,
    approval: FirstLiveSmokeApproval | None,
    flags: Mapping[str, str] | None,
    provider_allowlist: ProviderAllowlist | None,
    key_registry: KeyRegistry | None,
    pre_artifact_scan: ArtifactSafetyResult | None,
    post_artifact_scan: ArtifactSafetyResult | None,
    attempted_model_calls: int,
    retry_attempted: bool,
    reserve_attempted: bool,
    fallback_provider_attempted: bool,
    second_model_call_attempted: bool,
) -> tuple[str, ...]:
    conditions: list[str] = []
    conditions.extend(_approval_conditions(approval))
    conditions.extend(_flag_conditions(flags))
    conditions.extend(_allowlist_conditions(approval, provider_allowlist))
    conditions.extend(_key_conditions(approval, key_registry))
    if approval is not None:
        if attempted_model_calls > 1:
            conditions.append("budget exceeded")
        if retry_attempted or (approval.max_retries_per_call is not None and approval.max_retries_per_call > 0):
            conditions.append("retry attempted")
    if reserve_attempted:
        conditions.append("reserve attempted")
    if fallback_provider_attempted:
        conditions.append("provider not in allowlist")
    if second_model_call_attempted:
        conditions.append("second model call attempted")
    conditions.extend(_artifact_scan_conditions(pre_artifact_scan))
    conditions.extend(_artifact_scan_conditions(post_artifact_scan))
    return tuple(conditions)


def _approval_conditions(approval: FirstLiveSmokeApproval | None) -> tuple[str, ...]:
    if approval is None:
        return ("explicit approval missing",)
    if scan_value_for_unsafe_content(asdict(approval), value_path="approval"):
        return ("raw key found",)
    if _value_has_url(asdict(approval)):
        return ("arbitrary URL requested",)
    if approval.approval_phrase and approval.approval_phrase.strip().lower() in AMBIGUOUS_APPROVAL_PHRASES:
        return ("approval phrase ambiguous",)
    if not approval.approved_by_user:
        return ("explicit approval missing",)
    if (
        not approval.provider
        or not approval.model
        or approval.key_slot is None
        or approval.max_model_calls is None
        or approval.max_retries_per_call is None
        or approval.max_runtime_seconds is None
        or approval.allow_raw_output is None
    ):
        return ("required approval field missing",)
    if approval.approval_scope != "this_run_only":
        return ("approval phrase ambiguous",)
    if approval.allow_raw_output is not False:
        return ("allow_raw_output not false",)
    key_slot_condition = _key_slot_policy_condition(approval.key_slot)
    if key_slot_condition:
        return (key_slot_condition,)
    if approval.max_model_calls != 1 or approval.max_runtime_seconds <= 0:
        return ("budget invalid",)
    if approval.max_retries_per_call != 0:
        return ("retry attempted",)
    return ()


def _flag_conditions(flags: Mapping[str, str] | None) -> tuple[str, ...]:
    if flags is None:
        return ("runtime flag missing",)
    for flag_name in REQUIRED_LIVE_SMOKE_FLAGS:
        if flag_name not in flags:
            return ("runtime flag missing",)
        normalized = flags[flag_name].strip().lower()
        if normalized in FALSE_FLAG_VALUES or normalized not in TRUE_FLAG_VALUES:
            return ("runtime flag false",)
    return ()


def _allowlist_conditions(
    approval: FirstLiveSmokeApproval | None,
    provider_allowlist: ProviderAllowlist | None,
) -> tuple[str, ...]:
    if provider_allowlist is None or provider_allowlist.is_missing:
        return ("provider allowlist missing",)
    if provider_allowlist.is_empty:
        return ("provider allowlist empty",)
    provider = approval.provider if approval else None
    if not provider:
        return ()
    if provider not in KNOWN_PROVIDER_CANDIDATES:
        return ("unknown provider requested",)
    if provider not in provider_allowlist.providers:
        return ("provider not in allowlist",)
    if approval and approval.endpoint and not provider_allowlist.contains_endpoint(provider, approval.endpoint):
        return ("unknown endpoint requested",)
    return ()


def _key_conditions(approval: FirstLiveSmokeApproval | None, key_registry: KeyRegistry | None) -> tuple[str, ...]:
    if approval is None:
        return ()
    key_slot = _single_key_slot(approval)
    if key_slot is None:
        return ()
    if key_slot not in KEY_SLOTS:
        return ()
    if key_registry is None:
        return ("key missing",)
    try:
        configured = key_registry.has_key(key_slot)
    except ValueError:
        return ()
    if not configured:
        return ("key missing",)
    return ()


def _artifact_scan_conditions(scan: ArtifactSafetyResult | None) -> tuple[str, ...]:
    if scan is None:
        return ("artifact safety scan missing",)
    if not scan.ok:
        return ("artifact safety scan failed",)
    return ()


def _key_slot_policy_condition(key_slot_value: str | tuple[str, ...] | list[str]) -> str | None:
    key_slots = _key_slots_tuple(key_slot_value)
    if len(key_slots) != 1:
        return "required approval field missing"
    key_slot = key_slots[0]
    if scan_value_for_unsafe_content(key_slot) or ENV_VAR_NAME_PATTERN.match(key_slot):
        return "raw key found"
    if key_slot not in KEY_SLOTS:
        return "unknown provider requested" if URL_PATTERN.search(key_slot) else "raw key found"
    return None


def _single_key_slot(approval: FirstLiveSmokeApproval) -> str | None:
    key_slots = _key_slots_tuple(approval.key_slot)
    if len(key_slots) != 1:
        return None
    return key_slots[0]


def _key_slots_tuple(key_slot_value: str | tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if key_slot_value is None:
        return ()
    if isinstance(key_slot_value, str):
        return (key_slot_value,)
    return tuple(key_slot_value)


def _value_has_url(value: Any) -> bool:
    if isinstance(value, str):
        return bool(URL_PATTERN.search(value))
    if isinstance(value, Mapping):
        return any(_value_has_url(key) or _value_has_url(item) for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_value_has_url(item) for item in value)
    return False


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        if scan_value_for_unsafe_content(value) or URL_PATTERN.search(value):
            return "[BLOCKED_VALUE]"
        return mask_secrets(value)
    if isinstance(value, Mapping):
        return {_mask_value(key): _mask_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_value(item) for item in value)
    if isinstance(value, set):
        return {_mask_value(item) for item in value}
    return value


def _failure(condition: str) -> FirstLiveSmokeValidationResult:
    return FirstLiveSmokeValidationResult(False, condition, FAILURE_TYPE_BY_SMOKE_CONDITION[condition], condition)
