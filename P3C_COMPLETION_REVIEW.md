# P3C Completion Review

## Verdict

P3D entry: YES

P3C is complete for guarded disabled-by-default provider work. P3D may begin as live-call gate policy documentation and additional guard design. P3D should not enable live provider calls, real key loading, provider SDK imports, or network calls until a separate policy explicitly authorizes those actions.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3B_COMPLETION_REVIEW.md`
- `P3A_COMPLETION_REVIEW.md`
- `AICO_V0_CANON.md`
- `P3_CANON_REVIEW.md`
- `HANDOFF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_NOTES.md`
- `checklist.md`
- `aico_v0/p3_real_provider.py`
- `aico_v0/provider_base.py`
- `aico_v0/key_registry.py`
- `aico_v0/response_normalizer.py`
- `aico_v0/p3_fake_provider.py`
- `aico_v0/harness.py`
- `tests/test_p3_real_provider_guard.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

P3C adds a guarded real provider boundary without enabling a real provider. `RealProvider` is disabled by default, uses `DisabledTransport` by default, accepts only explicit config state, and routes injected fake/stub transport responses through `response_normalizer` before creating `ProviderResult`.

The implementation does not read `.env`, does not read env values, does not import provider SDKs, does not import network clients, does not perform live API calls, and does not perform LLM calls. Existing V0, P3A, P3B, and P3C guard tests pass.

## Critical Issues

None found.

## Required Fixes Before P3D

No blocking code or test fixes are required before P3D policy work.

P3D should begin with a live-call policy document, not with live provider activation. The policy must define gates for provider SDK import, key loading, network enablement, live-call execution, artifact masking, and test isolation.

## Non-blocking Recommendations

1. Write `AICO_P3D_CANON.md` or `P3D_LIVE_CALL_POLICY.md` before any actual provider activation.
2. Define an explicit two-gate or three-gate live-call model, with all gates defaulting off.
3. Add a test-only fake transport fixture module if P3D tests grow beyond the current in-memory `FakeTransport`.
4. Decide the unknown provider status mapping before real provider response parsing is introduced.
5. Keep provider SDK imports isolated in a future adapter module that is not imported by default.

## P3C Scope Compliance Review

P3C stays within scope.

- Actual API call path: none found.
- Actual LLM call path: none found.
- Actual key value usage: none found.
- Provider SDK import: none found.
- HTTP/network import or call path: none found.
- `.env` file creation or env value use: none found.
- `semantic_preflight` execution: not introduced.
- Repair loop execution: not introduced.
- Worker file edit and shell permission: not introduced.
- External URL, web search, and repo clone path: not introduced.

## Disabled-by-default Review

Disabled-by-default behavior is satisfactory.

- `RealProviderConfig()` defaults to `enabled=False`.
- `RealProvider()` defaults to `DisabledTransport`.
- Missing `AICO_ENABLE_REAL_PROVIDER` value is represented by `None` and remains disabled.
- `AICO_ENABLE_REAL_PROVIDER=false` remains disabled.
- `AICO_ENABLE_REAL_PROVIDER=true` does not open a live call path by itself. With no injected transport, `DisabledTransport` still raises `ProviderDisabledError`.
- Disabled `call_model` errors contain key_slot only and do not include raw key values, env values, or full prompt text.

## Enable Flag Safety Review

`AICO_ENABLE_REAL_PROVIDER` semantics are clear for P3C.

- Missing flag: disabled.
- False-like flag: disabled.
- True-like flag: only permits the configured transport boundary to be called.
- Default transport remains disabled, so true-like flag alone still performs no API/network call.
- Actual provider activation is not possible without new P3D work.

P3D should add an additional explicit live-call gate before any network-capable transport exists.

## Transport Boundary Review

The transport boundary is acceptable for P3D policy entry.

- `DisabledTransport` is the default.
- `DisabledTransport.call` raises `ProviderDisabledError`.
- `FakeTransport` is in-memory and has no network dependency.
- Injected fake/stub transport results are normalized through `normalize_provider_response`.
- `RealProvider.call_model` converts normalized transport output into `ProviderResult`.
- P3D can attach a real transport later at the same boundary, but only after live-call policy is written.

Risk to keep visible: `TransportResult` still has a `raw_output` field as a boundary input. That is acceptable because the next step normalizes and masks it, but real transport code must never persist it directly.

## Key Handling Review

Key handling remains safe for P3C.

- Raw key values are not read.
- `RealProvider` uses key_slot and env var name validation only.
- Env var names are strings in `KEY_SLOT_ENV_VARS`.
- Env var values are not logged, reported, returned, or included in exceptions.
- `KeyRegistry.raw_key_value` remains disabled and tested.
- Missing key and disabled states are represented without raw values.

P3D key loading, if introduced later, should be isolated behind a dedicated secret provider or a guarded `KeyRegistry` extension that never exposes raw values to reports, logs, prompts, or transport errors.

## ProviderResult Safety Review

ProviderResult safety rules remain intact.

- Unknown constructor fields are rejected by dataclass construction.
- There is no `raw_output` field.
- `raw_output_saved=True` is rejected.
- `raw_output_saved` defaults to `False`.
- Secret-like values are recursively masked in `content`, `masked_raw_output`, and `normalized_error`.
- Tests verify `repr` and `asdict` do not expose raw key-like values.
- `input_tokens` and `output_tokens` exist and may be `None`.

P3D real adapters should return through `response_normalizer` and `ProviderResult`; they should not create alternate result structures.

## Response Normalization Review

Required mappings are preserved.

| Input | Failure type |
| --- | --- |
| `timeout` | `MODEL_ERROR` |
| `429` | `MODEL_ERROR` |
| `500` | `MODEL_ERROR` |
| `provider_unavailable` | `MODEL_ERROR` |
| `no_response` | `MODEL_ERROR` |
| `non_json_response` | `SCHEMA_ERROR` |
| `schema_invalid_json` | `SCHEMA_ERROR` |
| `schema_valid_empty` | `WORKER_BAD_OUTPUT` |
| `security_leak` | `SECURITY_BLOCKED` |

Fake/stub transport results pass through `response_normalizer`. Malformed or secret-like raw-ish output is masked and `raw_output_saved` remains false. Failures that cannot produce worker artifacts are still expected to be logged by harness-level run logging, not by the normalizer itself.

## Test Coverage Review

| Coverage item | Test coverage | Status |
| --- | --- | --- |
| real provider is disabled by default | `test_real_provider_is_disabled_by_default` | Direct |
| disabled real provider call raises ProviderDisabledError | `test_disabled_real_provider_call_raises_provider_disabled_error` | Direct |
| disabled error message contains no raw key | `test_disabled_error_message_contains_no_raw_key_or_full_prompt` | Direct |
| disabled error message does not include full prompt | `test_disabled_error_message_contains_no_raw_key_or_full_prompt` | Direct |
| `AICO_ENABLE_REAL_PROVIDER` missing means disabled | `test_enable_flag_missing_means_disabled` | Direct |
| `AICO_ENABLE_REAL_PROVIDER=false` means disabled | `test_enable_flag_false_means_disabled` | Direct |
| `AICO_ENABLE_REAL_PROVIDER=true` still performs no network/API call in P3C | `test_enable_flag_true_still_uses_disabled_transport_by_default` | Direct |
| real provider uses DisabledTransport by default | `test_real_provider_is_disabled_by_default` | Direct |
| fake/stub transport can be injected without network | `test_fake_transport_can_be_injected_without_network` | Direct |
| fake/stub transport result is normalized through response_normalizer | `test_fake_transport_result_is_normalized_through_response_normalizer` | Direct |
| real provider skeleton does not import provider SDK | `test_real_provider_runtime_has_no_provider_sdk_or_network_imports` | Direct |
| runtime package has no forbidden SDK/network imports | `test_real_provider_runtime_has_no_provider_sdk_or_network_imports` plus V0 forbidden import test | Direct |
| key_slot is used, raw key value is not read | `test_key_slot_is_used_and_raw_key_value_is_not_read` | Direct |
| `KeyRegistry.raw_key_value` remains disabled | `test_key_registry_raw_key_value_remains_disabled` | Direct |
| ProviderResult rejects unknown field such as error | `test_provider_result_safety_rules_still_hold` and P3B boundary tests | Direct |
| ProviderResult has no raw_output field | `test_provider_result_safety_rules_still_hold` and P3B boundary tests | Direct |
| ProviderResult rejects raw_output_saved=True | `test_provider_result_safety_rules_still_hold` and P3B boundary tests | Direct |
| ProviderResult masks secret-like values recursively | `test_provider_result_safety_rules_still_hold` and P3B boundary tests | Direct |
| existing P3B provider boundary tests still pass | `tests/test_p3_provider_boundary.py` | Direct |
| existing P3A fake provider tests still pass | `tests/test_p3_fake_provider.py` | Direct |
| existing V0 tests still pass | `tests/test_v0_harness.py` | Direct |
| AGENTS.md and CLAUDE.md remain byte-identical | P3C/P3B tests and SHA256 check | Direct |

No blocking P3C test coverage gaps were found.

## P3D Entry Risk Review

P3D should address these risks before any live provider activation.

1. Write `AICO_P3D_CANON.md` or `P3D_LIVE_CALL_POLICY.md` before real key loading, provider SDK import, or network transport.
2. Keep live call default off.
3. Require at least separate gates for real provider enablement, key availability, and network/live-call execution.
4. Keep tests on fake/stub transport only unless explicitly running a quarantined live test profile outside normal `pytest -q`.
5. Decide whether provider SDK imports remain forbidden until a separate adapter phase.
6. Absorb provider-specific response shapes in adapter-specific parsing before normalization.
7. Keep token accounting in the adapter boundary and pass values through `ProviderResult`; do not estimate token usage in the normalizer.
8. Make mid-flight failure semantics explicit for live provider timeouts, rate limits, and unavailable responses.
9. Ensure live response text is never persisted as raw output and is only exposed through masked fields.

## Final Decision

P3D entry: YES

P3D may proceed as a live-call gate policy and disabled-by-default activation design phase. Actual live API calls, real key use, provider SDK imports, and network transports remain prohibited until that policy explicitly permits them.
