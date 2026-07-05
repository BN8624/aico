# P3 provider 계층의 공통 interface와 안전한 결과 타입을 정의한다.
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

KEY_SLOTS = (
    "manager_1",
    "worker_1",
    "worker_2",
    "worker_3",
    "worker_4",
    "auditor_1",
    "reserve_1",
)

WORKER_SLOTS = ("worker_1", "worker_2", "worker_3", "worker_4")

PROVIDER_STATUSES = (
    "success",
    "timeout",
    "rate_limited_429",
    "server_error_500",
    "provider_unavailable",
    "no_response",
    "non_json_response",
    "schema_invalid_json",
    "schema_valid_empty",
    "security_leak",
)

FAILURE_BY_PROVIDER_STATUS = {
    "timeout": "MODEL_ERROR",
    "rate_limited_429": "MODEL_ERROR",
    "server_error_500": "MODEL_ERROR",
    "provider_unavailable": "MODEL_ERROR",
    "no_response": "MODEL_ERROR",
    "non_json_response": "SCHEMA_ERROR",
    "schema_invalid_json": "SCHEMA_ERROR",
    "schema_valid_empty": "WORKER_BAD_OUTPUT",
    "security_leak": "SECURITY_BLOCKED",
}

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_ -]?key|token|credential|secret)\s*[:=]\s*[A-Za-z0-9_.-]{8,}"),
)


@dataclass(frozen=True)
class ProviderResult:
    status: str
    content: Any = None
    masked_raw_output: str | None = None
    raw_output_saved: bool = False
    mask_reason: str = "raw provider output is never saved unmasked"
    input_tokens: int | None = None
    output_tokens: int | None = None
    normalized_error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in PROVIDER_STATUSES:
            raise ValueError(f"unknown provider status: {self.status}")
        if self.raw_output_saved:
            raise ValueError("raw_output_saved must remain false in P3B provider results")
        object.__setattr__(self, "content", _mask_provider_value(self.content))
        object.__setattr__(self, "masked_raw_output", _mask_provider_value(self.masked_raw_output))
        object.__setattr__(self, "normalized_error", _mask_provider_value(self.normalized_error))


class Provider(Protocol):
    def call_model(
        self,
        key_slot: str,
        model: str,
        prompt: str,
        expected_schema: dict[str, Any],
        scenario: str,
    ) -> ProviderResult:
        ...


def mask_secrets(text: str) -> str:
    masked = text
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub("[MASKED_SECRET]", masked)
    return masked


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _mask_provider_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_secrets(value)
    if isinstance(value, Mapping):
        return {_mask_provider_value(key): _mask_provider_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_provider_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_provider_value(item) for item in value)
    if isinstance(value, set):
        return {_mask_provider_value(item) for item in value}
    return value
