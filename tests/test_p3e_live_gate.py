# P3E live-call gate 실패 조건을 실제 호출 없이 canonical failure로 고정한다.
from __future__ import annotations

import pytest

from aico_v0.artifact_safety import ArtifactSafetyResult
from aico_v0.key_registry import KeyRegistry
from aico_v0.live_gate import (
    FAILURE_TYPE_BY_GATE_CONDITION,
    LiveApproval,
    LiveBudget,
    failure_type_for_condition,
    validate_approval,
    validate_budget,
    validate_key_availability,
    validate_live_gate,
    validate_provider_allowlist,
    validate_runtime_flags,
)
from aico_v0.provider_allowlist import (
    CANDIDATE_PROVIDER_METADATA,
    DEFAULT_PROVIDER_ALLOWLIST,
    ProviderAllowlist,
)


def valid_approval(**overrides: object) -> LiveApproval:
    data = {
        "provider": "google_gemini",
        "key_slots": ("worker_1",),
        "max_model_calls": 1,
        "max_runtime_seconds": 60,
        "approval_scope": "this_run_only",
        "approved_by_user": True,
        "endpoint": "generate_content",
    }
    data.update(overrides)
    return LiveApproval(**data)


def assert_failure(result, failure_type: str) -> None:
    assert result.ok is False
    assert result.failure_type == failure_type


@pytest.mark.parametrize(
    ("approval", "failure_type"),
    [
        (None, "HUMAN_DECISION_REQUIRED"),
        (valid_approval(approval_phrase="continue"), "HUMAN_DECISION_REQUIRED"),
        (valid_approval(provider=None), "HUMAN_DECISION_REQUIRED"),
        (valid_approval(key_slots=()), "HUMAN_DECISION_REQUIRED"),
        (valid_approval(max_model_calls=None), "HUMAN_DECISION_REQUIRED"),
        (valid_approval(max_runtime_seconds=None), "HUMAN_DECISION_REQUIRED"),
        (valid_approval(approved_by_user=False), "HUMAN_DECISION_REQUIRED"),
    ],
)
def test_approval_failures_map_to_human_decision_required(approval: LiveApproval | None, failure_type: str) -> None:
    assert_failure(validate_approval(approval), failure_type)


@pytest.mark.parametrize(
    ("flags", "failure_type"),
    [
        ({}, "CONFIG_ERROR"),
        ({"AICO_ALLOW_LIVE_CALLS": "true"}, "CONFIG_ERROR"),
        ({"AICO_ENABLE_REAL_PROVIDER": "true"}, "CONFIG_ERROR"),
        ({"AICO_ENABLE_REAL_PROVIDER": "false", "AICO_ALLOW_LIVE_CALLS": "true"}, "CONFIG_ERROR"),
        ({"AICO_ENABLE_REAL_PROVIDER": "true", "AICO_ALLOW_LIVE_CALLS": "false"}, "CONFIG_ERROR"),
    ],
)
def test_runtime_flag_failures_map_to_config_error(flags: dict[str, str], failure_type: str) -> None:
    assert_failure(validate_runtime_flags(flags), failure_type)


def test_both_flags_true_are_insufficient_without_other_gates() -> None:
    result = validate_live_gate(
        approval=None,
        flags={"AICO_ENABLE_REAL_PROVIDER": "true", "AICO_ALLOW_LIVE_CALLS": "true"},
        provider_allowlist=ProviderAllowlist({"google_gemini": ("generate_content",)}),
        key_registry=KeyRegistry({"worker_1": True}),
        budget=LiveBudget.first_live_smoke(),
        artifact_scan=ArtifactSafetyResult(True, None, ()),
    )

    assert_failure(result, "HUMAN_DECISION_REQUIRED")


def test_provider_allowlist_default_is_empty_and_candidate_is_non_authorizing() -> None:
    assert DEFAULT_PROVIDER_ALLOWLIST.is_empty is True
    assert CANDIDATE_PROVIDER_METADATA["candidate_provider"] == "google_gemini"
    assert CANDIDATE_PROVIDER_METADATA["authorizes_live_call"] is False


@pytest.mark.parametrize(
    ("allowlist", "approval", "failure_type"),
    [
        (None, valid_approval(), "CONFIG_ERROR"),
        (ProviderAllowlist.empty(), valid_approval(), "CONFIG_ERROR"),
        (ProviderAllowlist({"google_gemini": ("generate_content",)}), valid_approval(provider="unknown_provider"), "SECURITY_BLOCKED"),
        (ProviderAllowlist({"other_known_provider": ("generate_content",)}), valid_approval(), "SECURITY_BLOCKED"),
        (ProviderAllowlist({"google_gemini": ("safe_endpoint",)}), valid_approval(endpoint="generate_content"), "SECURITY_BLOCKED"),
        (ProviderAllowlist({"google_gemini": ("generate_content",)}), valid_approval(provider="https://provider.example"), "SECURITY_BLOCKED"),
    ],
)
def test_provider_allowlist_failures(
    allowlist: ProviderAllowlist | None,
    approval: LiveApproval,
    failure_type: str,
) -> None:
    result = validate_provider_allowlist(approval, allowlist)
    assert_failure(result, failure_type)


@pytest.mark.parametrize(
    ("budget", "attempted_calls", "failure_type"),
    [
        (None, 0, "CONFIG_ERROR"),
        (LiveBudget(max_model_calls=2, max_runtime_seconds=60), 0, "CONFIG_ERROR"),
        (LiveBudget(max_model_calls=1, max_runtime_seconds=60, max_retries_per_call=1), 0, "CONFIG_ERROR"),
        (LiveBudget.first_live_smoke(), 2, "BUDGET_EXCEEDED"),
    ],
)
def test_budget_validation(budget: LiveBudget | None, attempted_calls: int, failure_type: str) -> None:
    assert_failure(validate_budget(budget, attempted_model_calls=attempted_calls), failure_type)


def test_first_live_smoke_budget_defaults() -> None:
    budget = LiveBudget.first_live_smoke()

    assert budget.max_model_calls == 1
    assert budget.max_retries_per_call == 0
    assert budget.max_consecutive_model_errors == 1
    assert budget.max_runtime_seconds == 60
    assert validate_budget(budget).ok is True


def test_key_availability_skeleton_uses_boolean_presence_only() -> None:
    approval = valid_approval(key_slots=("worker_1",))

    assert validate_key_availability(approval, KeyRegistry({"worker_1": True})).ok is True
    assert_failure(validate_key_availability(approval, KeyRegistry({"worker_1": False})), "CONFIG_ERROR")
    assert_failure(validate_key_availability(valid_approval(key_slots=("missing_slot",)), KeyRegistry()), "CONFIG_ERROR")


def test_failure_mapping_table_contains_required_canonical_values() -> None:
    expected = {
        "explicit approval missing": "HUMAN_DECISION_REQUIRED",
        "approval phrase ambiguous": "HUMAN_DECISION_REQUIRED",
        "provider not specified in approval": "HUMAN_DECISION_REQUIRED",
        "key slots not specified in approval": "HUMAN_DECISION_REQUIRED",
        "max_model_calls not specified in approval": "HUMAN_DECISION_REQUIRED",
        "max_runtime_seconds not specified in approval": "HUMAN_DECISION_REQUIRED",
        "AICO_ENABLE_REAL_PROVIDER missing": "CONFIG_ERROR",
        "AICO_ALLOW_LIVE_CALLS missing": "CONFIG_ERROR",
        "AICO_ENABLE_REAL_PROVIDER=false": "CONFIG_ERROR",
        "AICO_ALLOW_LIVE_CALLS=false": "CONFIG_ERROR",
        "provider allowlist missing": "CONFIG_ERROR",
        "provider allowlist empty": "CONFIG_ERROR",
        "unknown provider requested": "SECURITY_BLOCKED",
        "provider not in allowlist": "SECURITY_BLOCKED",
        "unknown endpoint requested": "SECURITY_BLOCKED",
        "arbitrary URL requested": "SECURITY_BLOCKED",
        "key availability check failed": "CONFIG_ERROR",
        "key slot missing": "CONFIG_ERROR",
        "raw key leaked": "SECURITY_BLOCKED",
        "env var value logged": "SECURITY_BLOCKED",
        "budget missing": "CONFIG_ERROR",
        "budget invalid": "CONFIG_ERROR",
        "budget exceeded": "BUDGET_EXCEEDED",
        "artifact safety scan missing": "CONFIG_ERROR",
        "raw key found in artifact": "SECURITY_BLOCKED",
        "unmasked raw provider output found in artifact": "SECURITY_BLOCKED",
        "raw_output_saved=True detected": "SECURITY_BLOCKED",
        "provider SDK import before approved phase": "SECURITY_BLOCKED",
        "network call in default tests": "SECURITY_BLOCKED",
        "live call attempted in default pytest": "SECURITY_BLOCKED",
        "ProviderResult safety rule broken": "SECURITY_BLOCKED",
        "final_report and failed_draft both generated": "REPORT_ERROR",
        "ceo_report generation failed": "REPORT_ERROR",
    }

    for condition, failure_type in expected.items():
        assert failure_type_for_condition(condition) == failure_type
    assert not (set(expected) - set(FAILURE_TYPE_BY_GATE_CONDITION))
