# P3X Negative Safety Report

## Verdict

result: passed

## Scope

negative safety tests / bad-input blocking proof only.

No additional live provider call was performed. P3X used helper validation, blocked paths, artifact injection, and P3W artifact regression only.

## Summary

P3X adds a negative safety matrix proving that bad inputs do not open the live boundary. The tests verify bad opt-in, multiple selections, retry/reserve/fallback/second-call attempts, raw-output persistence, raw key/env/secret injection, worker authority expansion, shell/web/repo/GitHub/parallel flags, tool/upload/batch/long-running flags, and bad toy missions.

## Bad Input Matrix

- Bad opt-in: blocked with zero provider calls.
- Missing provider/model/key_slot: blocked with zero provider calls.
- Multiple provider/model/key_slot: blocked.
- Reserve key, fallback provider, provider rotation, key rotation, allowlist widening: blocked.
- Retry, reserve, fallback, second-call, max-call expansion, count injection: blocked.
- Raw output, provider response, token usage, raw headers, raw response body: blocked.
- Raw key-like value, raw env-like value, bearer token, private key block, env dump marker, provider config dump, raw approval phrase, endpoint URL: blocked.
- Worker orchestration, worker pool dispatch, manager/auditor full run, file write, worker shell, shell, web, repo clone, GitHub, parallel, external write scope, auto PR/merge: blocked.
- Tool/function call, file upload, vector store, assistant/thread, batch job, long-running job, streaming multi-call: blocked.
- Bad toy missions including code edit, file mutation, repo analysis, web search, PDF/Excel conversion, long-form output, multi-step reasoning, secret/env/key inspection, external system call, and tool/function call: blocked.

## Blocked Categories

- `bad_opt_in`: passed.
- `multiple_selection`: passed.
- `retry_reserve_fallback_second_call`: passed.
- `raw_output_persistence`: passed.
- `raw_secret_injection`: passed.
- `worker_authority_expansion`: passed.
- `tool_upload_long_running`: passed.
- `bad_toy_mission`: passed.

## P3W Artifact Regression

Regression source: `runs/p3w_20260706T123731Z`.

- actual_provider_call_count: 1.
- call_model_count_before: 0.
- call_model_count_after: 1.
- model_call_count_before: 0.
- model_call_count_after: 1.
- retry_count: 0.
- reserve_used: false.
- fallback_used: false.
- second_call_attempted: false.
- raw_output_saved: false.
- masked_summary_saved: true.
- artifact_safety_scan: pass.
- provider: `google_gemini`.
- model: `gemma-4-31b-it`.
- key_slot: `worker_1`.
- key_fingerprint_masked: masked only.

## Call Count Safety

P3X did not rerun P3W live smoke. Additional provider calls: 0.

## Secret / Raw Output Safety

No raw key, raw env value, raw output, raw provider response, raw token usage dump, bearer token, private key block, endpoint URL, or raw provider config dump was persisted in P3X artifacts.

## Worker Authority Safety

Worker orchestration, worker pool dispatch, manager/auditor full run, worker file write, worker shell, shell, web, repo clone, GitHub automation, and parallel execution remain blocked.

## Test Results

- P3X targeted tests: `112 passed`.
- Full pytest: `pytest -q` passed with `1173 passed`.

## Remaining Risks

P3X is a negative safety proof. It does not authorize additional live calls or broader live operation. Future phases must keep the live boundary opt-in explicit and single-call scoped unless separately approved.
