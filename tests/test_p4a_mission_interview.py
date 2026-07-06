# P4A 미션 인터뷰 no-call helper의 판정과 안전 불변식을 검증한다.
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aico_v0.mission_interview import (
    MissionInterviewError,
    MissionInterviewInput,
    build_mission_interview,
    detect_mission_risks,
    write_mission_interview_result,
)


def build(text: str, *, max_questions: int = 8):
    return build_mission_interview(MissionInterviewInput(mission_text=text, max_questions=max_questions))


def clear_mission_text() -> str:
    return (
        "Create a Markdown brief from input.md. Output format: Markdown. "
        "Success criteria: verify the brief includes three bullet points. "
        "Constraint: no-call only and no worker dispatch."
    )


def risk_ids(result) -> set[str]:
    return {risk.id for risk in result.risk_flags}


def question_categories(result) -> set[str]:
    return {question.category for question in result.questions}


def test_clear_mission_returns_ready() -> None:
    result = build(clear_mission_text())
    assert result.result == "ready"
    assert not any(question.required for question in result.questions)
    assert result.normalized_brief.title.startswith("Create a Markdown brief")


def test_short_vague_mission_returns_needs_clarification() -> None:
    result = build("Fix it")
    assert result.result == "needs_clarification"
    assert "unclear_objective" in risk_ids(result)
    assert "objective" in question_categories(result)


def test_missing_output_format_creates_output_format_question() -> None:
    result = build("Summarize input.md. Success criteria: verify the summary is accurate. Constraint: no-call.")
    assert result.result == "needs_clarification"
    assert "output_format" in question_categories(result)


def test_missing_success_criteria_creates_success_criteria_question() -> None:
    result = build("Summarize input.md as Markdown. Constraint: no-call.")
    assert result.result == "needs_clarification"
    assert "success_criteria" in question_categories(result)


def test_mentioned_input_file_without_filename_creates_input_files_question() -> None:
    result = build(
        "Summarize the input file as Markdown. Success criteria: verify the key points. Constraint: no-call."
    )
    assert result.result == "needs_clarification"
    assert "input_files" in question_categories(result)


def test_max_questions_is_respected() -> None:
    result = build("Help with the file and web search, then write output", max_questions=2)
    assert len(result.questions) == 2


@pytest.mark.parametrize(
    ("mission", "risk_id"),
    [
        ("Make a live call to the provider. Output format: JSON. Success criteria: verify count.", "live_call_requested"),
        (
            "Dispatch a worker pool for this mission. Output format: Markdown. Success criteria: verify plan.",
            "worker_orchestration_requested",
        ),
        ("Run a shell command to inspect files. Output format: text. Success criteria: command passes.", "shell_requested"),
        ("Read the API key from .env. Output format: JSON. Success criteria: key found.", "secret_or_env_requested"),
        ("Delete all generated files. Output format: log. Success criteria: files removed.", "destructive_action"),
    ],
)
def test_blocking_risks_block_result(mission: str, risk_id: str) -> None:
    result = build(mission)
    assert result.result == "blocked"
    assert risk_id in risk_ids(result)
    assert any(risk.id == risk_id and risk.severity == "BLOCKING" for risk in result.risk_flags)


@pytest.mark.parametrize(
    ("mission", "risk_id"),
    [
        ("Use web search to prepare a Markdown report. Success criteria: verify citations. Constraint: no-call.", "web_requested"),
        ("Clone the GitHub repo and make a Markdown report. Success criteria: verify summary.", "repo_or_github_requested"),
        ("Run tasks in parallel and return JSON. Success criteria: verify all tasks listed.", "parallel_requested"),
    ],
)
def test_high_risks_are_not_ready(mission: str, risk_id: str) -> None:
    result = build(mission)
    assert result.result == "needs_clarification"
    assert any(risk.id == risk_id and risk.severity == "HIGH" for risk in result.risk_flags)


def test_broad_mission_creates_broad_scope_risk() -> None:
    result = build(
        "Analyze the entire project and improve everything. Output format: Markdown report. "
        "Success criteria: verify all issues are listed. Constraint: no-call."
    )
    assert "broad_scope" in risk_ids(result)


def test_no_call_invariants_always_hold() -> None:
    for mission in [clear_mission_text(), "Fix it", "Run a shell command and output JSON. Success criteria: verify."]:
        result = build(mission)
        assert result.no_call is True
        assert result.worker_orchestration is False
        assert result.live_call_allowed is False
        assert result.call_model_count == 0


def test_artifact_writer_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "mission_interview_result.json"
    result = build(clear_mission_text())
    write_mission_interview_result(result, output)
    text = output.read_text(encoding="utf-8")
    assert '"schema_version": "p4a_mission_interview.v1"' in text
    assert '"no_call": true' in text


@pytest.mark.parametrize(
    "payload_update",
    [
        {"normalized_brief": {"title": "api_key=abcdefghijklmnop"}},
        {"normalized_brief": {"title": "Bearer abcdefghijklmnopqrstuvwxyz"}},
        {"normalized_brief": {"title": "-----BEGIN PRIVATE KEY-----"}},
        {"provider_response": {"text": "raw"}},
        {"raw_output": "raw"},
        {"token_usage": {"input": 1}},
    ],
)
def test_artifact_writer_rejects_raw_leak_shapes(tmp_path: Path, payload_update: dict[str, object]) -> None:
    payload = build(clear_mission_text()).to_dict()
    payload.update(payload_update)
    with pytest.raises(MissionInterviewError) as exc_info:
        write_mission_interview_result(payload, tmp_path / "mission_interview_result.json")
    assert exc_info.value.failure_type == "SECURITY_BLOCKED"


def test_helper_does_not_read_env_import_provider_sdk_or_call_network_or_call_model() -> None:
    source_path = Path("aico_v0/mission_interview.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = {"os", "socket", "requests", "httpx", "urllib.request", "google", "genai", "openai", "anthropic"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name for alias in node.names}
            assert forbidden_modules.isdisjoint(imported)
        if isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden_modules
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                assert func.attr not in {"getenv", "call_model", "request", "urlopen"}
            if isinstance(func, ast.Name):
                assert func.id not in {"call_model"}
    assert ".environ" not in source
    assert "load_dotenv" not in source


def test_default_path_does_not_execute_live_smoke() -> None:
    result = build(clear_mission_text())
    assert result.no_call is True
    assert result.live_call_allowed is False
    assert result.call_model_count == 0
    assert not detect_mission_risks("Prepare a Markdown brief. Success criteria: verify. Constraint: no-call.")


def test_agents_and_claude_remain_byte_identical() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
