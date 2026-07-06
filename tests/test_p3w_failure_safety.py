# P3W 실패 경로가 retry 없이 안전 산출물만 남기는지 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

from aico_v0.controlled_live_smoke import (
    P3W_CONFIRM_PHRASE,
    build_p3w_live_smoke_config,
    run_controlled_single_call_live_smoke,
)


def test_pre_call_scan_failure_blocks_provider_call(tmp_path: Path) -> None:
    calls: list[int] = []
    cfg = build_p3w_live_smoke_config(
        provider="google_gemini",
        model="gemini-live-smoke-test",
        key_slot="worker_1",
        confirm_phrase=P3W_CONFIRM_PHRASE,
        live_smoke_opt_in=True,
        mission="Search the web.",
    )
    result = run_controlled_single_call_live_smoke(
        config=cfg,
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(1) or "should not happen",
    )
    assert calls == []
    assert result.actual_provider_call_count == 0
    assert result.failure_type == "SECURITY_BLOCKED"


def test_missing_key_maps_config_error_without_provider_call(tmp_path: Path) -> None:
    calls: list[int] = []
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(
            provider="google_gemini",
            model="gemini-live-smoke-test",
            key_slot="worker_1",
            confirm_phrase=P3W_CONFIRM_PHRASE,
            live_smoke_opt_in=True,
        ),
        env={},
        run_dir=tmp_path,
        provider_caller=lambda key, model, mission: calls.append(1) or "should not happen",
    )
    assert calls == []
    assert result.failure_type == "CONFIG_ERROR"
    assert result.actual_provider_call_count == 0


def test_default_pytest_does_not_execute_actual_live_smoke(tmp_path: Path) -> None:
    assert not Path("call_attempt_summary.json").exists()
    assert not Path("live_smoke_result.json").exists()
    assert not Path("artifact_safety_report.json").exists()
    assert not (tmp_path / "call_attempt_summary.json").exists()


def test_p3w_live_smoke_requires_explicit_opt_in(tmp_path: Path) -> None:
    result = run_controlled_single_call_live_smoke(
        config=build_p3w_live_smoke_config(
            provider="google_gemini",
            model="gemini-live-smoke-test",
            key_slot="worker_1",
            confirm_phrase=P3W_CONFIRM_PHRASE,
            live_smoke_opt_in=False,
        ),
        env={"AICO_WORKER_1_API_KEY": "test-key-for-fake-provider"},
        run_dir=tmp_path,
    )
    assert result.failure_type == "HUMAN_DECISION_REQUIRED"
    assert result.actual_provider_call_count == 0


def test_p3w_module_has_no_top_level_provider_sdk_imports() -> None:
    tree = ast.parse(Path("aico_v0/controlled_live_smoke.py").read_text(encoding="utf-8"))
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


def test_p3w_reads_no_key_or_env_values_outside_boundary() -> None:
    source = Path("aico_v0/controlled_live_smoke.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions_with_env_read: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            segment = ast.get_source_segment(source, node) or ""
            if "os.environ" in segment:
                functions_with_env_read.add(node.name)
    assert functions_with_env_read == {"build_p3w_live_smoke_config", "read_single_p3w_key_value"}
    assert "dotenv" not in source
    assert "open(" not in source


def test_p3w_does_not_use_call_model_method_name() -> None:
    source = Path("aico_v0/controlled_live_smoke.py").read_text(encoding="utf-8")
    assert ".call_model(" not in source


def test_agents_and_claude_remain_byte_identical() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
