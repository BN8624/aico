# P3Q linkage와 no-call 요약 artifact 경계가 안전한지 검증한다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.no_call_integration import (
    NO_CALL_INTEGRATION_ARTIFACT_NAME,
    P3QNoCallIntegrationError,
    build_no_call_integration_summary,
    write_no_call_integration_summary,
)

from tests.test_p3q_no_call_integration import approval_package_payload, final_gate_payload, runtime_flags_summary


def build_summary(**overrides: object):
    return build_no_call_integration_summary(
        approval_package=approval_package_payload(),
        final_live_gate_result=final_gate_payload(),
        runtime_flags_summary=runtime_flags_summary(),
        artifact_safety_summary={"ok": True},
        **overrides,
    )


def assert_failure(exc_info: pytest.ExceptionInfo[P3QNoCallIntegrationError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def test_approval_phrase_hash_linkage_is_safe() -> None:
    summary = build_summary().to_summary()

    assert len(str(summary["approval_phrase_hash"])) == 64
    assert "approval_phrase" not in summary
    assert summary["approval_package_ref"] == "approval_package.json"
    assert summary["final_gate_result_ref"] == "final_live_gate_result.json"


@pytest.mark.parametrize(
    "final_gate_update",
    [
        {"raw_output": "blocked"},
        {"raw_key": "sk-p3q-final-gate-secret"},
        {"env_var_value": "AICO_WORKER_1_API_KEY=secretvalue"},
        {"endpoint_url": "https://example.invalid"},
        {"status": "provider_success"},
        {"live_call_allowed": True},
        {"model_call_count": 1},
    ],
)
def test_final_gate_linkage_rejects_unsafe_or_live_fields(final_gate_update: dict[str, object]) -> None:
    final_gate = final_gate_payload(**final_gate_update)

    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        build_no_call_integration_summary(
            approval_package=approval_package_payload(),
            final_live_gate_result=final_gate,
            runtime_flags_summary=runtime_flags_summary(),
            artifact_safety_summary={"ok": True},
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_no_call_integration_summary_write_helper_blocks_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        write_no_call_integration_summary(tmp_path, build_summary(), artifact_name="../no_call_integration_summary.json")

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_no_call_integration_summary_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / NO_CALL_INTEGRATION_ARTIFACT_NAME

    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        write_no_call_integration_summary(tmp_path, build_summary(), artifact_name=str(outside))

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_no_call_integration_summary_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3QNoCallIntegrationError) as exc_info:
        write_no_call_integration_summary(tmp_path, build_summary(), artifact_name="unexpected.json")

    assert_failure(exc_info, "REPORT_ERROR")


def test_default_runtime_path_does_not_create_no_call_summary_or_approval_package() -> None:
    assert not Path(NO_CALL_INTEGRATION_ARTIFACT_NAME).exists()
    assert not Path("approval_package.json").exists()
    assert not Path("runs/no_call_integration_summary.json").exists()
    assert not Path("runs/approval_package.json").exists()

