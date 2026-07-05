# P3L key loading 경계를 실제 key read 없이 검증하는 skeleton이다.
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from .key_registry import KeyRegistry

ALLOWED_KEY_BOUNDARY_STATES = frozenset({"disabled", "not_approved", "existence_check_only", "candidate_only"})
FORBIDDEN_KEY_BOUNDARY_STATES = frozenset(
    {"approved", "active", "enabled", "live", "key_ready", "loaded", "value_loaded"}
)
KEY_BOUNDARY_LOCATION = "provider_adapter_internal_minimal_function_only"
KEY_BOUNDARY_FAILURES = {
    "unknown key loading state": "CONFIG_ERROR",
    "key missing": "CONFIG_ERROR",
    "actual key read before approved phase": "SECURITY_BLOCKED",
    "key loading allowed true in P3L": "SECURITY_BLOCKED",
    "key boundary active/enabled/live": "SECURITY_BLOCKED",
    "raw key found": "SECURITY_BLOCKED",
    "env var value found": "SECURITY_BLOCKED",
    "value_loaded true": "SECURITY_BLOCKED",
    "raw_key_present field": "SECURITY_BLOCKED",
}
_RAW_VALUE_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9._-]{10,}|[A-Z0-9_]*API_KEY\s*[:=]\s*[A-Za-z0-9_.-]{8,}",
    re.IGNORECASE,
)


class KeyLoadingBoundaryError(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = KEY_BOUNDARY_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class KeyLoadingBoundaryState:
    state: str = "disabled"
    key_loading_allowed: bool = False
    boundary_location: str = KEY_BOUNDARY_LOCATION

    @property
    def authorizes_key_loading(self) -> bool:
        return False


@dataclass(frozen=True)
class KeyExistenceSummary:
    key_slot: str
    env_var_name: str
    exists: bool
    value_loaded: bool = False
    failure_type: str | None = None
    error: str | None = None

    def to_summary(self) -> dict[str, object]:
        summary = {
            "key_slot": self.key_slot,
            "env_var_name": self.env_var_name,
            "exists": self.exists,
            "value_loaded": self.value_loaded,
            "failure_type": self.failure_type,
            "error": self.error,
        }
        validate_key_existence_summary(summary)
        return summary


def validate_key_loading_boundary_state(boundary: KeyLoadingBoundaryState | None) -> None:
    if boundary is None:
        raise KeyLoadingBoundaryError("unknown key loading state")
    if boundary.state in FORBIDDEN_KEY_BOUNDARY_STATES:
        raise KeyLoadingBoundaryError("key boundary active/enabled/live")
    if boundary.state not in ALLOWED_KEY_BOUNDARY_STATES:
        raise KeyLoadingBoundaryError("unknown key loading state")
    if boundary.key_loading_allowed is not False:
        raise KeyLoadingBoundaryError("key loading allowed true in P3L")
    if boundary.boundary_location != KEY_BOUNDARY_LOCATION:
        raise KeyLoadingBoundaryError("actual key read before approved phase")


def build_key_loading_boundary_summary(boundary: KeyLoadingBoundaryState | None = None) -> dict[str, object]:
    boundary = boundary or KeyLoadingBoundaryState()
    validate_key_loading_boundary_state(boundary)
    return {
        "state": boundary.state,
        "key_loading_allowed": False,
        "boundary_location": KEY_BOUNDARY_LOCATION,
        "authorizes_key_loading": False,
        "reads_env_value": False,
        "reads_raw_key": False,
    }


def build_key_existence_summary(key_registry: KeyRegistry, key_slot: str) -> KeyExistenceSummary:
    env_var_name = key_registry.env_var_name(key_slot)
    exists = key_registry.has_key(key_slot)
    if exists:
        return KeyExistenceSummary(key_slot=key_slot, env_var_name=env_var_name, exists=True)
    return KeyExistenceSummary(
        key_slot=key_slot,
        env_var_name=env_var_name,
        exists=False,
        failure_type="CONFIG_ERROR",
        error=f"missing key for key_slot={key_slot}",
    )


def assert_key_value_read_disabled(boundary: KeyLoadingBoundaryState | None = None) -> None:
    validate_key_loading_boundary_state(boundary or KeyLoadingBoundaryState())
    raise KeyLoadingBoundaryError("actual key read before approved phase")


def validate_key_existence_summary(summary: Mapping[str, object]) -> None:
    if summary.get("value_loaded") is not False:
        raise KeyLoadingBoundaryError("value_loaded true")
    if "raw_key_present" in summary:
        raise KeyLoadingBoundaryError("raw_key_present field")
    if "raw_key" in summary or "raw_key_value" in summary:
        raise KeyLoadingBoundaryError("raw key found")
    if "env_var_value" in summary:
        raise KeyLoadingBoundaryError("env var value found")
    exists = summary.get("exists")
    if not isinstance(exists, bool):
        raise KeyLoadingBoundaryError("unknown key loading state")
    for value in summary.values():
        if isinstance(value, str) and _RAW_VALUE_PATTERN.search(value):
            raise KeyLoadingBoundaryError("env var value found")
