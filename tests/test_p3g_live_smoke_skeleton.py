# P3G first live smoke 스켈레톤이 실제 호출 없이 정책을 검증하는지 확인한다.
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aico_v0.artifact_safety import ArtifactSafetyFinding, ArtifactSafetyResult
from aico_v0.key_registry import KeyRegistry
from aico_v0.live_smoke import (
    ALLOWED_LIVE_SMOKE_ARTIFACTS,
    FAILURE_TYPE_BY_SMOKE_CONDITION,
    FORBIDDEN_LIVE_SMOKE_ARTIFACTS,
    FirstLiveSmokeApproval,
    build_artifact_safety_report,
    build_live_smoke_result,
    run_first_live_smoke_disabled,
    validate_first_live_smoke_approval,
    validate_first_live_smoke_request,
    validate_live_smoke_artifact_names,
)
from aico_v0.live_test_policy import live_smoke_marker_policy, should_skip_live_smoke_test
from aico_v0.provider_allowlist import ProviderAllowlist


RAW_SECRET = "sk-" + "p3g-live-smoke-secret"


def valid_approval(**overrides: object) -> FirstLiveSmokeApproval:
    data = {
        "provider": "google_gemini",
        "model": "user-approved-model",
        "key_slot": "worker_1",
        "max_model_calls": 1,
        "max_retries_per_call": 0,
        "max_runtime_seconds": 60,
        "allow_raw_output": False,
        "approval_scope": "this_run_only",
        "approved_by_user": True,
        "endpoint": "generate_content",
    }
    data.update(overrides)
    return FirstLiveSmokeApproval(**data)


def ok_scan() -> ArtifactSafetyResult:
    return ArtifactSafetyResult(True, None, ())


def valid_request_overrides(**overrides: object) -> dict[str, object]:
    data = {
        "approval": valid_approval(),
        "flags": {
            "AICO_ENABLE_REAL_PROVIDER": "true",
            "AICO_ALLOW_LIVE_CALLS": "true",
            "AICO_ALLOW_FIRST_LIVE_SMOKE": "true",
        },
        "provider_allowlist": ProviderAllowlist({"google_gemini": ("generate_content",)}),
        "key_registry": KeyRegistry({"worker_1": True}),
        "pre_artifact_scan": ok_scan(),
        "post_artifact_scan": ok_scan(),
    }
    data.update(overrides)
    return data


def assert_failure(result, failure_type: str) -> None:
    assert result.ok is False
    assert result.failure_type == failure_type


@pytest.mark.parametrize(
    "approval",
    [
        None,
        valid_approval(approved_by_user=False),
        valid_approval(approval_phrase="continue"),
        valid_approval(provider=None),
        valid_approval(model=None),
        valid_approval(key_slot=None),
        valid_approval(max_model_calls=None),
        valid_approval(max_retries_per_call=None),
        valid_approval(max_runtime_seconds=None),
        valid_approval(allow_raw_output=None),
    ],
)
def test_first_live_smoke_approval_human_decision_failures(approval: FirstLiveSmokeApproval | None) -> None:
    assert_failure(validate_first_live_smoke_approval(approval), "HUMAN_DECISION_REQUIRED")


def test_first_live_smoke_requires_exactly_one_key_slot() -> None:
    assert validate_first_live_smoke_approval(valid_approval(key_slot="worker_1")).ok is True
    assert_failure(validate_first_live_smoke_approval(valid_approval(key_slot=("worker_1", "worker_2"))), "HUMAN_DECISION_REQUIRED")


@pytest.mark.parametrize("key_slot", ["unknown_slot", "AICO_WORKER_1_API_KEY", RAW_SECRET])
def test_first_live_smoke_rejects_unknown_or_raw_key_like_key_slot(key_slot: str) -> None:
    assert_failure(validate_first_live_smoke_approval(valid_approval(key_slot=key_slot)), "SECURITY_BLOCKED")


def test_first_live_smoke_budget_and_retry_policy() -> None:
    assert validate_first_live_smoke_approval(valid_approval(max_model_calls=1, max_retries_per_call=0)).ok is True
    assert_failure(validate_first_live_smoke_approval(valid_approval(max_model_calls=2)), "CONFIG_ERROR")
    assert_failure(validate_first_live_smoke_approval(valid_approval(max_retries_per_call=1)), "SECURITY_BLOCKED")


def test_first_live_smoke_rejects_retry_reserve_and_second_model_call_attempts() -> None:
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(retry_attempted=True)), "SECURITY_BLOCKED")
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(reserve_attempted=True)), "SECURITY_BLOCKED")
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(second_model_call_attempted=True)), "SECURITY_BLOCKED")
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(attempted_model_calls=2)), "BUDGET_EXCEEDED")


def test_first_live_smoke_rejects_allow_raw_output_not_false() -> None:
    assert_failure(validate_first_live_smoke_approval(valid_approval(allow_raw_output=True)), "SECURITY_BLOCKED")


def test_first_live_smoke_provider_allowlist_policy() -> None:
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(provider_allowlist=None)), "CONFIG_ERROR")
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(provider_allowlist=ProviderAllowlist.empty())), "CONFIG_ERROR")
    assert_failure(
        validate_first_live_smoke_request(
            **valid_request_overrides(provider_allowlist=ProviderAllowlist({"other_provider": ("generate_content",)}))
        ),
        "SECURITY_BLOCKED",
    )


def test_first_live_smoke_rejects_unknown_endpoint_and_arbitrary_url() -> None:
    assert_failure(
        validate_first_live_smoke_request(
            **valid_request_overrides(provider_allowlist=ProviderAllowlist({"google_gemini": ("safe_endpoint",)}))
        ),
        "SECURITY_BLOCKED",
    )
    assert_failure(validate_first_live_smoke_approval(valid_approval(provider="https://provider.example")), "SECURITY_BLOCKED")


def test_first_live_smoke_requires_artifact_safety_scan_before_and_after_call() -> None:
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(pre_artifact_scan=None)), "CONFIG_ERROR")
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(post_artifact_scan=None)), "CONFIG_ERROR")
    failed_scan = ArtifactSafetyResult(False, "SECURITY_BLOCKED", (ArtifactSafetyFinding("artifact", "SECURITY_BLOCKED", "raw key"),))
    assert_failure(validate_first_live_smoke_request(**valid_request_overrides(pre_artifact_scan=failed_scan)), "SECURITY_BLOCKED")


def test_live_smoke_result_schema_has_no_raw_key_or_raw_output() -> None:
    result = build_live_smoke_result(
        approval=valid_approval(run_id="run-1"),
        status="blocked",
        failure_type="SECURITY_BLOCKED",
        error="blocked " + RAW_SECRET,
        masked_raw_output="raw=" + RAW_SECRET,
    )

    rendered = repr(result)
    assert "raw_output" not in result
    assert "raw_key" not in result
    assert result["raw_output_saved"] is False
    assert result["key_slot"] == "worker_1"
    assert RAW_SECRET not in rendered


def test_live_smoke_result_rejects_raw_output_saved_true() -> None:
    with pytest.raises(ValueError, match="raw_output_saved"):
        build_live_smoke_result(approval=valid_approval(), status="blocked", raw_output_saved=True)


def test_artifact_safety_report_schema_masks_findings_and_maps_failures() -> None:
    failed = ArtifactSafetyResult(
        False,
        "SECURITY_BLOCKED",
        (ArtifactSafetyFinding("live_smoke_result.json", "SECURITY_BLOCKED", "raw key " + RAW_SECRET),),
    )
    report = build_artifact_safety_report(failed, scanned_artifacts=("live_smoke_result.json",))

    assert report["status"] == "fail"
    assert report["failure_type"] == "SECURITY_BLOCKED"
    assert RAW_SECRET not in repr(report)
    assert report["findings"][0]["message"] == "[BLOCKED_VALUE]"


def test_artifact_safety_report_maps_missing_scan_to_config_error() -> None:
    report = build_artifact_safety_report(None)

    assert report["status"] == "missing"
    assert report["failure_type"] == "CONFIG_ERROR"


@pytest.mark.parametrize("artifact_name", sorted(FORBIDDEN_LIVE_SMOKE_ARTIFACTS))
def test_first_live_smoke_forbidden_full_run_artifacts_are_rejected(artifact_name: str) -> None:
    assert_failure(validate_live_smoke_artifact_names({artifact_name}), "SECURITY_BLOCKED")


def test_first_live_smoke_allowed_artifact_set_is_narrow() -> None:
    assert ALLOWED_LIVE_SMOKE_ARTIFACTS == {
        "run_log.jsonl",
        "ceo_report.md",
        "live_smoke_result.json",
        "artifact_safety_report.json",
    }
    assert validate_live_smoke_artifact_names(set(ALLOWED_LIVE_SMOKE_ARTIFACTS)).ok is True


def test_live_smoke_marker_is_default_skip_and_non_executing() -> None:
    policy = live_smoke_marker_policy()

    assert policy["marker"] == "live_smoke"
    assert policy["default_enabled"] is False
    assert policy["default_skip"] is True
    assert should_skip_live_smoke_test() is True
    assert should_skip_live_smoke_test(explicit_enable=True) is True
    assert "live_smoke" in Path("pyproject.toml").read_text(encoding="utf-8")


def test_disabled_runner_performs_no_api_network_key_or_sdk_work() -> None:
    result = run_first_live_smoke_disabled(approval=valid_approval(), key_registry=KeyRegistry({"worker_1": True}))

    assert result.status == "blocked"
    assert result.failure_type == "SECURITY_BLOCKED"
    assert result.actual_api_call_count == 0
    assert result.actual_llm_call_count == 0
    assert result.actual_key_value_read_count == 0
    assert result.actual_network_call_count == 0
    assert result.provider_sdk_imported is False
    assert result.live_smoke_executed is False


def test_p3g_failure_mapping_uses_existing_canonical_failure_types() -> None:
    expected = {
        "approval missing": "HUMAN_DECISION_REQUIRED",
        "approval ambiguous": "HUMAN_DECISION_REQUIRED",
        "required approval field missing": "HUMAN_DECISION_REQUIRED",
        "runtime flag missing": "CONFIG_ERROR",
        "runtime flag false": "CONFIG_ERROR",
        "provider allowlist missing": "CONFIG_ERROR",
        "provider allowlist empty": "CONFIG_ERROR",
        "key missing": "CONFIG_ERROR",
        "budget missing": "CONFIG_ERROR",
        "budget invalid": "CONFIG_ERROR",
        "artifact safety scan missing": "CONFIG_ERROR",
        "artifact safety scan failed": "SECURITY_BLOCKED",
        "unknown provider requested": "SECURITY_BLOCKED",
        "provider not in allowlist": "SECURITY_BLOCKED",
        "unknown endpoint requested": "SECURITY_BLOCKED",
        "arbitrary URL requested": "SECURITY_BLOCKED",
        "raw key found": "SECURITY_BLOCKED",
        "env var value found": "SECURITY_BLOCKED",
        "unmasked raw provider output found": "SECURITY_BLOCKED",
        "raw_output_saved=True detected": "SECURITY_BLOCKED",
        "allow_raw_output not false": "SECURITY_BLOCKED",
        "network call in default tests": "SECURITY_BLOCKED",
        "live call attempted without all gates": "SECURITY_BLOCKED",
        "retry attempted": "SECURITY_BLOCKED",
        "reserve attempted": "SECURITY_BLOCKED",
        "second model call attempted": "SECURITY_BLOCKED",
        "budget exceeded": "BUDGET_EXCEEDED",
        "timeout": "MODEL_ERROR",
        "429": "MODEL_ERROR",
        "500": "MODEL_ERROR",
        "provider unavailable": "MODEL_ERROR",
        "no response": "MODEL_ERROR",
        "non-json response": "SCHEMA_ERROR",
        "schema-invalid json": "SCHEMA_ERROR",
        "schema-valid empty response": "WORKER_BAD_OUTPUT",
        "ceo_report generation failed": "REPORT_ERROR",
        "artifact write failure": "REPORT_ERROR",
    }
    actual = dict(FAILURE_TYPE_BY_SMOKE_CONDITION)
    actual["approval missing"] = actual["explicit approval missing"]
    actual["approval ambiguous"] = actual["approval phrase ambiguous"]

    for condition, failure_type in expected.items():
        assert actual[condition] == failure_type


def test_p3g_runtime_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
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


def test_agents_and_claude_remain_byte_identical_for_p3g() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
