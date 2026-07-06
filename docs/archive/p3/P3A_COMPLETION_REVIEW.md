# P3A Completion Review

## Verdict

P3B entry: YES

P3A satisfies the fake-provider completion bar. P3B may begin as provider adapter specification and preparation work, but live provider calls, real key loading, `.env` requirements, and network-backed tests remain out of scope until explicitly authorized by the next phase Canon or user instruction.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `AICO_V0_CANON.md`
- `P3_CANON_REVIEW.md`
- `HANDOFF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_NOTES.md`
- `checklist.md`
- `aico_v0/p3_fake_provider.py`
- `aico_v0/harness.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

P3A implements a fake-provider API worker layer without adding a real API client, real provider adapter, key loading, network path, LLM call path, semantic preflight execution, repair loop, dashboard, Issue integration, or CLI orchestration.

The implementation keeps the P3 key-slot model visible in artifacts through `manager_1`, `worker_1` through `worker_4`, `auditor_1`, and `reserve_1`. It records fake provider calls in `run_log.jsonl`, preserves V0 artifact rules, keeps `final_report.md` and `failed_draft.md` mutually exclusive, and attempts `ceo_report.md` with `REPORT_ERROR` fallback.

The dedicated P3A tests directly cover the fake-provider subset of `AICO_P3_CANON.md` Required Tests. Existing V0 tests continue to cover dry-run-only behavior and the V0 runtime requirements.

## Critical Issues

None found.

## Required Fixes Before P3B

No blocking code, test, or document fixes are required before entering P3B.

P3B should start with a provider adapter boundary review before any real provider implementation. The first P3B deliverable should define response normalization, token accounting ownership, timeout/error normalization, and key loading isolation without making live API calls.

## Non-blocking Recommendations

1. Extract shared run-log and report-writing helpers before real provider work if P3B starts to duplicate V0/P3A artifact code further.
2. Define a provider response normalization object before adding real adapters, so timeout, HTTP status, malformed payload, schema failure, and token metadata are converted once at the boundary.
3. Keep token accounting provider-specific at the adapter boundary, then pass normalized `input_tokens` and `output_tokens` into harness logging.
4. Write real-key loading policy as a separate Canon section before introducing `.env` or secret-provider behavior.
5. Add focused tests for missing required worker field, worker field type mismatch, role-out-of-scope output, WorkOrder-out-of-scope output, and token budget fields when those become part of P3B scope.

## P3A Scope Compliance Review

P3A is within scope.

- Fake provider only: satisfied by `FakeProvider` and `Provider` protocol in `aico_v0/p3_fake_provider.py`.
- Real API client absent: satisfied. No OpenAI, Anthropic, HTTP client, socket, browser, or subprocess import is present in runtime package tests.
- Real provider adapter absent: satisfied. The only provider implementation is the fake provider.
- Real key loading absent: satisfied. No `.env` requirement or key loader was added.
- Network path absent: satisfied. Tests explicitly scan for forbidden network/API imports.
- `semantic_preflight` not executed: satisfied. P3A result flags are false and tests assert no semantic preflight trace.
- Repair loop not executed: satisfied. P3A budget keeps `max_repair_loops=0` and tests assert no repair trace.
- Worker file edit and shell permission absent: satisfied. P3A WorkOrders set `can_edit_files=false` and `can_run_shell=false`.
- External URL, web search, and repo clone blocked: satisfied. Forbidden mission references become `SECURITY_BLOCKED` before fake provider calls.

## V0 Harness Compatibility Review

P3A is compatible with the V0 harness rules that must remain active in P3.

- P3A reuses V0 `deterministic_preflight`, so schema, permission, path, secret, and WorkOrder-count checks remain aligned.
- Run directory and artifact names match the established V0 pattern.
- `run_log.jsonl` contains the Canon fields for fake provider calls.
- `final_report.md` and `failed_draft.md` remain mutually exclusive.
- Failure paths attempt `ceo_report.md`; `REPORT_ERROR` fallback is implemented in P3A report writing.
- Mid-flight failure preserves already written `worker_results.jsonl`, stops remaining workers, and skips downstream artifacts.

The P3A module has some local helper duplication for logging, masking, and report writing. This is acceptable for the fake-provider phase, but real provider work should avoid growing a second full harness.

## P3 Required Tests Mapping

| Required test item | Current coverage | Status |
| --- | --- | --- |
| P3 document priority places `AICO_P3_CANON.md` above `AICO_V0_CANON.md` | `test_p3_document_priority_places_p3_above_v0` | Direct |
| API key raw value never appears in logs/reports/artifacts | `test_raw_api_key_never_appears_and_key_slot_is_logged` | Direct |
| key_slot is logged instead of raw key | `test_raw_api_key_never_appears_and_key_slot_is_logged`, happy-path slot assertions | Direct |
| reserve_1 is not used on happy path | `test_p3a_happy_path_uses_expected_slots_without_reserve`, `test_reserve_is_used_only_after_worker_model_error` | Direct |
| reserve_1 is used only after worker MODEL_ERROR | `test_reserve_is_used_only_after_worker_model_error` | Direct |
| retry and reserve calls count toward max_model_calls | `test_retry_and_reserve_calls_count_toward_max_model_calls` | Direct |
| max_model_calls exceeded becomes BUDGET_EXCEEDED | `test_max_model_calls_exceeded_becomes_budget_exceeded` | Direct |
| timeout becomes MODEL_ERROR | `test_provider_failure_mapping` | Direct |
| provider 429 becomes MODEL_ERROR | `test_provider_failure_mapping` | Direct |
| provider 500 becomes MODEL_ERROR | `test_provider_failure_mapping` | Direct |
| provider unavailable becomes MODEL_ERROR | `test_provider_failure_mapping` | Direct |
| no provider response creates no WorkerResult and logs MODEL_ERROR | `test_no_provider_response_creates_no_worker_result_and_logs_model_error` | Direct |
| non-json provider response becomes SCHEMA_ERROR | `test_provider_failure_mapping` | Direct |
| schema-invalid json response becomes SCHEMA_ERROR | `test_provider_failure_mapping` | Direct |
| schema-valid empty response becomes WORKER_BAD_OUTPUT | `test_provider_failure_mapping` | Direct |
| security leak becomes SECURITY_BLOCKED and does not retry | `test_raw_api_key_never_appears_and_key_slot_is_logged`, `test_security_leak_does_not_retry_or_use_reserve` | Direct |
| masked_raw_output is saved by default | `test_masked_raw_output_and_raw_output_saved_defaults` | Direct |
| raw_output_saved is false by default | `test_masked_raw_output_and_raw_output_saved_defaults` | Direct |
| malformed response raw output is not saved unmasked | `test_malformed_response_raw_output_is_not_saved_unmasked` | Direct |
| final_report and failed_draft remain mutually exclusive | `test_final_report_and_failed_draft_remain_mutually_exclusive` | Direct |
| ceo_report exists or REPORT_ERROR is logged | `test_ceo_report_exists_or_report_error_is_logged`, V0 report fallback test | Direct |
| semantic_preflight is still not executed | `test_semantic_preflight_and_repair_loop_are_not_executed` | Direct |
| repair loop is still not executed | `test_semantic_preflight_and_repair_loop_are_not_executed` | Direct |
| worker cannot request shell/file edit | `test_worker_cannot_request_shell_or_file_edit` | Direct |
| external URL, web search, repo clone remain blocked | `test_external_url_web_search_and_repo_clone_are_blocked` | Direct |
| unrecovered worker API failure preserves partial worker_results and stops downstream artifacts | `test_unrecovered_api_failure_preserves_partial_worker_results_and_stops_downstream` | Direct |
| max_consecutive_model_errors is enforced | `test_max_consecutive_model_errors_is_enforced` | Direct |
| AGENTS.md and CLAUDE.md remain byte-identical | `test_agents_and_claude_are_byte_identical` and SHA256 check | Direct |

Still not directly covered in the P3A test file because they are better suited for P3B or later provider-normalization work.

- worker JSON parse failure distinct from non-json fake response.
- missing required worker field from fake provider content.
- worker field type mismatch from fake provider content.
- role-out-of-scope worker output.
- WorkOrder-out-of-scope output.
- low-confidence assertion as a P3A provider-output case.
- `max_input_tokens`, `max_output_tokens`, and `max_runtime_seconds` budget failures.
- explicit `REPORT_ERROR` monkeypatch test for P3A report writer.

These are not blockers for P3B entry because the current P3A scope is fake-provider interface and failure-boundary validation, and V0 already covers several equivalent artifact-state rules.

## Key/Secret Safety Review

Key and secret handling is acceptable for P3A.

- No raw key loader exists.
- Runtime logs record `key_slot`, not raw key.
- Allowed slots are limited to `manager_1`, `worker_1`, `worker_2`, `worker_3`, `worker_4`, `auditor_1`, and `reserve_1`.
- Fake provider secret leakage becomes `SECURITY_BLOCKED`.
- Secret-like output is masked before text writes and blocked before worker payload persistence.
- `SECURITY_BLOCKED` is not retried and does not use `reserve_1`.

P3B risk: once real key loading exists, the adapter boundary must ensure prompts, provider errors, raw payloads, and exception messages cannot carry raw keys into `run_log.jsonl`, report files, or worker artifacts.

## Failure Boundary Review

The P3A failure boundary is clear enough for P3B entry.

- `MODEL_ERROR` covers timeout, 429, 500, provider unavailable, and no response.
- `SCHEMA_ERROR` covers non-json response, schema-invalid json, non-dict payload, missing required field, and selected type mismatch checks.
- `WORKER_BAD_OUTPUT` covers schema-valid empty worker output.
- `SECURITY_BLOCKED` covers secret-like provider output and forbidden external access requests.
- `BUDGET_EXCEEDED` covers `max_model_calls` and `max_consecutive_model_errors`.
- `REPORT_ERROR` is available for `ceo_report.md` write failure and preserves the previous failure type through `parent_event_id`.

P3B should expand fake or normalized-provider cases for role-out-of-scope output, WorkOrder-out-of-scope output, low-confidence assertions, and token/runtime budget failures.

## Retry and Reserve Review

Retry and reserve behavior matches the corrected P3 Canon for P3A.

- Happy path uses six fake calls and does not use `reserve_1`.
- `reserve_1` is used only after a worker `MODEL_ERROR`.
- `reserve_1` usage records `parent_event_id` pointing back to the failed worker event.
- Reserve calls count toward `max_model_calls`.
- `max_model_calls=7` supports manager 1, worker 4, auditor 1, and one reserve/retry call.
- `WORKER_BAD_OUTPUT` is not retried or reserved.
- `SECURITY_BLOCKED` is not retried or reserved.
- `max_retries_per_call=1` is represented through one reserve attempt.
- `max_consecutive_model_errors` is implemented and directly tested.

P3B risk: real provider retry policies must not add provider-internal retries that bypass harness call accounting.

## Artifact and Run Log Review

Artifact and logging behavior is compatible with Canon requirements.

- Fake provider calls write `FAKE_PROVIDER_CALL` events.
- Each fake provider event contains `timestamp`, `event_type`, `actor`, `model`, `key_slot`, `input_tokens`, `output_tokens`, `status`, `failure_type`, `error`, `artifact_path`, and `parent_event_id`.
- Non-failure fake call events have `failure_type=null`.
- Token fields are present and can be `null` for unknown output counts.
- Failure events include `failure_type`.
- Reserve and report failure paths use `parent_event_id`.
- `masked_raw_output`, `raw_output_saved`, and `mask_reason` are present in persisted worker results.
- Raw output is not persisted unmasked.
- Mid-flight failure keeps partial worker results and skips unavailable downstream artifacts.

One review note: `p3_fake_provider.py` does not reuse the V0 `RUN_LOG_FIELDS` constant directly. The produced field set matches Canon, but P3B should avoid parallel schema drift by sharing or centralizing the run-log event schema.

## P3B Entry Risk Review

P3B entry is acceptable if P3B begins with adapter design and fake/mock tests rather than live provider calls.

Main risks to address early in P3B.

1. Real provider response normalization is needed to keep `MODEL_ERROR`, `SCHEMA_ERROR`, `WORKER_BAD_OUTPUT`, and `SECURITY_BLOCKED` boundaries stable.
2. Provider-specific token usage should be normalized at the adapter boundary before writing run-log events.
3. Real provider retry behavior must be harness-owned or at least harness-visible so `max_model_calls`, `max_retries_per_call`, and `max_consecutive_model_errors` remain enforceable.
4. Real key loading needs a Canon-level policy before `.env`, OS environment, secret manager, or local config support is introduced.
5. Exception text from real provider clients must be masked before logging because provider SDK errors may include request metadata.

## Final Decision

P3B entry: YES

The P3A fake-provider layer is complete enough to proceed to P3B planning and provider adapter boundary work. P3B must still avoid live API calls until the next instruction explicitly permits real provider implementation and real key handling.
