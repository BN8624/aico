# P3E live-call gate 입력을 실제 호출 없이 canonical failure로 분류한다.
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .artifact_safety import ArtifactSafetyResult, scan_value_for_unsafe_content
from .key_registry import KeyRegistry
from .provider_base import mask_secrets
from .provider_allowlist import KNOWN_PROVIDER_CANDIDATES, ProviderAllowlist

FAILURE_TYPE_BY_GATE_CONDITION = {
    "explicit approval missing": "HUMAN_DECISION_REQUIRED",
    "approval phrase ambiguous": "HUMAN_DECISION_REQUIRED",
    "provider not specified in approval": "HUMAN_DECISION_REQUIRED",
    "key slots not specified in approval": "HUMAN_DECISION_REQUIRED",
    "max_model_calls not specified in approval": "HUMAN_DECISION_REQUIRED",
    "max_runtime_seconds not specified in approval": "HUMAN_DECISION_REQUIRED",
    "required approval field missing": "HUMAN_DECISION_REQUIRED",
    "AICO_ENABLE_REAL_PROVIDER missing": "CONFIG_ERROR",
    "AICO_ALLOW_LIVE_CALLS missing": "CONFIG_ERROR",
    "AICO_ENABLE_REAL_PROVIDER=false": "CONFIG_ERROR",
    "AICO_ALLOW_LIVE_CALLS=false": "CONFIG_ERROR",
    "live flag missing": "CONFIG_ERROR",
    "live flag false": "CONFIG_ERROR",
    "provider allowlist missing": "CONFIG_ERROR",
    "provider allowlist empty": "CONFIG_ERROR",
    "unknown provider requested": "SECURITY_BLOCKED",
    "provider not in allowlist": "SECURITY_BLOCKED",
    "unknown endpoint requested": "SECURITY_BLOCKED",
    "arbitrary URL requested": "SECURITY_BLOCKED",
    "key availability check failed": "CONFIG_ERROR",
    "key slot missing": "CONFIG_ERROR",
    "raw key leaked": "SECURITY_BLOCKED",
    "env var value logged": "SECURITY_BLOCKED",
    "env var value appears anywhere": "SECURITY_BLOCKED",
    "budget missing": "CONFIG_ERROR",
    "budget invalid": "CONFIG_ERROR",
    "budget exceeded": "BUDGET_EXCEEDED",
    "artifact safety scan missing": "CONFIG_ERROR",
    "artifact safety scan internal failure": "CONFIG_ERROR",
    "artifact safety scan failed": "SECURITY_BLOCKED",
    "raw key found in artifact": "SECURITY_BLOCKED",
    "unmasked raw provider output found in artifact": "SECURITY_BLOCKED",
    "raw_output_saved=True detected": "SECURITY_BLOCKED",
    "provider SDK import before approved phase": "SECURITY_BLOCKED",
    "network call in default tests": "SECURITY_BLOCKED",
    "live call attempted in default pytest": "SECURITY_BLOCKED",
    "ProviderResult safety rule broken": "SECURITY_BLOCKED",
    "final_report and failed_draft both generated": "REPORT_ERROR",
    "ceo_report generation failed": "REPORT_ERROR",
}

_TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_FLAG_VALUES = frozenset({"0", "false", "no", "off", ""})
_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)


@dataclass(frozen=True)
class LiveApproval:
    provider: str | None = None
    key_slots: tuple[str, ...] = ()
    max_model_calls: int | None = None
    max_runtime_seconds: int | None = None
    approval_scope: str = "this_run_only"
    approved_by_user: bool = False
    approval_phrase: str | None = None
    model: str | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_retries_per_call: int | None = None
    run_id: str | None = None
    expires_at: str | None = None
    reason: str | None = None
    endpoint: str | None = None
    metadata: Mapping[str, object] | None = None

    def __repr__(self) -> str:
        safe_fields = {key: _mask_approval_value(value) for key, value in asdict(self).items()}
        rendered = ", ".join(f"{key}={safe_fields[key]!r}" for key in safe_fields)
        return f"LiveApproval({rendered})"


@dataclass(frozen=True)
class LiveBudget:
    max_model_calls: int
    max_runtime_seconds: int
    max_retries_per_call: int = 0
    max_consecutive_model_errors: int = 1
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None

    @classmethod
    def first_live_smoke(cls) -> "LiveBudget":
        return cls(max_model_calls=1, max_runtime_seconds=60)


@dataclass(frozen=True)
class LiveGateResult:
    ok: bool
    condition: str | None
    failure_type: str | None
    error: str | None = None


def failure_type_for_condition(condition: str) -> str:
    return FAILURE_TYPE_BY_GATE_CONDITION[condition]


def validate_live_gate(
    *,
    approval: LiveApproval | None,
    flags: Mapping[str, str] | None,
    provider_allowlist: ProviderAllowlist | None,
    key_registry: KeyRegistry | None,
    budget: LiveBudget | None,
    artifact_scan: ArtifactSafetyResult | None,
    canon_approved: bool = True,
    test_isolation_ok: bool = True,
) -> LiveGateResult:
    for condition in _gate_conditions(
        approval=approval,
        flags=flags,
        provider_allowlist=provider_allowlist,
        key_registry=key_registry,
        budget=budget,
        artifact_scan=artifact_scan,
        canon_approved=canon_approved,
        test_isolation_ok=test_isolation_ok,
    ):
        return _failure(condition)
    return LiveGateResult(True, None, None)


def validate_approval(approval: LiveApproval | None) -> LiveGateResult:
    for condition in _approval_conditions(approval):
        return _failure(condition)
    return LiveGateResult(True, None, None)


def validate_runtime_flags(flags: Mapping[str, str] | None) -> LiveGateResult:
    for condition in _flag_conditions(flags):
        return _failure(condition)
    return LiveGateResult(True, None, None)


def validate_budget(budget: LiveBudget | None, *, attempted_model_calls: int = 0) -> LiveGateResult:
    if budget is None:
        return _failure("budget missing")
    if (
        budget.max_model_calls <= 0
        or budget.max_model_calls > 1
        or budget.max_runtime_seconds <= 0
        or budget.max_retries_per_call != 0
        or budget.max_consecutive_model_errors != 1
    ):
        return _failure("budget invalid")
    if attempted_model_calls > budget.max_model_calls:
        return _failure("budget exceeded")
    return LiveGateResult(True, None, None)


def validate_provider_allowlist(
    approval: LiveApproval | None,
    provider_allowlist: ProviderAllowlist | None,
) -> LiveGateResult:
    for condition in _allowlist_conditions(approval, provider_allowlist):
        return _failure(condition)
    return LiveGateResult(True, None, None)


def validate_key_availability(approval: LiveApproval | None, key_registry: KeyRegistry | None) -> LiveGateResult:
    if approval is None or not approval.key_slots:
        return _failure("key slot missing")
    if key_registry is None:
        return _failure("key availability check failed")
    for key_slot in approval.key_slots:
        try:
            if not key_registry.has_key(key_slot):
                return _failure("key availability check failed")
        except ValueError:
            return _failure("key slot missing")
    return LiveGateResult(True, None, None)


def _gate_conditions(
    *,
    approval: LiveApproval | None,
    flags: Mapping[str, str] | None,
    provider_allowlist: ProviderAllowlist | None,
    key_registry: KeyRegistry | None,
    budget: LiveBudget | None,
    artifact_scan: ArtifactSafetyResult | None,
    canon_approved: bool,
    test_isolation_ok: bool,
) -> tuple[str, ...]:
    conditions: list[str] = []
    if not canon_approved:
        conditions.append("explicit approval missing")
    conditions.extend(_approval_conditions(approval))
    conditions.extend(_flag_conditions(flags))
    conditions.extend(_allowlist_conditions(approval, provider_allowlist))
    if approval is not None:
        key_result = validate_key_availability(approval, key_registry)
        if not key_result.ok:
            conditions.append(key_result.condition or "key availability check failed")
    budget_result = validate_budget(budget)
    if not budget_result.ok:
        conditions.append(budget_result.condition or "budget invalid")
    if artifact_scan is None:
        conditions.append("artifact safety scan missing")
    elif not artifact_scan.ok:
        conditions.append("artifact safety scan failed")
    if not test_isolation_ok:
        conditions.append("live call attempted in default pytest")
    return tuple(conditions)


def _approval_conditions(approval: LiveApproval | None) -> tuple[str, ...]:
    if approval is None:
        return ("explicit approval missing",)
    if _approval_has_unsafe_content(approval):
        return ("raw key leaked",)
    if _approval_has_url(approval):
        return ("arbitrary URL requested",)
    if approval.approval_phrase and approval.approval_phrase.strip().lower() in {"continue", "proceed", "go ahead", "진행해", "계속해"}:
        return ("approval phrase ambiguous",)
    if not approval.approved_by_user:
        return ("explicit approval missing",)
    if not approval.provider:
        return ("provider not specified in approval",)
    if not approval.key_slots:
        return ("key slots not specified in approval",)
    if approval.max_model_calls is None:
        return ("max_model_calls not specified in approval",)
    if approval.max_runtime_seconds is None:
        return ("max_runtime_seconds not specified in approval",)
    if approval.approval_scope != "this_run_only":
        return ("approval phrase ambiguous",)
    return ()


def _approval_has_unsafe_content(approval: LiveApproval) -> bool:
    return bool(scan_value_for_unsafe_content(asdict(approval), value_path="approval"))


def _approval_has_url(approval: LiveApproval) -> bool:
    return _value_has_url(asdict(approval))


def _value_has_url(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_URL_PATTERN.search(value))
    if isinstance(value, Mapping):
        return any(_value_has_url(key) or _value_has_url(item) for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_value_has_url(item) for item in value)
    return False


def _mask_approval_value(value: Any) -> Any:
    if isinstance(value, str):
        if scan_value_for_unsafe_content(value) or _URL_PATTERN.search(value):
            return "[BLOCKED_APPROVAL_VALUE]"
        return mask_secrets(value)
    if isinstance(value, Mapping):
        return {_mask_approval_value(key): _mask_approval_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_approval_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_approval_value(item) for item in value)
    if isinstance(value, set):
        return {_mask_approval_value(item) for item in value}
    return value


def _flag_conditions(flags: Mapping[str, str] | None) -> tuple[str, ...]:
    if flags is None:
        return ("AICO_ENABLE_REAL_PROVIDER missing",)
    for flag_name in ("AICO_ENABLE_REAL_PROVIDER", "AICO_ALLOW_LIVE_CALLS"):
        if flag_name not in flags:
            return (f"{flag_name} missing",)
        normalized = flags[flag_name].strip().lower()
        if normalized in _FALSE_FLAG_VALUES or normalized not in _TRUE_FLAG_VALUES:
            return (f"{flag_name}=false",)
    return ()


def _allowlist_conditions(
    approval: LiveApproval | None,
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


def _failure(condition: str) -> LiveGateResult:
    return LiveGateResult(False, condition, FAILURE_TYPE_BY_GATE_CONDITION[condition], condition)
