# P3F Completion Review

## Verdict

P3G entry: NO

This NO is about P3G entry readiness. It is not related to live smoke approval. Actual live smoke, real API calls, real key use, provider SDK imports, and network calls remain forbidden.

The P3F policy is directionally safe and strongly limits first live smoke scope, but it has document-level blockers that should be fixed before P3G:

1. `P3F_FIRST_LIVE_SMOKE_POLICY.md` omits itself from its own Document Priority list, placing `P3D_LIVE_CALL_POLICY.md` above the P3F-specific policy.
2. The P3F Failure Mapping and Stop Conditions sections do not explicitly carry every condition defined elsewhere in the same P3F policy, especially `unknown endpoint requested` and `artifact safety scan failed`.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3F_FIRST_LIVE_SMOKE_POLICY.md`
- `P3D_LIVE_CALL_POLICY.md`
- `P3E_COMPLETION_REVIEW.md`
- `P3D_COMPLETION_REVIEW.md`
- `P3C_COMPLETION_REVIEW.md`
- `P3B_COMPLETION_REVIEW.md`
- `P3A_COMPLETION_REVIEW.md`
- `AICO_V0_CANON.md`
- `HANDOFF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_NOTES.md`
- `checklist.md`
- `pyproject.toml`
- `aico_v0/live_gate.py`
- `aico_v0/provider_allowlist.py`
- `aico_v0/artifact_safety.py`
- `aico_v0/live_test_policy.py`
- `aico_v0/p3_real_provider.py`
- `aico_v0/provider_base.py`
- `aico_v0/key_registry.py`
- `tests/test_p3e_live_gate.py`
- `tests/test_p3e_artifact_safety.py`
- `tests/test_p3e_offline_policy.py`
- `tests/test_p3_real_provider_guard.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

`P3F_FIRST_LIVE_SMOKE_POLICY.md` correctly frames P3F as policy/preparation only. It does not authorize live smoke, provider activation, real API calls, real key use, provider SDK imports, or network calls.

The policy defines first live smoke as a narrow future smoke with one provider candidate, one key_slot, one model call, zero retries, no reserve, no full-run artifacts, and mandatory artifact safety scans. It also preserves key_slot-only logging, raw key/raw output bans, offline default tests, and canonical failure types.

The main issues are not implementation issues. They are policy precision issues that matter before P3G because P3G will need to convert this policy into skeletons or tests.

## Critical Issues

1. Document priority is internally inconsistent.

`P3F_FIRST_LIVE_SMOKE_POLICY.md` lists `P3D_LIVE_CALL_POLICY.md` as priority 3 and omits `P3F_FIRST_LIVE_SMOKE_POLICY.md` from its own priority list. The current review priority places `P3F_FIRST_LIVE_SMOKE_POLICY.md` above `P3D_LIVE_CALL_POLICY.md`. Before P3G, the P3F policy should state that P3F-specific first-live-smoke rules outrank P3D general live-call policy when they conflict, while still remaining below `AICO_MASTER_CANON.md` and `AICO_P3_CANON.md`.

2. Failure mapping and stop conditions are slightly incomplete relative to the same policy.

The Provider Allowlist Policy states `unknown endpoint requested` is `SECURITY_BLOCKED`, but the Failure Mapping table and Stop Conditions section do not list it. The Artifact Safety Scan Policy states scan failure is `SECURITY_BLOCKED`, but the Failure Mapping table does not include `artifact safety scan failed`. These gaps are small but implementation-relevant.

## Required Fixes Before P3G

1. Update `P3F_FIRST_LIVE_SMOKE_POLICY.md` Document Priority to include itself at priority 3:

   `AICO_MASTER_CANON.md` > `AICO_P3_CANON.md` > `P3F_FIRST_LIVE_SMOKE_POLICY.md` > `P3D_LIVE_CALL_POLICY.md` > downstream review and handoff docs.

2. Add a conflict rule:

   P3F-specific first-live-smoke rules override broader P3D live-call policy when they conflict, unless either conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`.

3. Add `unknown endpoint requested -> SECURITY_BLOCKED` to P3F Failure Mapping.

4. Add `artifact safety scan failed -> SECURITY_BLOCKED` to P3F Failure Mapping.

5. Add `unknown endpoint requested` to P3F Stop Conditions.

6. Ensure P3G entry remains limited to live smoke implementation skeleton or policy/preparation unless a later explicit approval phase separately authorizes actual live smoke.

## Non-blocking Recommendations

1. In P3G, make the scope explicit before implementation: skeleton/policy first, not actual live smoke.
2. Consider adding a dedicated `live_smoke` marker helper rather than extending the current `live_provider` helper implicitly.
3. Define schemas for `live_smoke_result.json` and `artifact_safety_report.json` before any live smoke code writes them.
4. Decide whether `reserve_1` may be the single first-smoke key_slot or whether it is only forbidden as fallback reserve use.
5. Keep provider SDK import and real key loading deferred until a separate approval/review explicitly authorizes those steps.

## P3F Scope Compliance Review

P3F is documented as policy/preparation only.

- Live smoke execution: forbidden.
- Provider activation: forbidden.
- Actual API call: forbidden.
- Actual LLM call: forbidden.
- Actual key use: forbidden.
- Provider SDK import: forbidden.
- Network call: forbidden.
- Live smoke tests: forbidden.
- Existing harness code changes: not required.
- semantic_preflight and repair loop: forbidden.

This satisfies the P3F scope requirement.

## First Live Smoke Definition Review

The definition is clear:

- One provider candidate.
- One key_slot.
- One model call.
- Zero retries.
- No reserve use.
- Not manager/worker/auditor full run.
- Not 22-key usage or rotation.
- Not a real work artifact generation run.
- Only checks provider adapter, gates, logging, masking, artifact scanning, and failure mapping.

No blocker in this section.

## What First Live Smoke Is Not Review

The exclusions are explicit:

- Full AICO run.
- Manager + worker4 + auditor live run.
- Production execution.
- Real task automation.
- 22-key orchestration.
- Repair loop.
- semantic_preflight.
- Benchmark.
- Cost measurement run.
- Quality evaluation run.

No blocker in this section.

## Provider Candidate and Allowlist Review

The provider candidate policy is safe:

- `candidate_provider = google_gemini` is candidate metadata only.
- `candidate_model = user-approved later`.
- `candidate_key_slot = user-approved later`.
- Candidate metadata does not authorize live calls.
- Actual provider, model, and key_slot require a later explicit approval phase.

The allowlist policy is mostly complete:

- Default allowlist is empty.
- Empty allowlist forbids live calls.
- Missing allowlist is `CONFIG_ERROR`.
- Empty allowlist is `CONFIG_ERROR`.
- Unknown provider is `SECURITY_BLOCKED`.
- Provider not in allowlist is `SECURITY_BLOCKED`.
- Arbitrary URL is `SECURITY_BLOCKED`.
- Unknown endpoint is stated as `SECURITY_BLOCKED`.
- P3F does not open the allowlist.

Required fix: carry `unknown endpoint requested -> SECURITY_BLOCKED` into the Failure Mapping table and Stop Conditions section.

## Key Slot Policy Review

The key slot policy is clear:

- Exactly one key_slot is allowed.
- Allowed slots are `manager_1`, `worker_1`, `worker_2`, `worker_3`, `worker_4`, `auditor_1`, and `reserve_1`.
- First live smoke key_slot candidate remains `user-approved later`.
- Raw key value is forbidden in documents, prompts, logs, artifacts, reports, and exceptions.
- Env var names may be recorded.
- Env var values are forbidden.
- Key existence is boolean only.
- Missing key is `CONFIG_ERROR`.
- Raw key leak is `SECURITY_BLOCKED`.

Non-blocking recommendation: clarify before actual smoke whether choosing `reserve_1` as the single key_slot is allowed or whether `reserve_1` is excluded because reserve use is forbidden.

## Approval Policy Review

The approval policy is specific enough for later implementation:

- Generic phrases are not approval.
- Required approval format includes provider, model, key_slot, `max_model_calls`, `max_retries_per_call`, `max_runtime_seconds`, and `allow_raw_output`.
- `allow_raw_output=false` is mandatory.
- Approval scope must be this run only.
- Missing/ambiguous approval and missing fields are `HUMAN_DECISION_REQUIRED`.
- `allow_raw_output` not false is `SECURITY_BLOCKED`.

No blocker in this section.

## Runtime Flag Review

P3F requires all three future flags:

- `AICO_ENABLE_REAL_PROVIDER=true`
- `AICO_ALLOW_LIVE_CALLS=true`
- `AICO_ALLOW_FIRST_LIVE_SMOKE=true`

Missing or false flags are `CONFIG_ERROR`. The policy also states that all flags true are insufficient without approval, allowlist, budget, and artifact safety gates.

P3F correctly forbids implementing or activating flag execution paths. P3G will need to add the third-flag skeleton or keep it explicitly deferred.

## Budget and Retry Policy Review

The budget and retry policy is strict:

- `max_model_calls = 1`.
- `max_retries_per_call = 0`.
- `max_consecutive_model_errors = 1`.
- `max_runtime_seconds = 60`.
- Retry forbidden.
- Reserve forbidden.
- Fallback provider forbidden.
- Second model call forbidden.
- Missing/invalid budget is `CONFIG_ERROR`.
- Budget exceeded is `BUDGET_EXCEEDED`.
- Timeout, 429, and 500 stop as `MODEL_ERROR`.

No blocker in this section.

## Prompt and Expected Output Policy Review

Prompt constraints are safe:

- No secret, key, env value, or endpoint URL.
- No repo contents.
- No user work material.
- No external URL.
- No file modification or execution request.
- Simple structured output only.
- Provider connectivity check only.

Expected output is limited to minimal JSON. Non-JSON and schema-invalid output become `SCHEMA_ERROR`. Schema-valid empty output becomes `WORKER_BAD_OUTPUT`. Raw output storage is forbidden and `masked_raw_output` is the only allowed output-like field.

No blocker in this section.

## Artifact Policy Review

Allowed artifacts are limited to:

- `run_log.jsonl`
- `ceo_report.md`
- `live_smoke_result.json`
- `artifact_safety_report.json`

Forbidden artifacts are explicit:

- `final_report.md`
- `failed_draft.md`
- `manager_summary.json`
- `audit_report.json`
- `worker_results.jsonl` by default.

The policy also states first live smoke does not create full AICO run artifacts, all artifacts are secret scan targets, key_slot only is recorded, and raw key/raw output are forbidden.

No blocker in this section.

## Artifact Safety Scan Review

The scan policy is strong:

- Pre-smoke scan covers approval, prompt, and config.
- Post-smoke scan covers all artifacts.
- Raw key-like values, bearer tokens, private key blocks, unmasked raw provider output markers, and `raw_output_saved=True` are `SECURITY_BLOCKED`.
- Missing scan is `CONFIG_ERROR`.
- Scan failure is `SECURITY_BLOCKED`.
- Scan result is recorded in `artifact_safety_report.json`.

Required fix: add `artifact safety scan failed -> SECURITY_BLOCKED` to the Failure Mapping table for completeness.

## Logging and Failure Mapping Review

The logging fields match the P3 run_log shape:

- `timestamp`
- `event_type`
- `actor`
- `model`
- `key_slot`
- `input_tokens`
- `output_tokens`
- `status`
- `failure_type`
- `error`
- `artifact_path`
- `parent_event_id`

The policy requires key_slot-only logging, no raw key, null token counts when unknown, canonical provider errors, live smoke start/end events, and artifact safety scan events.

The failure mapping uses existing failure types only. The core mappings are present:

- Approval failures -> `HUMAN_DECISION_REQUIRED`.
- Runtime flag/allowlist/key/budget/scan missing -> `CONFIG_ERROR`.
- Security, allowlist, raw key/output, SDK/network, and ungated live call violations -> `SECURITY_BLOCKED`.
- Budget exceeded -> `BUDGET_EXCEEDED`.
- timeout/429/500/provider unavailable/no response -> `MODEL_ERROR`.
- non-JSON/schema-invalid -> `SCHEMA_ERROR`.
- schema-valid empty -> `WORKER_BAD_OUTPUT`.
- ceo/report artifact failures -> `REPORT_ERROR`.

Required fixes:

- Add `unknown endpoint requested -> SECURITY_BLOCKED`.
- Add `artifact safety scan failed -> SECURITY_BLOCKED`.

## Stop and Rollback Policy Review

Stop conditions cover approval, allowlist, runtime flags, key absence, raw key/env value/raw output, scan missing/failure, budget problems, retry/reserve/second call, SDK import, default-test network call, default-pytest live call, and `ProviderResult` safety breakage.

Required fix: add unknown endpoint requested as a stop condition.

Rollback policy is safe:

- No retry.
- No reserve.
- Do not widen allowlist.
- Do not change key_slot.
- Record canonical failure_type.
- Attempt `ceo_report.md`.
- Run artifact safety scan.
- Preserve failure artifacts without raw key or raw output.
- Decide next step only after separate review.

No rollback blocker.

## Test Policy and P3G Entry Requirements Review

The test policy is safe:

- P3F does not run live smoke tests.
- Default `pytest -q` is offline-only.
- Live smoke tests are excluded from default suite.
- Live smoke tests require a separate marker.
- Live smoke tests are forbidden without later explicit approval.
- P3F writes policy documentation only.
- Actual live smoke test implementation is allowed only in P3G or a later explicit approval phase.
- Recommended marker is `live_smoke`.

P3G entry requirements are present:

1. P3F first live smoke policy review complete.
2. Provider allowlist candidate fixed.
3. Provider SDK import permission approved or deferred.
4. Key loading isolation method approved or deferred.
5. First live smoke approval phrase fixed.
6. `live_smoke` marker policy fixed.
7. Live smoke artifact policy fixed.
8. Artifact safety scan pass criteria fixed.
9. First live smoke implementation scope fixed.
10. P3G entry judged YES.

Required fix: complete the P3F policy fixes above before P3G entry is YES.

## Required Tests Before Any Live Smoke Review

The required test list includes:

- First live smoke requires explicit approval.
- Generic approval phrase is rejected.
- Exactly one key_slot is required.
- Multiple key_slots are rejected.
- `max_model_calls = 1` is required.
- `max_model_calls > 1` is rejected.
- `max_retries_per_call = 0` is required.
- Retry greater than 0 is rejected.
- Reserve usage is rejected.
- `allow_raw_output != false` is rejected.
- Provider allowlist non-empty is required.
- Provider not in allowlist is rejected.
- Arbitrary URL is rejected.
- Artifact safety scan is required before call.
- Artifact safety scan is required after call.
- No `final_report.md`.
- No `failed_draft.md`.
- No `manager_summary.json`.
- No `audit_report.json`.
- key_slot only is recorded.
- No raw key is recorded.
- No raw output is stored.
- timeout/429/500 map to `MODEL_ERROR`.
- Non-JSON maps to `SCHEMA_ERROR`.
- Schema-valid empty maps to `WORKER_BAD_OUTPUT`.
- Default pytest does not run live smoke.
- `live_smoke` marker is excluded by default.

Non-blocking recommendation: add explicit test requirements for unknown endpoint rejection and artifact safety scan failure mapping when the P3F policy is fixed.

## P3G Entry Risk Review

P3G should not be actual live smoke by default. The safest P3G scope is live smoke implementation skeleton or policy/preparation:

- Implement or document `live_smoke` marker default-skip behavior.
- Add first-live-smoke approval object or schema extensions.
- Add single-key-slot validation.
- Add the third runtime flag gate as a skeleton.
- Add provider allowlist activation structure without opening it by default.
- Add `live_smoke_result.json` and `artifact_safety_report.json` schemas.
- Add offline tests for all P3F required tests.

Risks before any actual live smoke:

- Provider allowlist is still empty.
- Real key loading is still disabled.
- Provider SDK imports are still forbidden.
- Network transport is still forbidden.
- Actual first live smoke approval has not been granted.
- Live smoke artifacts do not yet have implementation schemas.
- `live_smoke` marker is not implemented; only `live_provider` exists today.

P3G should keep actual API calls, LLM calls, key usage, SDK imports, network calls, and live smoke forbidden unless a later explicit approval phase changes that.

## Final Decision

P3G entry: NO

P3F is close, but P3G should not start until the P3F policy fixes are made:

1. Add P3F itself to the P3F document priority above P3D.
2. Add the P3F-vs-P3D conflict rule.
3. Add missing failure mappings and stop condition coverage for `unknown endpoint requested` and artifact safety scan failure.

After those fixes, P3G may be reconsidered for live smoke implementation skeleton or policy/preparation only. This review does not authorize live smoke.
