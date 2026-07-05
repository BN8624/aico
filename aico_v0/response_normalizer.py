# Provider별 응답과 오류를 P3 canonical failure boundary로 정규화한다.
from __future__ import annotations

from dataclasses import dataclass

from .provider_base import FAILURE_BY_PROVIDER_STATUS, contains_secret, mask_secrets

PROVIDER_STATUS_ALIASES = {
    "429": "rate_limited_429",
    "500": "server_error_500",
    "provider unavailable": "provider_unavailable",
}


@dataclass(frozen=True)
class NormalizedProviderResult:
    provider_status: str
    failure_type: str | None
    normalized_error: str | None
    masked_raw_output: str | None
    raw_output_saved: bool
    mask_reason: str
    input_tokens: int | None
    output_tokens: int | None
    unsafe: bool


def normalize_provider_response(
    *,
    provider_status: str,
    raw_output: str | None = None,
    error: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> NormalizedProviderResult:
    canonical_status = PROVIDER_STATUS_ALIASES.get(provider_status, provider_status)
    masked_raw_output = mask_secrets(raw_output) if raw_output is not None else None
    unsafe = _has_secret(raw_output) or _has_secret(error)
    failure_type = "SECURITY_BLOCKED" if unsafe else FAILURE_BY_PROVIDER_STATUS.get(canonical_status)
    normalized_error = _normalized_error(canonical_status, failure_type, error, unsafe)
    return NormalizedProviderResult(
        provider_status=canonical_status,
        failure_type=failure_type,
        normalized_error=normalized_error,
        masked_raw_output=masked_raw_output,
        raw_output_saved=False,
        mask_reason="raw provider output is never saved unmasked",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        unsafe=unsafe,
    )


def _has_secret(value: str | None) -> bool:
    return bool(value and contains_secret(value))


def _normalized_error(
    provider_status: str,
    failure_type: str | None,
    error: str | None,
    unsafe: bool,
) -> str | None:
    if unsafe:
        return "provider response contained a secret-like value"
    if failure_type is None:
        return None
    return {
        "timeout": "provider timeout",
        "rate_limited_429": "provider returned 429",
        "server_error_500": "provider returned 500",
        "provider_unavailable": "provider unavailable",
        "no_response": "provider returned no response",
        "non_json_response": "provider response was not JSON",
        "schema_invalid_json": "provider response failed worker schema",
        "schema_valid_empty": "provider response was empty",
        "security_leak": "provider response contained a secret-like value",
    }.get(provider_status, error or provider_status)
