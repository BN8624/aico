# P3X가 P3W 실제 산출물을 재실행 없이 회귀 기준으로 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

from aico_v0.negative_safety import build_p3x_negative_safety_report, validate_p3x_p3w_artifact_regression


P3W_RUN_DIR = Path("runs/p3w_20260706T123731Z")


def test_p3w_artifact_regression_confirms_single_call_counts_and_flags() -> None:
    regression = validate_p3x_p3w_artifact_regression(P3W_RUN_DIR)
    assert regression["actual_provider_call_count"] == 1
    assert regression["call_model_count_before"] == 0
    assert regression["call_model_count_after"] == 1
    assert regression["model_call_count_before"] == 0
    assert regression["model_call_count_after"] == 1
    assert regression["retry_count"] == 0
    assert regression["reserve_used"] is False
    assert regression["fallback_used"] is False
    assert regression["second_call_attempted"] is False
    assert regression["raw_output_saved"] is False
    assert regression["masked_summary_saved"] is True
    assert regression["artifact_safety_scan"] == "pass"


def test_p3x_negative_safety_report_records_no_additional_live_paths() -> None:
    report = build_p3x_negative_safety_report(validate_p3x_p3w_artifact_regression(P3W_RUN_DIR))
    assert report["result"] == "passed"
    assert report["actual_live_call_rerun"] is False
    assert report["additional_provider_calls"] == 0
    assert report["key_value_read"] is False
    assert report["env_value_read"] is False
    assert report["provider_sdk_import"] is False
    assert report["network_call"] is False
    assert report["call_model_execution"] is False


def test_p3x_runtime_imports_no_provider_sdk_and_no_network_modules() -> None:
    tree = ast.parse(Path("aico_v0/negative_safety.py").read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert "google" not in modules
    assert "google.genai" not in modules
    assert "requests" not in modules
    assert "httpx" not in modules
    assert "socket" not in modules


def test_p3x_tests_do_not_read_env_key_or_call_model() -> None:
    source = Path("aico_v0/negative_safety.py").read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "dotenv" not in source
    assert "importlib" not in source
    assert ".call_model(" not in source
    assert "generate_content(" not in source
    assert ".env" not in source


def test_agents_and_claude_remain_byte_identical() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
