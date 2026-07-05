# P3J live smoke 산출물 쓰기 skeleton의 안전 경계를 검증한다.
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from aico_v0.artifact_safety import ArtifactSafetyFinding, ArtifactSafetyResult
from aico_v0.key_registry import KeyRegistry
from aico_v0.live_smoke import FAILURE_TYPE_BY_SMOKE_CONDITION, FirstLiveSmokeApproval
from aico_v0.live_smoke_artifacts import (
    ALLOWED_LIVE_SMOKE_ARTIFACTS,
    FORBIDDEN_LIVE_SMOKE_ARTIFACTS,
    ArtifactWriteBlocked,
    resolve_live_smoke_artifact_path,
    run_artifact_post_scan,
    run_artifact_pre_scan,
    run_first_live_smoke_disabled_with_artifacts,
    write_artifact_safety_report,
    write_live_smoke_result,
)
from aico_v0.live_test_policy import live_smoke_marker_policy, should_skip_live_smoke_test

RAW_SECRET = "sk-" + "p3j-live-smoke-secret"


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


def safe_result_fields(**overrides: object) -> dict[str, object]:
    data = {
        "status": "disabled",
        "failure_type": "SECURITY_BLOCKED",
        "error": "first live smoke execution is disabled",
        "model_call_count": 0,
        "retry_count": 0,
        "reserve_used": False,
        "raw_output_saved": False,
        "masked_raw_output": None,
        "artifact_safety_status": "not_run",
    }
    data.update(overrides)
    return data


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_blocked(exc_info: pytest.ExceptionInfo[ArtifactWriteBlocked], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_live_smoke_result_write_helper_writes_only_allowed_fields(tmp_path: Path) -> None:
    path = write_live_smoke_result(tmp_path, valid_approval(), **safe_result_fields())
    payload = read_json(path)

    assert path.name == "live_smoke_result.json"
    assert set(payload) == {
        "artifact_safety_status",
        "error",
        "failure_type",
        "input_tokens",
        "key_slot",
        "masked_raw_output",
        "max_model_calls",
        "max_retries_per_call",
        "model",
        "model_call_count",
        "output_tokens",
        "parent_event_id",
        "provider",
        "raw_output_saved",
        "reserve_used",
        "retry_count",
        "run_id",
        "status",
        "timestamp",
    }
    assert "raw_output" not in payload
    assert "raw_key" not in payload
    assert payload["raw_output_saved"] is False
    assert payload["key_slot"] == "worker_1"


def test_live_smoke_result_rejects_raw_output_field(tmp_path: Path) -> None:
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        write_live_smoke_result(tmp_path, valid_approval(), **safe_result_fields(raw_output="unmasked"))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_live_smoke_result_rejects_raw_output_saved_true(tmp_path: Path) -> None:
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        write_live_smoke_result(tmp_path, valid_approval(), **safe_result_fields(raw_output_saved=True))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "approval",
    [
        valid_approval(provider="https://provider.example"),
        valid_approval(model=RAW_SECRET),
        valid_approval(key_slot=RAW_SECRET),
    ],
)
def test_live_smoke_result_rejects_raw_key_like_provider_model_or_key_slot(
    tmp_path: Path,
    approval: FirstLiveSmokeApproval,
) -> None:
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        write_live_smoke_result(tmp_path, approval, **safe_result_fields())
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_live_smoke_result_disabled_skeleton_counts_are_zero(tmp_path: Path) -> None:
    path = write_live_smoke_result(tmp_path, valid_approval(), **safe_result_fields())
    payload = read_json(path)

    assert payload["model_call_count"] == 0
    assert payload["retry_count"] == 0
    assert payload["reserve_used"] is False
    assert payload["status"] in {"disabled", "not_executed", "prepared", "blocked"}


@pytest.mark.parametrize(
    ("field", "value", "failure_type"),
    [
        ("model_call_count", 1, "SECURITY_BLOCKED"),
        ("retry_count", 1, "SECURITY_BLOCKED"),
        ("reserve_used", True, "SECURITY_BLOCKED"),
        ("failure_type", "NOT_A_FAILURE", "CONFIG_ERROR"),
        ("status", "success", "SECURITY_BLOCKED"),
        ("artifact_safety_status", "unknown", "CONFIG_ERROR"),
    ],
)
def test_live_smoke_result_rejects_unsafe_state(
    tmp_path: Path,
    field: str,
    value: object,
    failure_type: str,
) -> None:
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        write_live_smoke_result(tmp_path, valid_approval(), **safe_result_fields(**{field: value}))
    assert_blocked(exc_info, failure_type)


def test_artifact_safety_report_write_helper_writes_required_fields(tmp_path: Path) -> None:
    scan = ArtifactSafetyResult(True, None, ())
    path = write_artifact_safety_report(tmp_path, scan, scanned_artifacts=("live_smoke_result.json",))
    payload = read_json(path)

    assert set(payload) == {"status", "scanned_artifacts", "findings", "failure_type", "summary"}
    assert payload["status"] == "pass"
    assert payload["scanned_artifacts"] == ["live_smoke_result.json"]


def test_artifact_safety_report_masks_finding_message(tmp_path: Path) -> None:
    scan = ArtifactSafetyResult(
        False,
        "SECURITY_BLOCKED",
        (ArtifactSafetyFinding("live_smoke_result.json", "SECURITY_BLOCKED", "raw key " + RAW_SECRET),),
    )
    path = write_artifact_safety_report(tmp_path, scan, scanned_artifacts=("live_smoke_result.json",))
    rendered = path.read_text(encoding="utf-8")
    payload = read_json(path)

    assert payload["status"] == "fail"
    assert payload["failure_type"] == "SECURITY_BLOCKED"
    assert RAW_SECRET not in rendered
    assert payload["findings"][0]["message"] == "[BLOCKED_VALUE]"


def test_artifact_safety_report_maps_scan_missing_to_config_error(tmp_path: Path) -> None:
    path = write_artifact_safety_report(tmp_path, None)
    payload = read_json(path)

    assert payload["status"] == "missing"
    assert payload["failure_type"] == "CONFIG_ERROR"


def test_artifact_safety_report_uses_run_relative_artifact_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.json"
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        write_artifact_safety_report(tmp_path, ArtifactSafetyResult(True, None, ()), scanned_artifacts=(str(outside),))
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize(
    "artifact_name",
    ["live_smoke_result.json", "artifact_safety_report.json", "run_log.jsonl", "ceo_report.md"],
)
def test_run_dir_path_guard_allows_allowed_artifacts(tmp_path: Path, artifact_name: str) -> None:
    resolved = resolve_live_smoke_artifact_path(tmp_path, artifact_name)

    assert resolved == (tmp_path / artifact_name).resolve()


@pytest.mark.parametrize(
    "artifact_name",
    [
        "../live_smoke_result.json",
        "nested/../live_smoke_result.json",
    ],
)
def test_run_dir_path_guard_blocks_path_traversal(tmp_path: Path, artifact_name: str) -> None:
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        resolve_live_smoke_artifact_path(tmp_path, artifact_name)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_run_dir_path_guard_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.json"
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        resolve_live_smoke_artifact_path(tmp_path, outside)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


@pytest.mark.parametrize("artifact_name", sorted(FORBIDDEN_LIVE_SMOKE_ARTIFACTS))
def test_run_dir_path_guard_blocks_forbidden_artifacts(tmp_path: Path, artifact_name: str) -> None:
    with pytest.raises(ArtifactWriteBlocked) as exc_info:
        resolve_live_smoke_artifact_path(tmp_path, artifact_name)
    assert_blocked(exc_info, "SECURITY_BLOCKED")


def test_disabled_runner_writes_only_allowed_artifacts_and_no_full_run_artifacts(tmp_path: Path) -> None:
    result = run_first_live_smoke_disabled_with_artifacts(
        tmp_path,
        valid_approval(),
        pre_scan_inputs={
            "approval": "provider=google_gemini key_slot=worker_1",
            "prompt": "Return a minimal JSON object matching the expected schema.",
        },
    )

    assert set(result.written_artifacts) <= ALLOWED_LIVE_SMOKE_ARTIFACTS
    assert set(result.written_artifacts) == {
        "artifact_safety_report.json",
        "ceo_report.md",
        "live_smoke_result.json",
        "run_log.jsonl",
    }
    for forbidden in FORBIDDEN_LIVE_SMOKE_ARTIFACTS:
        assert not (tmp_path / forbidden).exists()


def test_disabled_runner_performs_no_live_work_and_does_not_mark_success(tmp_path: Path) -> None:
    result = run_first_live_smoke_disabled_with_artifacts(
        tmp_path,
        valid_approval(),
        pre_scan_inputs={"prompt": "Return minimal JSON."},
    )
    payload = read_json(tmp_path / "live_smoke_result.json")

    assert result.status == "disabled"
    assert result.failure_type == "SECURITY_BLOCKED"
    assert result.actual_api_call_count == 0
    assert result.actual_llm_call_count == 0
    assert result.actual_key_value_read_count == 0
    assert result.actual_network_call_count == 0
    assert result.provider_sdk_imported is False
    assert result.live_smoke_executed is False
    assert payload["status"] != "success"
    assert payload["model_call_count"] == 0


def test_pre_and_post_scan_skeleton_failure_mapping(tmp_path: Path) -> None:
    missing_pre = run_artifact_pre_scan(None)
    failed_pre = run_artifact_pre_scan({"approval": "Bearer abcdefghijklmnopqrstuvwxyz"})

    assert missing_pre.failure_type == "CONFIG_ERROR"
    assert failed_pre.failure_type == "SECURITY_BLOCKED"

    missing_post = run_artifact_post_scan(tmp_path)
    assert missing_post.failure_type == "CONFIG_ERROR"

    (tmp_path / "live_smoke_result.json").write_text('{"raw_output_saved": true}', encoding="utf-8")
    failed_post = run_artifact_post_scan(tmp_path)
    assert failed_post.failure_type == "SECURITY_BLOCKED"


def test_failure_mapping_adds_p3j_conditions_without_new_failure_types() -> None:
    expected = {
        "path traversal attempted": "SECURITY_BLOCKED",
        "artifact path outside run_dir": "SECURITY_BLOCKED",
        "forbidden artifact attempted": "SECURITY_BLOCKED",
        "SDK import before approved phase": "SECURITY_BLOCKED",
        "actual key read before approved phase": "SECURITY_BLOCKED",
        "unknown failure_type": "CONFIG_ERROR",
    }

    for condition, failure_type in expected.items():
        assert FAILURE_TYPE_BY_SMOKE_CONDITION[condition] == failure_type


def test_default_pytest_does_not_execute_live_smoke() -> None:
    policy = live_smoke_marker_policy()

    assert policy["marker"] == "live_smoke"
    assert policy["default_skip"] is True
    assert should_skip_live_smoke_test() is True
    assert should_skip_live_smoke_test(explicit_enable=True) is True


def test_p3j_runtime_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
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


def test_agents_and_claude_remain_byte_identical_for_p3j() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
