# P3B real provider adapter의 비활성 skeleton 경계를 정의한다.
from __future__ import annotations

from typing import Any

from .key_registry import KeyRegistry
from .provider_base import ProviderResult


class ProviderDisabledError(RuntimeError):
    pass


class RealProvider:
    def __init__(self, key_registry: KeyRegistry | None = None) -> None:
        self.key_registry = key_registry or KeyRegistry()

    def call_model(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> ProviderResult:
        self.key_registry.env_var_name(key_slot)
        raise ProviderDisabledError(f"real provider is disabled in P3B skeleton for key_slot={key_slot}")
