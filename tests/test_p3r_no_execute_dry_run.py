# P3R no-execute dry run이 artifact와 호출 실행 경계를 열지 않는지 검증합니다.
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aico_v0.approval_package import APPROVAL_PACKAGE_ARTIFACT_NAME, approval_package_default_runtime_creation_enabled
from aico_v0.live_execution_boundary import (
    CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
    P3RLiveExecutionBoundaryError,
    build_blocked_call_safety_summary,
    build_no_execute_dry_run,
    call_attempt_summary_default_runtime_creation_enabled,
    validate_post_boundary_safety,
    write_call_attempt_summary,
)
from aico_v0.no_call_integration import (
    NO_CALL_INTEGRATION_ARTIFACT_NAME,
    no_call_integration_default_runtime_creation_enabled,
)

from tests.test_p3r_live_execution_boundary import safe_inputs


def assert_failure(exc_info: pytest.ExceptionInfo[P3RLiveExecutionBoundaryError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_blocked_call_safety_blocks_call_model_attempt() -> None:
    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        build_blocked_call_safety_summary(**safe_inputs(), call_model_attempted=True)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_blocked_call_safety_blocks_provider_transport_attempt() -> None:
    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        build_blocked_call_safety_summary(**safe_inputs(), provider_transport_attempted=True)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_blocked_call_safety_keeps_counts_closed_without_transport() -> None:
    summary = build_blocked_call_safety_summary(**safe_inputs()).to_summary()

    assert summary["status"] == "blocked"
    assert summary["call_attempt_state"] == "dry_run_blocked"
    assert summary["model_call_count"] == 0
    assert summary["live_call_allowed"] is False
    assert summary["provider_transport_called"] is False
    assert summary["call_model_executed"] is False


@pytest.mark.parametrize(
    "update",
    [
        {"provider_response": {"text": "blocked"}},
        {"token_usage": {"total_tokens": 1}},
        {"raw_output_saved": True},
    ],
)
def test_post_boundary_safety_rejects_provider_response_token_usage_and_raw_saved(update: dict[str, object]) -> None:
    summary = build_no_execute_dry_run(**safe_inputs()).to_summary()
    summary.update(update)

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        validate_post_boundary_safety(summary)

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_call_attempt_summary_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    summary = build_no_execute_dry_run(**safe_inputs())
    path = write_call_attempt_summary(tmp_path, summary)

    assert path == tmp_path / CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME
    assert path.exists()


def test_call_attempt_summary_write_helper_blocks_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        write_call_attempt_summary(
            tmp_path,
            build_no_execute_dry_run(**safe_inputs()),
            artifact_name="../call_attempt_summary.json",
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_call_attempt_summary_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME

    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        write_call_attempt_summary(tmp_path, build_no_execute_dry_run(**safe_inputs()), artifact_name=str(outside))

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_call_attempt_summary_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3RLiveExecutionBoundaryError) as exc_info:
        write_call_attempt_summary(tmp_path, build_no_execute_dry_run(**safe_inputs()), artifact_name="unexpected.json")

    assert_failure(exc_info, "REPORT_ERROR")


def test_default_runtime_path_creates_no_p3r_artifacts(tmp_path: Path) -> None:
    assert approval_package_default_runtime_creation_enabled() is False
    assert no_call_integration_default_runtime_creation_enabled() is False
    assert call_attempt_summary_default_runtime_creation_enabled() is False
    assert not (tmp_path / CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME).exists()
    assert not Path(CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME).exists()
    assert not Path(APPROVAL_PACKAGE_ARTIFACT_NAME).exists()
    assert not Path(NO_CALL_INTEGRATION_ARTIFACT_NAME).exists()
    assert not Path("live_smoke_result.json").exists()


def test_p3r_runtime_imports_no_provider_sdk_or_network_modules() -> None:
    path = Path("aico_v0/live_execution_boundary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_roots = {"requests", "httpx", "socket", "google", "openai", "anthropic", "genai", "dotenv"}
    forbidden_exact = {"urllib.request", "os.environ"}
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any(name.split(".")[0] in forbidden_roots for name in imports)
    assert not any(name in forbidden_exact for name in imports)


def test_p3r_runtime_reads_no_env_key_network_or_call_model() -> None:
    source = Path("aico_v0/live_execution_boundary.py").read_text(encoding="utf-8")
    assert "getenv(" not in source
    assert "environ.get(" not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"call_model", "request", "urlopen", "connect", "send"}
            elif isinstance(node.func, ast.Name):
                assert node.func.id not in {"call_model", "getenv"}


def test_p3r_helpers_keep_all_no_call_counters_closed() -> None:
    summary = build_no_execute_dry_run(**safe_inputs()).to_summary()

    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["actual_api_call_count"] == 0
    assert summary["actual_llm_call_count"] == 0
    assert summary["actual_key_value_read_count"] == 0
    assert summary["actual_sdk_import_count"] == 0
    assert summary["actual_network_call_count"] == 0
    assert summary["actual_live_smoke_count"] == 0
