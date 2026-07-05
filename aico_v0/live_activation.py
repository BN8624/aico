# P3K live provider activation을 실제 실행 없이 차단하는 skeleton이다.
from __future__ import annotations

from dataclasses import dataclass

from .key_registry import KeyRegistry
from .provider_allowlist import (
    CandidateProviderEntry,
    ProviderAllowlistSkeletonError,
    ProviderAllowlistState,
    validate_allowlist_state,
    validate_candidate_entry,
    validate_provider_name,
)


class LiveActivationBlocked(ProviderAllowlistSkeletonError):
    pass


@dataclass(frozen=True)
class LiveActivationSkeletonResult:
    status: str
    failure_type: str
    error: str
    provider: str | None = None
    model_call_count: int = 0
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_network_call_count: int = 0
    provider_sdk_imported: bool = False
    live_smoke_executed: bool = False
    provider_allowlist_activated: bool = False


@dataclass(frozen=True)
class KeyExistenceCheck:
    key_slot: str
    configured: bool
    failure_type: str | None = None
    error: str | None = None


def block_actual_activation_in_p3k(state: ProviderAllowlistState | None) -> LiveActivationSkeletonResult:
    if state is not None:
        validate_allowlist_state(state)
    raise LiveActivationBlocked("activation attempted in P3K")


def block_candidate_provider_live_call(
    entry: CandidateProviderEntry,
    *,
    state: ProviderAllowlistState | None = None,
) -> LiveActivationSkeletonResult:
    validate_candidate_entry(entry)
    if state is not None:
        validate_allowlist_state(state)
    raise LiveActivationBlocked("candidate provider live call attempted")


def build_disabled_activation_result(provider: str | None = None) -> LiveActivationSkeletonResult:
    if provider is not None:
        validate_provider_name(provider)
    return LiveActivationSkeletonResult(
        status="disabled",
        failure_type="SECURITY_BLOCKED",
        error="live provider activation is disabled in P3K skeleton",
        provider=provider,
    )


def check_key_existence_only(key_registry: KeyRegistry, key_slot: str) -> KeyExistenceCheck:
    configured = key_registry.has_key(key_slot)
    if configured:
        return KeyExistenceCheck(key_slot=key_slot, configured=True)
    return KeyExistenceCheck(
        key_slot=key_slot,
        configured=False,
        failure_type="CONFIG_ERROR",
        error=f"missing key for key_slot={key_slot}",
    )
