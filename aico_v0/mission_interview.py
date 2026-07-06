# P4A 미션 인터뷰 결과를 규칙 기반 no-call 데이터로 구성한다.
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from .artifact_safety import scan_artifacts

P4A_SCHEMA_VERSION = "p4a_mission_interview.v1"
P4A_MAX_TITLE_CHARS = 80
P4A_MIN_CLEAR_MISSION_CHARS = 24

MissionInterviewMode = Literal["draft", "review"]
MissionInterviewResultStatus = Literal["ready", "needs_clarification", "blocked"]
MissionRiskSeverity = Literal["LOW", "MEDIUM", "HIGH", "BLOCKING"]

QUESTION_CATEGORIES = (
    "objective",
    "input_files",
    "output_format",
    "success_criteria",
    "constraints",
    "safety_boundary",
    "deadline_or_priority",
    "unknowns",
)

BLOCKING_RISK_IDS = {
    "live_call_requested",
    "worker_orchestration_requested",
    "shell_requested",
    "secret_or_env_requested",
    "destructive_action",
}

RISK_DEFINITIONS: tuple[tuple[str, str, MissionRiskSeverity, str, str, tuple[str, ...]], ...] = (
    (
        "live_call_requested",
        "safety_boundary",
        "BLOCKING",
        "Mission asks for a live/API/model/provider call, which P4A cannot execute.",
        "Keep P4A as no-call and move any live-call request to a later explicit approval phase.",
        ("live call", "api call", "llm call", "provider call", "call the model", "use model", "use gemini"),
    ),
    (
        "worker_orchestration_requested",
        "safety_boundary",
        "BLOCKING",
        "Mission asks for worker orchestration, which P4A does not open.",
        "Keep worker orchestration blocked and clarify the mission as a no-call brief first.",
        ("worker pool", "orchestrate workers", "dispatch worker", "multi-agent", "manager run", "auditor run"),
    ),
    (
        "shell_requested",
        "safety_boundary",
        "BLOCKING",
        "Mission asks for shell or command execution.",
        "Clarify whether this can be handled as a no-call planning task before any execution phase.",
        ("shell", "command", "terminal", "powershell", "bash", "cmd.exe", "run pytest", "execute"),
    ),
    (
        "web_requested",
        "safety_boundary",
        "HIGH",
        "Mission asks for web access or browsing.",
        "Keep web access closed in P4A and ask for local inputs or defer to a later approved phase.",
        ("web search", "browse", "internet", "external url", "http://", "https://"),
    ),
    (
        "repo_or_github_requested",
        "safety_boundary",
        "HIGH",
        "Mission asks for repo clone or GitHub automation.",
        "Keep repo/GitHub automation closed in P4A and clarify local-file scope only.",
        ("repo clone", "clone repo", "github issue", "pull request", "merge pr", "github"),
    ),
    (
        "parallel_requested",
        "safety_boundary",
        "HIGH",
        "Mission asks for parallel execution.",
        "Keep parallel execution closed in P4A and split work into a sequential no-call plan.",
        ("parallel", "concurrently", "simultaneously", "fan-out"),
    ),
    (
        "file_write_requested",
        "scope",
        "HIGH",
        "Mission asks for file creation or modification.",
        "Clarify whether P4A should only draft a mission brief instead of changing files.",
        ("edit file", "modify file", "write file", "create file", "apply patch", "git commit"),
    ),
    (
        "secret_or_env_requested",
        "safety_boundary",
        "BLOCKING",
        "Mission asks for secret, key, token, or environment value access.",
        "Do not read secrets in P4A; ask the user to provide non-secret metadata only.",
        ("secret", "api key", "token", ".env", "environment variable", "env value", "private key"),
    ),
    (
        "destructive_action",
        "safety_boundary",
        "BLOCKING",
        "Mission asks for destructive action.",
        "Block execution and require a separate explicit safety review.",
        ("delete", "remove all", "drop database", "format disk", "wipe", "reset --hard"),
    ),
)


class MissionInterviewError(RuntimeError):
    def __init__(self, condition: str, failure_type: str) -> None:
        self.condition = condition
        self.failure_type = failure_type
        super().__init__(condition)


@dataclass(frozen=True)
class MissionInterviewInput:
    mission_text: str
    source_path: str | None = None
    user_context: dict[str, str] | None = None
    mode: MissionInterviewMode = "draft"
    max_questions: int = 8


@dataclass(frozen=True)
class MissionInterviewQuestion:
    id: str
    question: str
    reason: str
    required: bool
    category: str


@dataclass(frozen=True)
class MissionRiskFlag:
    id: str
    category: str
    severity: MissionRiskSeverity
    message: str
    recommended_action: str


@dataclass(frozen=True)
class NormalizedMissionBrief:
    title: str
    objective: str
    explicit_requirements: list[str]
    constraints: list[str]
    out_of_scope: list[str]
    assumptions: list[str]
    missing_information: list[str]
    risk_flags: list[MissionRiskFlag]
    recommended_next_action: str


@dataclass(frozen=True)
class MissionInterviewResult:
    schema_version: str
    result: MissionInterviewResultStatus
    normalized_brief: NormalizedMissionBrief
    questions: list[MissionInterviewQuestion]
    risk_flags: list[MissionRiskFlag]
    no_call: bool
    worker_orchestration: bool
    live_call_allowed: bool
    call_model_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_mission_interview(interview_input: MissionInterviewInput) -> MissionInterviewResult:
    normalized_text = normalize_mission_text(interview_input.mission_text)
    risks = detect_mission_risks(normalized_text)
    missing = detect_missing_information(normalized_text)
    questions = build_clarification_questions(normalized_text, missing, risks, interview_input.max_questions)
    result_status = _decide_result(questions, missing, risks)
    brief = NormalizedMissionBrief(
        title=_build_title(normalized_text),
        objective=_build_objective(normalized_text),
        explicit_requirements=extract_obvious_requirements(normalized_text),
        constraints=_extract_constraints(normalized_text),
        out_of_scope=_extract_out_of_scope(normalized_text),
        assumptions=_build_assumptions(interview_input),
        missing_information=missing,
        risk_flags=risks,
        recommended_next_action=_recommended_next_action(result_status),
    )
    return MissionInterviewResult(
        schema_version=P4A_SCHEMA_VERSION,
        result=result_status,
        normalized_brief=brief,
        questions=questions,
        risk_flags=risks,
        no_call=True,
        worker_orchestration=False,
        live_call_allowed=False,
        call_model_count=0,
    )


def normalize_mission_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def extract_obvious_requirements(text: str) -> list[str]:
    normalized = normalize_mission_text(text)
    if not normalized:
        return []
    parts = [part.strip(" -.;") for part in re.split(r"(?<=[.!?])\s+|;\s+", normalized) if part.strip()]
    return parts[:8]


def detect_missing_information(text: str) -> list[str]:
    normalized = normalize_mission_text(text)
    lowered = normalized.lower()
    missing: list[str] = []
    if len(normalized) < P4A_MIN_CLEAR_MISSION_CHARS or _looks_like_unclear_objective(lowered):
        missing.append("objective")
    if _mentions_input_file(lowered) and not _has_filename(normalized):
        missing.append("input_files")
    if not _has_output_format(lowered):
        missing.append("output_format")
    if not _has_success_criteria(lowered):
        missing.append("success_criteria")
    if not _has_constraints(lowered):
        missing.append("constraints")
    return _dedupe(missing)


def build_clarification_questions(
    text: str,
    missing_information: list[str] | None = None,
    risk_flags: list[MissionRiskFlag] | None = None,
    max_questions: int = 8,
) -> list[MissionInterviewQuestion]:
    missing = missing_information if missing_information is not None else detect_missing_information(text)
    risks = risk_flags if risk_flags is not None else detect_mission_risks(text)
    questions: list[MissionInterviewQuestion] = []
    for category in missing:
        questions.append(_question_for_missing(category))
    if any(risk.category == "safety_boundary" for risk in risks):
        questions.append(
            MissionInterviewQuestion(
                id="q_safety_boundary",
                question="Which requested actions must remain no-call and no-execution for this mission?",
                reason="P4A must clarify safety boundaries before any downstream work.",
                required=True,
                category="safety_boundary",
            )
        )
    if "deadline_or_priority" not in missing and not _has_deadline_or_priority(text.lower()):
        questions.append(
            MissionInterviewQuestion(
                id="q_deadline_or_priority",
                question="Is there a deadline or priority level for this mission?",
                reason="Priority helps sequence later work without changing P4A no-call scope.",
                required=False,
                category="deadline_or_priority",
            )
        )
    deduped = _dedupe_questions(questions)
    limit = max(0, max_questions)
    return deduped[:limit]


def detect_mission_risks(text: str) -> list[MissionRiskFlag]:
    normalized = normalize_mission_text(text)
    lowered = normalized.lower()
    risks: list[MissionRiskFlag] = []
    for risk_id, category, severity, message, action, needles in RISK_DEFINITIONS:
        if any(needle in lowered for needle in needles):
            risks.append(MissionRiskFlag(risk_id, category, severity, message, action))
    if _looks_broad(normalized):
        risks.append(
            MissionRiskFlag(
                "broad_scope",
                "scope",
                "MEDIUM",
                "Mission scope appears broad for a first no-call brief.",
                "Split the request into a smaller mission with explicit acceptance criteria.",
            )
        )
    if "output_format" in detect_missing_information(normalized):
        risks.append(
            MissionRiskFlag(
                "missing_output_format",
                "output_format",
                "MEDIUM",
                "Mission does not specify an output format.",
                "Ask the user to choose the expected artifact or response format.",
            )
        )
    if "success_criteria" in detect_missing_information(normalized):
        risks.append(
            MissionRiskFlag(
                "missing_success_criteria",
                "success_criteria",
                "MEDIUM",
                "Mission does not define success criteria.",
                "Ask the user how completion should be verified.",
            )
        )
    if "objective" in detect_missing_information(normalized):
        risks.append(
            MissionRiskFlag(
                "unclear_objective",
                "objective",
                "LOW",
                "Mission objective is too short or unclear.",
                "Ask for a concrete objective before dispatch.",
            )
        )
    return _dedupe_risks(risks)


def write_mission_interview_result(result: MissionInterviewResult | Mapping[str, Any], output_path: str | Path) -> None:
    payload = result.to_dict() if isinstance(result, MissionInterviewResult) else dict(result)
    _validate_result_payload(payload)
    path = Path(output_path)
    if "://" in str(path):
        raise MissionInterviewError("artifact path URL blocked", "SECURITY_BLOCKED")
    if ".." in path.parts:
        raise MissionInterviewError("artifact path traversal blocked", "SECURITY_BLOCKED")
    scan = scan_artifacts({path.name: payload})
    if not scan.ok:
        reason = scan.findings[0].reason if scan.findings else "artifact safety scan failed"
        raise MissionInterviewError(reason, scan.failure_type or "SECURITY_BLOCKED")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _validate_result_payload(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != P4A_SCHEMA_VERSION:
        raise MissionInterviewError("invalid schema_version", "CONFIG_ERROR")
    if payload.get("no_call") is not True:
        raise MissionInterviewError("no_call invariant violated", "SECURITY_BLOCKED")
    if payload.get("worker_orchestration") is not False:
        raise MissionInterviewError("worker_orchestration invariant violated", "SECURITY_BLOCKED")
    if payload.get("live_call_allowed") is not False:
        raise MissionInterviewError("live_call_allowed invariant violated", "SECURITY_BLOCKED")
    if payload.get("call_model_count") != 0:
        raise MissionInterviewError("call_model_count invariant violated", "SECURITY_BLOCKED")
    _block_forbidden_payload_fields(payload)


def _block_forbidden_payload_fields(value: Any, path: str = "payload") -> None:
    forbidden = {
        "raw_key",
        "raw_key_value",
        "key_value",
        "env_var_value",
        "raw_approval_phrase",
        "raw_provider_request",
        "raw_provider_response",
        "provider_response",
        "provider_config",
        "raw_output",
        "raw_model_output",
        "raw_response_body",
        "raw_headers",
        "token_usage",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in forbidden:
                raise MissionInterviewError(f"{path}.{key_text} field blocked", "SECURITY_BLOCKED")
            _block_forbidden_payload_fields(item, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _block_forbidden_payload_fields(item, f"{path}[{index}]")


def _decide_result(
    questions: list[MissionInterviewQuestion], missing: list[str], risks: list[MissionRiskFlag]
) -> MissionInterviewResultStatus:
    if any(risk.severity == "BLOCKING" for risk in risks):
        return "blocked"
    if any(question.required for question in questions) or missing or any(risk.severity in {"MEDIUM", "HIGH"} for risk in risks):
        return "needs_clarification"
    return "ready"


def _question_for_missing(category: str) -> MissionInterviewQuestion:
    questions = {
        "objective": ("What concrete outcome should this mission achieve?", "The objective is too short or unclear."),
        "input_files": ("Which exact input file paths should be used?", "The mission mentions input files without naming them."),
        "output_format": ("What output format should be produced?", "The mission does not specify an output format."),
        "success_criteria": ("How should completion be verified?", "The mission does not define success criteria."),
        "constraints": ("What constraints or non-goals should bound this mission?", "The mission does not state constraints."),
    }
    question, reason = questions.get(category, ("What missing context should be clarified?", "The mission has unknowns."))
    return MissionInterviewQuestion(
        id=f"q_{category}",
        question=question,
        reason=reason,
        required=True,
        category=category if category in QUESTION_CATEGORIES else "unknowns",
    )


def _build_title(text: str) -> str:
    if not text:
        return "Untitled mission"
    title = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()
    return title[:P4A_MAX_TITLE_CHARS] or "Untitled mission"


def _build_objective(text: str) -> str:
    return text or "Objective requires clarification."


def _extract_constraints(text: str) -> list[str]:
    lowered = text.lower()
    constraints = []
    for marker in ("no-call", "no call", "offline", "do not", "must not", "without"):
        if marker in lowered:
            constraints.append(f"Constraint mentioned: {marker}")
    return constraints


def _extract_out_of_scope(text: str) -> list[str]:
    lowered = text.lower()
    out = []
    for marker in ("out of scope", "exclude", "do not", "must not"):
        if marker in lowered:
            out.append(f"Out-of-scope marker mentioned: {marker}")
    return out


def _build_assumptions(interview_input: MissionInterviewInput) -> list[str]:
    assumptions = ["P4A output is no-call/data-only and does not grant execution authority."]
    if interview_input.source_path:
        assumptions.append(f"Mission source path is metadata only: {interview_input.source_path}")
    if interview_input.user_context:
        assumptions.append("User context was provided as non-secret metadata.")
    return assumptions


def _recommended_next_action(result_status: str) -> str:
    if result_status == "blocked":
        return "Resolve blocking safety risks before any worker dispatch or live execution."
    if result_status == "needs_clarification":
        return "Ask the clarification questions and rebuild the mission brief."
    return "Proceed to a no-call mission approval review before any dispatch."


def _mentions_input_file(lowered: str) -> bool:
    return any(token in lowered for token in ("file", "document", "pdf", "csv", "xlsx", "input"))


def _has_filename(text: str) -> bool:
    return bool(re.search(r"\b[\w.-]+\.(?:md|txt|pdf|csv|xlsx|docx|json|py|ts|js)\b", text, re.IGNORECASE))


def _has_output_format(lowered: str) -> bool:
    return any(token in lowered for token in ("output format", "markdown", "json", "csv", "table", "report", "brief", "checklist"))


def _has_success_criteria(lowered: str) -> bool:
    return any(token in lowered for token in ("success criteria", "acceptance", "done when", "passes", "verify", "validated", "test"))


def _has_constraints(lowered: str) -> bool:
    return any(token in lowered for token in ("constraint", "non-goal", "out of scope", "do not", "must not", "no-call", "offline"))


def _has_deadline_or_priority(lowered: str) -> bool:
    return any(token in lowered for token in ("deadline", "priority", "urgent", "today", "tomorrow"))


def _looks_like_unclear_objective(lowered: str) -> bool:
    return lowered in {"help", "fix", "review", "do this", "make it better", "improve"} or len(lowered.split()) < 4


def _looks_broad(text: str) -> bool:
    lowered = text.lower()
    return len(text) > 900 or any(token in lowered for token in ("everything", "entire project", "full system", "all files"))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _dedupe_questions(questions: list[MissionInterviewQuestion]) -> list[MissionInterviewQuestion]:
    seen: set[str] = set()
    result: list[MissionInterviewQuestion] = []
    for question in questions:
        if question.id not in seen:
            seen.add(question.id)
            result.append(question)
    return result


def _dedupe_risks(risks: list[MissionRiskFlag]) -> list[MissionRiskFlag]:
    seen: set[str] = set()
    result: list[MissionRiskFlag] = []
    for risk in risks:
        if risk.id not in seen:
            seen.add(risk.id)
            result.append(risk)
    return result
