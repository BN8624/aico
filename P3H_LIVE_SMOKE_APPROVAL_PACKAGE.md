# P3H Live Smoke Approval Package
## Status

P3H is approval-package documentation only.

P3H does not authorize a live smoke run. P3H does not implement provider activation. P3H does not permit actual API calls. P3H does not permit actual key use. P3H does not permit provider SDK imports. P3H does not permit network calls.

Actual first live smoke requires a later explicit approval phase.

## Purpose

P3H defines the approval package required before a future first live smoke can be reviewed. It fixes the approval phrase format, candidate recording format, budget limits, runtime flag expectations, artifact safety package, stop conditions, and P3I entry requirements.

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

For P3H approval-package work, document priority is:

1. `AICO_MASTER_CANON.md`
2. `AICO_P3_CANON.md`
3. `P3F_FIRST_LIVE_SMOKE_POLICY.md`
4. `P3G_COMPLETION_REVIEW.md`
5. `P3F_COMPLETION_REVIEW.md`
6. `P3D_LIVE_CALL_POLICY.md`
7. `P3E_COMPLETION_REVIEW.md`
8. `P3D_COMPLETION_REVIEW.md`
9. `P3C_COMPLETION_REVIEW.md`
10. `P3B_COMPLETION_REVIEW.md`
11. `P3A_COMPLETION_REVIEW.md`
12. `AICO_V0_CANON.md`
13. `HANDOFF.md`
14. `AGENTS.md` / `CLAUDE.md`
15. `CONTEXT_NOTES.md`
16. `checklist.md`

If this document conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`, the higher-priority Canon document wins.

If this document conflicts with `P3D_LIVE_CALL_POLICY.md`, the P3F first-live-smoke-specific policy remains the controlling policy for first live smoke scope. P3H only defines an approval package format and does not authorize execution.

## Current Safety Baseline

- P2 V0 dry-run is complete and offline.
- P3A fake-provider layer is complete and offline.
- P3B provider boundary skeleton and blocker fix are complete and offline.
- P3C guarded real-provider boundary is complete, disabled by default, and offline.
- P3D live-call gate policy and policy fix are complete.
- P3E activation preparation and LiveApproval blocker fix are complete.
- P3F first live smoke policy and policy fix are complete.
- P3G first live smoke skeleton and completion review are complete.
- Provider allowlist default remains empty.
- `RealProvider` defaults to disabled.
- Default transport remains `DisabledTransport`.
- `KeyRegistry.raw_key_value` remains disabled.
- `ProviderResult` has no `raw_output` field.
- `raw_output_saved` defaults to `false` and `raw_output_saved=True` is rejected.
- Default tests are offline and fake/disabled-only.

## Approval Package Definition

A first live smoke approval package is a documentation bundle that collects every approval, limit, safety check, and rollback condition needed before a future first live smoke can be reviewed.

It must include:

- explicit approval phrase.
- provider.
- model.
- key_slot.
- max_model_calls.
- max_retries_per_call.
- max_runtime_seconds.
- allow_raw_output.
- approval_scope.
- provider allowlist state.
- runtime flags.
- artifact safety scan requirement.
- live smoke prompt.
- expected output schema.
- artifact list.
- rollback and stop conditions.

Rules:

1. Approval package presence does not automatically execute a live smoke.
2. Approval package presence is not live smoke authorization.
3. The approval package must be reviewed in P3I or a later explicit approval phase.
4. The approval package must not contain a raw key, env var value, endpoint URL, or arbitrary URL.
5. The approval package records key_slot only.
6. The approval package may record provider and model candidates, but that does not authorize a provider call.

## Required Approval Phrase

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

Rules:

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

## Candidate Provider Section

P3H does not activate a provider.

Default candidate metadata:

```text
candidate_provider = google_gemini
candidate_status = candidate_only
```

Rules:

1. `candidate_provider` is not provider allowlist activation.
2. `candidate_provider` is not actual API call approval.
3. Presence of `candidate_provider` does not execute live smoke.
4. Unknown provider is `SECURITY_BLOCKED`.
5. Arbitrary URL or unknown endpoint is `SECURITY_BLOCKED`.
6. Provider allowlist activation is possible only in P3I or a later explicit approval phase.

## Candidate Model Section

The model is not fixed in P3H.

Default:

```text
candidate_model = user-approved later
```

Rules:

1. P3H does not select an actual model.
2. The actual model can be fixed only inside a later explicit approval phrase.
3. A model value containing a URL, key, token, or endpoint is `SECURITY_BLOCKED`.
4. Missing model is `HUMAN_DECISION_REQUIRED`.

## Candidate Key Slot Section

Exactly one key_slot is allowed for a future first live smoke.

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

P3H default:

```text
candidate_key_slot = user-approved later
```

Rules:

1. P3H does not fix an actual key_slot.
2. The actual key_slot can be fixed only inside a later explicit approval phrase.
3. First live smoke allows exactly one key_slot.
4. Multiple key_slots are `HUMAN_DECISION_REQUIRED`.
5. Unknown key_slot is `SECURITY_BLOCKED`.
6. Raw key-like key_slot is `SECURITY_BLOCKED`.
7. Using an env var name in place of key_slot is `SECURITY_BLOCKED`.
8. Raw key value must never be recorded in documents, prompts, logs, artifacts, reports, or exceptions.
9. Env var names may be recorded, but env var values are forbidden.

## Budget Section

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

## Runtime Flags Section

First live smoke can become a candidate only if all these future flags are true:

```text
AICO_ENABLE_REAL_PROVIDER=true
AICO_ALLOW_LIVE_CALLS=true
AICO_ALLOW_FIRST_LIVE_SMOKE=true
```

Rules:

1. Missing flag is `CONFIG_ERROR`.
2. Any false flag is `CONFIG_ERROR`.
3. All flags true are still insufficient without explicit approval.
4. All flags true are still insufficient without allowlist, budget, and artifact safety scan gates.
5. P3H forbids implementing or activating flag execution paths.

## Provider Allowlist Section

Current default:

```text
provider_allowlist = empty
```

Rules:

1. Empty allowlist forbids live smoke.
2. Missing allowlist is `CONFIG_ERROR`.
3. Empty allowlist is `CONFIG_ERROR`.
4. Provider not in allowlist is `SECURITY_BLOCKED`.
5. Unknown provider is `SECURITY_BLOCKED`.
6. Arbitrary URL requested is `SECURITY_BLOCKED`.
7. Unknown endpoint requested is `SECURITY_BLOCKED`.
8. P3H documentation alone does not open the allowlist.
9. Opening provider allowlist from empty to candidate is allowed only in P3I or a later explicit approval phase.

## SDK Import Policy

P3H does not allow provider SDK imports.

Rules:

1. Provider SDK import is forbidden in P3H.
2. Google, Gemini, OpenAI, Anthropic, and similar real SDK imports are forbidden.
3. SDK import allowance must be decided in P3I or a later explicit approval phase.
4. If later approved, SDK import must be isolated inside provider adapter files.
5. SDK import before approval is `SECURITY_BLOCKED`.

## Key Loading Policy

P3H does not allow actual key loading.

Rules:

1. Do not read actual key values.
2. Do not create `.env` files.
3. Do not use `.env` values.
4. Key existence may be represented only as a boolean.
5. Missing key is `CONFIG_ERROR`.
6. Raw key leak is `SECURITY_BLOCKED`.
7. Key loading allowance must be decided in P3I or a later explicit approval phase.
8. If later approved, key loading must be isolated to the smallest provider adapter boundary.

## Prompt Package

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

## Expected Output Schema

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

## Artifact Package

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

Rules:

1. First live smoke must not create full AICO run artifacts.
2. Every artifact is subject to secret scan.
3. Only key_slot is recorded.
4. Raw key recording is forbidden.
5. Raw output recording is forbidden.
6. `final_report.md` and `failed_draft.md` are forbidden.

## Artifact Safety Package

Artifact safety scan is required before and after live smoke.

Required scan targets:

- approval package.
- runtime flags summary.
- provider allowlist summary.
- prompt package.
- expected output schema.
- `run_log.jsonl`.
- `ceo_report.md`.
- `live_smoke_result.json`.
- `artifact_safety_report.json`.

Rules:

1. Prompt, approval, and config must be scanned before live smoke.
2. All artifacts must be scanned after live smoke.
3. Missing artifact safety scan is `CONFIG_ERROR`.
4. Failed artifact safety scan is `SECURITY_BLOCKED`.
5. Raw key-like value is `SECURITY_BLOCKED`.
6. Bearer token is `SECURITY_BLOCKED`.
7. Private key block is `SECURITY_BLOCKED`.
8. Unmasked raw provider output marker is `SECURITY_BLOCKED`.
9. `raw_output_saved=True` is `SECURITY_BLOCKED`.
10. Scan result must be recorded in `artifact_safety_report.json`.

## Logging Package

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
| allow_raw_output not false | `SECURITY_BLOCKED` |
| artifact safety scan missing | `CONFIG_ERROR` |
| artifact safety scan failed | `SECURITY_BLOCKED` |
| budget missing | `CONFIG_ERROR` |
| budget invalid | `CONFIG_ERROR` |
| budget exceeded | `BUDGET_EXCEEDED` |
| retry attempted | `SECURITY_BLOCKED` |
| reserve attempted | `SECURITY_BLOCKED` |
| second model call attempted | `SECURITY_BLOCKED` |
| SDK import appears before approved phase | `SECURITY_BLOCKED` |
| network call appears in default tests | `SECURITY_BLOCKED` |
| live smoke appears in default pytest | `SECURITY_BLOCKED` |
| `ProviderResult` safety rules broken | `SECURITY_BLOCKED` |

Every stop condition must map to a canonical failure_type before implementation proceeds.

## Rollback Package

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

## Pre-live Checklist

- [ ] explicit approval phrase present.
- [ ] provider specified.
- [ ] model specified.
- [ ] exactly one key_slot specified.
- [ ] key_slot is allowed.
- [ ] `max_model_calls = 1`.
- [ ] `max_retries_per_call = 0`.
- [ ] `max_runtime_seconds` set.
- [ ] `allow_raw_output = false`.
- [ ] `approval_scope = this_run_only`.
- [ ] runtime flags all true.
- [ ] provider allowlist non-empty.
- [ ] provider in allowlist.
- [ ] no arbitrary URL.
- [ ] key availability check safe.
- [ ] artifact safety pre-scan pass.
- [ ] default pytest offline-only.
- [ ] git status clean.
- [ ] tests passing.

## Approval Package Validation Checklist

- [ ] no raw key in approval package.
- [ ] no bearer token in approval package.
- [ ] no private key block in approval package.
- [ ] no env var value in approval package.
- [ ] no endpoint URL in approval package.
- [ ] no arbitrary URL in approval package.
- [ ] key_slot only.
- [ ] env var name allowed.
- [ ] masked placeholder allowed.
- [ ] approval phrase exact enough.
- [ ] this run only scope.

## P3I Entry Requirements

P3I entry requires:

1. P3H approval package review complete.
2. Provider, model, and key_slot candidate finalization decision.
3. Decision on whether to open provider allowlist.
4. Decision on whether to allow provider SDK import.
5. Decision on whether to allow key loading.
6. Final approval phrase before first live smoke.
7. Live smoke artifact write path decision.
8. Artifact safety scan connection method decision.
9. Live smoke failure rollback and review method decision.
10. P3I entry judged YES.

P3I entry YES is not actual live smoke approval. Actual execution requires a later explicit approval, passing tests, clean git state, and all gates satisfied.

## Final Rule

P3H does not authorize a live smoke.

P3H only defines the approval package required before a future first live smoke. Any actual live smoke requires a later explicit approval phase, passing tests, clean git state, and all gates satisfied.
