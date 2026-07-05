# P3I Final Preflight / Approval Review
## Status

P3I is final preflight / approval review documentation only.

P3I does not authorize a live smoke run. P3I does not open provider allowlist. P3I does not implement provider activation. P3I does not permit actual API calls. P3I does not permit actual key use. P3I does not permit provider SDK imports. P3I does not permit network calls.

Actual first live smoke requires P3J or a later explicit approval phase.

## Purpose

P3I defines the final preflight and approval review package required before a future first live smoke can be considered. It consolidates provider, model, key_slot, allowlist, SDK import, key loading, artifact write, artifact safety scan, failure mapping, stop condition, and rollback review requirements.

## Non-goals

- No actual API call.
- No actual LLM call.
- No actual key use.
- No `.env` file creation.
- No `.env` value usage.
- No actual key loading implementation.
- No provider SDK import.
- No HTTP or network import or call.
- No real provider connection.
- No live smoke execution.
- No live smoke test execution.
- No live-call flag implementation or activation.
- No provider adapter implementation.
- No existing harness code change.
- No semantic_preflight implementation or execution.
- No repair loop implementation or execution.
- No 22-key usage or rotation.
- No worker file edit permission.
- No worker shell permission.
- No external URL access, web search, or repo clone.
- No GitHub Issue integration, web dashboard, CLI agent orchestration, automatic PR, or automatic merge.

## Document Priority

For P3I final preflight / approval review work, document priority is:

1. `AICO_MASTER_CANON.md`
2. `AICO_P3_CANON.md`
3. `P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md`
4. `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`
5. `P3F_FIRST_LIVE_SMOKE_POLICY.md`
6. `P3G_COMPLETION_REVIEW.md`
7. `P3H_COMPLETION_REVIEW.md`
8. `P3F_COMPLETION_REVIEW.md`
9. `P3D_LIVE_CALL_POLICY.md`
10. `P3E_COMPLETION_REVIEW.md`
11. `P3D_COMPLETION_REVIEW.md`
12. `P3C_COMPLETION_REVIEW.md`
13. `P3B_COMPLETION_REVIEW.md`
14. `P3A_COMPLETION_REVIEW.md`
15. `AICO_V0_CANON.md`
16. `HANDOFF.md`
17. `AGENTS.md` / `CLAUDE.md`
18. `CONTEXT_NOTES.md`
19. `checklist.md`

If `P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md` conflicts with `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`, the P3I final preflight / approval review rule wins.

If this document conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`, the higher-priority Canon document wins.

`P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md` is not an actual live smoke approval document. P3I is final preflight / approval review documentation only. Actual live smoke remains forbidden until P3J or a later explicit approval phase.

## Current Safety Baseline

- P2 V0 dry-run is complete and offline.
- P3A fake-provider layer is complete and offline.
- P3B provider boundary skeleton and blocker fix are complete and offline.
- P3C guarded real-provider boundary is complete, disabled by default, and offline.
- P3D live-call gate policy and policy fix are complete.
- P3E activation preparation and LiveApproval blocker fix are complete.
- P3F first live smoke policy and policy fix are complete.
- P3G first live smoke skeleton and completion review are complete.
- P3H approval package documentation, review, and policy fix are complete.
- Provider allowlist default remains empty.
- `RealProvider` defaults to disabled.
- Default transport remains `DisabledTransport`.
- `KeyRegistry.raw_key_value` remains disabled.
- `ProviderResult` has no `raw_output` field.
- `raw_output_saved` defaults to `false` and `raw_output_saved=True` is rejected.
- Default tests are offline and fake/disabled-only.

## Final Preflight Definition

P3I final preflight is a documentation package used to check the following immediately before a future first live smoke is considered:

- provider candidate is safely recorded.
- model candidate is safely recorded.
- key_slot candidate is exactly one allowed slot.
- approval phrase is strict enough.
- provider allowlist opening conditions are clear.
- SDK import allowance is separated from live execution.
- key loading allowance is separated from live execution.
- runtime flag conditions are clear.
- budget is fixed to a one-call smoke.
- prompt is safe.
- expected output schema is minimal JSON.
- `live_smoke_result.json` and `artifact_safety_report.json` write conditions are safe.
- artifact safety scan is connected before and after the future smoke.
- rollback and review procedure is clear.

Rules:

1. Passing final preflight does not automatically execute live smoke.
2. Final preflight is not live smoke authorization.
3. Final preflight must be reviewed again in P3J or a later explicit approval phase.
4. Final preflight must not contain raw key, env var value, endpoint URL, or arbitrary URL.
5. Final preflight records key_slot only.
6. Final preflight may record provider, model, and key_slot candidates, but that does not authorize a provider call.

## Candidate Provider Review

P3I does not activate a provider.

Default candidate:

```text
candidate_provider = google_gemini
candidate_status = candidate_only
```

Review rules:

1. `candidate_provider` is not allowlist activation.
2. `candidate_provider` is not actual API call permission.
3. Presence of `candidate_provider` does not execute live smoke.
4. Unknown provider is `SECURITY_BLOCKED`.
5. Arbitrary URL or unknown endpoint is `SECURITY_BLOCKED`.
6. Provider allowlist activation is possible only in P3J or a later explicit approval phase.

Required decisions before P3J:

- Whether to keep `google_gemini` as the first live smoke provider candidate.
- Whether to review another provider candidate.
- Whether to open provider allowlist from empty to candidate.
- If allowlist opens, whether only provider name is allowed and endpoint URL remains forbidden.

## Candidate Model Review

P3I does not fix an actual model.

Default candidate:

```text
candidate_model = user-approved later
```

Review rules:

1. P3I does not fix an actual model.
2. Actual model can be fixed only inside P3J or a later explicit approval phrase.
3. A model value containing URL, key, token, or endpoint is `SECURITY_BLOCKED`.
4. Missing model is `HUMAN_DECISION_REQUIRED`.

Required decisions before P3J:

- Exact model string for first live smoke.
- Confirmation that model string is not an endpoint URL or secret-like value.
- Whether model string is fixed only inside the approval phrase.

## Candidate Key Slot Review

Allowed key_slot values:

```text
manager_1
worker_1
worker_2
worker_3
worker_4
auditor_1
reserve_1
```

P3I default:

```text
candidate_key_slot = user-approved later
```

Review rules:

1. P3I does not fix an actual key_slot.
2. Actual key_slot can be fixed only inside P3J or a later explicit approval phrase.
3. First live smoke allows exactly one key_slot.
4. Multiple key_slots are `HUMAN_DECISION_REQUIRED`.
5. Unknown key_slot is `SECURITY_BLOCKED`.
6. Raw key-like key_slot is `SECURITY_BLOCKED`.
7. Using an env var name in place of key_slot is `SECURITY_BLOCKED`.
8. Raw key value must never be recorded in documents, prompts, logs, artifacts, reports, or exceptions.
9. Env var names may be recorded, but env var values are forbidden.

Required decisions before P3J:

- Exact single key_slot for first live smoke.
- Whether `reserve_1` is allowed as the smoke key_slot.
- Whether `manager_1`, `worker_1`, or `auditor_1` is safest for smoke purpose.

## Approval Phrase Review

Actual first live smoke execution approval must use this format:

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

Review rules:

1. Anything outside this format is not live smoke approval.
2. Generic phrases such as `진행해`, `계속해`, `해봐`, `OK`, or `승인` are not approval.
3. Missing provider is `HUMAN_DECISION_REQUIRED`.
4. Missing model is `HUMAN_DECISION_REQUIRED`.
5. Missing key_slot is `HUMAN_DECISION_REQUIRED`.
6. Missing `max_model_calls` is `HUMAN_DECISION_REQUIRED`.
7. Missing `max_retries_per_call` is `HUMAN_DECISION_REQUIRED`.
8. Missing `max_runtime_seconds` is `HUMAN_DECISION_REQUIRED`.
9. Missing `allow_raw_output=false` is `HUMAN_DECISION_REQUIRED`.
10. `allow_raw_output` not false is `SECURITY_BLOCKED`.
11. Approval scope must be this run only.
12. Approval phrase containing raw key, token, URL, endpoint, or env var value is `SECURITY_BLOCKED`.

## Provider Allowlist Preflight

Current default:

```text
provider_allowlist = empty
```

P3I judgment:

P3I does not open provider allowlist. P3I documents only the conditions required before a later phase can open the allowlist.

Minimum conditions to open allowlist from empty to candidate:

1. P3I completion review passed.
2. Provider candidate is explicit.
3. Provider name is confirmed not to be a URL.
4. Endpoint URL recording remains forbidden.
5. Approval phrase names the provider.
6. Artifact safety pre-scan passes.
7. Default pytest remains offline-only.
8. Git state is clean.
9. Allowlist opening is authorized only in P3J or a later explicit approval phase.

Failure mapping:

| Condition | failure_type |
| --- | --- |
| allowlist missing | `CONFIG_ERROR` |
| allowlist empty | `CONFIG_ERROR` |
| provider not in allowlist | `SECURITY_BLOCKED` |
| unknown provider | `SECURITY_BLOCKED` |
| arbitrary URL requested | `SECURITY_BLOCKED` |
| unknown endpoint requested | `SECURITY_BLOCKED` |

## SDK Import Preflight

P3I does not allow provider SDK imports.

Minimum conditions before P3J or later SDK import allowance:

1. SDK import scope is limited to one provider adapter file.
2. SDK import does not execute in default pytest.
3. Offline tests without SDK import remain available.
4. SDK import without approval is `SECURITY_BLOCKED`.
5. SDK import approval is separate from live smoke approval.
6. Actual API call remains behind a separate gate even after SDK import approval.

Rules:

- provider SDK import before approved phase -> `SECURITY_BLOCKED`.
- network-capable SDK import in default runtime path -> `SECURITY_BLOCKED`.

## Key Loading Preflight

P3I does not allow actual key loading.

Minimum conditions before P3J or later key loading allowance:

1. Raw key value cannot reach prompt, log, artifact, report, or exception paths.
2. Key access is isolated to the smallest provider adapter boundary.
3. Key existence check returns boolean only.
4. Missing key is `CONFIG_ERROR`.
5. Raw key leak is `SECURITY_BLOCKED`.
6. Env var name recording remains allowed.
7. Env var value recording remains forbidden.
8. `.env` file creation remains forbidden.

Rules:

- actual key read before approved phase -> `SECURITY_BLOCKED`.
- raw key leaked -> `SECURITY_BLOCKED`.
- key missing -> `CONFIG_ERROR`.

## Runtime Flags Preflight

First live smoke can become a candidate only if all these future flags are true:

```text
AICO_ENABLE_REAL_PROVIDER=true
AICO_ALLOW_LIVE_CALLS=true
AICO_ALLOW_FIRST_LIVE_SMOKE=true
```

P3I does not implement or activate flag execution paths.

Rules:

1. Missing flag is `CONFIG_ERROR`.
2. Any false flag is `CONFIG_ERROR`.
3. All flags true are still insufficient without explicit approval.
4. All flags true are still insufficient without allowlist, budget, and artifact safety scan gates.
5. P3I does not actually turn on these flags.

## Budget Preflight

First live smoke budget is fixed:

```text
max_model_calls = 1
max_retries_per_call = 0
max_consecutive_model_errors = 1
max_runtime_seconds = 60
```

Rules:

1. `max_model_calls` must be exactly 1.
2. `max_model_calls > 1` is `SECURITY_BLOCKED`.
3. `max_retries_per_call` must be exactly 0.
4. Retry greater than 0 is `SECURITY_BLOCKED`.
5. Reserve use is forbidden.
6. Fallback provider use is forbidden.
7. A second model call is forbidden.
8. Missing budget is `CONFIG_ERROR`, or `HUMAN_DECISION_REQUIRED` when the missing value is an approval phrase field.
9. Invalid budget is `CONFIG_ERROR`.
10. Exceeded budget is `BUDGET_EXCEEDED`.

## Prompt Preflight

First live smoke prompt must be short and safe.

Allowed intent:

```text
Return a minimal JSON object matching the expected schema.
Do not include secrets, URLs, code execution, or external references.
```

Forbidden prompt content:

- secret.
- API key.
- env value.
- endpoint URL.
- arbitrary URL.
- repo contents.
- user business data.
- file edit request.
- shell or command execution request.
- external reference.

Rules:

1. Secret-like value in prompt is `SECURITY_BLOCKED`.
2. URL in prompt is `SECURITY_BLOCKED`.
3. File modification or execution request in prompt is `SECURITY_BLOCKED`.
4. Prompt is limited to provider-connection structured output smoke.

## Expected Output Preflight

First live smoke expected output is minimal JSON.

Example schema:

```json
{
  "status": "ok",
  "message": "string"
}
```

Rules:

1. Output must be JSON.
2. Non-JSON response is `SCHEMA_ERROR`.
3. Schema-invalid response is `SCHEMA_ERROR`.
4. Schema-valid empty response is `WORKER_BAD_OUTPUT`.
5. Raw output storage is forbidden.
6. Only `masked_raw_output` is allowed.

## Artifact Write Preflight

Allowed first live smoke artifacts:

```text
run_log.jsonl
ceo_report.md
live_smoke_result.json
artifact_safety_report.json
```

Forbidden artifacts:

```text
final_report.md
failed_draft.md
manager_summary.json
audit_report.json
worker_results.jsonl
```

P3I does not implement actual live smoke artifact file creation. P3I defines artifact write preflight conditions only.

Artifact write prerequisites:

1. Artifact write path is limited to the run directory.
2. `final_report.md` and `failed_draft.md` creation remains forbidden.
3. `manager_summary.json`, `audit_report.json`, and `worker_results.jsonl` creation remains forbidden.
4. Raw key field is absent.
5. `raw_output` field is absent.
6. `raw_output_saved=false`.
7. Artifact safety pre-scan passes.
8. Artifact write failure maps to `REPORT_ERROR`.

## Artifact Safety Scan Preflight

Artifact safety scan is required before and after future live smoke.

Pre-scan targets:

- approval phrase.
- provider/model/key_slot summary.
- runtime flags summary.
- provider allowlist summary.
- prompt package.
- expected output schema.
- artifact write plan.

Post-scan targets:

- `run_log.jsonl`.
- `ceo_report.md`.
- `live_smoke_result.json`.
- `artifact_safety_report.json`.

Rules:

1. Prompt, approval, config, and artifact write plan must be scanned before live smoke.
2. All artifacts must be scanned after live smoke.
3. Missing artifact safety scan is `CONFIG_ERROR`.
4. Failed artifact safety scan is `SECURITY_BLOCKED`.
5. Raw key-like value is `SECURITY_BLOCKED`.
6. Bearer token is `SECURITY_BLOCKED`.
7. Private key block is `SECURITY_BLOCKED`.
8. Unmasked raw provider output marker is `SECURITY_BLOCKED`.
9. `raw_output_saved=True` is `SECURITY_BLOCKED`.
10. Scan result is recorded in `artifact_safety_report.json`.

## Logging Preflight

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
7. Approval package validation event is recorded.

## Failure Mapping Review

No new failure_type is added.

| Condition | failure_type |
| --- | --- |
| approval missing | `HUMAN_DECISION_REQUIRED` |
| approval ambiguous | `HUMAN_DECISION_REQUIRED` |
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
| unknown endpoint requested | `SECURITY_BLOCKED` |
| arbitrary URL requested | `SECURITY_BLOCKED` |
| raw key found | `SECURITY_BLOCKED` |
| env var value found | `SECURITY_BLOCKED` |
| unmasked raw provider output found | `SECURITY_BLOCKED` |
| `raw_output_saved=True` detected | `SECURITY_BLOCKED` |
| `allow_raw_output` not false | `SECURITY_BLOCKED` |
| network call in default tests | `SECURITY_BLOCKED` |
| live call attempted without all gates | `SECURITY_BLOCKED` |
| retry attempted | `SECURITY_BLOCKED` |
| reserve attempted | `SECURITY_BLOCKED` |
| second model call attempted | `SECURITY_BLOCKED` |
| SDK import before approved phase | `SECURITY_BLOCKED` |
| actual key read before approved phase | `SECURITY_BLOCKED` |
| budget exceeded | `BUDGET_EXCEEDED` |
| timeout | `MODEL_ERROR` |
| 429 | `MODEL_ERROR` |
| 500 | `MODEL_ERROR` |
| provider unavailable | `MODEL_ERROR` |
| no response | `MODEL_ERROR` |
| non-json response | `SCHEMA_ERROR` |
| schema-invalid json | `SCHEMA_ERROR` |
| schema-valid empty response | `WORKER_BAD_OUTPUT` |
| `ceo_report.md` generation failed | `REPORT_ERROR` |
| artifact write failure | `REPORT_ERROR` |

## Stop Conditions

| Stop condition | failure_type |
| --- | --- |
| approval package missing | `HUMAN_DECISION_REQUIRED` |
| approval phrase missing | `HUMAN_DECISION_REQUIRED` |
| approval phrase ambiguous | `HUMAN_DECISION_REQUIRED` |
| required approval field missing | `HUMAN_DECISION_REQUIRED` |
| provider missing | `HUMAN_DECISION_REQUIRED` |
| model missing | `HUMAN_DECISION_REQUIRED` |
| key_slot missing | `HUMAN_DECISION_REQUIRED` |
| multiple key_slots | `HUMAN_DECISION_REQUIRED` |
| unknown key_slot | `SECURITY_BLOCKED` |
| raw key-like key_slot | `SECURITY_BLOCKED` |
| provider allowlist missing | `CONFIG_ERROR` |
| provider allowlist empty | `CONFIG_ERROR` |
| provider not in allowlist | `SECURITY_BLOCKED` |
| unknown provider requested | `SECURITY_BLOCKED` |
| unknown endpoint requested | `SECURITY_BLOCKED` |
| arbitrary URL requested | `SECURITY_BLOCKED` |
| runtime flag missing | `CONFIG_ERROR` |
| runtime flag false | `CONFIG_ERROR` |
| key missing | `CONFIG_ERROR` |
| raw key appears anywhere | `SECURITY_BLOCKED` |
| env var value appears anywhere | `SECURITY_BLOCKED` |
| raw output appears anywhere | `SECURITY_BLOCKED` |
| `allow_raw_output` not false | `SECURITY_BLOCKED` |
| artifact safety scan missing | `CONFIG_ERROR` |
| artifact safety scan failed | `SECURITY_BLOCKED` |
| budget missing | `CONFIG_ERROR` |
| budget invalid | `CONFIG_ERROR` |
| budget exceeded | `BUDGET_EXCEEDED` |
| retry attempted | `SECURITY_BLOCKED` |
| reserve attempted | `SECURITY_BLOCKED` |
| second model call attempted | `SECURITY_BLOCKED` |
| SDK import appears before approved phase | `SECURITY_BLOCKED` |
| actual key read appears before approved phase | `SECURITY_BLOCKED` |
| network call appears in default tests | `SECURITY_BLOCKED` |
| live smoke appears in default pytest | `SECURITY_BLOCKED` |
| `ProviderResult` safety rules broken | `SECURITY_BLOCKED` |

Every stop condition must map to a canonical failure_type before implementation proceeds.

## Rollback and Review Procedure

If first live smoke fails:

1. Do not retry.
2. Do not use reserve.
3. Do not use fallback provider.
4. Do not widen allowlist.
5. Do not change key_slot.
6. Do not make a second call.
7. Record the failure cause as a canonical failure_type.
8. Attempt to create `ceo_report.md`.
9. Run artifact safety scan.
10. Preserve failure artifacts without raw key or raw output.
11. Decide the next step only after a separate review.

## Required Decisions Before P3J

Before P3J, these decisions are required:

1. Whether P3J is actual live smoke phase or another implementation/review split.
2. Whether provider allowlist opens from empty to `google_gemini` candidate.
3. Exact model string.
4. Exact single key_slot.
5. Whether SDK import is allowed in P3J.
6. Whether key loading is allowed in P3J.
7. Whether artifact write path is implemented.
8. Whether artifact safety scan is connected to actual artifact write path.
9. Whether live smoke failure review document is mandatory.
10. Where and when the actual approval phrase is recorded.

## P3J Entry Requirements

P3J entry requires:

1. P3I final preflight review complete.
2. Provider, model, and key_slot candidate finalization decision.
3. Decision on whether to open provider allowlist.
4. Decision on whether to allow provider SDK import.
5. Decision on whether to allow key loading.
6. Final approval phrase before first live smoke.
7. Live smoke artifact write path decision.
8. Artifact safety scan connection method decision.
9. Live smoke failure rollback and review method decision.
10. P3J entry judged YES.

P3J entry YES is not actual live smoke approval. Actual execution requires separate explicit approval, passing tests, clean git state, and all gates satisfied.

## Final Rule

P3I does not authorize a live smoke.

P3I only defines the final preflight / approval review required before a future first live smoke. Any actual live smoke requires P3J or a later explicit approval phase, passing tests, clean git state, and all gates satisfied.
