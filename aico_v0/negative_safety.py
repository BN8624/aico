# P3X bad-input 차단 행렬과 P3W 산출물 회귀 검증을 제공한다.
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .artifact_safety import scan_value_for_unsafe_content
from .controlled_live_smoke import (
    P3W_CONFIRM_PHRASE,
    P3W_CREATED_FOR,
    P3W_EXPECTED_PHRASE,
    P3W_PHASE,
    P3WLiveSmokeError,
    build_p3w_live_smoke_config,
    scan_p3w_artifacts,
    validate_p3w_live_smoke_config,
    validate_toy_live_smoke_mission,
)
from .provider_base import contains_secret

P3X_RESULT = "negative_safety_tests_bad_input_blocking_proof"
P3X_ALLOWED_ACTUAL_PROVIDER_CALL_COUNT = 1
P3X_ALLOWED_MODEL = "gemma-4-31b-it"
P3X_ALLOWED_PROVIDER = "google_gemini"
P3X_ALLOWED_KEY_SLOT = "worker_1"
P3X_MAX_MASKED_PREVIEW_CHARS = 80

P3X_FORBIDDEN_TRUE_FIELDS = {
    "allowlist_widening_allowed": "allowlist widening requested",
    "retry_allowed": "retry attempt",
    "reserve_allowed": "reserve attempt",
    "reserve_used": "reserve attempt",
    "fallback_allowed": "fallback attempt",
    "fallback_used": "fallback attempt",
    "second_call_allowed": "second call attempt",
    "second_call_attempted": "second call attempt",
    "raw_output_saved": "raw output persistence requested",
    "worker_orchestration": "worker orchestration attempt",
    "worker_pool_dispatch": "worker pool dispatch attempt",
    "manager_full_run": "manager full run attempt",
    "auditor_full_run": "auditor full run attempt",
    "worker_file_write_allowed": "worker file write attempt",
    "worker_shell_allowed": "worker shell attempt",
    "shell_allowed": "shell attempt",
    "web_allowed": "web attempt",
    "repo_clone_allowed": "repo clone attempt",
    "github_allowed": "GitHub attempt",
    "parallel_allowed": "parallel execution attempt",
    "external_write_scope": "external write scope attempt",
    "auto_pr_allowed": "auto PR attempt",
    "auto_merge_allowed": "auto merge attempt",
    "tool_call_allowed": "tool call attempt",
    "function_call_allowed": "function call attempt",
    "file_upload_allowed": "file upload attempt",
    "vector_store_allowed": "vector store attempt",
    "assistant_thread_allowed": "assistant thread attempt",
    "batch_job_allowed": "batch job attempt",
    "long_running_job_allowed": "long-running job attempt",
    "streaming_multi_call_allowed": "streaming multi-call attempt",
}

P3X_FORBIDDEN_ARTIFACT_FIELDS = {
    "raw_key",
    "raw_key_value",
    "key_value",
    "env_var_value",
    "raw_approval_phrase",
    "raw_provider_request",
    "raw_provider_response",
    "provider_response",
    "provider_config",
    "raw_output",
    "raw_model_output",
    "raw_response_body",
    "raw_headers",
    "token_usage",
}


def build_p3x_safe_config(**overrides: Any) -> dict[str, object]:
    config = build_p3w_live_smoke_config(
        provider=P3X_ALLOWED_PROVIDER,
        model=P3X_ALLOWED_MODEL,
        key_slot=P3X_ALLOWED_KEY_SLOT,
        confirm_phrase=P3W_CONFIRM_PHRASE,
        live_smoke_opt_in=True,
        run_id="p3x-negative-test",
    ).to_summary()
    config.update(overrides)
    return config


def validate_p3x_negative_config(payload: Mapping[str, object]) -> None:
    data = dict(payload)
    _block_unsafe_values(data)
    if data.get("live_smoke_opt_in") is not True:
        raise P3WLiveSmokeError("human opt-in missing", "HUMAN_DECISION_REQUIRED")
    validate_p3w_live_smoke_config(data)
    _validate_p3x_extra_policy_fields(data)


def validate_p3x_bad_artifact(payload: Mapping[str, object]) -> None:
    _block_unsafe_values(payload)
    scan = scan_p3w_artifacts({"p3x_bad_artifact": payload})
    if not scan.ok:
        raise P3WLiveSmokeError(scan.findings[0].reason, scan.failure_type or "SECURITY_BLOCKED")
    _validate_p3x_extra_policy_fields(payload)
    summary = payload.get("masked_output_summary")
    if isinstance(summary, Mapping):
        preview = summary.get("output_preview_masked", "")
        if isinstance(preview, str) and len(preview) > P3X_MAX_MASKED_PREVIEW_CHARS:
            raise P3WLiveSmokeError("masked summary too long", "SECURITY_BLOCKED")
        if contains_secret(preview) or scan_value_for_unsafe_content(preview):
            raise P3WLiveSmokeError("masked summary contains unsafe content", "SECURITY_BLOCKED")


def validate_p3x_toy_mission(mission: str) -> None:
    validate_toy_live_smoke_mission(mission)


def validate_p3x_p3w_artifact_regression(run_dir: Path) -> dict[str, object]:
    call_attempt = _load_json(run_dir / "call_attempt_summary.json")
    live_result = _load_json(run_dir / "live_smoke_result.json")
    safety_report = _load_json(run_dir / "artifact_safety_report.json")
    final_gate = _load_json(run_dir / "final_live_gate_result.json")

    for name, payload in {
        "call_attempt_summary.json": call_attempt,
        "live_smoke_result.json": live_result,
        "artifact_safety_report.json": safety_report,
        "final_live_gate_result.json": final_gate,
    }.items():
        _block_unsafe_values(payload)
        scan = scan_p3w_artifacts({name: payload})
        if not scan.ok:
            raise P3WLiveSmokeError(scan.findings[0].reason, scan.failure_type or "SECURITY_BLOCKED")

    _require(call_attempt.get("phase") == P3W_PHASE, "invalid P3W phase", "CONFIG_ERROR")
    _require(call_attempt.get("created_for") == P3W_CREATED_FOR, "invalid P3W purpose", "CONFIG_ERROR")
    _require(call_attempt.get("provider") == P3X_ALLOWED_PROVIDER, "provider mismatch", "CONFIG_ERROR")
    _require(live_result.get("provider") == P3X_ALLOWED_PROVIDER, "provider mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("model") == P3X_ALLOWED_MODEL, "model mismatch", "CONFIG_ERROR")
    _require(live_result.get("model") == P3X_ALLOWED_MODEL, "model mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("key_slot_ref") == P3X_ALLOWED_KEY_SLOT, "key_slot mismatch", "CONFIG_ERROR")
    _require(live_result.get("key_slot_ref") == P3X_ALLOWED_KEY_SLOT, "key_slot mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("call_model_count_before") == 0, "call count before mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("call_model_count_after") == 1, "call count after mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("model_call_count_before") == 0, "model count before mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("model_call_count_after") == 1, "model count after mismatch", "CONFIG_ERROR")
    _require(live_result.get("call_model_count") == 1, "call count mismatch", "CONFIG_ERROR")
    _require(live_result.get("model_call_count") == 1, "model count mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("max_model_calls") == 1, "max_model_calls mismatch", "CONFIG_ERROR")
    _require(call_attempt.get("retry_count") == 0, "retry count mismatch", "SECURITY_BLOCKED")
    _require(live_result.get("retry_count") == 0, "retry count mismatch", "SECURITY_BLOCKED")
    for field in ("reserve_used", "fallback_used", "second_call_attempted", "raw_output_saved"):
        _require(call_attempt.get(field) is False, f"{field} mismatch", "SECURITY_BLOCKED")
        _require(live_result.get(field) is False, f"{field} mismatch", "SECURITY_BLOCKED")

    masked_summary = live_result.get("masked_output_summary")
    _require(isinstance(masked_summary, Mapping), "masked summary missing", "CONFIG_ERROR")
    _require(masked_summary.get("output_present") is True, "masked summary missing", "CONFIG_ERROR")
    _require(masked_summary.get("contains_expected_phrase") is True, "expected phrase missing", "WORKER_BAD_OUTPUT")
    _require(masked_summary.get("secret_scan_passed") is True, "masked summary unsafe", "SECURITY_BLOCKED")
    _require(masked_summary.get("raw_output_saved") is False, "raw_output_saved mismatch", "SECURITY_BLOCKED")
    _require(P3W_EXPECTED_PHRASE in str(masked_summary.get("output_preview_masked", "")), "masked preview mismatch", "WORKER_BAD_OUTPUT")
    _require(safety_report.get("status") == "pass", "artifact safety scan failed", "SECURITY_BLOCKED")
    _require(final_gate.get("status") == "p3w_single_call_boundary_recorded", "final gate linkage mismatch", "CONFIG_ERROR")

    return {
        "actual_provider_call_count": P3X_ALLOWED_ACTUAL_PROVIDER_CALL_COUNT,
        "call_model_count_before": call_attempt["call_model_count_before"],
        "call_model_count_after": call_attempt["call_model_count_after"],
        "model_call_count_before": call_attempt["model_call_count_before"],
        "model_call_count_after": call_attempt["model_call_count_after"],
        "retry_count": call_attempt["retry_count"],
        "reserve_used": call_attempt["reserve_used"],
        "fallback_used": call_attempt["fallback_used"],
        "second_call_attempted": call_attempt["second_call_attempted"],
        "raw_output_saved": call_attempt["raw_output_saved"],
        "masked_summary_saved": True,
        "artifact_safety_scan": safety_report["status"],
    }


def build_p3x_negative_safety_report(regression: Mapping[str, object]) -> dict[str, object]:
    return {
        "phase": "P3X",
        "result": "passed",
        "scope": P3X_RESULT,
        "actual_live_call_rerun": False,
        "additional_provider_calls": 0,
        "key_value_read": False,
        "env_value_read": False,
        "provider_sdk_import": False,
        "network_call": False,
        "call_model_execution": False,
        "p3w_regression": dict(regression),
        "blocked_categories": {
            "bad_opt_in": True,
            "multiple_selection": True,
            "retry_reserve_fallback_second_call": True,
            "raw_output_persistence": True,
            "raw_secret_injection": True,
            "worker_authority_expansion": True,
            "tool_upload_long_running": True,
            "bad_toy_mission": True,
        },
    }


def _validate_p3x_extra_policy_fields(payload: Mapping[str, object]) -> None:
    for field, reason in P3X_FORBIDDEN_TRUE_FIELDS.items():
        if payload.get(field) is True:
            raise P3WLiveSmokeError(reason, "SECURITY_BLOCKED")
    for count_field in ("retry_count", "actual_provider_call_count"):
        if _int_value(payload.get(count_field)) > 0:
            raise P3WLiveSmokeError(f"{count_field} > 0", "SECURITY_BLOCKED")
    for count_field in ("call_model_count_after", "model_call_count_after", "call_model_count", "model_call_count"):
        if _int_value(payload.get(count_field)) > 1:
            raise P3WLiveSmokeError(f"{count_field} > 1", "SECURITY_BLOCKED")
    if _int_value(payload.get("max_retries_per_call")) > 0:
        raise P3WLiveSmokeError("retry attempt", "SECURITY_BLOCKED")


def _block_unsafe_values(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in P3X_FORBIDDEN_ARTIFACT_FIELDS:
                raise P3WLiveSmokeError(f"{key_text} field found", "SECURITY_BLOCKED")
            _block_unsafe_values(key_text, f"{path}.{key_text}.key")
            _block_unsafe_values(item, f"{path}.{key_text}")
        return
    if isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            _block_unsafe_values(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if contains_secret(value) or scan_value_for_unsafe_content(value) or "AIza" in value:
            raise P3WLiveSmokeError(f"unsafe content found at {path}", "SECURITY_BLOCKED")
        lowered = value.lower()
        if "://" in value or "googleapis.com" in lowered:
            raise P3WLiveSmokeError(f"endpoint URL found at {path}", "SECURITY_BLOCKED")
        if "env dump" in lowered or "provider config" in lowered:
            raise P3WLiveSmokeError(f"unsafe dump marker found at {path}", "SECURITY_BLOCKED")


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise P3WLiveSmokeError(f"missing artifact {path.name}", "CONFIG_ERROR") from exc
    if not isinstance(payload, dict):
        raise P3WLiveSmokeError(f"invalid artifact {path.name}", "CONFIG_ERROR")
    return payload


def _require(condition: bool, reason: str, failure_type: str) -> None:
    if not condition:
        raise P3WLiveSmokeError(reason, failure_type)


def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0
