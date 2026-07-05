# P3P 승인 문구를 실제 호출 없이 안전한 필드로 파싱하는 스켈레톤이다.
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping

from .artifact_safety import scan_value_for_unsafe_content
from .live_smoke import FAILURE_TYPE_BY_SMOKE_CONDITION
from .provider_allowlist import ProviderAllowlistSkeletonError, validate_provider_name
from .provider_base import KEY_SLOTS, contains_secret

APPROVAL_PHRASE_HEADER = "I approve AICO first live smoke for this run only:"
APPROVAL_REQUIRED_FIELDS = (
    "provider",
    "model",
    "key_slot",
    "max_model_calls",
    "max_retries_per_call",
    "max_runtime_seconds",
    "allow_raw_output",
)
APPROVAL_SCOPE = "first_live_smoke_this_run_only"
P3P_FAILURES = {
    **FAILURE_TYPE_BY_SMOKE_CONDITION,
    "generic approval phrase": "HUMAN_DECISION_REQUIRED",
    "multiple key_slots": "HUMAN_DECISION_REQUIRED",
    "raw key/token/env var value in approval": "SECURITY_BLOCKED",
    "run_id mismatch": "CONFIG_ERROR",
    "missing linkage required field": "CONFIG_ERROR",
    "raw approval phrase found": "SECURITY_BLOCKED",
    "approval package location unsafe": "SECURITY_BLOCKED",
    "live_call_allowed true in P3P": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3P": "SECURITY_BLOCKED",
    "success-like status in P3P": "SECURITY_BLOCKED",
    "provider allowlist actual activation attempted in P3P": "SECURITY_BLOCKED",
    "sdk_import_allowed true in P3P": "SECURITY_BLOCKED",
    "key_loading_allowed true in P3P": "SECURITY_BLOCKED",
    "live_calls_allowed true in P3P": "SECURITY_BLOCKED",
}
GENERIC_APPROVAL_PHRASES = {
    "continue",
    "proceed",
    "go ahead",
    "ok",
    "yes",
    "approved",
    "승인",
    "진행해",
    "계속해",
    "해봐",
    "다음 단계로 가",
}
_KEY_VALUE_SEPARATOR = re.compile(r"^\s*([a-z_]+)\s*=\s*(.*?)\s*$")
_BLOCKED_PROVIDER_DOMAIN_PATTERNS = (
    r"op" + r"enai\.com",
    r"anth" + r"ropic\.com",
)
_URL_OR_ENDPOINT = re.compile(
    r"https?://|(?:generativelanguage|[A-Za-z0-9-]+)\.googleapis\.com|"
    + "|".join(_BLOCKED_PROVIDER_DOMAIN_PATTERNS),
    re.IGNORECASE,
)
_ENV_VAR_NAME = re.compile(r"^AICO_[A-Z0-9_]*API_KEY$")
_SAFE_HASH = re.compile(r"^[a-f0-9]{64}$")


class P3PApprovalError(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = P3P_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class ParsedApprovalPhrase:
    provider: str
    model: str
    key_slot: str
    max_model_calls: int
    max_retries_per_call: int
    max_runtime_seconds: int
    allow_raw_output: bool
    approval_scope: str = APPROVAL_SCOPE
    approved_by_user: bool = True

    def to_safe_fields(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "key_slot": self.key_slot,
            "max_model_calls": self.max_model_calls,
            "max_retries_per_call": self.max_retries_per_call,
            "max_runtime_seconds": self.max_runtime_seconds,
            "allow_raw_output": self.allow_raw_output,
            "approval_scope": self.approval_scope,
            "approved_by_user": self.approved_by_user,
        }


def parse_approval_phrase(approval_phrase: str | None) -> ParsedApprovalPhrase:
    if approval_phrase is None or not approval_phrase.strip():
        raise P3PApprovalError("approval missing")
    stripped = approval_phrase.strip()
    if stripped.lower() in GENERIC_APPROVAL_PHRASES:
        raise P3PApprovalError("generic approval phrase")
    if stripped.count(APPROVAL_PHRASE_HEADER) != 1:
        raise P3PApprovalError("approval ambiguous")
    if not stripped.startswith(APPROVAL_PHRASE_HEADER):
        raise P3PApprovalError("approval ambiguous")

    fields = _parse_fields(stripped.splitlines()[1:])
    parsed = ParsedApprovalPhrase(
        provider=fields["provider"],
        model=fields["model"],
        key_slot=fields["key_slot"],
        max_model_calls=_parse_int(fields["max_model_calls"]),
        max_retries_per_call=_parse_int(fields["max_retries_per_call"]),
        max_runtime_seconds=_parse_int(fields["max_runtime_seconds"]),
        allow_raw_output=_parse_bool(fields["allow_raw_output"]),
    )
    validate_final_provider(parsed.provider)
    validate_final_model(parsed.model)
    validate_final_key_slot(parsed.key_slot)
    if parsed.max_model_calls != 1:
        raise P3PApprovalError("live call attempted without all gates")
    if parsed.max_retries_per_call != 0:
        raise P3PApprovalError("retry attempted")
    if parsed.max_runtime_seconds <= 0:
        raise P3PApprovalError("budget invalid")
    if parsed.allow_raw_output is not False:
        raise P3PApprovalError("allow_raw_output not false")
    if _approval_contains_unsafe_values(parsed.to_safe_fields()):
        raise P3PApprovalError("raw key/token/env var value in approval")
    return parsed


def build_approval_phrase_hash(approval_phrase: str) -> str:
    parse_approval_phrase(approval_phrase)
    digest = hashlib.sha256(approval_phrase.encode("utf-8")).hexdigest()
    validate_approval_phrase_hash(digest)
    return digest


def validate_approval_phrase_hash(value: str) -> None:
    if not _SAFE_HASH.fullmatch(value):
        raise P3PApprovalError("raw key/token/env var value in approval")


def validate_final_provider(provider: str | None) -> str:
    if not provider:
        raise P3PApprovalError("required approval field missing")
    try:
        validate_provider_name(provider)
    except ProviderAllowlistSkeletonError as exc:
        raise P3PApprovalError(exc.condition) from exc
    return provider


def validate_final_model(model: str | None) -> str:
    if not model:
        raise P3PApprovalError("required approval field missing")
    if _is_unsafe_decision_value(model):
        raise P3PApprovalError("raw key/token/env var value in approval")
    return model


def validate_final_key_slot(key_slot: str | tuple[str, ...] | list[str] | None) -> str:
    if key_slot is None:
        raise P3PApprovalError("required approval field missing")
    key_slots = (key_slot,) if isinstance(key_slot, str) else tuple(key_slot)
    if len(key_slots) != 1:
        raise P3PApprovalError("multiple key_slots")
    slot = key_slots[0]
    if _ENV_VAR_NAME.fullmatch(slot):
        raise P3PApprovalError("raw key/token/env var value in approval")
    if _is_unsafe_decision_value(slot):
        raise P3PApprovalError("raw key/token/env var value in approval")
    if slot not in KEY_SLOTS:
        raise P3PApprovalError("unknown provider requested")
    return slot


def _parse_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        match = _KEY_VALUE_SEPARATOR.match(line)
        if not match:
            raise P3PApprovalError("approval ambiguous")
        key, value = match.groups()
        if key in fields:
            raise P3PApprovalError("approval ambiguous")
        fields[key] = value
    if any(field not in fields or fields[field] == "" for field in APPROVAL_REQUIRED_FIELDS):
        raise P3PApprovalError("required approval field missing")
    key_slot_value = fields["key_slot"]
    if "," in key_slot_value or ";" in key_slot_value:
        raise P3PApprovalError("multiple key_slots")
    return fields


def _parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise P3PApprovalError("budget invalid") from exc


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "false":
        return False
    if normalized == "true":
        return True
    raise P3PApprovalError("required approval field missing")


def _approval_contains_unsafe_values(fields: Mapping[str, object]) -> bool:
    return bool(scan_value_for_unsafe_content(fields, value_path="approval"))


def _is_unsafe_decision_value(value: str) -> bool:
    return bool(
        _URL_OR_ENDPOINT.search(value)
        or contains_secret(value)
        or scan_value_for_unsafe_content(value)
        or _ENV_VAR_NAME.fullmatch(value)
    )
