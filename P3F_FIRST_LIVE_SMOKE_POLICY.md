# P3F First Live Smoke Policy

## Status

P3F is policy/preparation only.

P3F does not authorize a live smoke run. P3F does not implement provider activation. P3F does not permit actual API calls. P3F does not permit actual key use. P3F does not permit provider SDK imports. P3F does not permit network calls.

Actual first live smoke requires a later explicit approval phase.

## Purpose

P3F defines the policy required before a future first live smoke can be considered. It limits that smoke to a single provider candidate, one key slot, one model call, zero retries, no reserve, no full run artifacts, and mandatory artifact safety scans before and after the call.

## Non-goals

- No actual API call.
- No actual LLM call.
- No actual key use.
- No `.env` file creation.
- No `.env` value based live call.
- No actual key loading implementation.
- No provider SDK import.
- No HTTP or network import or call.
- No real provider connection.
- No live smoke execution.
- No live smoke test execution.
- No live-call flag implementation or activation.
- No provider adapter implementation.
- No harness code change.
- No semantic_preflight implementation or execution.
- No repair loop implementation or execution.
- No 22-key usage or rotation.
- No worker file edit permission.
- No worker shell permission.
- No external URL access, web search, or repo clone.
- No GitHub Issue integration, web dashboard, CLI agent orchestration, automatic PR, or automatic merge.

## Document Priority

For P3F policy/preparation work, document priority is:

1. `AICO_MASTER_CANON.md`
2. `AICO_P3_CANON.md`
3. `P3D_LIVE_CALL_POLICY.md`
4. `P3E_COMPLETION_REVIEW.md`
5. `P3D_COMPLETION_REVIEW.md`
6. `P3C_COMPLETION_REVIEW.md`
7. `P3B_COMPLETION_REVIEW.md`
8. `P3A_COMPLETION_REVIEW.md`
9. `AICO_V0_CANON.md`
10. `HANDOFF.md`
11. `AGENTS.md` / `CLAUDE.md`
12. `CONTEXT_NOTES.md`
13. `checklist.md`

If this policy conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`, the higher-priority Canon document wins.

## Current Safety Baseline

- P2 V0 dry-run is complete and offline.
- P3A fake-provider layer is complete and offline.
- P3B provider boundary skeleton and blocker fix are complete and offline.
- P3C guarded real-provider boundary is complete, disabled by default, and offline.
- P3D live-call gate policy and policy fix are complete.
- P3E activation preparation and LiveApproval blocker fix are complete.
- Provider allowlist default remains empty.
- `RealProvider` defaults to disabled.
- Default transport remains `DisabledTransport`.
- `KeyRegistry.raw_key_value` remains disabled.
- `ProviderResult` has no `raw_output` field.
- `raw_output_saved` defaults to `false` and `raw_output_saved=True` is rejected.
- Default tests are offline and fake/disabled-only.

## First Live Smoke Definition

First live smoke is limited to:

- One provider candidate.
- One key_slot.
- One model call.
- Zero retries.
- No reserve use.
- Not a manager/worker/auditor full run.
- Not 22-key usage.
- Not 22-key rotation.
- Not a real work artifact generation run.
- Only checking that provider adapter, gates, logging, masking, artifact scanning, and failure mapping can operate safely.

## What First Live Smoke Is Not

First live smoke is not:

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

## Provider Candidate Policy

P3F does not activate a provider. It records candidate metadata only.

Default candidate metadata:

- `candidate_provider = google_gemini`
- `candidate_model = user-approved later`
- `candidate_key_slot = user-approved later`

Rules:

1. `candidate_provider` is not allowlist activation.
2. `candidate_model` is not a selected live model.
3. `candidate_key_slot` is not approval to use a real key.
4. Candidate metadata alone cannot authorize a live call.
5. Actual provider, model, and key_slot must be fixed in a later explicit approval phase.

## Provider Allowlist Policy

Current default:

- `provider_allowlist = empty`

Rules:

1. An empty allowlist forbids live calls.
2. Missing allowlist is `CONFIG_ERROR`.
3. Empty allowlist is `CONFIG_ERROR`.
4. Unknown provider requested is `SECURITY_BLOCKED`.
5. Provider not in allowlist is `SECURITY_BLOCKED`.
6. Arbitrary URL requested is `SECURITY_BLOCKED`.
7. Unknown endpoint requested is `SECURITY_BLOCKED`.
8. P3F documentation alone does not open the allowlist.
9. Opening the allowlist is allowed only in P3G or a later explicit approval phase.

## Key Slot Policy

First live smoke allows exactly one key_slot.

Rules:

1. Exactly one key_slot is allowed.
2. The key_slot must be one of `manager_1`, `worker_1`, `worker_2`, `worker_3`, `worker_4`, `auditor_1`, or `reserve_1`.
3. The first live smoke key_slot candidate remains `user-approved later`.
4. Raw key value must never be written to documents, prompts, logs, artifacts, reports, or exceptions.
5. Env var names may be recorded.
6. Env var values must not be recorded.
7. Key existence is represented only as a boolean.
8. Missing key is `CONFIG_ERROR`.
9. Raw key leak is `SECURITY_BLOCKED`.

## Approval Policy

Actual first live smoke execution requires later explicit approval. Generic approval language is not enough.

These phrases are not approval:

- `진행해`
- `계속해`
- `해봐`
- `다음 단계로 가`
- `승인`
- `OK`

Required approval format:

```text
I approve AICO first live smoke for this run only:
provider = <provider_name>
model = <model_name>
key_slot = <one_allowed_key_slot>
max_model_calls = 1
max_retries_per_call = 0
max_runtime_seconds = <number>
allow_raw_output = false
```

Rules:

1. Missing approval phrase is `HUMAN_DECISION_REQUIRED`.
2. Ambiguous approval phrase is `HUMAN_DECISION_REQUIRED`.
3. Missing provider is `HUMAN_DECISION_REQUIRED`.
4. Missing model is `HUMAN_DECISION_REQUIRED`.
5. Missing key_slot is `HUMAN_DECISION_REQUIRED`.
6. Missing `max_model_calls` is `HUMAN_DECISION_REQUIRED`.
7. Missing `max_retries_per_call` is `HUMAN_DECISION_REQUIRED`.
8. Missing `max_runtime_seconds` is `HUMAN_DECISION_REQUIRED`.
9. `allow_raw_output` not equal to `false` is `SECURITY_BLOCKED`.
10. Approval scope must be this run only.

## Runtime Flag Policy

First live smoke can only become a candidate if all of these flags are true:

- `AICO_ENABLE_REAL_PROVIDER=true`
- `AICO_ALLOW_LIVE_CALLS=true`
- `AICO_ALLOW_FIRST_LIVE_SMOKE=true`

Rules:

1. Missing flag is `CONFIG_ERROR`.
2. Any false flag is `CONFIG_ERROR`.
3. Even if all flags are true, live smoke is forbidden without explicit approval.
4. Even if all flags are true, live smoke is forbidden without provider allowlist, budget, and artifact safety scan gates.
5. P3F forbids implementing or activating flag execution paths.

## Budget Policy

First live smoke budget is fixed:

- `max_model_calls = 1`
- `max_retries_per_call = 0`
- `max_consecutive_model_errors = 1`
- `max_runtime_seconds = 60`

Rules:

1. `max_model_calls` must be exactly 1.
2. Retry must be exactly 0.
3. Reserve use is forbidden.
4. Missing budget is `CONFIG_ERROR`.
5. Invalid budget is `CONFIG_ERROR`.
6. Exceeded budget is `BUDGET_EXCEEDED`.
7. A full live run after first smoke requires a separate phase and separate approval.

## Retry Policy

- Retry is forbidden.
- Reserve is forbidden.
- Fallback provider is forbidden.
- A second model call is forbidden.
- Timeout, 429, or 500 stops the smoke as `MODEL_ERROR`.

## Prompt Policy

First live smoke prompt must be short and safe.

Rules:

1. Prompt must not contain secrets, keys, env values, or endpoint URLs.
2. Prompt must not include repo contents.
3. Prompt must not include user work material.
4. Prompt must not include external URLs.
5. Prompt must not request file modification or execution.
6. Prompt must request only a simple structured output smoke.
7. Prompt must check provider connectivity only, not perform real AICO work.

Recommended smoke prompt intent:

```text
Return a minimal JSON object matching the expected schema.
Do not include secrets, URLs, code execution, or external references.
```

## Expected Output Policy

First live smoke expected output is minimal JSON only.

Example schema:

```json
{
  "status": "ok",
  "message": "string"
}
```

Rules:

1. Output must be JSON.
2. Schema-invalid response is `SCHEMA_ERROR`.
3. Non-JSON response is `SCHEMA_ERROR`.
4. Schema-valid empty response is `WORKER_BAD_OUTPUT`.
5. Raw output storage is forbidden.
6. Only `masked_raw_output` is allowed.

## Artifact Policy

Allowed first live smoke artifacts:

- `run_log.jsonl`
- `ceo_report.md`
- `live_smoke_result.json`
- `artifact_safety_report.json`

Rules:

1. `final_report.md` is forbidden.
2. `failed_draft.md` is forbidden.
3. `manager_summary.json` is forbidden.
4. `audit_report.json` is forbidden.
5. `worker_results.jsonl` is forbidden by default.
6. First live smoke does not create full AICO run artifacts.
7. Every artifact is subject to secret scan.
8. Only key_slot may be recorded.
9. Raw key must not be recorded.
10. Raw output must not be recorded.

## Artifact Safety Scan Policy

Artifact safety scan is required before and after first live smoke.

Rules:

1. Before the smoke, approval, prompt, and config must be scanned.
2. After the smoke, all artifacts must be scanned.
3. Raw key-like value is `SECURITY_BLOCKED`.
4. Bearer token is `SECURITY_BLOCKED`.
5. Private key block is `SECURITY_BLOCKED`.
6. Unmasked raw provider output marker is `SECURITY_BLOCKED`.
7. `raw_output_saved=True` is `SECURITY_BLOCKED`.
8. Missing artifact safety scan is `CONFIG_ERROR`.
9. Failed artifact safety scan is `SECURITY_BLOCKED`.
10. Scan result must be recorded in `artifact_safety_report.json`.

## Logging Policy

`run_log.jsonl` fields:

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

Rules:

1. Only key_slot is recorded.
2. Raw key is not recorded.
3. Unknown token counts may be null.
4. Provider error is recorded as a canonical failure_type.
5. Live smoke start and end events are recorded.
6. Artifact safety scan events are recorded.

## Failure Mapping

No new failure_type is added by P3F.

Required mappings:

| Condition | failure_type |
| --- | --- |
| explicit approval missing | `HUMAN_DECISION_REQUIRED` |
| approval phrase ambiguous | `HUMAN_DECISION_REQUIRED` |
| required approval field missing | `HUMAN_DECISION_REQUIRED` |
| runtime flag missing | `CONFIG_ERROR` |
| runtime flag false | `CONFIG_ERROR` |
| provider allowlist missing | `CONFIG_ERROR` |
| provider allowlist empty | `CONFIG_ERROR` |
| key missing | `CONFIG_ERROR` |
| budget missing | `CONFIG_ERROR` |
| budget invalid | `CONFIG_ERROR` |
| artifact safety scan missing | `CONFIG_ERROR` |
| unknown provider requested | `SECURITY_BLOCKED` |
| provider not in allowlist | `SECURITY_BLOCKED` |
| arbitrary URL requested | `SECURITY_BLOCKED` |
| raw key found | `SECURITY_BLOCKED` |
| env var value found | `SECURITY_BLOCKED` |
| unmasked raw provider output found | `SECURITY_BLOCKED` |
| `raw_output_saved=True` detected | `SECURITY_BLOCKED` |
| `allow_raw_output` not false | `SECURITY_BLOCKED` |
| network call in default tests | `SECURITY_BLOCKED` |
| live call attempted without all gates | `SECURITY_BLOCKED` |
| budget exceeded | `BUDGET_EXCEEDED` |
| timeout | `MODEL_ERROR` |
| 429 | `MODEL_ERROR` |
| 500 | `MODEL_ERROR` |
| provider unavailable | `MODEL_ERROR` |
| no response | `MODEL_ERROR` |
| non-json response | `SCHEMA_ERROR` |
| schema-invalid json | `SCHEMA_ERROR` |
| schema-valid empty response | `WORKER_BAD_OUTPUT` |
| ceo_report generation failed | `REPORT_ERROR` |
| artifact write failure | `REPORT_ERROR` |

## Stop Conditions

The following stop the first live smoke path:

- Approval missing.
- Approval ambiguous.
- Required approval field missing.
- Provider allowlist missing.
- Provider allowlist empty.
- Provider not in allowlist.
- Unknown provider requested.
- Runtime flag missing.
- Runtime flag false.
- Key missing.
- Raw key appears anywhere.
- Env var value appears anywhere.
- Raw output appears anywhere.
- Artifact safety scan missing.
- Artifact safety scan failed.
- Budget missing.
- Budget invalid.
- Budget exceeded.
- Retry attempted.
- Reserve attempted.
- Second model call attempted.
- SDK import appears before approved phase.
- Network call appears in default tests.
- Live call appears in default pytest.
- `ProviderResult` safety rules broken.

## Rollback Policy

If first live smoke fails:

1. Do not retry.
2. Do not use reserve.
3. Do not widen the allowlist.
4. Do not change key_slot.
5. Record the failure cause as a canonical failure_type.
6. Attempt to create `ceo_report.md`.
7. Run artifact safety scan.
8. Preserve failure artifacts without raw key or raw output.
9. Decide the next step only after a separate review.

## Test Policy

P3F does not run live smoke tests.

Rules:

1. Default `pytest -q` is offline-only.
2. Live smoke tests are excluded from the default suite.
3. Live smoke tests require a separate marker.
4. Live smoke tests are forbidden without later explicit approval.
5. P3F writes policy documentation only.
6. Actual live smoke test implementation is allowed only in P3G or a later explicit approval phase.

Recommended marker:

- `live_smoke`

## Live Test Isolation Policy

- `live_smoke` tests must be skipped or excluded by default.
- Default local and CI test commands must not execute live smoke.
- Default tests must not import provider SDKs.
- Default tests must not open network transport.
- Default tests must not read real key values.
- Any live smoke test file must require a separate command and approval document.

## P3G Entry Requirements

Before P3G:

1. P3F first live smoke policy review is complete.
2. Provider allowlist candidate is fixed.
3. Provider SDK import permission is explicitly approved or deferred.
4. Key loading isolation method is explicitly approved or deferred.
5. First live smoke approval phrase is fixed.
6. `live_smoke` marker policy is fixed.
7. Live smoke artifact policy is fixed.
8. Artifact safety scan pass criteria are fixed.
9. First live smoke implementation scope is fixed.
10. P3G entry is judged YES.

## Required Tests Before Any Live Smoke

- First live smoke requires explicit approval.
- Generic approval phrase is rejected.
- First live smoke requires exactly one key_slot.
- First live smoke rejects multiple key_slots.
- First live smoke requires `max_model_calls = 1`.
- First live smoke rejects `max_model_calls > 1`.
- First live smoke requires `max_retries_per_call = 0`.
- First live smoke rejects retry greater than 0.
- First live smoke rejects reserve usage.
- First live smoke rejects `allow_raw_output != false`.
- First live smoke requires provider allowlist non-empty.
- First live smoke rejects provider not in allowlist.
- First live smoke rejects arbitrary URL.
- First live smoke requires artifact safety scan before call.
- First live smoke requires artifact safety scan after call.
- First live smoke writes no `final_report.md`.
- First live smoke writes no `failed_draft.md`.
- First live smoke writes no `manager_summary.json`.
- First live smoke writes no `audit_report.json`.
- First live smoke records key_slot only.
- First live smoke records no raw key.
- First live smoke stores no raw output.
- First live smoke maps timeout, 429, and 500 to `MODEL_ERROR`.
- First live smoke maps non-JSON to `SCHEMA_ERROR`.
- First live smoke maps schema-valid empty response to `WORKER_BAD_OUTPUT`.
- Default pytest does not run live smoke.
- `live_smoke` marker is excluded by default.

## Final Rule

P3F does not authorize a live smoke.

P3F only defines the policy required before a future first live smoke. Any actual live smoke requires a later explicit approval phase, passing tests, clean git state, and all gates satisfied.
