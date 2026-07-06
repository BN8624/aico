# P3Q no-call 통합 경로를 실제 실행 없이 검증하고 요약하는 스켈레톤이다.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .activation_guards import (
    P3PActivationGuardError,
    key_loading_activation_guard,
    live_call_activation_guard,
    provider_allowlist_activation_guard,
    sdk_import_activation_guard,
)
from .approval_package import (
    APPROVAL_PACKAGE_ARTIFACT_NAME,
    ApprovalPackage,
    build_approval_final_gate_linkage,
    validate_approval_package_payload,
)
from .approval_phrase import P3PApprovalError, P3P_FAILURES, validate_final_key_slot, validate_final_model, validate_final_provider
from .artifact_safety import ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .key_loading_boundary import KeyLoadingBoundaryState
from .provider_allowlist import ProviderAllowlistState
from .sdk_boundary import SDKBoundaryState

NO_CALL_INTEGRATION_ARTIFACT_NAME = "no_call_integration_summary.json"
NO_CALL_INTEGRATION_ALLOWED_STATUSES = frozenset({"prepared", "ready_for_review", "blocked", "fail"})
NO_CALL_INTEGRATION_FORBIDDEN_STATUSES = frozenset(
    {"success", "live_success", "api_success", "provider_success", "executed", "called", "completed_live_call"}
)
NO_CALL_INTEGRATION_FORBIDDEN_FIELDS = frozenset(
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
P3Q_FAILURES = {
    **P3P_FAILURES,
    "success-like status in P3Q": "SECURITY_BLOCKED",
    "live_call_allowed true in P3Q": "SECURITY_BLOCKED",
    "model_call_count > 0 in P3Q": "SECURITY_BLOCKED",
}


class P3QNoCallIntegrationError(RuntimeError):
    def __init__(self, condition: str, *, failure_type: str | None = None) -> None:
        self.condition = condition
        self.failure_type = failure_type or P3Q_FAILURES[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class NoCallIntegrationSummary:
    status: str
    ready_for_review: bool
    live_call_allowed: bool
    model_call_count: int
    approval_package_ref: str
    final_gate_result_ref: str
    approval_phrase_hash: str
    provider: str
    model: str
    key_slot: str
    activation_guards: tuple[dict[str, object], ...]
    artifact_safety_status: str
    failure_type: str | None
    errors: tuple[str, ...]
    raw_output_saved: bool
    run_id: str
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_sdk_import_count: int = 0
    actual_network_call_count: int = 0
    actual_live_smoke_count: int = 0

    def to_summary(self) -> dict[str, object]:
        payload = asdict(self)
        validate_no_call_integration(payload)
        return payload


def build_no_call_integration_summary(
    *,
    approval_package: ApprovalPackage | Mapping[str, Any],
    final_live_gate_result: Mapping[str, Any],
    provider_allowlist_state: ProviderAllowlistState | None = None,
    sdk_boundary_state: SDKBoundaryState | None = None,
    key_loading_boundary_state: KeyLoadingBoundaryState | None = None,
    runtime_flags_summary: Mapping[str, object] | None,
    artifact_safety_summary: ArtifactSafetyResult | Mapping[str, object] | None,
    key_existence_summary: Mapping[str, object] | None = None,
    status: str = "prepared",
    provider_actual_activation_attempted: bool = False,
    sdk_import_allowed: bool = False,
    provider_sdk_imported: bool = False,
    network_capable_imported: bool = False,
    key_loading_allowed: bool = False,
    actual_key_read_attempted: bool = False,
    live_call_allowed: bool = False,
    model_call_count: int = 0,
    call_model_attempted: bool = False,
) -> NoCallIntegrationSummary:
    _validate_injected_metadata("runtime_flags_summary", runtime_flags_summary)
    artifact_status = _artifact_safety_status(artifact_safety_summary)
    package_payload = approval_package.to_summary() if isinstance(approval_package, ApprovalPackage) else dict(approval_package)
    try:
        validate_approval_package_payload(package_payload)
        linkage = build_approval_final_gate_linkage(
            approval_package=package_payload,
            final_gate_result=final_live_gate_result,
            approval_package_ref=APPROVAL_PACKAGE_ARTIFACT_NAME,
            final_gate_result_ref="final_live_gate_result.json",
        )
    except P3PApprovalError as exc:
        raise _translate_error(exc) from exc
    try:
        guards = (
            _guard_summary(
                provider_allowlist_activation_guard(
                    provider_allowlist_state,
                    actual_activation_attempted=provider_actual_activation_attempted,
                )
            ),
            _guard_summary(
                sdk_import_activation_guard(
                    sdk_boundary_state,
                    sdk_import_allowed=sdk_import_allowed,
                    provider_sdk_imported=provider_sdk_imported,
                    network_capable_imported=network_capable_imported,
                )
            ),
            _guard_summary(
                key_loading_activation_guard(
                    key_loading_boundary_state,
                    key_loading_allowed=key_loading_allowed,
                    actual_key_read_attempted=actual_key_read_attempted,
                    key_existence_summary=key_existence_summary,
                )
            ),
            _guard_summary(
                live_call_activation_guard(
                    live_call_allowed=live_call_allowed,
                    model_call_count=model_call_count,
                    status=status,
                    call_model_attempted=call_model_attempted,
                )
            ),
        )
    except P3PActivationGuardError as exc:
        raise _translate_error(exc) from exc
    summary = NoCallIntegrationSummary(
        status=status,
        ready_for_review=status == "ready_for_review",
        live_call_allowed=False,
        model_call_count=0,
        approval_package_ref=linkage.approval_package_ref,
        final_gate_result_ref=linkage.final_gate_result_ref,
        approval_phrase_hash=linkage.approval_phrase_hash,
        provider=str(package_payload["provider"]),
        model=str(package_payload["model"]),
        key_slot=str(package_payload["key_slot"]),
        activation_guards=guards,
        artifact_safety_status=artifact_status,
        failure_type=None,
        errors=(),
        raw_output_saved=False,
        run_id=linkage.run_id,
    )
    summary.to_summary()
    return summary


def validate_no_call_integration(summary: Mapping[str, Any]) -> None:
    required = {
        "status",
        "ready_for_review",
        "live_call_allowed",
        "model_call_count",
        "approval_package_ref",
        "final_gate_result_ref",
        "approval_phrase_hash",
        "provider",
        "model",
        "key_slot",
        "activation_guards",
        "artifact_safety_status",
        "failure_type",
        "errors",
        "raw_output_saved",
        "run_id",
    }
    if not required <= set(summary):
        raise P3QNoCallIntegrationError("missing linkage required field")
    _reject_forbidden_fields(summary)
    status = str(summary["status"])
    if status in NO_CALL_INTEGRATION_FORBIDDEN_STATUSES:
        raise P3QNoCallIntegrationError("success-like status in P3Q")
    if status not in NO_CALL_INTEGRATION_ALLOWED_STATUSES:
        raise P3QNoCallIntegrationError("unknown gate status")
    if summary["live_call_allowed"] is not False:
        raise P3QNoCallIntegrationError("live_call_allowed true in P3Q")
    if summary["model_call_count"] != 0:
        raise P3QNoCallIntegrationError("model_call_count > 0 in P3Q")
    if summary["raw_output_saved"] is not False:
        raise P3QNoCallIntegrationError("raw_output_saved=True detected")
    try:
        validate_final_provider(_string(summary["provider"]))
        validate_final_model(_string(summary["model"]))
        validate_final_key_slot(_string(summary["key_slot"]))
    except P3PApprovalError as exc:
        raise _translate_error(exc) from exc
    if not summary["approval_package_ref"] or not summary["final_gate_result_ref"] or not summary["approval_phrase_hash"]:
        raise P3QNoCallIntegrationError("missing linkage required field")
    if scan_value_for_unsafe_content(dict(summary), value_path="no_call_integration"):
        raise P3QNoCallIntegrationError("raw key/token/env var value in approval")
    scan_result = scan_artifacts({NO_CALL_INTEGRATION_ARTIFACT_NAME: dict(summary)})
    if not scan_result.ok:
        raise P3QNoCallIntegrationError("raw key/token/env var value in approval", failure_type=scan_result.failure_type)


def write_no_call_integration_summary(
    run_dir: Path,
    summary: NoCallIntegrationSummary | Mapping[str, Any],
    *,
    artifact_name: str = NO_CALL_INTEGRATION_ARTIFACT_NAME,
) -> Path:
    payload = summary.to_summary() if isinstance(summary, NoCallIntegrationSummary) else dict(summary)
    validate_no_call_integration(payload)
    path = resolve_no_call_integration_path(run_dir, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3QNoCallIntegrationError("artifact write failure") from exc
    return path


def resolve_no_call_integration_path(run_dir: Path, artifact_path: str | Path) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)
    if ".." in requested.parts:
        raise P3QNoCallIntegrationError("path traversal attempted")
    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3QNoCallIntegrationError("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise P3QNoCallIntegrationError("artifact path outside run_dir")
    if relative.as_posix() != NO_CALL_INTEGRATION_ARTIFACT_NAME:
        raise P3QNoCallIntegrationError("artifact write failure")
    return resolved


def no_call_integration_default_runtime_creation_enabled() -> bool:
    return False


def _guard_summary(result: Any) -> dict[str, object]:
    payload = result.to_summary()
    _reject_forbidden_fields(payload)
    if scan_value_for_unsafe_content(payload, value_path="activation_guard"):
        raise P3QNoCallIntegrationError("raw key/token/env var value in approval")
    return payload


def _artifact_safety_status(summary: ArtifactSafetyResult | Mapping[str, object] | None) -> str:
    if summary is None:
        raise P3QNoCallIntegrationError("artifact safety scan missing")
    if isinstance(summary, ArtifactSafetyResult):
        if not summary.ok:
            raise P3QNoCallIntegrationError("artifact safety scan failed", failure_type=summary.failure_type)
        return "pass"
    _validate_injected_metadata("artifact_safety_summary", summary)
    ok = summary.get("ok")
    status = summary.get("status")
    if ok is False or status in {"fail", "failed", "blocked"}:
        raise P3QNoCallIntegrationError("artifact safety scan failed")
    if ok is True or status in {"pass", "ok"}:
        return "pass"
    raise P3QNoCallIntegrationError("artifact safety scan missing")


def _validate_injected_metadata(name: str, payload: Mapping[str, object] | None) -> None:
    if payload is None:
        raise P3QNoCallIntegrationError("required gate not_run")
    _reject_forbidden_fields(payload)
    if scan_value_for_unsafe_content(dict(payload), value_path=name):
        raise P3QNoCallIntegrationError("raw key/token/env var value in approval")


def _reject_forbidden_fields(payload: Mapping[str, Any]) -> None:
    if NO_CALL_INTEGRATION_FORBIDDEN_FIELDS & set(payload):
        raise P3QNoCallIntegrationError(
            "raw approval phrase found"
            if "approval_phrase" in payload or "raw_approval_phrase" in payload
            else "raw key/token/env var value in approval"
        )


def _string(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise P3QNoCallIntegrationError("missing linkage required field")
    return value


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _translate_error(exc: P3PApprovalError | P3PActivationGuardError) -> P3QNoCallIntegrationError:
    return P3QNoCallIntegrationError(exc.condition, failure_type=exc.failure_type)
