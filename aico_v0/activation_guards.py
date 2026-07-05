# P3P 활성화 경계를 실제 호출 없이 항상 차단하는 guard 스켈레톤이다.
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .approval_phrase import P3P_FAILURES
from .key_loading_boundary import (
    KeyLoadingBoundaryError,
    KeyLoadingBoundaryState,
    validate_key_existence_summary,
    validate_key_loading_boundary_state,
)
from .provider_allowlist import (
    CandidateProviderEntry,
    ProviderAllowlistSkeletonError,
    ProviderAllowlistState,
    google_gemini_candidate_entry,
    validate_allowlist_state,
    validate_candidate_entry,
)
from .sdk_boundary import SDKBoundaryError, SDKBoundaryState, validate_sdk_boundary_state

P3P_SUCCESS_LIKE_STATUSES = frozenset(
    {"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"}
)


class P3PActivationGuardError(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = P3P_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class P3PActivationGuardResult:
    guard_name: str
    status: str = "prepared"
    failure_type: str | None = None
    live_call_allowed: bool = False
    model_call_count: int = 0
    raw_output_saved: bool = False
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_network_call_count: int = 0
    provider_sdk_imported: bool = False
    live_smoke_executed: bool = False
    provider_allowlist_activated: bool = False
    sdk_import_activated: bool = False
    key_loading_activated: bool = False

    def to_summary(self) -> dict[str, object]:
        return {
            "guard_name": self.guard_name,
            "status": self.status,
            "failure_type": self.failure_type,
            "live_call_allowed": False,
            "model_call_count": 0,
            "raw_output_saved": False,
            "actual_api_call_count": 0,
            "actual_llm_call_count": 0,
            "actual_key_value_read_count": 0,
            "actual_network_call_count": 0,
            "provider_sdk_imported": False,
            "live_smoke_executed": False,
            "provider_allowlist_activated": False,
            "sdk_import_activated": False,
            "key_loading_activated": False,
        }


def provider_allowlist_activation_guard(
    state: ProviderAllowlistState | None = None,
    *,
    actual_activation_attempted: bool = False,
) -> P3PActivationGuardResult:
    if actual_activation_attempted:
        raise P3PActivationGuardError("provider allowlist actual activation attempted in P3P")
    state = state or ProviderAllowlistState.candidate(google_gemini_candidate_entry())
    try:
        validate_allowlist_state(state)
    except ProviderAllowlistSkeletonError as exc:
        raise P3PActivationGuardError(_p3p_condition(exc.condition)) from exc
    if state.state not in {"candidate", "disabled", "empty"}:
        raise P3PActivationGuardError("candidate interpreted as active")
    for entry in state.candidates:
        _validate_candidate_permissions(entry)
    return P3PActivationGuardResult("provider_allowlist_activation_guard")


def sdk_import_activation_guard(
    boundary: SDKBoundaryState | None = None,
    *,
    sdk_import_allowed: bool = False,
    provider_sdk_imported: bool = False,
    network_capable_imported: bool = False,
) -> P3PActivationGuardResult:
    if sdk_import_allowed:
        raise P3PActivationGuardError("sdk_import_allowed true in P3P")
    if provider_sdk_imported:
        raise P3PActivationGuardError("provider SDK imported in runtime path")
    if network_capable_imported:
        raise P3PActivationGuardError("network-capable SDK import in runtime path")
    try:
        validate_sdk_boundary_state(boundary or SDKBoundaryState())
    except SDKBoundaryError as exc:
        raise P3PActivationGuardError(_p3p_condition(exc.condition)) from exc
    return P3PActivationGuardResult("sdk_import_activation_guard")


def key_loading_activation_guard(
    boundary: KeyLoadingBoundaryState | None = None,
    *,
    key_loading_allowed: bool = False,
    actual_key_read_attempted: bool = False,
    key_existence_summary: Mapping[str, object] | None = None,
) -> P3PActivationGuardResult:
    if key_loading_allowed:
        raise P3PActivationGuardError("key_loading_allowed true in P3P")
    if actual_key_read_attempted:
        raise P3PActivationGuardError("actual key read before approved phase")
    try:
        validate_key_loading_boundary_state(boundary or KeyLoadingBoundaryState())
        if key_existence_summary is not None:
            validate_key_existence_summary(key_existence_summary)
    except KeyLoadingBoundaryError as exc:
        raise P3PActivationGuardError(_p3p_condition(exc.condition)) from exc
    return P3PActivationGuardResult("key_loading_activation_guard")


def live_call_activation_guard(
    *,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
    status: str = "prepared",
    call_model_attempted: bool = False,
) -> P3PActivationGuardResult:
    if live_call_allowed:
        raise P3PActivationGuardError("live_call_allowed true in P3P")
    if model_call_count > 0:
        raise P3PActivationGuardError("model_call_count > 0 in P3P")
    if status in P3P_SUCCESS_LIKE_STATUSES:
        raise P3PActivationGuardError("success-like status in P3P")
    if call_model_attempted:
        raise P3PActivationGuardError("live call attempted without all gates")
    return P3PActivationGuardResult("live_call_activation_guard", status=status)


def assert_p3p_no_call_safety() -> dict[str, object]:
    guards = (
        provider_allowlist_activation_guard(),
        sdk_import_activation_guard(),
        key_loading_activation_guard(),
        live_call_activation_guard(),
    )
    return {
        "live_call_allowed": False,
        "model_call_count": 0,
        "raw_output_saved": False,
        "actual_api_call_count": sum(guard.actual_api_call_count for guard in guards),
        "actual_llm_call_count": sum(guard.actual_llm_call_count for guard in guards),
        "actual_key_value_read_count": sum(guard.actual_key_value_read_count for guard in guards),
        "actual_sdk_import_count": sum(1 for guard in guards if guard.provider_sdk_imported),
        "actual_network_call_count": sum(guard.actual_network_call_count for guard in guards),
        "actual_live_smoke_count": sum(1 for guard in guards if guard.live_smoke_executed),
    }


def _validate_candidate_permissions(entry: CandidateProviderEntry) -> None:
    try:
        validate_candidate_entry(entry)
    except ProviderAllowlistSkeletonError as exc:
        raise P3PActivationGuardError(_p3p_condition(exc.condition)) from exc
    if entry.live_calls_allowed:
        raise P3PActivationGuardError("live_calls_allowed true in P3P")
    if entry.sdk_import_allowed:
        raise P3PActivationGuardError("sdk_import_allowed true in P3P")
    if entry.key_loading_allowed:
        raise P3PActivationGuardError("key_loading_allowed true in P3P")


def _p3p_condition(condition: str) -> str:
    if condition == "SDK import allowed true in P3L":
        return "sdk_import_allowed true in P3P"
    if condition == "key loading allowed true in P3L":
        return "key_loading_allowed true in P3P"
    return condition
