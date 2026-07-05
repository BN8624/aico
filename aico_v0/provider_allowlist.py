# P3E provider allowlist 기본 empty 정책과 후보 메타데이터를 정의한다.
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

CANDIDATE_PROVIDER = "google_gemini"
CANDIDATE_MODEL = "user-approved later"
CANDIDATE_KEY_SLOTS = "user-approved later"
KNOWN_PROVIDER_CANDIDATES = frozenset({CANDIDATE_PROVIDER})


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
