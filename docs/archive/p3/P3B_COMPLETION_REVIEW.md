# P3B Completion Review

## Verdict

P3C entry: YES

P3B blocker fixes are complete. The invalid key_slot path no longer raises `TypeError`, `ProviderResult` rejects unknown fields such as `error` and `raw_output`, provider-result content is masked before storage, and direct tests cover the formerly missing paths. P3C may begin as guarded real provider adapter policy and implementation work, but live API calls and real key use remain forbidden until explicitly authorized by the next phase policy.

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

The implementation is aligned with the P3B skeleton goal after blocker fixes. `pytest -q` passes with 96 tests, and the V0, P3A, and P3B provider boundary test suites pass. The former invalid key_slot branch now returns a safe `ProviderResult("security_leak", normalized_error="invalid key slot")`, which maps to `SECURITY_BLOCKED`.

## Critical Issues

None after this blocker fix.

Resolved blockers:

1. The invalid key_slot branch no longer passes an unknown `error` field to `ProviderResult`.
2. `ProviderResult` now validates provider status, rejects `raw_output_saved=True`, has no `raw_output` field, rejects unknown constructor fields, and masks secret-like values in `content`, `masked_raw_output`, and `normalized_error`.

## Required Fixes Before P3C

No blocking fixes remain before P3C.

Completed in this blocker fix:

1. Fixed invalid key_slot handling in `FakeProvider.call_model`.
2. Added direct invalid key_slot coverage and canonical `SECURITY_BLOCKED` mapping assertion.
3. Added direct `KeyRegistry.raw_key_value` disabled-access coverage.
4. Added `ProviderResult` tests for unknown field rejection, absent `raw_output`, `raw_output_saved=false`, `raw_output_saved=True` rejection, token field nullability, and secret masking in `repr` and `asdict`.
5. Added `ProviderResult` runtime masking and status validation.

## Non-blocking Recommendations

1. Add `flask` and `fastapi` to the P3B boundary forbidden import test to match the V0 runtime forbidden import scan.
2. Add tests for provider status aliases `rate_limited_429`, `server_error_500`, and `provider unavailable` in addition to `429` and `500`.
3. Consider centralizing run-log field schema so V0, P3A, and later P3C do not drift.
4. Document the future real-provider enable flag before implementation. Recommended default: `AICO_ENABLE_REAL_PROVIDER=false`.
5. Decide whether unknown statuses in `normalize_provider_response` should become `MODEL_ERROR`, `SCHEMA_ERROR`, or a config/security failure before any live provider calls.

## P3B Scope Compliance Review

P3B complies with the requested scope.

- Actual API call path: none found.
- Actual LLM call path: none found.
- Actual key value usage: none found.
- Provider SDK import: none found in `aico_v0`.
- Network import or call path: none found in `aico_v0`.
- `.env` file creation or env value use: none found.
- Real provider skeleton disabled state: satisfied. `RealProvider.call_model` raises `ProviderDisabledError`.
- `semantic_preflight` execution: not introduced.
- Repair loop execution: not introduced.

The blocker fix did not add any live provider capability.

## Provider Interface Review

`provider_base.py` provides a shared `Provider` protocol, `ProviderResult`, key slots, provider statuses, canonical failure mapping, and secret masking helpers. This is a good common boundary for fake and real providers.

Strengths:

- Fake and real provider skeletons share the same `call_model` signature.
- `ProviderResult` includes `input_tokens` and `output_tokens`, and both can be `None`.
- `ProviderResult` removes the old raw output field and defaults `raw_output_saved=false`.
- Provider-specific statuses can be mapped through `FAILURE_BY_PROVIDER_STATUS` and `response_normalizer.py`.

Safety properties now covered:

- `ProviderResult` rejects unknown fields such as `error`.
- `ProviderResult` has no `raw_output` field and rejects attempts to pass one.
- `ProviderResult` rejects `raw_output_saved=True`.
- `ProviderResult` validates status against `PROVIDER_STATUSES`.
- `ProviderResult` masks secret-like values in `content`, `masked_raw_output`, and `normalized_error`.

Remaining P3C design point: real adapters should still prefer the normalizer path rather than constructing provider results ad hoc.

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

`raw_key_value` disabled-access behavior is now directly tested.

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

Remaining P3C design points:

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

Invalid key_slot behavior is now covered and maps safely to `SECURITY_BLOCKED`.

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
| key registry never returns/logs raw key in artifacts | `test_key_registry_describes_presence_without_raw_key_values`, `test_key_registry_raw_key_access_is_disabled_without_exposing_key` | Direct |
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
| invalid key_slot path does not raise TypeError | `test_invalid_key_slot_path_does_not_raise_type_error_and_maps_safely` | Direct |
| invalid key_slot path maps to canonical safe failure | `test_invalid_key_slot_path_does_not_raise_type_error_and_maps_safely` | Direct |
| ProviderResult rejects unknown fields such as error | `test_provider_result_rejects_unknown_fields_and_raw_output` | Direct |
| ProviderResult rejects or lacks raw_output | `test_provider_result_rejects_unknown_fields_and_raw_output` | Direct |
| ProviderResult never exposes raw key through repr/asdict | `test_provider_result_masks_raw_key_in_repr_and_asdict` | Direct |
| fake provider P3A tests still pass | `tests/test_p3_fake_provider.py` | Direct |
| V0 tests still pass | `tests/test_v0_harness.py` | Direct |
| AGENTS.md and CLAUDE.md remain byte-identical | `test_agents_and_claude_remain_byte_identical_for_p3b`, SHA256 check | Direct |

No blocking coverage gaps remain before P3C.

Non-blocking coverage to add before live provider calls:

- unknown provider status normalization policy.
- provider status aliases `rate_limited_429`, `server_error_500`, and `provider unavailable`.

## P3C Entry Risk Review

P3C may begin after this blocker fix, limited to guarded real provider adapter policy and implementation work. Live provider calls, real key use, `.env` value use, network calls, and provider SDK imports still require explicit next-phase authorization.

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

P3C entry: YES

P3B blockers are resolved. P3C may proceed as guarded real provider adapter policy and disabled-by-default implementation work, with no live API calls or real key usage unless separately authorized.
