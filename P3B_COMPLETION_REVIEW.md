# P3B Completion Review

## Verdict

P3C entry: NO

P3B establishes the right provider boundary direction, but P3C should not start until the invalid key_slot path and ProviderResult safety boundary are hardened. The current test suite passes, but it does not exercise one broken fake-provider branch that would matter when guarded real adapter work begins.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3A_COMPLETION_REVIEW.md`
- `AICO_V0_CANON.md`
- `P3_CANON_REVIEW.md`
- `HANDOFF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_NOTES.md`
- `checklist.md`
- `aico_v0/provider_base.py`
- `aico_v0/p3_fake_provider.py`
- `aico_v0/p3_real_provider.py`
- `aico_v0/key_registry.py`
- `aico_v0/response_normalizer.py`
- `aico_v0/harness.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

P3B added a shared provider interface, disabled real provider skeleton, key_slot to env-var-name registry, response normalizer, and dedicated provider boundary tests. It did not add live API calls, LLM calls, key value loading, provider SDK imports, network imports, `.env` loading, semantic preflight, repair loop, dashboard, Issue integration, or CLI orchestration.

The implementation is mostly aligned with the P3B skeleton goal. `pytest -q` passes with 91 tests, and the V0 and P3A test suites still pass. The key blocker is that one invalid key_slot branch in `FakeProvider.call_model` still constructs `ProviderResult("security_leak", error="invalid key slot")`, but `ProviderResult` no longer accepts `error`. That branch would raise `TypeError` instead of returning a canonical `SECURITY_BLOCKED`-compatible result.

## Critical Issues

1. `aico_v0/p3_fake_provider.py` has a stale `ProviderResult(error=...)` call in the invalid key_slot branch.

   Impact: invalid key_slot handling can crash with `TypeError` instead of producing a safe provider result. The current tests do not cover this branch. This is a blocker before P3C because guarded real adapter work will increase reliance on key_slot validation behavior.

2. `ProviderResult` is safer than before because it has no `raw_output` field, but it is not structurally impossible to place raw key or raw provider data in `content` or `masked_raw_output`.

   Impact: P3C needs a stronger construction path or explicit adapter policy so real provider adapters cannot bypass masking by directly constructing `ProviderResult` with unsafe values.

## Required Fixes Before P3C

1. Fix the invalid key_slot branch in `FakeProvider.call_model` to use `normalized_error` or another valid safe field.
2. Add a direct test for invalid key_slot behavior and assert it does not crash, does not retry through reserve, and maps to `SECURITY_BLOCKED`.
3. Add a direct test for `KeyRegistry.raw_key_value` to confirm raw key access is disabled and the error message contains only key_slot.
4. Define a safe ProviderResult construction rule before guarded real adapter work. Prefer a factory or normalizer path that always masks provider text and never exposes raw output.
5. Decide whether unknown provider statuses in `normalize_provider_response` should become `MODEL_ERROR`, `SCHEMA_ERROR`, or an explicit blocked/config error before real provider integration.

## Non-blocking Recommendations

1. Add `flask` and `fastapi` to the P3B boundary forbidden import test to match the V0 runtime forbidden import scan.
2. Add tests for provider status aliases `rate_limited_429`, `server_error_500`, and `provider unavailable` in addition to `429` and `500`.
3. Consider centralizing run-log field schema so V0, P3A, and later P3C do not drift.
4. Document the future real-provider enable flag before implementation. Recommended default: `AICO_ENABLE_REAL_PROVIDER=false`.

## P3B Scope Compliance Review

P3B mostly complies with the requested scope.

- Actual API call path: none found.
- Actual LLM call path: none found.
- Actual key value usage: none found.
- Provider SDK import: none found in `aico_v0`.
- Network import or call path: none found in `aico_v0`.
- `.env` file creation or env value use: none found.
- Real provider skeleton disabled state: satisfied. `RealProvider.call_model` raises `ProviderDisabledError`.
- `semantic_preflight` execution: not introduced.
- Repair loop execution: not introduced.

The invalid key_slot branch is a correctness issue, not a scope violation.

## Provider Interface Review

`provider_base.py` provides a shared `Provider` protocol, `ProviderResult`, key slots, provider statuses, canonical failure mapping, and secret masking helpers. This is a good common boundary for fake and real providers.

Strengths:

- Fake and real provider skeletons share the same `call_model` signature.
- `ProviderResult` includes `input_tokens` and `output_tokens`, and both can be `None`.
- `ProviderResult` removes the old raw output field and defaults `raw_output_saved=false`.
- Provider-specific statuses can be mapped through `FAILURE_BY_PROVIDER_STATUS` and `response_normalizer.py`.

Gaps before P3C:

- `ProviderResult` can still carry unsafe data through flexible `content` and `masked_raw_output` fields if a real adapter constructs it directly.
- `ProviderResult` does not enforce that `status` is one of `PROVIDER_STATUSES`.
- The invalid key_slot branch in `FakeProvider` is out of sync with the new `ProviderResult` field names.

## Real Provider Skeleton Review

`p3_real_provider.py` stays disabled and does not import SDKs or network clients.

- SDK import: none.
- HTTP/network call: none.
- Actual key value access: none.
- `call_model` behavior: validates key_slot by env-var-name lookup, then raises `ProviderDisabledError`.
- Disabled error message: includes key_slot only, not key value or env value.
- P3C extension path: acceptable as a guarded adapter boundary, provided real call enablement remains default-off.

The skeleton is safe enough as a disabled object, but P3C should define a real-provider enable flag and fake transport requirement before any implementation.

## Key Registry and Secret Safety Review

`key_registry.py` correctly defines seven key slots.

- `manager_1`
- `worker_1`
- `worker_2`
- `worker_3`
- `worker_4`
- `auditor_1`
- `reserve_1`

The key_slot to env var name mapping is clear and uses `AICO_MANAGER_1_API_KEY`, `AICO_WORKER_1_API_KEY` through `AICO_WORKER_4_API_KEY`, `AICO_AUDITOR_1_API_KEY`, and `AICO_RESERVE_1_API_KEY`.

Safety review:

- Env var names can be listed.
- Env var values are not read.
- `KeyRegistry.describe_slot` reports configured boolean and missing-key `CONFIG_ERROR` without raw values.
- `raw_key_value` raises and does not return a value.
- Logs and artifacts continue to use key_slot in P3A paths.
- `SECURITY_BLOCKED` remains non-retryable in P3A.

Gap before P3C: `raw_key_value` behavior is not directly tested.

## Response Normalizer Review

`response_normalizer.py` covers the required P3B mapping.

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

The normalizer masks raw-ish output, sets `raw_output_saved=false`, provides `mask_reason`, carries token fields, and marks secret-like content as unsafe with `SECURITY_BLOCKED`.

Gaps before P3C:

- Unknown provider statuses currently produce `failure_type=None`.
- The normalizer is not yet wired into `p3_fake_provider.py`; P3A still uses `FAILURE_BY_PROVIDER_STATUS` directly.
- Failures that cannot produce `worker_results.jsonl` are logged by P3A harness code, not by the normalizer itself. That is acceptable, but P3C should keep that responsibility explicit.

## P3A Compatibility Review

P3A compatibility is intact under the current tests.

- P3A fake provider tests pass.
- Fake provider uses the shared provider interface.
- Fake and real skeleton call boundaries match.
- Retry, reserve, and model call budget tests still pass.
- Mid-flight failure behavior still passes.
- `final_report.md` and `failed_draft.md` mutual exclusion still passes.
- `ceo_report.md` or `REPORT_ERROR` behavior still passes.

Compatibility caveat: invalid key_slot behavior is not covered and currently broken.

## V0 Harness Compatibility Review

V0 compatibility is intact.

- Existing V0 tests pass.
- V0 dry-run API call count remains zero.
- V0 dry-run LLM call count remains zero.
- P3B provider boundary modules do not alter `run_dry_run`.
- No semantic_preflight execution trace is introduced.
- No repair loop execution trace is introduced.

## Test Coverage Review

| Coverage item | Test coverage | Status |
| --- | --- | --- |
| fake provider and real provider skeleton share same provider interface | `test_fake_provider_and_real_provider_share_provider_interface` | Direct |
| real provider skeleton performs no network/API call | `test_real_provider_skeleton_is_disabled_and_performs_no_api_call`, forbidden import test | Direct |
| real provider skeleton raises disabled/not implemented error | `test_real_provider_skeleton_is_disabled_and_performs_no_api_call` | Direct |
| real provider skeleton error message contains no raw key | `test_real_provider_disabled_error_contains_no_raw_key` | Direct |
| key_slot to env var name mapping includes all seven slots | `test_key_slot_to_env_var_name_mapping_contains_required_slots` | Direct |
| key registry never returns/logs raw key in artifacts | `test_key_registry_describes_presence_without_raw_key_values` | Partial |
| env var names may be listed, env var values are not logged | `test_env_var_names_may_be_listed_but_values_are_not_logged` | Direct |
| missing key is represented without exposing raw key | `test_missing_key_is_represented_without_exposing_raw_key` | Direct |
| response normalizer maps timeout to MODEL_ERROR | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps 429 to MODEL_ERROR | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps 500 to MODEL_ERROR | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps no_response to MODEL_ERROR | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps non_json_response to SCHEMA_ERROR | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps schema_invalid_json to SCHEMA_ERROR | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps schema_valid_empty to WORKER_BAD_OUTPUT | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| response normalizer maps security_leak to SECURITY_BLOCKED | `test_response_normalizer_maps_provider_status_to_failure_type` | Direct |
| normalized malformed output is masked or marked unsafe | `test_normalized_malformed_output_is_masked_and_never_raw_saved` | Direct |
| raw_output_saved is never true by default | `test_provider_result_token_fields_exist_and_may_be_null`, normalizer malformed test | Direct |
| ProviderResult token fields exist and may be null | `test_provider_result_token_fields_exist_and_may_be_null` | Direct |
| fake provider P3A tests still pass | `tests/test_p3_fake_provider.py` | Direct |
| V0 tests still pass | `tests/test_v0_harness.py` | Direct |
| AGENTS.md and CLAUDE.md remain byte-identical | `test_agents_and_claude_remain_byte_identical_for_p3b`, SHA256 check | Direct |

Missing or insufficient tests before P3C:

- invalid key_slot path in fake provider.
- direct `KeyRegistry.raw_key_value` disabled-access test.
- unknown provider status normalization policy.
- ProviderResult construction path that prevents unmasked provider text.

## P3C Entry Risk Review

P3C should not begin until the blocking fixes above are made.

Risks to settle before guarded real provider adapter implementation:

1. `.env` and key loading policy needs a short Canon or policy document before any env value is read.
2. Actual key value reads, when allowed, should be isolated in `key_registry.py` or a dedicated secret provider module and should never return values to log/report/artifact code.
3. Real provider adapter must remain disabled by default.
4. If an enable flag is added, recommended name and default are `AICO_ENABLE_REAL_PROVIDER=false`.
5. Tests must use monkeypatch or fake transport so network calls cannot happen even if a future adapter is accidentally invoked.
6. Provider-specific response shape differences should be absorbed in adapter-specific parsing, then passed to `response_normalizer.py`.
7. Token accounting should be collected in the provider adapter, then normalized into `ProviderResult` and `run_log.jsonl`; the normalizer should not estimate tokens.
8. A short `AICO_P3C_CANON.md` or `P3C_PROVIDER_POLICY.md` should be written before any actual key loading or provider SDK work.

## Final Decision

P3C entry: NO

P3B is directionally correct and offline-safe, but the invalid key_slot branch and ProviderResult safety boundary need hardening before guarded real provider adapter work starts.
