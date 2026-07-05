# P3P 승인 패키지를 실제 호출 없이 안전하게 검증하고 직렬화하는 스켈레톤이다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .approval_phrase import (
    P3PApprovalError,
    P3P_FAILURES,
    ParsedApprovalPhrase,
    validate_approval_phrase_hash,
    validate_final_key_slot,
    validate_final_model,
    validate_final_provider,
)
from .artifact_safety import scan_artifacts, scan_value_for_unsafe_content

APPROVAL_PACKAGE_SCHEMA_VERSION = "p3_first_live_smoke_approval_v1"
APPROVAL_PACKAGE_SCOPE = "first_live_smoke_this_run_only"
APPROVAL_PACKAGE_ARTIFACT_NAME = "approval_package.json"
APPROVAL_PACKAGE_FORBIDDEN_FIELDS = frozenset(
    {
        "approval_phrase",
        "raw_approval_phrase",
        "raw_output",
        "endpoint_url",
        "raw_key",
        "raw_key_value",
        "key_value",
        "env_var_value",
    }
)


@dataclass(frozen=True)
class ApprovalPackage:
    schema_version: str
    run_id: str
    approval_scope: str
    approved_by_user: bool
    provider: str
    model: str
    key_slot: str
    max_model_calls: int
    max_retries_per_call: int
    max_runtime_seconds: int
    allow_raw_output: bool
    approval_phrase_hash: str
    raw_output_saved: bool = False
    live_call_allowed: bool = False
    model_call_count_before_execution: int = 0

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_approval_package_payload(payload)
        return payload


@dataclass(frozen=True)
class ApprovalFinalGateLinkage:
    run_id: str
    approval_package_ref: str
    approval_phrase_hash: str
    final_gate_result_ref: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_linkage_payload(payload)
        return payload


def build_approval_package(
    *,
    parsed: ParsedApprovalPhrase,
    run_id: str,
    approval_phrase_hash: str,
) -> ApprovalPackage:
    package = ApprovalPackage(
        schema_version=APPROVAL_PACKAGE_SCHEMA_VERSION,
        run_id=run_id,
        approval_scope=APPROVAL_PACKAGE_SCOPE,
        approved_by_user=parsed.approved_by_user,
        provider=parsed.provider,
        model=parsed.model,
        key_slot=parsed.key_slot,
        max_model_calls=parsed.max_model_calls,
        max_retries_per_call=parsed.max_retries_per_call,
        max_runtime_seconds=parsed.max_runtime_seconds,
        allow_raw_output=parsed.allow_raw_output,
        approval_phrase_hash=approval_phrase_hash,
    )
    package.to_summary()
    return package


def validate_approval_package_payload(payload: Mapping[str, Any]) -> None:
    _reject_forbidden_fields(payload)
    required_fields = {
        "schema_version",
        "run_id",
        "approval_scope",
        "approved_by_user",
        "provider",
        "model",
        "key_slot",
        "max_model_calls",
        "max_retries_per_call",
        "max_runtime_seconds",
        "allow_raw_output",
        "approval_phrase_hash",
        "raw_output_saved",
        "live_call_allowed",
        "model_call_count_before_execution",
    }
    if not required_fields <= set(payload):
        raise P3PApprovalError("required approval field missing")
    if payload["schema_version"] != APPROVAL_PACKAGE_SCHEMA_VERSION:
        raise P3PApprovalError("budget invalid")
    if payload["approval_scope"] != APPROVAL_PACKAGE_SCOPE:
        raise P3PApprovalError("approval ambiguous")
    if payload["approved_by_user"] is not True:
        raise P3PApprovalError("approval missing")
    validate_final_provider(_string(payload["provider"]))
    validate_final_model(_string(payload["model"]))
    validate_final_key_slot(_string(payload["key_slot"]))
    if payload["max_model_calls"] != 1:
        raise P3PApprovalError("live call attempted without all gates")
    if payload["max_retries_per_call"] != 0:
        raise P3PApprovalError("retry attempted")
    if not isinstance(payload["max_runtime_seconds"], int) or payload["max_runtime_seconds"] <= 0:
        raise P3PApprovalError("budget invalid")
    if payload["allow_raw_output"] is not False:
        raise P3PApprovalError("allow_raw_output not false")
    validate_approval_phrase_hash(_string(payload["approval_phrase_hash"]))
    if payload["raw_output_saved"] is not False:
        raise P3PApprovalError("raw_output_saved=True detected")
    if payload["live_call_allowed"] is not False:
        raise P3PApprovalError("live_call_allowed true in P3P")
    if payload["model_call_count_before_execution"] != 0:
        raise P3PApprovalError("model_call_count > 0 in P3P")
    if scan_value_for_unsafe_content(dict(payload), value_path="approval_package"):
        raise P3PApprovalError("raw key/token/env var value in approval")


def write_approval_package(
    run_dir: Path,
    package: ApprovalPackage | Mapping[str, Any],
    *,
    artifact_name: str = APPROVAL_PACKAGE_ARTIFACT_NAME,
) -> Path:
    payload = package.to_summary() if isinstance(package, ApprovalPackage) else dict(package)
    validate_approval_package_payload(payload)
    scan_result = scan_artifacts({APPROVAL_PACKAGE_ARTIFACT_NAME: payload})
    if not scan_result.ok:
        raise P3PApprovalError("raw key/token/env var value in approval")
    path = resolve_approval_package_path(run_dir, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3PApprovalError("artifact write failure") from exc
    return path


def resolve_approval_package_path(run_dir: Path, artifact_path: str | Path) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if ".." in requested.parts:
        raise P3PApprovalError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3PApprovalError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3PApprovalError("artifact path outside run_dir")
    if relative.as_posix() != APPROVAL_PACKAGE_ARTIFACT_NAME:
        raise P3PApprovalError("artifact write failure")
    return resolved


def build_approval_final_gate_linkage(
    *,
    approval_package: ApprovalPackage | Mapping[str, Any],
    final_gate_result: Mapping[str, Any],
    approval_package_ref: str = APPROVAL_PACKAGE_ARTIFACT_NAME,
    final_gate_result_ref: str = "final_live_gate_result.json",
) -> ApprovalFinalGateLinkage:
    package_payload = approval_package.to_summary() if isinstance(approval_package, ApprovalPackage) else dict(approval_package)
    validate_approval_package_payload(package_payload)
    validate_final_gate_linkage_target(final_gate_result)
    linkage = ApprovalFinalGateLinkage(
        run_id=_string(package_payload["run_id"]),
        approval_package_ref=approval_package_ref,
        approval_phrase_hash=_string(package_payload["approval_phrase_hash"]),
        final_gate_result_ref=final_gate_result_ref,
    )
    validate_approval_final_gate_linkage(package_payload, final_gate_result, linkage)
    return linkage


def validate_approval_final_gate_linkage(
    approval_package: Mapping[str, Any],
    final_gate_result: Mapping[str, Any],
    linkage: ApprovalFinalGateLinkage | Mapping[str, Any],
) -> None:
    package_payload = dict(approval_package)
    linkage_payload = linkage.to_summary() if isinstance(linkage, ApprovalFinalGateLinkage) else dict(linkage)
    validate_approval_package_payload(package_payload)
    validate_final_gate_linkage_target(final_gate_result)
    validate_linkage_payload(linkage_payload)
    if package_payload["run_id"] != final_gate_result.get("run_id") or package_payload["run_id"] != linkage_payload.get("run_id"):
        raise P3PApprovalError("run_id mismatch")
    if package_payload["approval_phrase_hash"] != linkage_payload.get("approval_phrase_hash"):
        raise P3PApprovalError("missing linkage required field")


def validate_final_gate_linkage_target(final_gate_result: Mapping[str, Any]) -> None:
    required = {"run_id", "status", "live_call_allowed", "model_call_count", "raw_output_saved"}
    if not required <= set(final_gate_result):
        raise P3PApprovalError("missing linkage required field")
    _reject_forbidden_fields(final_gate_result)
    status = final_gate_result.get("status")
    if status in {"success", "live_success", "api_success", "provider_success", "executed", "called"}:
        raise P3PApprovalError("success-like status in P3P")
    if final_gate_result.get("live_call_allowed") is not False:
        raise P3PApprovalError("live_call_allowed true in P3P")
    if final_gate_result.get("model_call_count") != 0:
        raise P3PApprovalError("model_call_count > 0 in P3P")
    if final_gate_result.get("raw_output_saved") is not False:
        raise P3PApprovalError("raw_output_saved=True detected")
    if scan_value_for_unsafe_content(dict(final_gate_result), value_path="final_gate_result"):
        raise P3PApprovalError("raw key/token/env var value in approval")


def validate_linkage_payload(payload: Mapping[str, Any]) -> None:
    required = {"run_id", "approval_package_ref", "approval_phrase_hash", "final_gate_result_ref"}
    if not required <= set(payload):
        raise P3PApprovalError("missing linkage required field")
    _reject_forbidden_fields(payload)
    validate_approval_phrase_hash(_string(payload["approval_phrase_hash"]))
    if scan_value_for_unsafe_content(dict(payload), value_path="linkage"):
        raise P3PApprovalError("raw key/token/env var value in approval")


def approval_package_default_runtime_creation_enabled() -> bool:
    return False


def _reject_forbidden_fields(payload: Mapping[str, Any]) -> None:
    if APPROVAL_PACKAGE_FORBIDDEN_FIELDS & set(payload):
        raise P3PApprovalError("raw approval phrase found" if "approval_phrase" in payload or "raw_approval_phrase" in payload else "raw key/token/env var value in approval")


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3PApprovalError("required approval field missing")
    return value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
