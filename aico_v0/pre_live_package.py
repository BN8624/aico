# P3S pre-live artifact package를 실제 호출 없이 조립하고 검증하는 스켈레톤입니다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .approval_package import APPROVAL_PACKAGE_ARTIFACT_NAME, write_approval_package
from .artifact_safety import ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .live_execution_boundary import (
    CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
    P3R_FAILURES,
    P3RLiveExecutionBoundaryError,
    validate_live_execution_boundary,
    write_call_attempt_summary,
)
from .no_call_integration import NO_CALL_INTEGRATION_ARTIFACT_NAME, write_no_call_integration_summary

PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME = "pre_live_package_manifest.json"
PRE_LIVE_PACKAGE_SCHEMA_VERSION = "p3_pre_live_package_manifest_v1"
PRE_LIVE_PACKAGE_CREATED_FOR = "no_call_pre_live_package_only"
PRE_LIVE_ALLOWED_STATUSES = frozenset({"prepared", "ready_for_review", "blocked", "fail"})
PRE_LIVE_SUCCESS_LIKE_STATUSES = frozenset(
    {"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"}
)
PRE_LIVE_REQUIRED_ITEM_NAMES = frozenset(
    {
        "approval_package",
        "no_call_integration_summary",
        "call_attempt_summary",
        "final_live_gate_result",
        "artifact_safety_report",
    }
)
PRE_LIVE_FORBIDDEN_FIELDS = frozenset(
    {
        "approval_phrase",
        "raw_approval_phrase",
        "raw_output",
        "endpoint_url",
        "raw_key",
        "raw_key_value",
        "key_value",
        "env_var_value",
        "provider_response",
        "token_usage",
    }
)
PRE_LIVE_FAILURE_PRIORITY = (
    "SECURITY_BLOCKED",
    "BUDGET_EXCEEDED",
    "REPORT_ERROR",
    "CONFIG_ERROR",
    "HUMAN_DECISION_REQUIRED",
    "MODEL_ERROR",
    "SCHEMA_ERROR",
    "WORKER_BAD_OUTPUT",
)
P3S_FAILURES = {
    **P3R_FAILURES,
    "success-like status in P3S": "SECURITY_BLOCKED",
    "live_call_allowed true in P3S": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3S": "SECURITY_BLOCKED",
    "call_model_count > 0 in P3S": "SECURITY_BLOCKED",
    "missing required package item": "CONFIG_ERROR",
    "required item not scanned": "CONFIG_ERROR",
    "required item scan failed": "SECURITY_BLOCKED",
    "approval_phrase_hash mismatch": "CONFIG_ERROR",
    "missing approval_phrase_hash": "CONFIG_ERROR",
    "missing artifact reference": "CONFIG_ERROR",
    "artifact reference mismatch": "CONFIG_ERROR",
    "unsafe artifact reference": "SECURITY_BLOCKED",
    "pre-scan missing": "CONFIG_ERROR",
    "post-scan missing": "CONFIG_ERROR",
    "scan failed": "SECURITY_BLOCKED",
    "SDK import marker in P3S": "SECURITY_BLOCKED",
    "key loaded marker in P3S": "SECURITY_BLOCKED",
    "network call marker in P3S": "SECURITY_BLOCKED",
    "live smoke marker in P3S": "SECURITY_BLOCKED",
}


class P3SPreLivePackageError(RuntimeError):
    def __init__(self, condition: str, *, failure_type: str | None = None) -> None:
        self.condition = condition
        self.failure_type = failure_type or P3S_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class PreLivePackageItem:
    name: str
    ref: str
    run_id: str
    approval_phrase_hash: str
    required: bool = True
    artifact_safety_status: str = "pass"
    raw_output_saved: bool = False
    live_call_allowed: bool = False
    model_call_count: int = 0

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_package_item(payload)
        return payload


@dataclass(frozen=True)
class PreLivePackageManifest:
    schema_version: str
    run_id: str
    status: str
    ready_for_review: bool
    live_call_allowed: bool
    model_call_count: int
    call_model_count: int
    approval_package_ref: str
    no_call_integration_summary_ref: str
    call_attempt_summary_ref: str
    final_gate_result_ref: str
    approval_phrase_hash: str
    provider: str
    model: str
    key_slot: str
    artifact_safety_pre_scan_status: str
    artifact_safety_post_scan_status: str
    package_items: tuple[PreLivePackageItem, ...]
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    created_for: str

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        payload["package_items"] = [item.to_summary() for item in self.package_items]
        validate_pre_live_package(payload)
        return payload


def build_pre_live_package_manifest(
    *,
    approval_package: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
    artifact_safety_summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    runtime_flags_summary: Mapping[str, Any],
    rollback_plan_summary: Mapping[str, Any],
    artifact_safety_post_scan: ArtifactSafetyResult | Mapping[str, Any] | None = None,
    status: str = "prepared",
) -> PreLivePackageManifest:
    validate_no_call_invariants(runtime_flags_summary)
    validate_no_call_invariants(rollback_plan_summary)
    validate_no_call_invariants(approval_package)
    validate_no_call_invariants(no_call_integration_summary)
    validate_no_call_invariants(call_attempt_summary)
    validate_no_call_invariants(final_live_gate_result)
    try:
        validate_live_execution_boundary(call_attempt_summary)
    except P3RLiveExecutionBoundaryError as exc:
        raise _translate_p3r_error(exc) from exc
    pre_scan_status = _artifact_scan_status(artifact_safety_summary, missing_condition="pre-scan missing")
    post_scan_status = _artifact_scan_status(artifact_safety_post_scan, missing_condition="post-scan missing", allow_not_run=True)
    run_id = _consistent_run_id(approval_package, no_call_integration_summary, call_attempt_summary, final_live_gate_result)
    approval_hash = _consistent_approval_hash(
        approval_package,
        no_call_integration_summary,
        call_attempt_summary,
        final_live_gate_result,
    )
    refs = _consistent_refs(no_call_integration_summary, call_attempt_summary)
    items = tuple(
        PreLivePackageItem(
            name=name,
            ref=ref,
            run_id=run_id,
            approval_phrase_hash=approval_hash,
            artifact_safety_status="pass",
        )
        for name, ref in (
            ("approval_package", refs["approval_package_ref"]),
            ("no_call_integration_summary", refs["no_call_integration_summary_ref"]),
            ("call_attempt_summary", refs["call_attempt_summary_ref"]),
            ("final_live_gate_result", refs["final_gate_result_ref"]),
            ("artifact_safety_report", "artifact_safety_report.json"),
        )
    )
    manifest = PreLivePackageManifest(
        schema_version=PRE_LIVE_PACKAGE_SCHEMA_VERSION,
        run_id=run_id,
        status=status,
        ready_for_review=status == "ready_for_review",
        live_call_allowed=False,
        model_call_count=0,
        call_model_count=0,
        approval_package_ref=refs["approval_package_ref"],
        no_call_integration_summary_ref=refs["no_call_integration_summary_ref"],
        call_attempt_summary_ref=refs["call_attempt_summary_ref"],
        final_gate_result_ref=refs["final_gate_result_ref"],
        approval_phrase_hash=approval_hash,
        provider=_string(approval_package.get("provider")),
        model=_string(approval_package.get("model")),
        key_slot=_string(approval_package.get("key_slot")),
        artifact_safety_pre_scan_status=pre_scan_status,
        artifact_safety_post_scan_status=post_scan_status,
        package_items=items,
        failure_type=None,
        errors=(),
        raw_output_saved=False,
        created_for=PRE_LIVE_PACKAGE_CREATED_FOR,
    )
    manifest.to_summary()
    return manifest


def assemble_pre_live_package(
    *,
    approval_package: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
    runtime_flags_summary: Mapping[str, Any],
    rollback_plan_summary: Mapping[str, Any],
    run_dir: Path | None = None,
    write_artifacts: bool = False,
) -> PreLivePackageManifest:
    pre_scan = scan_artifacts(
        {
            APPROVAL_PACKAGE_ARTIFACT_NAME: dict(approval_package),
            NO_CALL_INTEGRATION_ARTIFACT_NAME: dict(no_call_integration_summary),
            CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME: dict(call_attempt_summary),
            "final_live_gate_result.json": dict(final_live_gate_result),
            "runtime_flags_summary.json": dict(runtime_flags_summary),
            "rollback_plan_summary.json": dict(rollback_plan_summary),
        }
    )
    manifest = build_pre_live_package_manifest(
        approval_package=approval_package,
        no_call_integration_summary=no_call_integration_summary,
        call_attempt_summary=call_attempt_summary,
        final_live_gate_result=final_live_gate_result,
        artifact_safety_summary=pre_scan,
        runtime_flags_summary=runtime_flags_summary,
        rollback_plan_summary=rollback_plan_summary,
        artifact_safety_post_scan={"status": "not_run"},
        status="ready_for_review",
    )
    post_scan = scan_artifacts(
        {
            APPROVAL_PACKAGE_ARTIFACT_NAME: dict(approval_package),
            NO_CALL_INTEGRATION_ARTIFACT_NAME: dict(no_call_integration_summary),
            CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME: dict(call_attempt_summary),
            PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME: manifest.to_summary(),
        }
    )
    manifest = build_pre_live_package_manifest(
        approval_package=approval_package,
        no_call_integration_summary=no_call_integration_summary,
        call_attempt_summary=call_attempt_summary,
        final_live_gate_result=final_live_gate_result,
        artifact_safety_summary=pre_scan,
        runtime_flags_summary=runtime_flags_summary,
        rollback_plan_summary=rollback_plan_summary,
        artifact_safety_post_scan=post_scan,
        status="ready_for_review",
    )
    if write_artifacts:
        if run_dir is None:
            raise P3SPreLivePackageError("missing artifact reference")
        write_approval_package(run_dir, approval_package)
        write_no_call_integration_summary(run_dir, no_call_integration_summary)
        write_call_attempt_summary(run_dir, call_attempt_summary)
        write_pre_live_package_manifest(run_dir, manifest, pre_scan=pre_scan, post_scan=post_scan)
    return manifest


def validate_pre_live_package(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "run_id",
        "status",
        "ready_for_review",
        "live_call_allowed",
        "model_call_count",
        "call_model_count",
        "approval_package_ref",
        "no_call_integration_summary_ref",
        "call_attempt_summary_ref",
        "final_gate_result_ref",
        "approval_phrase_hash",
        "provider",
        "model",
        "key_slot",
        "artifact_safety_pre_scan_status",
        "artifact_safety_post_scan_status",
        "package_items",
        "failure_type",
        "errors",
        "raw_output_saved",
        "created_for",
    }
    if not required <= set(manifest):
        raise P3SPreLivePackageError("missing required package item")
    if manifest["schema_version"] != PRE_LIVE_PACKAGE_SCHEMA_VERSION:
        raise P3SPreLivePackageError("missing required package item")
    _validate_status(_string(manifest["status"]))
    if manifest["created_for"] != PRE_LIVE_PACKAGE_CREATED_FOR:
        raise P3SPreLivePackageError("live_call_allowed true in P3S")
    validate_no_call_invariants(manifest)
    _validate_safe_ref(_string(manifest["approval_package_ref"]))
    _validate_safe_ref(_string(manifest["no_call_integration_summary_ref"]))
    _validate_safe_ref(_string(manifest["call_attempt_summary_ref"]))
    _validate_safe_ref(_string(manifest["final_gate_result_ref"]))
    validate_approval_phrase_hash(_string(manifest["approval_phrase_hash"]))
    _validate_scan_field(_string(manifest["artifact_safety_pre_scan_status"]), missing_condition="pre-scan missing")
    _validate_post_scan_field(_string(manifest["artifact_safety_post_scan_status"]))
    items = list(manifest["package_items"])
    item_names = {str(item.get("name")) for item in items if isinstance(item, Mapping)}
    if not PRE_LIVE_REQUIRED_ITEM_NAMES <= item_names:
        raise P3SPreLivePackageError("missing required package item")
    for item in items:
        if not isinstance(item, Mapping):
            raise P3SPreLivePackageError("missing required package item")
        validate_package_item(item)
        if item.get("run_id") != manifest["run_id"]:
            raise P3SPreLivePackageError("run_id mismatch")
        if item.get("approval_phrase_hash") != manifest["approval_phrase_hash"]:
            raise P3SPreLivePackageError("approval_phrase_hash mismatch")
    scan_result = scan_artifacts({PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME: dict(manifest)})
    if not scan_result.ok:
        raise P3SPreLivePackageError("scan failed", failure_type=scan_result.failure_type)


def validate_package_item(item: Mapping[str, Any]) -> None:
    required = {
        "name",
        "ref",
        "run_id",
        "approval_phrase_hash",
        "required",
        "artifact_safety_status",
        "raw_output_saved",
        "live_call_allowed",
        "model_call_count",
    }
    if not required <= set(item):
        raise P3SPreLivePackageError("missing required package item")
    validate_no_call_invariants(item)
    if item.get("required") is not True:
        raise P3SPreLivePackageError("missing required package item")
    _validate_safe_ref(_string(item["ref"]))
    validate_approval_phrase_hash(_string(item["approval_phrase_hash"]))
    _validate_scan_field(_string(item["artifact_safety_status"]), missing_condition="required item not scanned")


def validate_no_call_invariants(payload: Mapping[str, Any]) -> None:
    _reject_forbidden_fields(payload)
    if "status" in payload:
        _validate_status(_string(payload["status"]))
    blocked_true_fields = {
        "live_call_allowed": "live_call_allowed true in P3S",
        "raw_output_saved": "raw_output_saved=True detected",
        "provider_sdk_imported": "SDK import marker in P3S",
        "sdk_import_activated": "SDK import marker in P3S",
        "sdk_imported": "SDK import marker in P3S",
        "key_loading_activated": "key loaded marker in P3S",
        "key_loaded": "key loaded marker in P3S",
        "reads_raw_key": "key loaded marker in P3S",
        "reads_env_value": "env var value found",
        "network_call": "network call marker in P3S",
        "live_smoke_executed": "live smoke marker in P3S",
        "provider_allowlist_activated": "candidate interpreted as active",
        "retry_allowed": "retry_allowed true",
        "reserve_allowed": "reserve_allowed true",
        "fallback_allowed": "fallback_allowed true",
        "second_call_allowed": "second_call_allowed true",
        "call_model_executed": "call_model attempted in P3R",
    }
    for field, condition in blocked_true_fields.items():
        if payload.get(field) is True:
            raise P3SPreLivePackageError(condition)
    for field in (
        "model_call_count",
        "model_call_count_before_execution",
        "call_model_count",
        "actual_api_call_count",
        "actual_llm_call_count",
        "actual_key_value_read_count",
        "actual_env_value_read_count",
        "actual_sdk_import_count",
        "actual_network_call_count",
        "actual_live_smoke_count",
    ):
        if int(payload.get(field, 0) or 0) > 0:
            if field == "call_model_count":
                raise P3SPreLivePackageError("call_model_count > 0 in P3S")
            if field == "actual_sdk_import_count":
                raise P3SPreLivePackageError("SDK import marker in P3S")
            if field in {"actual_key_value_read_count", "actual_env_value_read_count"}:
                raise P3SPreLivePackageError("key loaded marker in P3S")
            if field == "actual_network_call_count":
                raise P3SPreLivePackageError("network call marker in P3S")
            if field == "actual_live_smoke_count":
                raise P3SPreLivePackageError("live smoke marker in P3S")
            raise P3SPreLivePackageError("model_call_count > 0 in P3S")
    if scan_value_for_unsafe_content(dict(payload), value_path="pre_live_package"):
        raise P3SPreLivePackageError("raw key/token/env var value in approval")


def validate_consistency(
    *,
    approval_package: Mapping[str, Any],
    no_call_integration_summary: Mapping[str, Any],
    call_attempt_summary: Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
) -> None:
    _consistent_run_id(approval_package, no_call_integration_summary, call_attempt_summary, final_live_gate_result)
    _consistent_approval_hash(approval_package, no_call_integration_summary, call_attempt_summary, final_live_gate_result)
    _consistent_refs(no_call_integration_summary, call_attempt_summary)


def write_pre_live_package_manifest(
    run_dir: Path,
    manifest: PreLivePackageManifest | Mapping[str, Any],
    *,
    pre_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    post_scan: ArtifactSafetyResult | Mapping[str, Any] | None,
    artifact_name: str = PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME,
) -> Path:
    _artifact_scan_status(pre_scan, missing_condition="pre-scan missing")
    _artifact_scan_status(post_scan, missing_condition="post-scan missing")
    payload = manifest.to_summary() if isinstance(manifest, PreLivePackageManifest) else dict(manifest)
    validate_pre_live_package(payload)
    path = resolve_pre_live_package_manifest_path(run_dir, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3SPreLivePackageError("artifact write failure") from exc
    return path


def resolve_pre_live_package_manifest_path(run_dir: Path, artifact_path: str | Path) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if _is_url_ref(str(artifact_path)):
        raise P3SPreLivePackageError("unsafe artifact reference")
    if ".." in requested.parts:
        raise P3SPreLivePackageError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3SPreLivePackageError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3SPreLivePackageError("artifact path outside run_dir")
    if relative.as_posix() != PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME:
        raise P3SPreLivePackageError("artifact write failure")
    return resolved


def pre_live_package_default_runtime_creation_enabled() -> bool:
    return False


def aggregate_package_failure_type(failure_types: Sequence[str | None]) -> str | None:
    present = {failure_type for failure_type in failure_types if failure_type}
    for failure_type in PRE_LIVE_FAILURE_PRIORITY:
        if failure_type in present:
            return failure_type
    return None


def validate_approval_phrase_hash(value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise P3SPreLivePackageError("missing approval_phrase_hash")


def _consistent_run_id(*payloads: Mapping[str, Any]) -> str:
    run_ids = []
    for payload in payloads:
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise P3SPreLivePackageError("run_id mismatch")
        run_ids.append(run_id)
    if len(set(run_ids)) != 1:
        raise P3SPreLivePackageError("run_id mismatch")
    return run_ids[0]


def _consistent_approval_hash(*payloads: Mapping[str, Any]) -> str:
    hashes = []
    for payload in payloads:
        value = payload.get("approval_phrase_hash")
        if not isinstance(value, str) or not value:
            raise P3SPreLivePackageError("missing approval_phrase_hash")
        validate_approval_phrase_hash(value)
        hashes.append(value)
    if len(set(hashes)) != 1:
        raise P3SPreLivePackageError("approval_phrase_hash mismatch")
    return hashes[0]


def _consistent_refs(no_call_integration_summary: Mapping[str, Any], call_attempt_summary: Mapping[str, Any]) -> dict[str, str]:
    refs = {
        "approval_package_ref": _string(no_call_integration_summary.get("approval_package_ref")),
        "no_call_integration_summary_ref": _string(call_attempt_summary.get("no_call_integration_ref")),
        "call_attempt_summary_ref": CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
        "final_gate_result_ref": _string(no_call_integration_summary.get("final_gate_result_ref")),
    }
    if call_attempt_summary.get("approval_package_ref") != refs["approval_package_ref"]:
        raise P3SPreLivePackageError("artifact reference mismatch")
    if call_attempt_summary.get("final_gate_result_ref") != refs["final_gate_result_ref"]:
        raise P3SPreLivePackageError("artifact reference mismatch")
    if refs["no_call_integration_summary_ref"] != NO_CALL_INTEGRATION_ARTIFACT_NAME:
        raise P3SPreLivePackageError("artifact reference mismatch")
    for ref in refs.values():
        _validate_safe_ref(ref)
    return refs


def _artifact_scan_status(
    summary: ArtifactSafetyResult | Mapping[str, Any] | None,
    *,
    missing_condition: str,
    allow_not_run: bool = False,
) -> str:
    if summary is None:
        raise P3SPreLivePackageError(missing_condition)
    if isinstance(summary, ArtifactSafetyResult):
        if not summary.ok:
            raise P3SPreLivePackageError("scan failed", failure_type=summary.failure_type)
        return "pass"
    _reject_forbidden_fields(summary)
    if scan_value_for_unsafe_content(dict(summary), value_path="artifact_safety_summary"):
        raise P3SPreLivePackageError("raw key/token/env var value in approval")
    status = summary.get("status")
    ok = summary.get("ok")
    if ok is True or status in {"pass", "ok"}:
        return "pass"
    if allow_not_run and status == "not_run":
        return "not_run"
    if ok is False or status in {"fail", "failed", "blocked"}:
        raise P3SPreLivePackageError("scan failed")
    raise P3SPreLivePackageError(missing_condition)


def _validate_scan_field(status: str, *, missing_condition: str) -> None:
    if status == "pass":
        return
    if status in {"not_run", "missing"}:
        raise P3SPreLivePackageError(missing_condition)
    raise P3SPreLivePackageError("required item scan failed")


def _validate_post_scan_field(status: str) -> None:
    if status in {"pass", "not_run"}:
        return
    if status == "missing":
        raise P3SPreLivePackageError("post-scan missing")
    raise P3SPreLivePackageError("scan failed")


def _validate_status(status: str) -> None:
    if status in PRE_LIVE_SUCCESS_LIKE_STATUSES:
        raise P3SPreLivePackageError("success-like status in P3S")
    if status not in PRE_LIVE_ALLOWED_STATUSES:
        raise P3SPreLivePackageError("unknown gate status")


def _validate_safe_ref(ref: str) -> None:
    if not ref:
        raise P3SPreLivePackageError("missing artifact reference")
    if _is_url_ref(ref):
        raise P3SPreLivePackageError("unsafe artifact reference")
    requested = Path(ref)
    if requested.is_absolute():
        raise P3SPreLivePackageError("unsafe artifact reference")
    if ".." in requested.parts:
        raise P3SPreLivePackageError("path traversal attempted")


def _reject_forbidden_fields(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if key in PRE_LIVE_FORBIDDEN_FIELDS:
            if key == "provider_response":
                raise P3SPreLivePackageError("provider response found")
            if key == "token_usage":
                raise P3SPreLivePackageError("token usage found")
            raise P3SPreLivePackageError("raw key/token/env var value in approval")
        if isinstance(value, Mapping):
            _reject_forbidden_fields(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_forbidden_fields(item)


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3SPreLivePackageError("missing artifact reference")
    return value


def _is_url_ref(value: str) -> bool:
    return value.startswith(("http://", "https://")) or "://" in value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _translate_p3r_error(exc: P3RLiveExecutionBoundaryError) -> P3SPreLivePackageError:
    return P3SPreLivePackageError(exc.condition, failure_type=exc.failure_type)
