# P3X bad config가 live boundary 전에 차단되는지 검증한다.
from __future__ import annotations

import pytest

from aico_v0.controlled_live_smoke import P3W_CONFIRM_PHRASE, P3WLiveSmokeError
from aico_v0.negative_safety import build_p3x_safe_config, validate_p3x_negative_config


def assert_blocked(update: dict[str, object], expected_failure: str) -> None:
    payload = build_p3x_safe_config(**update)
    with pytest.raises(P3WLiveSmokeError) as exc_info:
        validate_p3x_negative_config(payload)
    assert exc_info.value.failure_type == expected_failure


def test_missing_opt_in_blocks_with_zero_provider_calls() -> None:
    assert_blocked({"live_smoke_opt_in": False}, "HUMAN_DECISION_REQUIRED")


@pytest.mark.parametrize(
    "confirm_marker",
    [
        "not-confirmed",
        " " + P3W_CONFIRM_PHRASE,
        P3W_CONFIRM_PHRASE + " ",
        "--execute",
        "--live",
        "--call-model",
    ],
)
def test_bad_confirm_phrase_blocks(confirm_marker: str) -> None:
    assert_blocked({"confirm_phrase_hash_or_marker": confirm_marker}, "HUMAN_DECISION_REQUIRED")


@pytest.mark.parametrize("field", ["provider", "model", "key_slot"])
def test_missing_provider_model_key_slot_blocks(field: str) -> None:
    assert_blocked({field: ""}, "CONFIG_ERROR")


@pytest.mark.parametrize(
    ("field", "value", "failure_type"),
    [
        ("provider", ["google_gemini", "other"], "CONFIG_ERROR"),
        ("model", ["gemma-4-31b-it", "other"], "CONFIG_ERROR"),
        ("key_slot", ["worker_1", "worker_2"], "SECURITY_BLOCKED"),
        ("provider", "google_gemini,other", "CONFIG_ERROR"),
        ("model", "gemma-4-31b-it,other", "CONFIG_ERROR"),
        ("key_slot", "worker_1,worker_2", "SECURITY_BLOCKED"),
        ("key_slot", "reserve_1", "SECURITY_BLOCKED"),
        ("fallback_provider", "google_gemini", "SECURITY_BLOCKED"),
        ("provider_rotation_allowed", True, "SECURITY_BLOCKED"),
        ("key_rotation_allowed", True, "SECURITY_BLOCKED"),
        ("allowlist_widening_allowed", True, "SECURITY_BLOCKED"),
    ],
)
def test_multiple_selection_reserve_fallback_and_rotation_block(
    field: str, value: object, failure_type: str
) -> None:
    assert_blocked({field: value}, failure_type)


@pytest.mark.parametrize(
    ("field", "value", "failure_type"),
    [
        ("retry_allowed", True, "SECURITY_BLOCKED"),
        ("max_retries_per_call", 1, "SECURITY_BLOCKED"),
        ("retry_count", 1, "SECURITY_BLOCKED"),
        ("reserve_allowed", True, "SECURITY_BLOCKED"),
        ("reserve_used", True, "SECURITY_BLOCKED"),
        ("fallback_allowed", True, "SECURITY_BLOCKED"),
        ("fallback_used", True, "SECURITY_BLOCKED"),
        ("second_call_allowed", True, "SECURITY_BLOCKED"),
        ("second_call_attempted", True, "SECURITY_BLOCKED"),
        ("max_model_calls", 2, "BUDGET_EXCEEDED"),
        ("call_model_count_after", 2, "SECURITY_BLOCKED"),
        ("model_call_count_after", 2, "SECURITY_BLOCKED"),
        ("actual_provider_call_count", 2, "SECURITY_BLOCKED"),
    ],
)
def test_retry_reserve_fallback_second_call_and_count_injections_block(
    field: str, value: object, failure_type: str
) -> None:
    assert_blocked({field: value}, failure_type)


@pytest.mark.parametrize(
    "field",
    [
        "worker_orchestration",
        "worker_pool_dispatch",
        "manager_full_run",
        "auditor_full_run",
        "worker_file_write_allowed",
        "worker_shell_allowed",
        "shell_allowed",
        "web_allowed",
        "repo_clone_allowed",
        "github_allowed",
        "parallel_allowed",
        "external_write_scope",
        "auto_pr_allowed",
        "auto_merge_allowed",
    ],
)
def test_worker_authority_expansion_blocks(field: str) -> None:
    assert_blocked({field: True}, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "field",
    [
        "tool_call_allowed",
        "function_call_allowed",
        "file_upload_allowed",
        "vector_store_allowed",
        "assistant_thread_allowed",
        "batch_job_allowed",
        "long_running_job_allowed",
        "streaming_multi_call_allowed",
    ],
)
def test_tool_upload_batch_and_long_running_blocks(field: str) -> None:
    assert_blocked({field: True}, "SECURITY_BLOCKED")
