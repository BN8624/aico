# P3W controlled single-call live smoke 경계를 실행하고 안전 산출물을 작성한다.
from __future__ import annotations

import hashlib
import importlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact_safety import ArtifactSafetyFinding, ArtifactSafetyResult, scan_artifacts, scan_value_for_unsafe_content
from .key_registry import KEY_SLOT_ENV_VARS
from .provider_allowlist import KNOWN_PROVIDER_CANDIDATES, validate_provider_name
from .provider_base import contains_secret, mask_secrets

P3W_SCHEMA_VERSION = "p3w_controlled_single_call_live_smoke_v1"
P3W_PHASE = "P3W"
P3W_CREATED_FOR = "controlled_single_call_live_smoke"
P3W_CONFIRM_PHRASE = "controlled-single-call"
P3W_TOY_MISSION = 'Return exactly one short sentence saying: "AICO live smoke boundary check passed."'
P3W_EXPECTED_PHRASE = "AICO live smoke boundary check passed."
P3W_ALLOWED_PROVIDER = "google_gemini"
P3W_MAX_PREVIEW_CHARS = 80
P3W_ARTIFACT_NAMES = frozenset(
    {
        "call_attempt_summary.json",
        "live_smoke_result.json",
        "artifact_safety_report.json",
        "final_live_gate_result.json",
    }
)
P3W_ALLOWED_RESULT_STATUSES = frozenset(
    {"single_call_completed", "single_call_failed_safely", "blocked", "config_error", "security_blocked"}
)
P3W_FORBIDDEN_RESULT_STATUSES = frozenset(
    {
        "live_success",
        "provider_success",
        "api_success",
        "unbounded_success",
        "multi_call_completed",
        "retry_success",
        "fallback_success",
        "reserve_success",
    }
)
P3W_FAILURE_PRIORITY = (
    "SECURITY_BLOCKED",
    "BUDGET_EXCEEDED",
    "REPORT_ERROR",
    "CONFIG_ERROR",
    "HUMAN_DECISION_REQUIRED",
    "MODEL_ERROR",
    "SCHEMA_ERROR",
    "WORKER_BAD_OUTPUT",
)


class P3WLiveSmokeError(RuntimeError):
    def __init__(self, condition: str, failure_type: str) -> None:
        self.condition = condition
        self.failure_type = failure_type
        super().__init__(condition)


@dataclass(frozen=True)
class P3WLiveSmokeConfig:
    schema_version: str
    phase: str
    run_id: str
    provider: str
    model: str
    key_slot: str
    mission: str
    max_model_calls: int
    model_call_count_before: int
    call_model_count_before: int
    retry_allowed: bool
    reserve_allowed: bool
    fallback_allowed: bool
    second_call_allowed: bool
    worker_count: int
    worker_file_write_allowed: bool
    worker_shell_allowed: bool
    web_allowed: bool
    repo_clone_allowed: bool
    github_allowed: bool
    parallel_allowed: bool
    raw_output_persistence_allowed: bool
    confirm_phrase_hash_or_marker: str
    created_for: str
    live_smoke_opt_in: bool

    def to_summary(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class LoadedP3WKey:
    key_slot: str
    key_value: str
    key_fingerprint_masked: str


@dataclass(frozen=True)
class P3WLiveSmokeRunResult:
    run_id: str
    run_dir: Path
    status: str
    failure_type: str | None
    errors: tuple[str, ...]
    actual_provider_call_count: int
    call_model_count_before: int
    call_model_count_after: int
    model_call_count_before: int
    model_call_count_after: int
    retry_count: int
    reserve_used: bool
    fallback_used: bool
    second_call_attempted: bool
    raw_output_saved: bool
    masked_summary_saved: bool
    key_fingerprint_masked: str | None
    written_artifacts: tuple[str, ...]
    artifact_safety_scan: str

    def to_summary(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "status": self.status,
            "failure_type": self.failure_type,
            "errors": list(self.errors),
            "actual_provider_call_count": self.actual_provider_call_count,
            "call_model_count_before": self.call_model_count_before,
            "call_model_count_after": self.call_model_count_after,
            "model_call_count_before": self.model_call_count_before,
            "model_call_count_after": self.model_call_count_after,
            "retry_count": self.retry_count,
            "reserve_used": self.reserve_used,
            "fallback_used": self.fallback_used,
            "second_call_attempted": self.second_call_attempted,
            "raw_output_saved": self.raw_output_saved,
            "masked_summary_saved": self.masked_summary_saved,
            "key_fingerprint_masked": self.key_fingerprint_masked,
            "written_artifacts": list(self.written_artifacts),
            "artifact_safety_scan": self.artifact_safety_scan,
        }


ProviderCaller = Callable[[str, str, str], str]


def p3w_default_runtime_creation_enabled() -> bool:
    return False


def build_p3w_live_smoke_config(
    *,
    env: Mapping[str, str] | None = None,
    run_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    key_slot: str | None = None,
    confirm_phrase: str | None = None,
    live_smoke_opt_in: bool | None = None,
    mission: str = P3W_TOY_MISSION,
    **overrides: Any,
) -> P3WLiveSmokeConfig:
    source = env if env is not None else os.environ
    opt_in = source.get("AICO_P3W_LIVE_SMOKE") == "1" if live_smoke_opt_in is None else live_smoke_opt_in
    provider_value = provider if provider is not None else source.get("AICO_P3W_PROVIDER", "")
    model_value = model if model is not None else source.get("AICO_P3W_MODEL", "")
    key_slot_value = key_slot if key_slot is not None else source.get("AICO_P3W_KEY_SLOT", "")
    confirm_value = confirm_phrase if confirm_phrase is not None else source.get("AICO_P3W_CONFIRM", "")
    data = {
        "schema_version": P3W_SCHEMA_VERSION,
        "phase": P3W_PHASE,
        "run_id": run_id or _default_run_id(),
        "provider": provider_value,
        "model": model_value,
        "key_slot": key_slot_value,
        "mission": mission,
        "max_model_calls": 1,
        "model_call_count_before": 0,
        "call_model_count_before": 0,
        "retry_allowed": False,
        "reserve_allowed": False,
        "fallback_allowed": False,
        "second_call_allowed": False,
        "worker_count": 1,
        "worker_file_write_allowed": False,
        "worker_shell_allowed": False,
        "web_allowed": False,
        "repo_clone_allowed": False,
        "github_allowed": False,
        "parallel_allowed": False,
        "raw_output_persistence_allowed": False,
        "confirm_phrase_hash_or_marker": _confirm_marker(confirm_value),
        "created_for": P3W_CREATED_FOR,
        "live_smoke_opt_in": opt_in,
    }
    data.update(overrides)
    config = P3WLiveSmokeConfig(**data)
    return config


def validate_p3w_live_smoke_config(config: P3WLiveSmokeConfig | Mapping[str, object]) -> None:
    payload = config.to_summary() if isinstance(config, P3WLiveSmokeConfig) else dict(config)
    if payload.get("schema_version") != P3W_SCHEMA_VERSION or payload.get("phase") != P3W_PHASE:
        raise P3WLiveSmokeError("invalid P3W schema", "CONFIG_ERROR")
    if payload.get("created_for") != P3W_CREATED_FOR:
        raise P3WLiveSmokeError("invalid P3W created_for", "CONFIG_ERROR")
    if payload.get("live_smoke_opt_in") is not True:
        raise P3WLiveSmokeError("human opt-in missing", "HUMAN_DECISION_REQUIRED")
    if payload.get("confirm_phrase_hash_or_marker") != _confirm_marker(P3W_CONFIRM_PHRASE):
        raise P3WLiveSmokeError("bad confirm phrase", "HUMAN_DECISION_REQUIRED")
    validate_provider_model_key_slot_selection(payload)
    validate_toy_live_smoke_mission(str(payload.get("mission", "")))
    _require_value(payload, "max_model_calls", 1, "max_model_calls exceeded", "BUDGET_EXCEEDED")
    _require_value(payload, "model_call_count_before", 0, "model_call_count > 0 before P3W", "SECURITY_BLOCKED")
    _require_value(payload, "call_model_count_before", 0, "call_model_count > 0 before P3W", "SECURITY_BLOCKED")
    _require_value(payload, "worker_count", 1, "worker orchestration attempt", "SECURITY_BLOCKED")
    for field in (
        "retry_allowed",
        "reserve_allowed",
        "fallback_allowed",
        "second_call_allowed",
        "worker_file_write_allowed",
        "worker_shell_allowed",
        "web_allowed",
        "repo_clone_allowed",
        "github_allowed",
        "parallel_allowed",
        "raw_output_persistence_allowed",
    ):
        _require_value(payload, field, False, f"{field} true", "SECURITY_BLOCKED")


def validate_provider_model_key_slot_selection(payload: Mapping[str, object]) -> None:
    provider = _single_text(payload.get("provider"), "provider", "CONFIG_ERROR")
    model = _single_text(payload.get("model"), "model", "CONFIG_ERROR")
    key_slot = _single_text(payload.get("key_slot"), "key_slot", "SECURITY_BLOCKED")
    if _unsafe_public_text(provider):
        raise P3WLiveSmokeError("arbitrary endpoint URL", "SECURITY_BLOCKED")
    if _unsafe_public_text(model):
        raise P3WLiveSmokeError("model contains unsafe value", "SECURITY_BLOCKED")
    validate_provider_name(provider)
    if provider != P3W_ALLOWED_PROVIDER or provider not in KNOWN_PROVIDER_CANDIDATES:
        raise P3WLiveSmokeError("unknown provider requested", "SECURITY_BLOCKED")
    if key_slot not in KEY_SLOT_ENV_VARS:
        raise P3WLiveSmokeError("unknown key_slot", "SECURITY_BLOCKED")
    if key_slot == "reserve_1":
        raise P3WLiveSmokeError("reserve key requested", "SECURITY_BLOCKED")
    if payload.get("fallback_provider"):
        raise P3WLiveSmokeError("fallback provider requested", "SECURITY_BLOCKED")
    if payload.get("provider_rotation_allowed") is True:
        raise P3WLiveSmokeError("provider rotation requested", "SECURITY_BLOCKED")
    if payload.get("key_rotation_allowed") is True:
        raise P3WLiveSmokeError("key rotation requested", "SECURITY_BLOCKED")


def validate_toy_live_smoke_mission(mission: str) -> None:
    forbidden = (
        "file",
        "attach",
        "web",
        "http",
        "tool",
        "function",
        "edit",
        "shell",
        "repo",
        "secret",
        "env",
        "key",
        "long",
    )
    lowered = mission.lower()
    if any(token in lowered for token in forbidden):
        raise P3WLiveSmokeError("unsafe toy mission", "SECURITY_BLOCKED")
    if mission != P3W_TOY_MISSION:
        raise P3WLiveSmokeError("toy mission mismatch", "CONFIG_ERROR")
    if len(mission) > 120:
        raise P3WLiveSmokeError("toy mission too long", "SECURITY_BLOCKED")


def read_single_p3w_key_value(
    key_slot: str | list[str] | tuple[str, ...],
    *,
    env: Mapping[str, str] | None = None,
) -> LoadedP3WKey:
    slot = _single_text(key_slot, "key_slot", "SECURITY_BLOCKED")
    if slot == "reserve_1":
        raise P3WLiveSmokeError("reserve key read attempt", "SECURITY_BLOCKED")
    if slot not in KEY_SLOT_ENV_VARS:
        raise P3WLiveSmokeError("unknown key_slot", "SECURITY_BLOCKED")
    source = env if env is not None else os.environ
    key_value = source.get(KEY_SLOT_ENV_VARS[slot])
    if not key_value:
        raise P3WLiveSmokeError("missing key", "CONFIG_ERROR")
    if "\n" in key_value or "\r" in key_value:
        raise P3WLiveSmokeError("invalid key value shape", "SECURITY_BLOCKED")
    return LoadedP3WKey(slot, key_value, _masked_key_fingerprint(key_value))


def import_selected_provider_sdk(provider: str) -> Any:
    if provider != P3W_ALLOWED_PROVIDER:
        raise P3WLiveSmokeError("arbitrary SDK import", "SECURITY_BLOCKED")
    try:
        return importlib.import_module("google.genai")
    except ImportError as exc:
        raise P3WLiveSmokeError("SDK import failure", "CONFIG_ERROR") from exc


def call_selected_provider_once(*, provider: str, model: str, key_value: str, mission: str) -> str:
    if provider != P3W_ALLOWED_PROVIDER:
        raise P3WLiveSmokeError("unknown provider requested", "SECURITY_BLOCKED")
    genai = import_selected_provider_sdk(provider)
    client = genai.Client(api_key=key_value)
    response = client.models.generate_content(model=model, contents=mission)
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise P3WLiveSmokeError("provider returned invalid response shape", "SCHEMA_ERROR")
    return text


def run_controlled_single_call_live_smoke(
    *,
    config: P3WLiveSmokeConfig | None = None,
    env: Mapping[str, str] | None = None,
    run_dir: Path | None = None,
    provider_caller: ProviderCaller | None = None,
) -> P3WLiveSmokeRunResult:
    config = config or build_p3w_live_smoke_config(env=env)
    run_root = run_dir or Path("runs") / f"p3w_{config.run_id}"
    run_root.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    failure_type: str | None = None
    status = "blocked"
    key: LoadedP3WKey | None = None
    raw_output: str | None = None
    call_model_count_after = 0
    model_call_count_after = 0
    actual_provider_call_count = 0

    pre_scan = run_p3w_pre_call_scan(config)
    if not pre_scan.ok:
        failure_type = pre_scan.failure_type or "SECURITY_BLOCKED"
        errors = [finding.reason for finding in pre_scan.findings]
    else:
        try:
            validate_p3w_live_smoke_config(config)
            key = read_single_p3w_key_value(config.key_slot, env=env)
            caller = provider_caller or (
                lambda key_value, model, mission: call_selected_provider_once(
                    provider=config.provider,
                    model=model,
                    key_value=key_value,
                    mission=mission,
                )
            )
            actual_provider_call_count = 1
            call_model_count_after = 1
            model_call_count_after = 1
            raw_output = caller(key.key_value, config.model, config.mission)
            status = "single_call_completed"
        except P3WLiveSmokeError as exc:
            failure_type = exc.failure_type
            errors = [exc.condition]
            status = _status_for_failure(exc.failure_type, attempted=actual_provider_call_count > 0)
        except Exception as exc:  # provider SDK exceptions must not leak raw response or key data.
            failure_type = "MODEL_ERROR" if actual_provider_call_count else "CONFIG_ERROR"
            errors = [mask_secrets(str(exc))[:120] or "provider call failed"]
            status = _status_for_failure(failure_type, attempted=actual_provider_call_count > 0)

    masked_summary = build_masked_output_summary(raw_output)
    call_attempt_summary = build_call_attempt_summary(
        config=config,
        key_fingerprint_masked=key.key_fingerprint_masked if key else None,
        call_model_count_after=call_model_count_after,
        model_call_count_after=model_call_count_after,
        failure_type=failure_type,
        errors=tuple(errors),
    )
    live_smoke_result = build_live_smoke_result(
        config=config,
        status=status,
        call_model_count=call_model_count_after,
        model_call_count=model_call_count_after,
        failure_type=failure_type,
        errors=tuple(errors),
        masked_output_summary=masked_summary,
    )
    final_gate_result = build_final_live_gate_result_linkage(config, live_smoke_result, call_attempt_summary)
    post_scan = scan_p3w_artifacts(
        {
            "call_attempt_summary.json": call_attempt_summary,
            "live_smoke_result.json": live_smoke_result,
            "final_live_gate_result.json": final_gate_result,
        }
    )
    if not post_scan.ok and failure_type != "SECURITY_BLOCKED":
        failure_type = post_scan.failure_type or "SECURITY_BLOCKED"
        status = "security_blocked"
        errors = [finding.reason for finding in post_scan.findings]
        call_attempt_summary["failure_type"] = failure_type
        call_attempt_summary["errors"] = errors
        live_smoke_result["status"] = status
        live_smoke_result["failure_type"] = failure_type
        live_smoke_result["errors"] = errors
        final_gate_result["failure_type"] = failure_type
        final_gate_result["errors"] = errors
        post_scan = scan_p3w_artifacts(
            {
                "call_attempt_summary.json": call_attempt_summary,
                "live_smoke_result.json": live_smoke_result,
                "final_live_gate_result.json": final_gate_result,
            }
        )

    safety_report = build_artifact_safety_report(post_scan)
    paths = (
        write_call_attempt_summary(run_root, call_attempt_summary),
        write_live_smoke_result(run_root, live_smoke_result),
        write_final_live_gate_result(run_root, final_gate_result),
        write_artifact_safety_report(run_root, safety_report),
    )
    written = tuple(path.name for path in paths)
    return P3WLiveSmokeRunResult(
        run_id=config.run_id,
        run_dir=run_root,
        status=status,
        failure_type=failure_type,
        errors=tuple(errors),
        actual_provider_call_count=actual_provider_call_count,
        call_model_count_before=config.call_model_count_before,
        call_model_count_after=call_model_count_after,
        model_call_count_before=config.model_call_count_before,
        model_call_count_after=model_call_count_after,
        retry_count=0,
        reserve_used=False,
        fallback_used=False,
        second_call_attempted=False,
        raw_output_saved=False,
        masked_summary_saved=masked_summary["output_present"] is True,
        key_fingerprint_masked=key.key_fingerprint_masked if key else None,
        written_artifacts=written,
        artifact_safety_scan=safety_report["status"],
    )


def build_toy_live_smoke_mission() -> str:
    return P3W_TOY_MISSION


def build_masked_output_summary(raw_output: str | None) -> dict[str, object]:
    if raw_output is None:
        return {
            "output_present": False,
            "output_length": 0,
            "output_preview_masked": "",
            "contains_expected_phrase": False,
            "secret_scan_passed": True,
            "raw_output_saved": False,
        }
    preview = mask_secrets(raw_output[:P3W_MAX_PREVIEW_CHARS]).replace("\n", " ")
    if contains_secret(preview) or scan_value_for_unsafe_content(preview):
        preview = "[MASKED_OUTPUT]"
    return {
        "output_present": True,
        "output_length": len(raw_output),
        "output_preview_masked": preview,
        "contains_expected_phrase": P3W_EXPECTED_PHRASE in raw_output,
        "secret_scan_passed": not contains_secret(preview),
        "raw_output_saved": False,
    }


def build_call_attempt_summary(
    *,
    config: P3WLiveSmokeConfig,
    key_fingerprint_masked: str | None,
    call_model_count_after: int,
    model_call_count_after: int,
    failure_type: str | None,
    errors: tuple[str, ...] = (),
) -> dict[str, object]:
    payload = {
        "schema_version": P3W_SCHEMA_VERSION,
        "phase": P3W_PHASE,
        "run_id": config.run_id,
        "provider": config.provider,
        "model": config.model,
        "key_slot_ref": config.key_slot,
        "key_fingerprint_masked": key_fingerprint_masked,
        "call_model_count_before": config.call_model_count_before,
        "call_model_count_after": call_model_count_after,
        "model_call_count_before": config.model_call_count_before,
        "model_call_count_after": model_call_count_after,
        "max_model_calls": config.max_model_calls,
        "retry_count": 0,
        "reserve_used": False,
        "fallback_used": False,
        "second_call_attempted": False,
        "worker_count": config.worker_count,
        "worker_file_write_allowed": False,
        "worker_shell_allowed": False,
        "web_allowed": False,
        "repo_clone_allowed": False,
        "github_allowed": False,
        "parallel_allowed": False,
        "raw_output_saved": False,
        "masked_summary_ref": "live_smoke_result.json#masked_output_summary",
        "failure_type": failure_type,
        "errors": list(errors),
        "created_for": P3W_CREATED_FOR,
    }
    validate_call_attempt_summary(payload)
    return payload


def build_live_smoke_result(
    *,
    config: P3WLiveSmokeConfig,
    status: str,
    call_model_count: int,
    model_call_count: int,
    failure_type: str | None,
    errors: tuple[str, ...],
    masked_output_summary: Mapping[str, object],
) -> dict[str, object]:
    payload = {
        "schema_version": P3W_SCHEMA_VERSION,
        "phase": P3W_PHASE,
        "run_id": config.run_id,
        "status": status,
        "provider": config.provider,
        "model": config.model,
        "key_slot_ref": config.key_slot,
        "call_attempt_summary_ref": "call_attempt_summary.json",
        "artifact_safety_report_ref": "artifact_safety_report.json",
        "call_model_count": call_model_count,
        "model_call_count": model_call_count,
        "max_model_calls": config.max_model_calls,
        "retry_count": 0,
        "reserve_used": False,
        "fallback_used": False,
        "second_call_attempted": False,
        "raw_output_saved": False,
        "masked_output_summary": dict(masked_output_summary),
        "toy_mission_result_summary": {
            "mission_kind": "toy_text",
            "contains_expected_phrase": masked_output_summary.get("contains_expected_phrase") is True,
        },
        "failure_type": failure_type,
        "errors": list(errors),
        "created_for": P3W_CREATED_FOR,
    }
    validate_live_smoke_result(payload)
    return payload


def build_final_live_gate_result_linkage(
    config: P3WLiveSmokeConfig,
    live_smoke_result: Mapping[str, object],
    call_attempt_summary: Mapping[str, object],
) -> dict[str, object]:
    payload = {
        "schema_version": "p3w_final_live_gate_linkage_v1",
        "phase": P3W_PHASE,
        "run_id": config.run_id,
        "status": "p3w_single_call_boundary_recorded",
        "provider": config.provider,
        "model": config.model,
        "key_slot_ref": config.key_slot,
        "call_attempt_summary_ref": "call_attempt_summary.json",
        "live_smoke_result_ref": "live_smoke_result.json",
        "artifact_safety_report_ref": "artifact_safety_report.json",
        "call_model_count": live_smoke_result.get("call_model_count"),
        "model_call_count": live_smoke_result.get("model_call_count"),
        "max_model_calls": call_attempt_summary.get("max_model_calls"),
        "retry_count": 0,
        "reserve_used": False,
        "fallback_used": False,
        "second_call_attempted": False,
        "raw_output_saved": False,
        "failure_type": live_smoke_result.get("failure_type"),
        "errors": list(live_smoke_result.get("errors", [])),
        "created_for": P3W_CREATED_FOR,
    }
    scan = scan_p3w_artifacts({"final_live_gate_result.json": payload})
    if not scan.ok:
        raise P3WLiveSmokeError(scan.findings[0].reason, scan.failure_type or "SECURITY_BLOCKED")
    return payload


def build_artifact_safety_report(scan_result: ArtifactSafetyResult) -> dict[str, object]:
    return {
        "schema_version": "p3w_artifact_safety_report_v1",
        "phase": P3W_PHASE,
        "status": "pass" if scan_result.ok else "fail",
        "failure_type": scan_result.failure_type,
        "checks": {
            "raw_key_absent": scan_result.ok,
            "raw_env_value_absent": scan_result.ok,
            "raw_approval_phrase_absent": scan_result.ok,
            "raw_provider_request_absent": scan_result.ok,
            "raw_provider_response_absent": scan_result.ok,
            "raw_output_absent": scan_result.ok,
            "raw_headers_absent": scan_result.ok,
            "token_usage_raw_dump_absent": scan_result.ok,
            "endpoint_url_absent": scan_result.ok,
            "bearer_token_absent": scan_result.ok,
            "private_key_block_absent": scan_result.ok,
            "raw_output_saved_false": scan_result.ok,
            "call_model_count_lte_one": scan_result.ok,
            "model_call_count_lte_one": scan_result.ok,
            "retry_count_zero": scan_result.ok,
            "reserve_used_false": scan_result.ok,
            "fallback_used_false": scan_result.ok,
            "second_call_attempted_false": scan_result.ok,
        },
        "findings": [
            {
                "artifact_path": finding.artifact_path,
                "failure_type": finding.failure_type,
                "message": mask_secrets(finding.reason),
            }
            for finding in scan_result.findings
        ],
        "summary": "P3W artifact safety scan passed" if scan_result.ok else "P3W artifact safety scan failed",
        "created_for": P3W_CREATED_FOR,
    }


def validate_call_attempt_summary(payload: Mapping[str, object]) -> None:
    _validate_common_artifact(payload)
    if payload.get("call_model_count_before") != 0 or payload.get("model_call_count_before") != 0:
        raise P3WLiveSmokeError("call count before must be zero", "SECURITY_BLOCKED")
    _validate_counts(payload)


def validate_live_smoke_result(payload: Mapping[str, object]) -> None:
    _validate_common_artifact(payload)
    status = str(payload.get("status"))
    if status in P3W_FORBIDDEN_RESULT_STATUSES or status not in P3W_ALLOWED_RESULT_STATUSES:
        raise P3WLiveSmokeError("forbidden P3W status", "SECURITY_BLOCKED")
    _validate_counts(payload)


def run_p3w_pre_call_scan(config: P3WLiveSmokeConfig) -> ArtifactSafetyResult:
    try:
        validate_toy_live_smoke_mission(config.mission)
    except P3WLiveSmokeError as exc:
        return ArtifactSafetyResult(False, exc.failure_type, (ArtifactSafetyFinding("toy_mission", exc.failure_type, exc.condition),))
    artifacts = {
        "live_smoke_config": {
            "phase": config.phase,
            "run_id": config.run_id,
            "provider": config.provider,
            "model": config.model,
            "key_slot": config.key_slot,
            "mission": config.mission,
            "max_model_calls": config.max_model_calls,
            "model_call_count_before": config.model_call_count_before,
            "call_model_count_before": config.call_model_count_before,
            "retry_allowed": config.retry_allowed,
            "reserve_allowed": config.reserve_allowed,
            "fallback_allowed": config.fallback_allowed,
            "second_call_allowed": config.second_call_allowed,
            "raw_output_persistence_allowed": config.raw_output_persistence_allowed,
            "created_for": config.created_for,
        }
    }
    return scan_artifacts(artifacts)


def scan_p3w_artifacts(artifacts: Mapping[str, Any] | None) -> ArtifactSafetyResult:
    if artifacts is None:
        return ArtifactSafetyResult(False, "CONFIG_ERROR", (ArtifactSafetyFinding("<scan>", "CONFIG_ERROR", "artifact safety scan missing"),))
    findings: list[ArtifactSafetyFinding] = []
    for artifact_name, payload in artifacts.items():
        findings.extend(_scan_p3w_value(artifact_name, payload))
    if findings:
        failure_type = _aggregate_failure_type(findings)
        return ArtifactSafetyResult(False, failure_type, tuple(findings))
    return ArtifactSafetyResult(True, None, ())


def write_call_attempt_summary(run_dir: Path, payload: Mapping[str, object]) -> Path:
    validate_call_attempt_summary(payload)
    return _write_p3w_json(run_dir, "call_attempt_summary.json", payload)


def write_live_smoke_result(run_dir: Path, payload: Mapping[str, object]) -> Path:
    validate_live_smoke_result(payload)
    return _write_p3w_json(run_dir, "live_smoke_result.json", payload)


def write_final_live_gate_result(run_dir: Path, payload: Mapping[str, object]) -> Path:
    scan = scan_p3w_artifacts({"final_live_gate_result.json": payload})
    if not scan.ok:
        raise P3WLiveSmokeError(scan.findings[0].reason, scan.failure_type or "SECURITY_BLOCKED")
    return _write_p3w_json(run_dir, "final_live_gate_result.json", payload)


def write_artifact_safety_report(run_dir: Path, payload: Mapping[str, object]) -> Path:
    if payload.get("status") not in {"pass", "fail"}:
        raise P3WLiveSmokeError("artifact safety scan missing", "CONFIG_ERROR")
    return _write_p3w_json(run_dir, "artifact_safety_report.json", payload)


def main() -> int:
    result = run_controlled_single_call_live_smoke()
    print(json.dumps(result.to_summary(), sort_keys=True, ensure_ascii=True))
    return 0 if result.status in {"single_call_completed", "single_call_failed_safely", "blocked", "config_error"} else 1


def _write_p3w_json(run_dir: Path, artifact_name: str, payload: Mapping[str, object]) -> Path:
    path = _resolve_p3w_artifact_path(run_dir, artifact_name)
    scan = scan_p3w_artifacts({artifact_name: payload})
    if not scan.ok:
        raise P3WLiveSmokeError(scan.findings[0].reason, scan.failure_type or "SECURITY_BLOCKED")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise P3WLiveSmokeError("artifact write failure", "REPORT_ERROR") from exc
    return path


def _resolve_p3w_artifact_path(run_dir: Path, artifact_name: str) -> Path:
    if artifact_name not in P3W_ARTIFACT_NAMES:
        raise P3WLiveSmokeError("forbidden artifact attempted", "SECURITY_BLOCKED")
    root = run_dir.resolve()
    requested = Path(artifact_name)
    if requested.is_absolute() or ".." in requested.parts:
        raise P3WLiveSmokeError("artifact path outside run_dir", "SECURITY_BLOCKED")
    resolved = (root / requested).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise P3WLiveSmokeError("artifact path outside run_dir", "SECURITY_BLOCKED") from exc
    return resolved


def _validate_common_artifact(payload: Mapping[str, object]) -> None:
    scan = scan_p3w_artifacts({"artifact": payload})
    if not scan.ok:
        raise P3WLiveSmokeError(scan.findings[0].reason, scan.failure_type or "SECURITY_BLOCKED")
    if payload.get("phase") != P3W_PHASE:
        raise P3WLiveSmokeError("invalid P3W artifact phase", "CONFIG_ERROR")
    if payload.get("created_for") != P3W_CREATED_FOR:
        raise P3WLiveSmokeError("invalid P3W artifact purpose", "CONFIG_ERROR")


def _validate_counts(payload: Mapping[str, object]) -> None:
    call_count = _int_value(payload.get("call_model_count_after", payload.get("call_model_count", 0)))
    model_count = _int_value(payload.get("model_call_count_after", payload.get("model_call_count", 0)))
    if call_count > 1:
        raise P3WLiveSmokeError("call_model_count > 1", "SECURITY_BLOCKED")
    if model_count > 1:
        raise P3WLiveSmokeError("model_call_count > 1", "SECURITY_BLOCKED")
    if payload.get("max_model_calls") != 1:
        raise P3WLiveSmokeError("max_model_calls exceeded", "BUDGET_EXCEEDED")
    if payload.get("retry_count") != 0:
        raise P3WLiveSmokeError("retry attempt", "SECURITY_BLOCKED")
    for field in ("reserve_used", "fallback_used", "second_call_attempted", "raw_output_saved"):
        if payload.get(field) is not False:
            raise P3WLiveSmokeError(f"{field} true", "SECURITY_BLOCKED")


def _scan_p3w_value(path: str, value: Any) -> list[ArtifactSafetyFinding]:
    findings: list[ArtifactSafetyFinding] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in {
                "raw_key",
                "raw_key_value",
                "key_value",
                "env_var_value",
                "raw_approval_phrase",
                "raw_provider_request",
                "raw_provider_response",
                "raw_output",
                "raw_headers",
                "provider_response",
                "token_usage",
            }:
                findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", f"{key_text} field found"))
            findings.extend(_scan_p3w_value(f"{path}.{key_text}", item))
        if value.get("raw_output_saved") is True:
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "raw_output_saved=true"))
        if _int_value(value.get("call_model_count_after", value.get("call_model_count", 0))) > 1:
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "call_model_count>1"))
        if _int_value(value.get("model_call_count_after", value.get("model_call_count", 0))) > 1:
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "model_call_count>1"))
        if _int_value(value.get("retry_count", 0)) > 0:
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "retry_count>0"))
        for field in ("reserve_used", "fallback_used", "second_call_attempted"):
            if value.get(field) is True:
                findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", f"{field}=true"))
        status = value.get("status")
        if isinstance(status, str) and status in P3W_FORBIDDEN_RESULT_STATUSES:
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "forbidden success-like status"))
        return findings
    if isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            findings.extend(_scan_p3w_value(f"{path}[{index}]", item))
        return findings
    if isinstance(value, str):
        if contains_secret(value) or scan_value_for_unsafe_content(value):
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "raw secret-like value found"))
        if "://" in value or "googleapis.com" in value:
            findings.append(ArtifactSafetyFinding(path, "SECURITY_BLOCKED", "endpoint URL found"))
    return findings


def _single_text(value: object, field_name: str, failure_type: str) -> str:
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise P3WLiveSmokeError(f"multiple {field_name}s requested", failure_type)
        value = value[0]
    if not isinstance(value, str) or not value.strip():
        raise P3WLiveSmokeError(f"missing {field_name}", "CONFIG_ERROR")
    text = value.strip()
    if "," in text or ";" in text:
        raise P3WLiveSmokeError(f"multiple {field_name}s requested", failure_type)
    return text


def _unsafe_public_text(value: str) -> bool:
    return "://" in value or "googleapis.com" in value or contains_secret(value)


def _require_value(payload: Mapping[str, object], field: str, expected: object, condition: str, failure_type: str) -> None:
    if payload.get(field) != expected:
        raise P3WLiveSmokeError(condition, failure_type)


def _confirm_marker(confirm_phrase: str | None) -> str:
    if confirm_phrase != P3W_CONFIRM_PHRASE:
        return "not-confirmed"
    digest = hashlib.sha256(confirm_phrase.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def _masked_key_fingerprint(key_value: str) -> str:
    digest = hashlib.sha256(key_value.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:8]}...{digest[-4:]}"


def _status_for_failure(failure_type: str, *, attempted: bool) -> str:
    if failure_type == "SECURITY_BLOCKED":
        return "security_blocked"
    if failure_type == "CONFIG_ERROR":
        return "single_call_failed_safely" if attempted else "config_error"
    return "single_call_failed_safely" if attempted else "blocked"


def _aggregate_failure_type(findings: list[ArtifactSafetyFinding]) -> str:
    priorities = {failure_type: index for index, failure_type in enumerate(P3W_FAILURE_PRIORITY)}
    return min((finding.failure_type for finding in findings), key=lambda item: priorities.get(item, 999))


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
