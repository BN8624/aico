# P3B provider boundary skeleton과 key/normalization 규칙을 검증한다.
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from aico_v0.key_registry import KEY_SLOT_ENV_VARS, KeyRegistry
from aico_v0.p3_fake_provider import FakeProvider
from aico_v0.p3_real_provider import ProviderDisabledError, RealProvider
from aico_v0.provider_base import KEY_SLOTS, ProviderResult
from aico_v0.response_normalizer import normalize_provider_response


def test_fake_provider_and_real_provider_share_provider_interface() -> None:
    fake_signature = inspect.signature(FakeProvider.call_model)
    real_signature = inspect.signature(RealProvider.call_model)

    assert list(fake_signature.parameters) == list(real_signature.parameters)
    assert fake_signature.return_annotation == real_signature.return_annotation == "ProviderResult"


def test_real_provider_skeleton_is_disabled_and_performs_no_api_call() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}))

    with pytest.raises(ProviderDisabledError, match="disabled in P3B skeleton"):
        provider.call_model("worker_1", "disabled-model", "prompt", {"kind": "worker"}, "happy")


def test_real_provider_disabled_error_contains_no_raw_key() -> None:
    raw_key = "sk-" + "p3b-boundary-secret-value"
    provider = RealProvider(KeyRegistry({"worker_1": True}))

    with pytest.raises(ProviderDisabledError) as exc_info:
        provider.call_model("worker_1", "disabled-model", raw_key, {"kind": "worker"}, "happy")

    assert raw_key not in str(exc_info.value)
    assert "worker_1" in str(exc_info.value)


def test_key_slot_to_env_var_name_mapping_contains_required_slots() -> None:
    assert tuple(KEY_SLOT_ENV_VARS) == KEY_SLOTS
    assert KEY_SLOT_ENV_VARS["manager_1"] == "AICO_MANAGER_1_API_KEY"
    assert KEY_SLOT_ENV_VARS["worker_1"] == "AICO_WORKER_1_API_KEY"
    assert KEY_SLOT_ENV_VARS["worker_2"] == "AICO_WORKER_2_API_KEY"
    assert KEY_SLOT_ENV_VARS["worker_3"] == "AICO_WORKER_3_API_KEY"
    assert KEY_SLOT_ENV_VARS["worker_4"] == "AICO_WORKER_4_API_KEY"
    assert KEY_SLOT_ENV_VARS["auditor_1"] == "AICO_AUDITOR_1_API_KEY"
    assert KEY_SLOT_ENV_VARS["reserve_1"] == "AICO_RESERVE_1_API_KEY"


def test_key_registry_describes_presence_without_raw_key_values() -> None:
    raw_key = "sk-" + "p3b-boundary-secret-value"
    registry = KeyRegistry({"worker_1": True})
    status = registry.describe_slot("worker_1")

    assert status.key_slot == "worker_1"
    assert status.env_var_name == "AICO_WORKER_1_API_KEY"
    assert status.configured is True
    assert raw_key not in repr(status)


def test_env_var_names_may_be_listed_but_values_are_not_logged() -> None:
    raw_key = "sk-" + "p3b-boundary-secret-value"
    registry = KeyRegistry({"manager_1": True, "reserve_1": False})
    descriptions = registry.describe_all()
    rendered = "\n".join(repr(description) for description in descriptions)

    assert "AICO_MANAGER_1_API_KEY" in rendered
    assert "AICO_RESERVE_1_API_KEY" in rendered
    assert raw_key not in rendered


def test_missing_key_is_represented_without_exposing_raw_key() -> None:
    raw_key = "sk-" + "p3b-boundary-secret-value"
    registry = KeyRegistry()
    status = registry.describe_slot("auditor_1")

    assert status.configured is False
    assert status.failure_type == "CONFIG_ERROR"
    assert status.error == "missing key for key_slot=auditor_1"
    assert raw_key not in repr(status)


@pytest.mark.parametrize(
    ("provider_status", "failure_type"),
    [
        ("timeout", "MODEL_ERROR"),
        ("429", "MODEL_ERROR"),
        ("500", "MODEL_ERROR"),
        ("provider_unavailable", "MODEL_ERROR"),
        ("no_response", "MODEL_ERROR"),
        ("non_json_response", "SCHEMA_ERROR"),
        ("schema_invalid_json", "SCHEMA_ERROR"),
        ("schema_valid_empty", "WORKER_BAD_OUTPUT"),
        ("security_leak", "SECURITY_BLOCKED"),
    ],
)
def test_response_normalizer_maps_provider_status_to_failure_type(provider_status: str, failure_type: str) -> None:
    normalized = normalize_provider_response(provider_status=provider_status)

    assert normalized.failure_type == failure_type


def test_normalized_malformed_output_is_masked_and_never_raw_saved() -> None:
    normalized = normalize_provider_response(
        provider_status="non_json_response",
        raw_output="token=" + "sk-" + "p3b-boundary-secret-value",
        input_tokens=4,
        output_tokens=None,
    )

    assert normalized.failure_type == "SECURITY_BLOCKED"
    assert normalized.masked_raw_output == "token=[MASKED_SECRET]"
    assert normalized.raw_output_saved is False
    assert normalized.unsafe is True


def test_provider_result_token_fields_exist_and_may_be_null() -> None:
    result = ProviderResult("no_response")

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.raw_output_saved is False


def test_real_provider_boundary_has_no_forbidden_sdk_or_network_imports() -> None:
    source = "\n".join(
        Path(path).read_text(encoding="utf-8").lower()
        for path in [
            "aico_v0/provider_base.py",
            "aico_v0/key_registry.py",
            "aico_v0/response_normalizer.py",
            "aico_v0/p3_real_provider.py",
        ]
    )
    forbidden = ("requests", "httpx", "urllib", "socket", "subprocess", "webbrowser", "openai", "anthropic")

    assert not any(name in source for name in forbidden)


def test_agents_and_claude_remain_byte_identical_for_p3b() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
