# P3S pre-live package artifact helper가 명시 호출과 안전 경로만 허용하는지 검증합니다.
from __future__ import annotations

from pathlib import Path

import pytest

from aico_v0.approval_package import APPROVAL_PACKAGE_ARTIFACT_NAME, approval_package_default_runtime_creation_enabled
from aico_v0.live_execution_boundary import (
    CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME,
    call_attempt_summary_default_runtime_creation_enabled,
)
from aico_v0.no_call_integration import (
    NO_CALL_INTEGRATION_ARTIFACT_NAME,
    no_call_integration_default_runtime_creation_enabled,
)
from aico_v0.pre_live_package import (
    PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME,
    P3SPreLivePackageError,
    assemble_pre_live_package,
    build_pre_live_package_manifest,
    pre_live_package_default_runtime_creation_enabled,
    resolve_pre_live_package_manifest_path,
    write_pre_live_package_manifest,
)

from tests.test_p3s_pre_live_package import p3s_inputs


def assert_failure(exc_info: pytest.ExceptionInfo[P3SPreLivePackageError], failure_type: str) -> None:
    assert exc_info.value.failure_type == failure_type


def safe_manifest():
    inputs = p3s_inputs()
    return build_pre_live_package_manifest(
        approval_package=inputs["approval_package"],
        no_call_integration_summary=inputs["no_call_integration_summary"],
        call_attempt_summary=inputs["call_attempt_summary"],
        final_live_gate_result=inputs["final_live_gate_result"],
        artifact_safety_summary={"ok": True},
        runtime_flags_summary=inputs["runtime_flags_summary"],
        rollback_plan_summary=inputs["rollback_plan_summary"],
        artifact_safety_post_scan={"ok": True},
        status="ready_for_review",
    )


def test_assemble_pre_live_package_safe_no_write_path_creates_no_files(tmp_path: Path) -> None:
    manifest = assemble_pre_live_package(**p3s_inputs())

    assert manifest.to_summary()["status"] == "ready_for_review"
    assert not (tmp_path / PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME).exists()
    assert not Path(PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME).exists()


def test_assemble_pre_live_package_explicit_write_uses_run_dir(tmp_path: Path) -> None:
    manifest = assemble_pre_live_package(**p3s_inputs(), run_dir=tmp_path, write_artifacts=True)

    assert manifest.to_summary()["live_call_allowed"] is False
    assert (tmp_path / APPROVAL_PACKAGE_ARTIFACT_NAME).exists()
    assert (tmp_path / NO_CALL_INTEGRATION_ARTIFACT_NAME).exists()
    assert (tmp_path / CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME).exists()
    assert (tmp_path / PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME).exists()


def test_pre_live_manifest_write_helper_stays_inside_run_dir(tmp_path: Path) -> None:
    path = write_pre_live_package_manifest(tmp_path, safe_manifest(), pre_scan={"ok": True}, post_scan={"ok": True})

    assert path == tmp_path / PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME
    assert path.exists()


def test_pre_live_manifest_write_helper_blocks_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(P3SPreLivePackageError) as exc_info:
        write_pre_live_package_manifest(
            tmp_path,
            safe_manifest(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="../pre_live_package_manifest.json",
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_pre_live_manifest_write_helper_blocks_outside_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        write_pre_live_package_manifest(
            tmp_path,
            safe_manifest(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name=str(outside),
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_pre_live_manifest_write_failure_maps_report_error(tmp_path: Path) -> None:
    with pytest.raises(P3SPreLivePackageError) as exc_info:
        write_pre_live_package_manifest(
            tmp_path,
            safe_manifest(),
            pre_scan={"ok": True},
            post_scan={"ok": True},
            artifact_name="unexpected.json",
        )

    assert_failure(exc_info, "REPORT_ERROR")


def test_pre_live_manifest_write_requires_pre_scan(tmp_path: Path) -> None:
    with pytest.raises(P3SPreLivePackageError) as exc_info:
        write_pre_live_package_manifest(tmp_path, safe_manifest(), pre_scan=None, post_scan={"ok": True})

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_manifest_write_requires_post_scan(tmp_path: Path) -> None:
    with pytest.raises(P3SPreLivePackageError) as exc_info:
        write_pre_live_package_manifest(tmp_path, safe_manifest(), pre_scan={"ok": True}, post_scan=None)

    assert_failure(exc_info, "CONFIG_ERROR")


def test_pre_live_manifest_rejects_scan_failure() -> None:
    inputs = p3s_inputs()

    with pytest.raises(P3SPreLivePackageError) as exc_info:
        build_pre_live_package_manifest(
            approval_package=inputs["approval_package"],
            no_call_integration_summary=inputs["no_call_integration_summary"],
            call_attempt_summary=inputs["call_attempt_summary"],
            final_live_gate_result=inputs["final_live_gate_result"],
            artifact_safety_summary={"ok": False},
            runtime_flags_summary=inputs["runtime_flags_summary"],
            rollback_plan_summary=inputs["rollback_plan_summary"],
        )

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_pre_live_resolver_blocks_url_ref(tmp_path: Path) -> None:
    with pytest.raises(P3SPreLivePackageError) as exc_info:
        resolve_pre_live_package_manifest_path(tmp_path, "https://example.invalid/pre_live_package_manifest.json")

    assert_failure(exc_info, "SECURITY_BLOCKED")


def test_default_runtime_path_creates_no_p3s_artifacts(tmp_path: Path) -> None:
    assert approval_package_default_runtime_creation_enabled() is False
    assert no_call_integration_default_runtime_creation_enabled() is False
    assert call_attempt_summary_default_runtime_creation_enabled() is False
    assert pre_live_package_default_runtime_creation_enabled() is False
    assert not (tmp_path / APPROVAL_PACKAGE_ARTIFACT_NAME).exists()
    assert not (tmp_path / NO_CALL_INTEGRATION_ARTIFACT_NAME).exists()
    assert not (tmp_path / CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME).exists()
    assert not (tmp_path / PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME).exists()
    assert not Path(APPROVAL_PACKAGE_ARTIFACT_NAME).exists()
    assert not Path(NO_CALL_INTEGRATION_ARTIFACT_NAME).exists()
    assert not Path(CALL_ATTEMPT_SUMMARY_ARTIFACT_NAME).exists()
    assert not Path(PRE_LIVE_PACKAGE_MANIFEST_ARTIFACT_NAME).exists()
    assert not Path("live_smoke_result.json").exists()
