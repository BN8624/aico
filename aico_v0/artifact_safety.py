# P3E 산출물 안전 스캔 규칙과 결과 구조를 제공한다.
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .provider_base import contains_secret

SAFE_ENV_VAR_NAMES = {
    "AICO_MANAGER_1_API_KEY",
    "AICO_WORKER_1_API_KEY",
    "AICO_WORKER_2_API_KEY",
    "AICO_WORKER_3_API_KEY",
    "AICO_WORKER_4_API_KEY",
    "AICO_AUDITOR_1_API_KEY",
    "AICO_RESERVE_1_API_KEY",
}

_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_ENV_VALUE_PATTERN = re.compile(r"\bAICO_[A-Z0-9_]*API_KEY\s*[:=]\s*['\"]?[A-Za-z0-9_.-]{8,}")
_RAW_PROVIDER_OUTPUT_PATTERN = re.compile(
    r"(?i)(<<raw_provider_output>>|raw_provider_output\s*[:=]|unmasked_provider_output\s*[:=])"
)
_RAW_OUTPUT_SAVED_TRUE_PATTERN = re.compile(r'(?i)"?raw_output_saved"?\s*[:=]\s*true')
_RAW_OUTPUT_FIELD_PATTERN = re.compile(r'(?i)"raw_output"\s*:')


@dataclass(frozen=True)
class ArtifactSafetyFinding:
    artifact_path: str
    failure_type: str
    reason: str


@dataclass(frozen=True)
class ArtifactSafetyResult:
    ok: bool
    failure_type: str | None
    findings: tuple[ArtifactSafetyFinding, ...]

    def to_run_log_event(self) -> dict[str, object]:
        return {
            "event_type": "ARTIFACT_SAFETY_SCAN",
            "status": "ok" if self.ok else "failure",
            "failure_type": self.failure_type,
            "error": "; ".join(finding.reason for finding in self.findings) or None,
            "artifact_path": None,
        }


def scan_artifacts(artifacts: Mapping[str, Any] | None) -> ArtifactSafetyResult:
    if artifacts is None:
        return _config_error("artifact safety scan missing")

    findings: list[ArtifactSafetyFinding] = []
    artifact_names = set(artifacts)
    if {"final_report.md", "failed_draft.md"} <= artifact_names:
        findings.append(
            ArtifactSafetyFinding(
                "final_report.md,failed_draft.md",
                "REPORT_ERROR",
                "final_report.md and failed_draft.md both generated",
            )
        )

    for artifact_path, payload in artifacts.items():
        findings.extend(_scan_text(artifact_path, _serialize_payload(payload)))

    if findings:
        failure_type = "REPORT_ERROR" if any(f.failure_type == "REPORT_ERROR" for f in findings) else "SECURITY_BLOCKED"
        return ArtifactSafetyResult(False, failure_type, tuple(findings))
    return ArtifactSafetyResult(True, None, ())


def scan_artifact_text(artifact_path: str, text: str) -> ArtifactSafetyResult:
    findings = tuple(_scan_text(artifact_path, text))
    if not findings:
        return ArtifactSafetyResult(True, None, ())
    return ArtifactSafetyResult(False, findings[0].failure_type, findings)


def scan_value_for_unsafe_content(value: Any, *, value_path: str = "<value>") -> tuple[ArtifactSafetyFinding, ...]:
    return tuple(_scan_value(value_path, value))


def value_contains_unsafe_content(value: Any) -> bool:
    return bool(scan_value_for_unsafe_content(value))


def _scan_value(value_path: str, value: Any) -> list[ArtifactSafetyFinding]:
    if isinstance(value, str):
        return _scan_text(value_path, value)
    if isinstance(value, Mapping):
        findings: list[ArtifactSafetyFinding] = []
        for key, item in value.items():
            findings.extend(_scan_value(f"{value_path}.{key}", key))
            findings.extend(_scan_value(f"{value_path}.{key}", item))
        return findings
    if isinstance(value, (list, tuple, set)):
        findings = []
        for index, item in enumerate(value):
            findings.extend(_scan_value(f"{value_path}[{index}]", item))
        return findings
    return []


def _scan_text(artifact_path: str, text: str) -> list[ArtifactSafetyFinding]:
    findings: list[ArtifactSafetyFinding] = []
    checks = (
        (contains_secret(text), "raw key-like value detected"),
        (bool(_ENV_VALUE_PATTERN.search(text)), "env var value pattern detected"),
        (bool(_BEARER_TOKEN_PATTERN.search(text)), "bearer token pattern detected"),
        (bool(_PRIVATE_KEY_PATTERN.search(text)), "private key block detected"),
        (bool(_RAW_PROVIDER_OUTPUT_PATTERN.search(text)), "unmasked raw provider output marker detected"),
        (bool(_RAW_OUTPUT_SAVED_TRUE_PATTERN.search(text)), "raw_output_saved=True detected"),
        (bool(_RAW_OUTPUT_FIELD_PATTERN.search(text)), "raw_output field detected"),
    )
    for matched, reason in checks:
        if matched:
            findings.append(ArtifactSafetyFinding(artifact_path, "SECURITY_BLOCKED", reason))
    return findings


def _serialize_payload(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _config_error(reason: str) -> ArtifactSafetyResult:
    return ArtifactSafetyResult(False, "CONFIG_ERROR", (ArtifactSafetyFinding("<scan>", "CONFIG_ERROR", reason),))
