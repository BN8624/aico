# P3C real provider guard와 fake transport 경계를 검증한다.
from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path

import pytest

from aico_v0.key_registry import KeyRegistry
from aico_v0.p3_real_provider import (
    DisabledTransport,
    FakeTransport,
    ProviderDisabledError,
    RealProvider,
    RealProviderConfig,
    TransportResult,
)
from aico_v0.provider_base import ProviderResult

RAW_KEY = "sk-" + "p3c-guard-secret-value"
FULL_PROMPT = "Full prompt must never appear in disabled provider errors."


def test_real_provider_is_disabled_by_default() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}))

    assert provider.config.enabled is False
    assert isinstance(provider.transport, DisabledTransport)


def test_disabled_real_provider_call_raises_provider_disabled_error() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}))

    with pytest.raises(ProviderDisabledError):
        provider.call_model("worker_1", "model", "prompt", {"kind": "worker"}, "happy")


def test_disabled_error_message_contains_no_raw_key_or_full_prompt() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}))

    with pytest.raises(ProviderDisabledError) as exc_info:
        provider.call_model("worker_1", "model", FULL_PROMPT + " " + RAW_KEY, {"kind": "worker"}, "happy")

    message = str(exc_info.value)
    assert RAW_KEY not in message
    assert FULL_PROMPT not in message
    assert "worker_1" in message


def test_enable_flag_missing_means_disabled() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}), config=RealProviderConfig(None))

    assert provider.config.enabled is False
    with pytest.raises(ProviderDisabledError):
        provider.call_model("worker_1", "model", "prompt", {}, "happy")


def test_enable_flag_false_means_disabled() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}), config=RealProviderConfig("false"))

    assert provider.config.enabled is False
    with pytest.raises(ProviderDisabledError):
        provider.call_model("worker_1", "model", "prompt", {}, "happy")


def test_enable_flag_true_still_uses_disabled_transport_by_default() -> None:
    provider = RealProvider(KeyRegistry({"worker_1": True}), config=RealProviderConfig("true"))

    assert provider.config.enabled is True
    assert isinstance(provider.transport, DisabledTransport)
    with pytest.raises(ProviderDisabledError, match="transport is disabled"):
        provider.call_model("worker_1", "model", "prompt", {}, "happy")


def test_fake_transport_can_be_injected_without_network() -> None:
    transport = FakeTransport(TransportResult("success", content={"summary": "ok"}, raw_output='{"summary":"ok"}'))
    provider = RealProvider(
        KeyRegistry({"worker_1": True}),
        config=RealProviderConfig("true"),
        transport=transport,
    )

    result = provider.call_model("worker_1", "model", "prompt", {"kind": "worker"}, "happy")

    assert result.status == "success"
    assert result.content == {"summary": "ok"}
    assert transport.calls == [{"key_slot": "worker_1", "model": "model", "scenario": "happy"}]


def test_fake_transport_result_is_normalized_through_response_normalizer() -> None:
    transport = FakeTransport(
        TransportResult(
            "429",
            raw_output="token=" + RAW_KEY,
            error="rate limited " + RAW_KEY,
            input_tokens=10,
            output_tokens=None,
        )
    )
    provider = RealProvider(
        KeyRegistry({"worker_1": True}),
        config=RealProviderConfig("true"),
        transport=transport,
    )

    result = provider.call_model("worker_1", "model", "prompt", {}, "rate-limit")

    assert result.status == "rate_limited_429"
    assert result.normalized_error == "provider response contained a secret-like value"
    assert result.masked_raw_output == "token=[MASKED_SECRET]"
    assert result.raw_output_saved is False
    assert result.input_tokens == 10
    assert result.output_tokens is None


def test_real_provider_runtime_has_no_provider_sdk_or_network_imports() -> None:
    forbidden_roots = {"requests", "httpx", "socket", "google", "openai", "anthropic", "genai"}
    forbidden_exact = {"urllib.request"}
    runtime_paths = [path for path in Path("aico_v0").glob("*.py")]
    imports: set[str] = set()
    for path in runtime_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

    assert not any(name.split(".")[0] in forbidden_roots for name in imports)
    assert not any(name in forbidden_exact for name in imports)


def test_key_slot_is_used_and_raw_key_value_is_not_read() -> None:
    class NoRawKeyRegistry(KeyRegistry):
        def raw_key_value(self, key_slot: str) -> str:
            raise AssertionError("raw key value must not be read")

    transport = FakeTransport(TransportResult("success", content={"ok": True}, raw_output='{"ok":true}'))
    provider = RealProvider(
        NoRawKeyRegistry({"worker_1": True}),
        config=RealProviderConfig("true"),
        transport=transport,
    )

    result = provider.call_model("worker_1", "model", "prompt", {}, "happy")

    assert result.status == "success"
    assert transport.calls[0]["key_slot"] == "worker_1"


def test_key_registry_raw_key_value_remains_disabled() -> None:
    registry = KeyRegistry({"worker_1": True})

    with pytest.raises(RuntimeError) as exc_info:
        registry.raw_key_value("worker_1")

    assert RAW_KEY not in str(exc_info.value)
    assert "worker_1" in str(exc_info.value)


def test_provider_result_safety_rules_still_hold() -> None:
    with pytest.raises(TypeError):
        ProviderResult("security_leak", error="invalid key slot")
    with pytest.raises(TypeError):
        ProviderResult("success", raw_output="unmasked output")
    with pytest.raises(ValueError, match="raw_output_saved"):
        ProviderResult("success", raw_output_saved=True)

    result = ProviderResult(
        "success",
        content={"secret": RAW_KEY},
        masked_raw_output="raw=" + RAW_KEY,
        normalized_error="error " + RAW_KEY,
    )
    rendered = repr(result) + repr(asdict(result))
    assert not hasattr(result, "raw_output")
    assert result.raw_output_saved is False
    assert RAW_KEY not in rendered
    assert "[MASKED_SECRET]" in rendered


def test_agents_and_claude_remain_byte_identical_for_p3c() -> None:
    assert Path("AGENTS.md").read_bytes() == Path("CLAUDE.md").read_bytes()
