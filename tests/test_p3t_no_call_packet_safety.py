# P3T packet 경계가 SDK, key, network, call_model 실행 경로를 열지 않는지 검증합니다.
from __future__ import annotations

import ast
from pathlib import Path

from aico_v0.final_live_approval_packet import (
    FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
    HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
    build_final_live_approval_packet,
    final_live_approval_packet_default_runtime_creation_enabled,
    human_confirmation_checklist_default_runtime_creation_enabled,
)
from aico_v0.live_execution_boundary import CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME, call_attempt_summary_default_runtime_creation_enabled
from aico_v0.no_call_integration import (
    NO_CALL_INTEGRATION_ARTIFACT_NAME,
    no_call_integration_default_runtime_creation_enabled,
)
from aico_v0.pre_live_package import (
    PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME,
    pre_live_package_default_runtime_creation_enabled,
)
from tests.test_p3t_final_live_approval_packet import p3t_inputs


FORBIDDEN_IMPORT_ROOTS = {"requests", "httpx", "socket", "google", "genai", "openai", "anthropic", "dotenv"}
FORBIDDEN_IMPORT_MODULES = {"urllib.request"}
FORBIDDEN_ENV_READ_MARKERS = ("getenv(", "environ.get(", "os.environ")
P3T_BOUNDARY_FILES = (
    Path("aico_v0/final_live_approval_packet.py"),
    Path("aico_v0/pre_live_package.py"),
    Path("aico_v0/live_execution_boundary.py"),
)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_p3t_runtime_imports_no_provider_sdk_or_network_modules() -> None:
    modules = imported_modules(Path("aico_v0/final_live_approval_packet.py"))

    violations = [
        module
        for module in modules
        if module.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS or module in FORBIDDEN_IMPORT_MODULES
    ]

    assert violations == []


def test_p3t_source_reads_no_env_or_key_value_and_uses_no_network_strings() -> None:
    source = Path("aico_v0/final_live_approval_packet.py").read_text(encoding="utf-8")

    assert all(marker not in source for marker in FORBIDDEN_ENV_READ_MARKERS)
    assert "requests." not in source
    assert "httpx." not in source
    assert "urllib.request" not in source
    assert "socket." not in source
    assert "google." not in source
    assert "genai" not in source
    assert "openai" not in source
    assert "anthropic" not in source


def test_p3t_p3s_p3r_boundaries_do_not_call_call_model() -> None:
    for path in P3T_BOUNDARY_FILES:
        source = path.read_text(encoding="utf-8")
        assert "call_model(" not in source
        assert ".call_model(" not in source


def test_default_runtime_paths_do_not_create_pre_live_or_final_approval_artifacts(tmp_path: Path) -> None:
    assert final_live_approval_packet_default_runtime_creation_enabled() is False
    assert human_confirmation_checklist_default_runtime_creation_enabled() is False
    assert pre_live_package_default_runtime_creation_enabled() is False
    assert no_call_integration_default_runtime_creation_enabled() is False
    assert call_attempt_summary_default_runtime_creation_enabled() is False

    for artifact_name in (
        "approval_package.json",
        NO_CALL_INTEGRATION_ARTIFACT_NAME,
        CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
        PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME,
        FINAL_LIVE_APPROVAL_PACKET_ARTIFACT_NAME,
        HUMAN_CONFIRMATION_CHECKLIST_ARTIFACT_NAME,
        "live_smoke_result.json",
    ):
        assert not (tmp_path / artifact_name).exists()
        assert not Path(artifact_name).exists()


def test_agents_and_claude_remain_byte_identical() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()


def test_packet_helpers_keep_no_call_counters_closed() -> None:
    inputs = p3t_inputs()
    packet = build_final_live_approval_packet(
        pre_live_package_manifest=inputs["pre_live_package_manifest"],
        approval_package_summary=inputs["approval_package"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        artifact_safety_summary=inputs["artifact_safety_summary"],
        runtime_flags_summary=inputs["runtime_flags_summary"],
        rollback_plan_summary=inputs["rollback_plan_summary"],
        test_evidence_summary=inputs["test_evidence_summary"],
        human_decision_summary=inputs["human_decision_summary"],
    ).to_summary()

    assert packet["execution_allowed"] is False
    assert packet["live_call_allowed"] is False
    assert packet["model_call_count"] == 0
    assert packet["call_model_count"] == 0
    assert packet["raw_output_saved"] is False
    assert packet["ready_for_human_review"] is True
