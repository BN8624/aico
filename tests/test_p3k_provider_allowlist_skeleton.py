# P3K provider allowlist candidate와 activation-disabled skeleton을 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aico_v0.artifact_safety import scan_artifacts
from aico_v0.key_registry import KeyRegistry
from aico_v0.live_activation import (
    LiveActivationBlocked,
    block_actual_activation_in_p3k,
    block_candidate_provider_live_call,
    build_disabled_activation_result,
    check_key_existence_only,
)
from aico_v0.live_smoke import FAILURE_TYPE_BY_SMOKE_CONDITION
from aico_v0.provider_allowlist import (
    CANDIDATE_PROVIDER,
    DEFAULT_PROVIDER_ALLOWLIST,
    DEFAULT_PROVIDER_ALLOWLIST_STATE,
    FAILURE_TYPE_BY_ALLOWLIST_CONDITION,
    CandidateProviderEntry,
    ProviderAllowlistSkeletonError,
    ProviderAllowlistState,
    candidate_authorizes_key_loading,
    candidate_authorizes_live_call,
    candidate_authorizes_sdk_import,
    google_gemini_candidate_entry,
    open_candidate_allowlist,
    validate_allowlist_state,
    validate_candidate_entry,
    validate_provider_name,
)

RAW_SECRET = "sk-" + "p3k-provider-secret-value"


def assert_blocked(exc_info: pytest.ExceptionInfo[ProviderAllowlistSkeletonError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_default_provider_allowlist_is_empty_or_disabled() -> None:
    assert DEFAULT_PROVIDER_ALLOWLIST.is_empty is True
    assert DEFAULT_PROVIDER_ALLOWLIST_STATE.state == "empty"
    assert DEFAULT_PROVIDER_ALLOWLIST_STATE.authorizes_live_call is False
    assert DEFAULT_PROVIDER_ALLOWLIST_STATE.authorizes_sdk_import is False
    assert DEFAULT_PROVIDER_ALLOWLIST_STATE.authorizes_key_loading is False


def test_google_gemini_candidate_entry_is_candidate_only() -> None:
    entry = google_gemini_candidate_entry()
    state = open_candidate_allowlist()
    summary = entry.to_summary()

    assert entry.provider == CANDIDATE_PROVIDER == "google_gemini"
    assert entry.status == "candidate"
    assert entry.activation == "disabled"
    assert entry.endpoint_url is None
    assert entry.sdk_import_allowed is False
    assert entry.key_loading_allowed is False
    assert entry.live_calls_allowed is False
    assert summary["endpoint_url"] is None
    assert summary["sdk_import_allowed"] is False
    assert summary["key_loading_allowed"] is False
    assert summary["live_calls_allowed"] is False
    assert state.state == "candidate"
    assert state.authorizes_live_call is False
    assert state.authorizes_sdk_import is False
    assert state.authorizes_key_loading is False


def test_candidate_entry_does_not_authorize_live_call_sdk_import_or_key_loading() -> None:
    entry = google_gemini_candidate_entry()

    assert candidate_authorizes_live_call(entry) is False
    assert candidate_authorizes_sdk_import(entry) is False
    assert candidate_authorizes_key_loading(entry) is False


@pytest.mark.parametrize(
    ("provider", "failure_type"),
    [
        ("https://generativelanguage.googleapis.com", "SECURITY_BLOCKED"),
        ("http://provider.example", "SECURITY_BLOCKED"),
        ("ftp://provider.example", "SECURITY_BLOCKED"),
        ("generativelanguage.googleapis.com", "SECURITY_BLOCKED"),
        ("openai.com", "SECURITY_BLOCKED"),
        ("anthropic.com", "SECURITY_BLOCKED"),
        ("google_gemini/v1", "SECURITY_BLOCKED"),
        ("google_gemini:generate", "SECURITY_BLOCKED"),
        ("google_gemini?model=one", "SECURITY_BLOCKED"),
        (RAW_SECRET, "SECURITY_BLOCKED"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "SECURITY_BLOCKED"),
        ("unknown_provider", "SECURITY_BLOCKED"),
    ],
)
def test_provider_name_rejects_urls_endpoints_raw_keys_and_unknown_provider(
    provider: str,
    failure_type: str,
) -> None:
    with pytest.raises(ProviderAllowlistSkeletonError) as exc_info:
        validate_provider_name(provider)
    assert_blocked(exc_info, failure_type)


@pytest.mark.parametrize(
    ("entry", "failure_type"),
    [
        (CandidateProviderEntry(endpoint_url="https://generativelanguage.googleapis.com"), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(sdk_import_allowed=True), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(key_loading_allowed=True), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(live_calls_allowed=True), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(status="active"), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(status="live"), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(status="enabled_for_call"), "SECURITY_BLOCKED"),
        (CandidateProviderEntry(activation="active"), "SECURITY_BLOCKED"),
    ],
)
def test_candidate_entry_rejects_activation_or_permission_like_values(
    entry: CandidateProviderEntry,
    failure_type: str,
) -> None:
    with pytest.raises(ProviderAllowlistSkeletonError) as exc_info:
        validate_candidate_entry(entry)
    assert_blocked(exc_info, failure_type)


def test_unknown_allowlist_state_maps_to_config_error() -> None:
    with pytest.raises(ProviderAllowlistSkeletonError) as exc_info:
        validate_allowlist_state(ProviderAllowlistState("mystery"))
    assert_blocked(exc_info, "CONFIG_ERROR")


@pytest.mark.parametrize("state", ["active", "live", "enabled_for_call", "provider_ready", "api_ready"])
def test_activation_like_allowlist_state_is_rejected(state: str) -> None:
    with pytest.raises(ProviderAllowlistSkeletonError) as exc_info:
        validate_allowlist_state(ProviderAllowlistState(state))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_actual_activation_attempt_in_p3k_is_blocked() -> None:
    with pytest.raises(LiveActivationBlocked) as exc_info:
        block_actual_activation_in_p3k(open_candidate_allowlist())
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_candidate_provider_live_call_attempt_is_blocked() -> None:
    with pytest.raises(LiveActivationBlocked) as exc_info:
        block_candidate_provider_live_call(google_gemini_candidate_entry(), state=open_candidate_allowlist())
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_candidate_allowlist_does_not_import_sdk_read_key_call_network_or_api() -> None:
    entry = google_gemini_candidate_entry()
    state = open_candidate_allowlist()
    result = build_disabled_activation_result(entry.provider)

    assert state.authorizes_live_call is False
    assert state.authorizes_sdk_import is False
    assert state.authorizes_key_loading is False
    assert result.status == "disabled"
    assert result.model_call_count == 0
    assert result.actual_api_call_count == 0
    assert result.actual_llm_call_count == 0
    assert result.actual_key_value_read_count == 0
    assert result.actual_network_call_count == 0
    assert result.provider_sdk_imported is False
    assert result.live_smoke_executed is False
    assert result.provider_allowlist_activated is False
    assert result.status not in {"success", "api_success", "provider_success", "live_success"}


def test_key_existence_boolean_skeleton_never_returns_raw_key_value() -> None:
    configured = check_key_existence_only(KeyRegistry({"worker_1": True}), "worker_1")
    missing = check_key_existence_only(KeyRegistry({"worker_1": False}), "worker_1")

    assert configured.configured is True
    assert configured.failure_type is None
    assert missing.configured is False
    assert missing.failure_type == "CONFIG_ERROR"
    assert not hasattr(configured, "raw_key")
    assert not hasattr(configured, "raw_key_value")


def test_key_registry_raw_key_value_remains_disabled_in_p3k() -> None:
    with pytest.raises(RuntimeError, match="raw key access is disabled"):
        KeyRegistry({"worker_1": True}).raw_key_value("worker_1")


def test_artifact_safety_scan_accepts_safe_candidate_summary() -> None:
    result = scan_artifacts({"provider_allowlist_summary": google_gemini_candidate_entry().to_summary()})

    assert result.ok is True


def test_artifact_safety_scan_rejects_candidate_summary_with_endpoint_url() -> None:
    result = scan_artifacts(
        {
            "provider_allowlist_summary": {
                "provider": "google_gemini",
                "endpoint_url": "https://generativelanguage.googleapis.com",
            }
        }
    )

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"


def test_artifact_safety_scan_rejects_candidate_summary_with_raw_key_like_value() -> None:
    result = scan_artifacts({"provider_allowlist_summary": {"provider": RAW_SECRET}})

    assert result.ok is False
    assert result.failure_type == "SECURITY_BLOCKED"


def test_p3k_failure_mapping_uses_existing_canonical_failure_types() -> None:
    expected = {
        "provider allowlist missing": "CONFIG_ERROR",
        "provider allowlist empty": "CONFIG_ERROR",
        "unknown allowlist state": "CONFIG_ERROR",
        "unknown provider requested": "SECURITY_BLOCKED",
        "provider not in allowlist": "SECURITY_BLOCKED",
        "provider URL requested": "SECURITY_BLOCKED",
        "endpoint URL requested": "SECURITY_BLOCKED",
        "arbitrary URL requested": "SECURITY_BLOCKED",
        "raw key found": "SECURITY_BLOCKED",
        "env var value found": "SECURITY_BLOCKED",
        "candidate interpreted as active": "SECURITY_BLOCKED",
        "activation attempted in P3K": "SECURITY_BLOCKED",
        "SDK import before approved phase": "SECURITY_BLOCKED",
        "actual key read before approved phase": "SECURITY_BLOCKED",
        "live call attempted without all gates": "SECURITY_BLOCKED",
        "candidate provider live call attempted": "SECURITY_BLOCKED",
        "endpoint_url not null": "SECURITY_BLOCKED",
        "sdk_import_allowed true": "SECURITY_BLOCKED",
        "key_loading_allowed true": "SECURITY_BLOCKED",
        "live_calls_allowed true": "SECURITY_BLOCKED",
        "artifact write failure": "REPORT_ERROR",
    }

    for condition, failure_type in expected.items():
        assert FAILURE_TYPE_BY_ALLOWLIST_CONDITION[condition] == failure_type
        assert FAILURE_TYPE_BY_SMOKE_CONDITION[condition] == failure_type


def test_default_pytest_does_not_execute_live_smoke_in_p3k() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "live_smoke" in pyproject
    assert "live_provider" in pyproject


def test_p3k_runtime_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
    forbidden_roots = {"requests", "httpx", "socket", "google", "openai", "anthropic", "genai", "dotenv"}
    forbidden_exact = {"urllib.request", "os.environ"}
    imports: set[str] = set()
    for path in Path("aico_v0").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

    assert not any(name.split(".")[0] in forbidden_roots for name in imports)
    assert not any(name in forbidden_exact for name in imports)


def test_agents_and_claude_remain_byte_identical_for_p3k() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
