# P3L provider SDK import 경계를 실제 import 없이 검증하는 skeleton이다.
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from .provider_allowlist import validate_provider_name

ALLOWED_SDK_BOUNDARY_STATES = frozenset({"disabled", "not_approved", "candidate_only"})
FORBIDDEN_SDK_BOUNDARY_STATES = frozenset({"approved", "active", "enabled", "live", "sdk_ready", "import_ready"})
SDK_BOUNDARY_LOCATION = "provider_adapter_internal_only"
SDK_BOUNDARY_FAILURES = {
    "unknown SDK import state": "CONFIG_ERROR",
    "SDK import before approved phase": "SECURITY_BLOCKED",
    "SDK import allowed true in P3L": "SECURITY_BLOCKED",
    "SDK boundary active/enabled/live": "SECURITY_BLOCKED",
    "provider SDK imported in runtime path": "SECURITY_BLOCKED",
    "network-capable SDK import in runtime path": "SECURITY_BLOCKED",
    "endpoint URL requested": "SECURITY_BLOCKED",
    "raw key found": "SECURITY_BLOCKED",
}
_UNSAFE_SUMMARY_PATTERN = re.compile(
    r"https?://|[A-Za-z0-9.-]+\.[A-Za-z]{2,}|sk-[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9._-]{10,}",
    re.IGNORECASE,
)


class SDKBoundaryError(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = SDK_BOUNDARY_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class SDKBoundaryState:
    state: str = "disabled"
    provider: str = "google_gemini"
    sdk_import_allowed: bool = False
    boundary_location: str = SDK_BOUNDARY_LOCATION

    @property
    def authorizes_sdk_import(self) -> bool:
        return False


def validate_sdk_boundary_state(boundary: SDKBoundaryState | None) -> None:
    if boundary is None:
        raise SDKBoundaryError("unknown SDK import state")
    validate_provider_name(boundary.provider)
    if boundary.state in FORBIDDEN_SDK_BOUNDARY_STATES:
        raise SDKBoundaryError("SDK boundary active/enabled/live")
    if boundary.state not in ALLOWED_SDK_BOUNDARY_STATES:
        raise SDKBoundaryError("unknown SDK import state")
    if boundary.sdk_import_allowed is not False:
        raise SDKBoundaryError("SDK import allowed true in P3L")
    if boundary.boundary_location != SDK_BOUNDARY_LOCATION:
        raise SDKBoundaryError("SDK import before approved phase")


def build_sdk_boundary_summary(boundary: SDKBoundaryState | None = None) -> dict[str, object]:
    boundary = boundary or SDKBoundaryState()
    validate_sdk_boundary_state(boundary)
    summary = {
        "provider": boundary.provider,
        "state": boundary.state,
        "sdk_import_allowed": False,
        "boundary_location": SDK_BOUNDARY_LOCATION,
        "imports_provider_sdk": False,
        "checks_sdk_availability": False,
        "imports_network_module": False,
        "authorizes_live_call": False,
    }
    validate_sdk_boundary_summary(summary)
    return summary


def assert_sdk_import_disabled(boundary: SDKBoundaryState | None = None) -> None:
    validate_sdk_boundary_state(boundary or SDKBoundaryState())
    raise SDKBoundaryError("SDK import before approved phase")


def validate_sdk_boundary_summary(summary: Mapping[str, object]) -> None:
    for forbidden_field in ("endpoint_url", "sdk_path", "api_key", "env_var_value"):
        if forbidden_field in summary:
            raise SDKBoundaryError("endpoint URL requested" if forbidden_field == "endpoint_url" else "raw key found")
    if summary.get("sdk_import_allowed") is not False:
        raise SDKBoundaryError("SDK import allowed true in P3L")
    for value in summary.values():
        if isinstance(value, str) and _UNSAFE_SUMMARY_PATTERN.search(value):
            raise SDKBoundaryError("endpoint URL requested" if "://" in value or "." in value else "raw key found")
