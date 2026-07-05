# P3P 승인 문구와 승인 패키지 스켈레톤이 호출 권한을 열지 않는지 검증한다.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aico_v0.approval_package import (
    APPROVAL_PACKAGE_ARTIFACT_NAME,
    ApprovalFinalGateLinkage,
    ApprovalPackage,
    approval_package_default_runtime_creation_enabled,
    build_approval_final_gate_linkage,
    build_approval_package,
    validate_approval_final_gate_linkage,
    validate_approval_package_payload,
    write_approval_package,
)
from aico_v0.approval_phrase import (
    P3PApprovalError,
    build_approval_phrase_hash,
    parse_approval_phrase,
    validate_final_key_slot,
    validate_final_model,
    validate_final_provider,
)

RAW_SECRET = "sk-" + "p3p-approval-secret-value"


def approval_phrase(**overrides: str) -> str:
    fields = {
        "provider": "google_gemini",
        "model": "user-approved-model",
        "key_slot": "worker_1",
        "max_model_calls": "1",
        "max_retries_per_call": "0",
        "max_runtime_seconds": "60",
        "allow_raw_output": "false",
    }
    fields.update(overrides)
    return "\n".join(
        [
            "I approve AICO first live smoke for this run only:",
            *(f"{key} = {value}" for key, value in fields.items() if value != "<omit>"),
        ]
    )


def parsed_package() -> tuple[str, object, ApprovalPackage]:
    phrase = approval_phrase()
    parsed = parse_approval_phrase(phrase)
    digest = build_approval_phrase_hash(phrase)
    package = build_approval_package(parsed=parsed, run_id="run-p3p-001", approval_phrase_hash=digest)
    return digest, parsed, package


def final_gate_payload(run_id: str = "run-p3p-001", **overrides: object) -> dict[str, object]:
    payload = {
        "run_id": run_id,
        "status": "ready_for_review",
        "live_call_allowed": False,
        "model_call_count": 0,
        "raw_output_saved": False,
        "errors": [],
    }
    payload.update(overrides)
    return payload


def assert_failure(exc_info: pytest.ExceptionInfo[P3PApprovalError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_exact_approval_phrase_parses() -> None:
    parsed = parse_approval_phrase(approval_phrase())

    assert parsed.provider == "google_gemini"
    assert parsed.model == "user-approved-model"
    assert parsed.key_slot == "worker_1"
    assert parsed.max_model_calls == 1
    assert parsed.max_retries_per_call == 0
    assert parsed.max_runtime_seconds == 60
    assert parsed.allow_raw_output is False
    assert "I approve AICO" not in repr(parsed)


@pytest.mark.parametrize("phrase", ["OK", "continue", "승인", "진행해"])
def test_generic_approval_phrase_rejected(phrase: str) -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        parse_approval_phrase(phrase)
    assert_failure(exc_info, "HUMAN_DECISION_REQUIRED")


def test_missing_approval_maps_human_decision_required() -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        parse_approval_phrase(None)
    assert_failure(exc_info, "HUMAN_DECISION_REQUIRED")


def test_missing_required_approval_field_maps_human_decision_required() -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        parse_approval_phrase(approval_phrase(model="<omit>"))
    assert_failure(exc_info, "HUMAN_DECISION_REQUIRED")


@pytest.mark.parametrize(
    "overrides",
    [
        {"allow_raw_output": "true"},
        {"max_model_calls": "2"},
        {"max_retries_per_call": "1"},
        {"provider": "https://provider.example"},
        {"provider": "generativelanguage.googleapis.com"},
        {"model": RAW_SECRET},
    ],
)
def test_unsafe_approval_fields_map_security_blocked(overrides: dict[str, str]) -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        parse_approval_phrase(approval_phrase(**overrides))
    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_multiple_key_slots_maps_human_decision_required() -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        parse_approval_phrase(approval_phrase(key_slot="worker_1, worker_2"))
    assert_failure(exc_info, "HUMAN_DECISION_REQUIRED")


def test_parser_does_not_copy_raw_approval_phrase_into_error_or_repr() -> None:
    raw_phrase = approval_phrase(model=RAW_SECRET)
    with pytest.raises(P3PApprovalError) as exc_info:
        parse_approval_phrase(raw_phrase)

    assert raw_phrase not in str(exc_info.value)
    assert raw_phrase not in repr(exc_info.value)
    assert RAW_SECRET not in str(exc_info.value)


def test_approval_phrase_hash_is_safe() -> None:
    digest = build_approval_phrase_hash(approval_phrase())

    assert len(digest) == 64
    assert digest.isalnum()
    assert RAW_SECRET not in digest


def test_approval_package_schema_validates_happy_path() -> None:
    digest, _, package = parsed_package()
    payload = package.to_summary()

    assert payload["schema_version"] == "p3_first_live_smoke_approval_v1"
    assert payload["approval_phrase_hash"] == digest
    assert payload["raw_output_saved"] is False
    assert payload["live_call_allowed"] is False
    assert payload["model_call_count_before_execution"] == 0
    assert "approval_phrase" not in payload
    assert "raw_output" not in payload
    assert "endpoint_url" not in payload


@pytest.mark.parametrize(
    "payload_update",
    [
        {"approval_phrase": approval_phrase()},
        {"raw_output": "unmasked"},
        {"endpoint_url": "https://provider.example"},
        {"raw_key": RAW_SECRET},
        {"env_var_value": "AICO_WORKER_1_API_KEY=actual-secret"},
        {"raw_output_saved": True},
        {"live_call_allowed": True},
        {"model_call_count_before_execution": 1},
    ],
)
def test_approval_package_rejects_forbidden_fields_or_live_permissions(payload_update: dict[str, object]) -> None:
    _, _, package = parsed_package()
    payload = package.to_summary()
    payload.update(payload_update)

    with pytest.raises(P3PApprovalError) as exc_info:
        validate_approval_package_payload(payload)
    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_approval_package_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    _, _, package = parsed_package()
    path = write_approval_package(tmp_path, package)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path == (tmp_path / APPROVAL_PACKAGE_ARTIFACT_NAME).resolve()
    assert payload["live_call_allowed"] is False
    assert payload["model_call_count_before_execution"] == 0


def test_approval_package_write_helper_blocks_path_traversal(tmp_path: Path) -> None:
    _, _, package = parsed_package()
    with pytest.raises(P3PApprovalError) as exc_info:
        write_approval_package(tmp_path, package, artifact_name="../approval_package.json")
    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_approval_package_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    _, _, package = parsed_package()
    outside = tmp_path.parent / "approval_package.json"
    with pytest.raises(P3PApprovalError) as exc_info:
        write_approval_package(tmp_path, package, artifact_name=str(outside))
    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_approval_package_write_failure_maps_report_error(tmp_path: Path) -> None:
    _, _, package = parsed_package()
    with pytest.raises(P3PApprovalError) as exc_info:
        write_approval_package(tmp_path, package, artifact_name="unexpected.json")
    assert_failure(exc_info, "REPORT_ERROR")


def test_default_runtime_path_does_not_create_approval_package(tmp_path: Path) -> None:
    parsed_package()

    assert approval_package_default_runtime_creation_enabled() is False
    assert not (tmp_path / APPROVAL_PACKAGE_ARTIFACT_NAME).exists()


def test_linkage_validates_run_id_match_and_hash_only() -> None:
    digest, _, package = parsed_package()
    linkage = build_approval_final_gate_linkage(approval_package=package, final_gate_result=final_gate_payload())

    assert linkage.run_id == "run-p3p-001"
    assert linkage.approval_phrase_hash == digest
    assert "approval_phrase" not in linkage.to_summary()


def test_linkage_rejects_run_id_mismatch() -> None:
    _, _, package = parsed_package()
    with pytest.raises(P3PApprovalError) as exc_info:
        build_approval_final_gate_linkage(approval_package=package, final_gate_result=final_gate_payload("other-run"))
    assert_failure(exc_info, "CONFIG_ERROR")


def test_linkage_rejects_raw_approval_phrase() -> None:
    _, _, package = parsed_package()
    linkage = ApprovalFinalGateLinkage(
        run_id="run-p3p-001",
        approval_package_ref="approval_package.json",
        approval_phrase_hash=package.approval_phrase_hash,
        final_gate_result_ref="final_live_gate_result.json",
    ).to_summary()
    linkage["approval_phrase"] = approval_phrase()

    with pytest.raises(P3PApprovalError) as exc_info:
        validate_approval_final_gate_linkage(package.to_summary(), final_gate_payload(), linkage)
    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_provider_model_and_key_slot_validators() -> None:
    assert validate_final_provider("google_gemini") == "google_gemini"
    assert validate_final_model("user-approved-model") == "user-approved-model"
    assert validate_final_key_slot("worker_1") == "worker_1"


@pytest.mark.parametrize("provider", ["unknown_provider", "https://provider.example"])
def test_provider_validator_rejects_unknown_or_url_provider(provider: str) -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        validate_final_provider(provider)
    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_model_validator_rejects_missing_or_unsafe_model() -> None:
    with pytest.raises(P3PApprovalError) as missing_exc:
        validate_final_model(None)
    assert_failure(missing_exc, "HUMAN_DECISION_REQUIRED")
    with pytest.raises(P3PApprovalError) as unsafe_exc:
        validate_final_model("https://model.example")
    assert_failure(unsafe_exc, "SECURITY_BLOCKED")


@pytest.mark.parametrize("slot", [("worker_1", "worker_2"), "unknown_slot", "AICO_WORKER_1_API_KEY"])
def test_key_slot_validator_rejects_multiple_unknown_or_env_var_slot(slot: object) -> None:
    with pytest.raises(P3PApprovalError) as exc_info:
        validate_final_key_slot(slot)  # type: ignore[arg-type]
    assert exc_info.value.failure_type in {"HUMAN_DECISION_REQUIRED", "SECURITY_BLOCKED"}
