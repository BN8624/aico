# P3C real provider adapter의 guarded disabled-by-default 경계를 정의한다.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .key_registry import KeyRegistry
from .provider_base import ProviderResult
from .response_normalizer import normalize_provider_response

REAL_PROVIDER_ENABLE_FLAG = "AICO_ENABLE_REAL_PROVIDER"
_TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})


class ProviderDisabledError(RuntimeError):
    pass


@dataclass(frozen=True)
class RealProviderConfig:
    enable_flag_value: str | None = None

    @property
    def enabled(self) -> bool:
        if self.enable_flag_value is None:
            return False
        return self.enable_flag_value.strip().lower() in _TRUE_FLAG_VALUES


@dataclass(frozen=True)
class TransportResult:
    provider_status: str
    content: Any = None
    raw_output: str | None = None
    error: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderTransport(Protocol):
    def call(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> TransportResult:
        ...


class DisabledTransport:
    def call(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> TransportResult:
        raise ProviderDisabledError(f"real provider transport is disabled in P3C for key_slot={key_slot}")


class FakeTransport:
    def __init__(self, result: TransportResult | None = None) -> None:
        self.result = result or TransportResult(
            "success",
            content={"summary": "fake transport result"},
            raw_output='{"summary":"fake transport result"}',
            input_tokens=None,
            output_tokens=None,
        )
        self.calls: list[dict[str, Any]] = []

    def call(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> TransportResult:
        self.calls.append({"key_slot": key_slot, "model": model, "scenario": scenario})
        return self.result


class RealProvider:
    def __init__(
        self,
        key_registry: KeyRegistry | None = None,
        config: RealProviderConfig | None = None,
        transport: ProviderTransport | None = None,
    ) -> None:
        self.key_registry = key_registry or KeyRegistry()
        self.config = config or RealProviderConfig()
        self.transport = transport or DisabledTransport()

    def call_model(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> ProviderResult:
        self.key_registry.env_var_name(key_slot)
        if not self.config.enabled:
            raise ProviderDisabledError(
                f"real provider is disabled in P3C for key_slot={key_slot}; "
                f"{REAL_PROVIDER_ENABLE_FLAG}=true is required with fake or stub transport"
            )

        transport_result = self.transport.call(key_slot, model, prompt, expected_schema, scenario)
        normalized = normalize_provider_response(
            provider_status=transport_result.provider_status,
            raw_output=transport_result.raw_output,
            error=transport_result.error,
            input_tokens=transport_result.input_tokens,
            output_tokens=transport_result.output_tokens,
        )
        return ProviderResult(
            normalized.provider_status,
            content=transport_result.content,
            masked_raw_output=normalized.masked_raw_output,
            raw_output_saved=normalized.raw_output_saved,
            mask_reason=normalized.mask_reason,
            input_tokens=normalized.input_tokens,
            output_tokens=normalized.output_tokens,
            normalized_error=normalized.normalized_error,
        )
