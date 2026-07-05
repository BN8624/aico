# P3J live smoke 산출물 쓰기와 run_dir 경계를 검증한다.
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .artifact_safety import ArtifactSafetyResult, scan_artifacts
from .live_smoke import (
    ALLOWED_LIVE_SMOKE_ARTIFACTS,
    FAILURE_TYPE_BY_SMOKE_CONDITION,
    FORBIDDEN_LIVE_SMOKE_ARTIFACTS,
    FirstLiveSmokeApproval,
    build_artifact_safety_report,
    build_live_smoke_result,
)

ARTIFACT_FAILURE_TYPE_BY_CONDITION = {
    **FAILURE_TYPE_BY_SMOKE_CONDITION,
}

CANONICAL_FAILURE_TYPES = frozenset(
    {
        "HUMAN_DECISION_REQUIRED",
        "CONFIG_ERROR",
        "SECURITY_BLOCKED",
        "BUDGET_EXCEEDED",
        "MODEL_ERROR",
        "SCHEMA_ERROR",
        "WORKER_BAD_OUTPUT",
        "REPORT_ERROR",
    }
)
SAFE_LIVE_SMOKE_STATUSES = frozenset({"disabled", "not_executed", "prepared", "blocked"})
SAFE_ARTIFACT_SAFETY_STATUSES = frozenset({"pass", "fail", "missing", "not_run"})


class ArtifactWriteBlocked(RuntimeError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        self.failure_type = ARTIFACT_FAILURE_TYPE_BY_CONDITION[condition]
        super().__init__(condition)


@dataclass(frozen=True)
class DisabledLiveSmokeArtifactRunResult:
    status: str
    failure_type: str
    error: str
    run_dir: Path
    written_artifacts: tuple[str, ...]
    pre_scan_status: str
    post_scan_status: str
    actual_api_call_count: int = 0
    actual_llm_call_count: int = 0
    actual_key_value_read_count: int = 0
    actual_network_call_count: int = 0
    provider_sdk_imported: bool = False
    live_smoke_executed: bool = False


def resolve_live_smoke_artifact_path(run_dir: Path, artifact_path: str | Path) -> Path:
    run_root = run_dir.resolve()
    requested = Path(artifact_path)

    if ".." in requested.parts:
        raise ArtifactWriteBlocked("path traversal attempted")

    if requested.is_absolute():
        resolved = requested.resolve()
        if not _is_relative_to(resolved, run_root):
            raise ArtifactWriteBlocked("artifact path outside run_dir")
        relative = resolved.relative_to(run_root)
    else:
        relative = requested
        resolved = (run_root / relative).resolve()
        if not _is_relative_to(resolved, run_root):
            raise ArtifactWriteBlocked("artifact path outside run_dir")

    relative_name = relative.as_posix()
    if relative.name in FORBIDDEN_LIVE_SMOKE_ARTIFACTS or relative_name in FORBIDDEN_LIVE_SMOKE_ARTIFACTS:
        raise ArtifactWriteBlocked("forbidden artifact attempted")
    if relative_name not in ALLOWED_LIVE_SMOKE_ARTIFACTS:
        raise ArtifactWriteBlocked("artifact write failure")
    return resolved


def write_live_smoke_result(
    run_dir: Path,
    approval: FirstLiveSmokeApproval,
    *,
    artifact_name: str = "live_smoke_result.json",
    **result_fields: Any,
) -> Path:
    if "raw_output" in result_fields:
        raise ArtifactWriteBlocked("unmasked raw provider output found")
    if result_fields.get("raw_output_saved") is True:
        raise ArtifactWriteBlocked("raw_output_saved=True detected")
    payload = build_live_smoke_result(approval=approval, **result_fields)
    _validate_live_smoke_result_payload(payload)
    return _write_json(run_dir, artifact_name, payload)


def write_artifact_safety_report(
    run_dir: Path,
    scan_result: ArtifactSafetyResult | None,
    *,
    artifact_name: str = "artifact_safety_report.json",
    scanned_artifacts: tuple[str, ...] = (),
) -> Path:
    safe_scanned = tuple(_safe_run_relative_path(path) for path in scanned_artifacts)
    payload = build_artifact_safety_report(scan_result, scanned_artifacts=safe_scanned)
    _validate_artifact_safety_report_payload(payload)
    return _write_json(run_dir, artifact_name, payload)


def run_artifact_pre_scan(artifacts: Mapping[str, Any] | None) -> ArtifactSafetyResult:
    return scan_artifacts(artifacts)


def run_artifact_post_scan(run_dir: Path) -> ArtifactSafetyResult:
    artifacts: dict[str, Any] = {}
    for artifact_name in ALLOWED_LIVE_SMOKE_ARTIFACTS:
        artifact_path = run_dir / artifact_name
        if artifact_path.exists():
            artifacts[artifact_name] = artifact_path.read_text(encoding="utf-8")
    if not artifacts:
        return scan_artifacts(None)
    return scan_artifacts(artifacts)


def run_first_live_smoke_disabled_with_artifacts(
    run_dir: Path,
    approval: FirstLiveSmokeApproval,
    *,
    pre_scan_inputs: Mapping[str, Any] | None,
) -> DisabledLiveSmokeArtifactRunResult:
    run_dir.mkdir(parents=True, exist_ok=True)
    pre_scan = run_artifact_pre_scan(pre_scan_inputs)
    artifact_safety_status = "pass" if pre_scan.ok else "fail"
    failure_type = "SECURITY_BLOCKED"
    error = "first live smoke execution is disabled in P3J skeleton"

    result_path = write_live_smoke_result(
        run_dir,
        approval,
        status="disabled",
        failure_type=failure_type,
        error=error,
        model_call_count=0,
        retry_count=0,
        reserve_used=False,
        raw_output_saved=False,
        masked_raw_output=None,
        artifact_safety_status=artifact_safety_status,
    )
    write_ceo_report_skeleton(run_dir, failure_type=failure_type, error=error)
    write_run_log_event(
        run_dir,
        {
            "event_type": "LIVE_SMOKE_DISABLED",
            "status": "blocked",
            "failure_type": failure_type,
            "error": error,
            "artifact_path": result_path.name,
            "key_slot": _safe_key_slot(approval),
            "model": approval.model,
            "input_tokens": None,
            "output_tokens": None,
            "parent_event_id": None,
        },
    )
    post_scan = run_artifact_post_scan(run_dir)
    safety_report_path = write_artifact_safety_report(
        run_dir,
        post_scan,
        scanned_artifacts=("run_log.jsonl", "ceo_report.md", "live_smoke_result.json", "artifact_safety_report.json"),
    )

    written = tuple(sorted(path.name for path in run_dir.iterdir() if path.is_file()))
    return DisabledLiveSmokeArtifactRunResult(
        status="disabled",
        failure_type=failure_type,
        error=error,
        run_dir=run_dir,
        written_artifacts=written,
        pre_scan_status="pass" if pre_scan.ok else "fail",
        post_scan_status="pass" if post_scan.ok else "fail",
    )


def write_ceo_report_skeleton(run_dir: Path, *, failure_type: str, error: str) -> Path:
    _validate_failure_type(failure_type)
    content = f"# CEO Report\n\nstatus: disabled\nfailure_type: {failure_type}\nerror: {error}\n"
    path = resolve_live_smoke_artifact_path(run_dir, "ceo_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_run_log_event(run_dir: Path, event: Mapping[str, Any]) -> Path:
    path = resolve_live_smoke_artifact_path(run_dir, "run_log.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True, ensure_ascii=True) + "\n")
    return path


def _validate_live_smoke_result_payload(payload: Mapping[str, Any]) -> None:
    if "raw_output" in payload or "raw_key" in payload:
        raise ArtifactWriteBlocked("raw key found")
    if payload.get("raw_output_saved") is not False:
        raise ArtifactWriteBlocked("raw_output_saved=True detected")
    if payload.get("reserve_used") is not False:
        raise ArtifactWriteBlocked("reserve attempted")
    if payload.get("retry_count") != 0:
        raise ArtifactWriteBlocked("retry attempted")
    if payload.get("model_call_count") != 0:
        raise ArtifactWriteBlocked("second model call attempted")
    if payload.get("status") not in SAFE_LIVE_SMOKE_STATUSES:
        raise ArtifactWriteBlocked("live call attempted without all gates")
    if payload.get("artifact_safety_status") not in SAFE_ARTIFACT_SAFETY_STATUSES:
        raise ArtifactWriteBlocked("artifact safety scan missing")
    failure_type = payload.get("failure_type")
    if failure_type is not None:
        _validate_failure_type(str(failure_type))
    for field in ("provider", "model", "key_slot"):
        value = payload.get(field)
        if isinstance(value, str) and _has_unsafe_public_value(value):
            raise ArtifactWriteBlocked("raw key found")


def _validate_artifact_safety_report_payload(payload: Mapping[str, Any]) -> None:
    if payload.get("status") not in {"pass", "fail", "missing"}:
        raise ArtifactWriteBlocked("artifact safety scan missing")
    failure_type = payload.get("failure_type")
    if payload["status"] == "fail" and failure_type != "SECURITY_BLOCKED":
        raise ArtifactWriteBlocked("artifact safety scan failed")
    if payload["status"] == "missing" and failure_type != "CONFIG_ERROR":
        raise ArtifactWriteBlocked("artifact safety scan missing")
    for finding in payload.get("findings", ()):
        if isinstance(finding, Mapping):
            message = str(finding.get("message", ""))
            if _has_unsafe_public_value(message):
                raise ArtifactWriteBlocked("raw key found")


def _write_json(run_dir: Path, artifact_name: str, payload: Mapping[str, Any]) -> Path:
    path = resolve_live_smoke_artifact_path(run_dir, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ArtifactWriteBlocked("artifact write failure") from exc
    return path


def _safe_run_relative_path(path: str) -> str:
    requested = Path(path)
    if requested.is_absolute() or ".." in requested.parts:
        raise ArtifactWriteBlocked("artifact path outside run_dir")
    if requested.name in FORBIDDEN_LIVE_SMOKE_ARTIFACTS:
        raise ArtifactWriteBlocked("forbidden artifact attempted")
    return requested.as_posix()


def _validate_failure_type(failure_type: str) -> None:
    if failure_type not in CANONICAL_FAILURE_TYPES:
        raise ArtifactWriteBlocked("unknown failure_type")


def _has_unsafe_public_value(value: str) -> bool:
    return "://" in value or bool(re.search(r"sk-[A-Za-z0-9_-]{10,}", value))


def _safe_key_slot(approval: FirstLiveSmokeApproval) -> str | None:
    if isinstance(approval.key_slot, str):
        return approval.key_slot
    if isinstance(approval.key_slot, (list, tuple)) and len(approval.key_slot) == 1:
        return approval.key_slot[0]
    return None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
