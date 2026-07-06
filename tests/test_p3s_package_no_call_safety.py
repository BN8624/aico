# P3S package assembly helper가 SDK, key, network, live call 경로를 열지 않는지 검증합니다.
from __future__ import annotations

import ast
from pathlib import Path

from aico_v0.pre_live_package import assemble_pre_live_package

from tests.test_p3s_pre_live_package import p3s_inputs


def test_p3s_helpers_keep_all_no_call_counters_closed() -> None:
    summary = assemble_pre_live_package(**p3s_inputs()).to_summary()

    assert summary["live_call_allowed"] is False
    assert summary["model_call_count"] == 0
    assert summary["call_model_count"] == 0
    assert summary["raw_output_saved"] is False
    assert summary["artifact_safety_pre_scan_status"] == "pass"
    assert summary["artifact_safety_post_scan_status"] == "pass"


def test_p3s_runtime_imports_no_provider_sdk_or_network_modules() -> None:
    tree = ast.parse(Path("aico_v0/pre_live_package.py").read_text(encoding="utf-8"))
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


def test_p3s_runtime_reads_no_env_key_network_or_call_model() -> None:
    source = Path("aico_v0/pre_live_package.py").read_text(encoding="utf-8")
    forbidden_strings = [
        "getenv(",
        "environ.get(",
        "os.environ",
        "call_model(",
        ".call_model(",
        "urlopen(",
        ".request(",
        ".connect(",
        ".send(",
    ]
    for needle in forbidden_strings:
        assert needle not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"call_model", "request", "urlopen", "connect", "send"}
            elif isinstance(node.func, ast.Name):
                assert node.func.id not in {"call_model", "getenv"}


def test_p3s_does_not_import_provider_sdk_in_runtime_modules() -> None:
    runtime_files = [
        Path("aico_v0/pre_live_package.py"),
        Path("aico_v0/live_execution_boundary.py"),
        Path("aico_v0/no_call_integration.py"),
        Path("aico_v0/approval_package.py"),
        Path("aico_v0/activation_guards.py"),
    ]
    forbidden_roots = {"google", "genai", "openai", "anthropic", "requests", "httpx", "socket"}
    for path in runtime_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(alias.name.split(".")[0] in forbidden_roots for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden_roots


def test_agents_and_claude_remain_byte_identical() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
