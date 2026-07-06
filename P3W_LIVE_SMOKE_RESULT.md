# P3W Live Smoke Result

## Status

result: blocked

P3W controlled single-call live smoke runner was implemented and invoked once through the P3W entrypoint. The run stopped before provider call because explicit opt-in values were not present.

This is a safe pre-call block, not a completed live provider call.

## Scope

- P3W scope: controlled single-call live smoke boundary only.
- Worker orchestration: NO.
- Multi-agent run: NO.
- Useful production task: NO.
- Worker file modification: NO.
- Worker shell execution: NO.
- Web access: NO.
- Repo clone: NO.
- GitHub integration: NO.
- Parallel execution: NO.
- Retry/reserve/fallback/second call: NO.
- Raw output persistence: NO.

## Run Summary

- run_id: `20260706T120953Z`
- run_dir: `runs/p3w_20260706T120953Z`
- provider: not activated because opt-in was missing.
- model: not activated because opt-in was missing.
- key_slot: not loaded because opt-in was missing.
- key_fingerprint_masked: null.
- actual_provider_call_count: 0.
- call_model_count_before: 0.
- call_model_count_after: 0.
- model_call_count_before: 0.
- model_call_count_after: 0.
- retry_count: 0.
- reserve_used: false.
- fallback_used: false.
- second_call_attempted: false.
- raw_output_saved: false.
- masked_summary_saved: false.
- artifact_safety_scan: pass.
- failure_type: `HUMAN_DECISION_REQUIRED`.
- safe block reason: human opt-in missing.

## Artifacts

- `call_attempt_summary.json`: created inside `runs/p3w_20260706T120953Z`.
- `live_smoke_result.json`: created inside `runs/p3w_20260706T120953Z`.
- `artifact_safety_report.json`: created inside `runs/p3w_20260706T120953Z`.
- `final_live_gate_result.json`: created inside `runs/p3w_20260706T120953Z`.

No raw key, raw env value, raw approval phrase, raw provider request, raw provider response, raw model output, raw headers, raw token usage dump, endpoint URL, bearer token, or private key block was stored.

## Verification

- P3W targeted tests: `pytest -q tests/test_p3w_controlled_live_smoke.py tests/test_p3w_single_call_boundary.py tests/test_p3w_live_artifact_safety.py tests/test_p3w_failure_safety.py` passed with `81 passed`.
- Default pre-live test suite: `pytest -q` passed with `1061 passed`.
- P3W entrypoint executed once: `python -m aico_v0.controlled_live_smoke`.
- P3W artifact safety scan: passed.
- P3W artifact raw leak JSON check: passed.
- Post-run test suite: `pytest -q` passed with `1061 passed`.
- AGENTS.md and CLAUDE.md byte-identical check: passed.
- P3W/P3V/P3U/P3T/P3S/P3R boundary `call_model` string check: passed.

## Next Requirement

To get `single_call_completed` instead of `blocked`, a later run must provide exact P3W opt-in values and one configured key slot:

- `AICO_P3W_LIVE_SMOKE=1`
- `AICO_P3W_PROVIDER=<single_provider>`
- `AICO_P3W_MODEL=<single_model>`
- `AICO_P3W_KEY_SLOT=<single_non_reserve_key_slot>`
- `AICO_P3W_CONFIRM=controlled-single-call`

That later run must still keep `max_model_calls=1`, `retry_count=0`, `reserve_used=false`, `fallback_used=false`, `second_call_attempted=false`, and `raw_output_saved=false`.
