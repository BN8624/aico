# P3E provider allowlist 기본 empty 정책과 후보 메타데이터를 정의한다.
from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

CANDIDATE_PROVIDER = "google_gemini"
CANDIDATE_MODEL = "user-approved later"
CANDIDATE_KEY_SLOTS = "user-approved later"
KNOWN_PROVIDER_CANDIDATES = frozenset({CANDIDATE_PROVIDER})
ALLOWED_ALLOWLIST_STATES = frozenset({"empty", "candidate", "disabled"})
FORBIDDEN_ALLOWLIST_STATES = frozenset({"active", "live", "enabled_for_call", "provider_ready", "api_ready"})
SAFE_CANDIDATE_NOTE = "candidate only; not activated"
FAILURE_TYPE_BY_ALLOWLIST_CONDITION = {
    "provider allowlist missing": "CONFIG_ERROR",
    "provider allowlist empty": "CONFIG_ERROR",
    "unknown allowlist state": "CONFIG_ERROR",
    "unknown provider requested": "SECURITY_BLOCKED",
    "provider not in allowlist": "SECURITY_BLOCKED",
    "provider URL requested": "SECURITY_BLOCKED",
    "endpoint URL requested": "SECURITY_BLOCKED",
    "arbitrary URL requested": "SECURITY_BLOCKED",
    "raw key found": "SECURITY_BLOCKED",
    "env var value found": "SECURITY_BLOCKED",
    "candidate interpreted as active": "SECURITY_BLOCKED",
    "activation attempted in P3K": "SECURITY_BLOCKED",
    "SDK import before approved phase": "SECURITY_BLOCKED",
    "actual key read before approved phase": "SECURITY_BLOCKED",
    "live call attempted without all gates": "SECURITY_BLOCKED",
    "candidate provider live call attempted": "SECURITY_BLOCKED",
    "endpoint_url not null": "SECURITY_BLOCKED",
    "sdk_import_allowed true": "SECURITY_BLOCKED",
    "key_loading_allowed true": "SECURITY_BLOCKED",
    "live_calls_allowed true": "SECURITY_BLOCKED",
    "artifact write failure": "REPORT_ERROR",
}
URL_OR_ENDPOINT_PATTERN = re.compile(
    r"https?://|[A-Za-z0-9.-]+\.[A-Za-z]{2,}|/|:|\?",
    re.IGNORECASE,
)
RAW_KEY_PROVIDER_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9._-]{10,}|-----BEGIN\s+PRIVATE\s+KEY-----",
    re.IGNORECASE,
)


class ProviderAllowlistSkeletonError(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = FAILURE_TYPE_BY_ALLOWLIST_CONDITION[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class CandidateProviderEntry:
    provider: str = CANDIDATE_PROVIDER
    status: str = "candidate"
    activation: str = "disabled"
    endpoint_url: str | None = None
    sdk_import_allowed: bool = False
    key_loading_allowed: bool = False
    live_calls_allowed: bool = False
    notes: str = SAFE_CANDIDATE_NOTE

    def to_summary(self) -> dict[str, object]:
        validate_candidate_entry(self)
        return {
            "provider": self.provider,
            "status": self.status,
            "activation": self.activation,
            "endpoint_url": self.endpoint_url,
            "sdk_import_allowed": self.sdk_import_allowed,
            "key_loading_allowed": self.key_loading_allowed,
            "live_calls_allowed": self.live_calls_allowed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ProviderAllowlistState:
    state: str
    candidates: tuple[CandidateProviderEntry, ...] = ()

    @classmethod
    def empty(cls) -> "ProviderAllowlistState":
        return cls("empty")

    @classmethod
    def disabled(cls) -> "ProviderAllowlistState":
        return cls("disabled")

    @classmethod
    def candidate(cls, entry: CandidateProviderEntry) -> "ProviderAllowlistState":
        validate_candidate_entry(entry)
        return cls("candidate", (entry,))

    @property
    def authorizes_live_call(self) -> bool:
        return False

    @property
    def authorizes_sdk_import(self) -> bool:
        return False

    @property
    def authorizes_key_loading(self) -> bool:
        return False

    def to_summary(self) -> dict[str, object]:
        validate_allowlist_state(self)
        return {
            "state": self.state,
            "authorizes_live_call": False,
            "authorizes_sdk_import": False,
            "authorizes_key_loading": False,
            "candidates": [entry.to_summary() for entry in self.candidates],
        }


@dataclass(frozen=True)
class ProviderAllowlist:
    providers: Mapping[str, tuple[str, ...]] | None = None

    def __post_init__(self) -> None:
        if self.providers is not None:
            copied = {provider: tuple(endpoints) for provider, endpoints in self.providers.items()}
            object.__setattr__(self, "providers", MappingProxyType(copied))

    @classmethod
    def empty(cls) -> "ProviderAllowlist":
        return cls({})

    @property
    def is_missing(self) -> bool:
        return self.providers is None

    @property
    def is_empty(self) -> bool:
        return self.providers == {}

    def contains_provider(self, provider: str) -> bool:
        return bool(self.providers and provider in self.providers)

    def contains_endpoint(self, provider: str, endpoint: str) -> bool:
        return bool(self.providers and endpoint in self.providers.get(provider, ()))


DEFAULT_PROVIDER_ALLOWLIST = ProviderAllowlist.empty()
CANDIDATE_PROVIDER_METADATA = MappingProxyType(
    {
        "candidate_provider": CANDIDATE_PROVIDER,
        "candidate_model": CANDIDATE_MODEL,
        "candidate_key_slots": CANDIDATE_KEY_SLOTS,
        "authorizes_live_call": False,
    }
)
DEFAULT_PROVIDER_ALLOWLIST_STATE = ProviderAllowlistState.empty()


def google_gemini_candidate_entry(**overrides: Any) -> CandidateProviderEntry:
    data = {
        "provider": CANDIDATE_PROVIDER,
        "status": "candidate",
        "activation": "disabled",
        "endpoint_url": None,
        "sdk_import_allowed": False,
        "key_loading_allowed": False,
        "live_calls_allowed": False,
        "notes": SAFE_CANDIDATE_NOTE,
    }
    data.update(overrides)
    entry = CandidateProviderEntry(**data)
    validate_candidate_entry(entry)
    return entry


def open_candidate_allowlist(provider: str = CANDIDATE_PROVIDER) -> ProviderAllowlistState:
    validate_provider_name(provider)
    return ProviderAllowlistState.candidate(google_gemini_candidate_entry(provider=provider))


def validate_allowlist_state(state: ProviderAllowlistState | None) -> None:
    if state is None:
        raise ProviderAllowlistSkeletonError("provider allowlist missing")
    if state.state in FORBIDDEN_ALLOWLIST_STATES:
        raise ProviderAllowlistSkeletonError("candidate interpreted as active")
    if state.state not in ALLOWED_ALLOWLIST_STATES:
        raise ProviderAllowlistSkeletonError("unknown allowlist state")
    if state.state == "candidate":
        if len(state.candidates) != 1:
            raise ProviderAllowlistSkeletonError("unknown allowlist state")
        validate_candidate_entry(state.candidates[0])
    elif state.candidates:
        raise ProviderAllowlistSkeletonError("candidate interpreted as active")


def validate_candidate_entry(entry: CandidateProviderEntry) -> None:
    validate_provider_name(entry.provider)
    if entry.status != "candidate":
        if entry.status in FORBIDDEN_ALLOWLIST_STATES:
            raise ProviderAllowlistSkeletonError("candidate interpreted as active")
        raise ProviderAllowlistSkeletonError("unknown allowlist state")
    if entry.activation != "disabled":
        raise ProviderAllowlistSkeletonError("candidate interpreted as active")
    if entry.endpoint_url is not None:
        raise ProviderAllowlistSkeletonError("endpoint_url not null")
    if entry.sdk_import_allowed is not False:
        raise ProviderAllowlistSkeletonError("sdk_import_allowed true")
    if entry.key_loading_allowed is not False:
        raise ProviderAllowlistSkeletonError("key_loading_allowed true")
    if entry.live_calls_allowed is not False:
        raise ProviderAllowlistSkeletonError("live_calls_allowed true")


def validate_provider_name(provider: str) -> None:
    if RAW_KEY_PROVIDER_PATTERN.search(provider):
        raise ProviderAllowlistSkeletonError("raw key found")
    if "://" in provider and not provider.startswith(("http://", "https://")):
        raise ProviderAllowlistSkeletonError("arbitrary URL requested")
    if provider.startswith(("http://", "https://")):
        raise ProviderAllowlistSkeletonError("provider URL requested")
    if URL_OR_ENDPOINT_PATTERN.search(provider):
        raise ProviderAllowlistSkeletonError("endpoint URL requested")
    if provider not in KNOWN_PROVIDER_CANDIDATES:
        raise ProviderAllowlistSkeletonError("unknown provider requested")


def candidate_authorizes_live_call(entry: CandidateProviderEntry) -> bool:
    validate_candidate_entry(entry)
    return False


def candidate_authorizes_sdk_import(entry: CandidateProviderEntry) -> bool:
    validate_candidate_entry(entry)
    return False


def candidate_authorizes_key_loading(entry: CandidateProviderEntry) -> bool:
    validate_candidate_entry(entry)
    return False
