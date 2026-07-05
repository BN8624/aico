# P3E 기본 테스트가 offline-only이며 live marker가 실행을 열지 않는지 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

from aico_v0.live_test_policy import live_provider_marker_policy, should_skip_live_provider_test


def test_default_pytest_remains_offline_only() -> None:
    policy = live_provider_marker_policy()

    assert policy["marker"] == "live_provider"
    assert policy["default_enabled"] is False
    assert policy["default_skip"] is True
    assert should_skip_live_provider_test() is True


def test_live_provider_marker_is_registered_but_non_executing_by_default() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "live_provider" in pyproject
    assert should_skip_live_provider_test(explicit_enable=True) is True


def test_runtime_package_has_no_forbidden_sdk_network_or_env_value_imports() -> None:
    forbidden_roots = {"requests", "httpx", "socket", "google", "openai", "anthropic", "genai", "dotenv"}
    forbidden_exact = {"urllib.request", "os.environ"}
    imports: set[str] = set()
    runtime_paths = [path for path in Path("aico_v0").glob("*.py")]
    for path in runtime_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

    assert not any(name.split(".")[0] in forbidden_roots for name in imports)
    assert not any(name in forbidden_exact for name in imports)


def test_p3e_runtime_has_no_live_call_counters_or_key_usage() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("aico_v0").glob("*.py")).lower()
    raw_key_calls = []
    for path in Path("aico_v0").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "raw_key_value":
                raw_key_calls.append((path, node.lineno))

    assert "actual_api_call_count += 1" not in source
    assert "actual_llm_call_count += 1" not in source
    assert raw_key_calls == []
    assert "os.environ" not in source


def test_agents_and_claude_remain_byte_identical_for_p3e() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
