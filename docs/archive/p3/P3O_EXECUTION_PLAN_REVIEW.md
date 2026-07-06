# P3O Execution Plan Review
## Status

P3O is execution plan review and explicit approval gate documentation only.

P3O does not authorize a live smoke run. P3O does not execute a live smoke run. P3O does not open provider allowlist activation. P3O does not permit provider SDK imports. P3O does not permit key loading. P3O does not permit actual API calls. P3O does not permit actual key use. P3O does not permit network calls. P3O does not change `live_call_allowed=false`. P3O does not change `model_call_count=0`.

Actual first live smoke requires P3P or a later explicit approval phase.

## Purpose

P3O defines the execution plan review and explicit approval gate that must exist before any future first live smoke can be considered. It records how a later phase may intake an exact approval phrase, create an approval package, bind that package to `final_live_gate_result.json`, and decide whether the next phase is still review-only or narrowly authorized for one call.

## Non-goals

- No actual API call.
- No actual LLM call.
- No actual key use.
- No raw key value read.
- No env var value read.
- No `.env` file creation or value use.
- No actual key loading implementation.
- No provider SDK import.
- No Google, Gemini, OpenAI, Anthropic, `google`, `genai`, `openai`, or `anthropic` runtime import.
- No HTTP or network import or call.
- No real provider connection.
- No actual provider adapter activation.
- No live smoke execution.
- No live smoke test execution.
- No live-call flag execution path activation.
- No provider endpoint URL use.
- No arbitrary URL allowlist.
- No provider allowlist actual activation.
- No SDK import activation.
- No key loading activation.
- No `live_call_allowed=true` transition.
- No `model_call_count=1` transition.
- No `approval_package.json` creation.
- No runtime linkage implementation between `final_live_gate_result.json` and `approval_package.json`.
- No full manager/worker/auditor live run.
- No 22-key use or rotation.
- No semantic preflight or repair loop.
- No worker file edit permission or worker shell permission.
- No external URL access, web search, repo clone, GitHub Issue integration, web dashboard, CLI agent orchestration, automatic PR, or automatic merge.

## Document Priority

For P3O execution plan review work, document priority is:

1. `AICO_MASTER_CANON.md`
2. `AICO_P3_CANON.md`
3. `P3O_EXECUTION_PLAN_REVIEW.md`
4. `P3N_DRY_AUTHORIZATION_REVIEW.md`
5. `P3N_COMPLETION_REVIEW.md`
6. `P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md`
7. `P3M_COMPLETION_REVIEW.md`
8. `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`
9. `P3F_FIRST_LIVE_SMOKE_POLICY.md`
10. `P3L_COMPLETION_REVIEW.md`
11. `P3K_COMPLETION_REVIEW.md`
12. `P3J_COMPLETION_REVIEW.md`
13. `P3I_COMPLETION_REVIEW.md`
14. `P3G_COMPLETION_REVIEW.md`
15. `P3F_COMPLETION_REVIEW.md`
16. `P3D_LIVE_CALL_POLICY.md`
17. `P3E_COMPLETION_REVIEW.md`
18. `P3D_COMPLETION_REVIEW.md`
19. `P3C_COMPLETION_REVIEW.md`
20. `P3B_COMPLETION_REVIEW.md`
21. `P3A_COMPLETION_REVIEW.md`
22. `AICO_V0_CANON.md`
23. `HANDOFF.md`
24. `AGENTS.md` / `CLAUDE.md`
25. `CONTEXT_NOTES.md`
26. `checklist.md`

If `P3O_EXECUTION_PLAN_REVIEW.md` conflicts with `P3N_DRY_AUTHORIZATION_REVIEW.md`, the P3O execution plan review rule wins for execution-plan shape and explicit approval gate documentation.

If this document conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`, the higher-priority Canon document wins.

`P3O_EXECUTION_PLAN_REVIEW.md` is not an actual live smoke approval document. P3O is execution plan review / explicit approval gate documentation only. Actual live smoke remains forbidden until P3P or a later explicit approval phase.

## Current Safety Baseline

- P2 V0 dry-run through P3N completion review are complete.
- `live_call_allowed=false`.
- `model_call_count=0`.
- Provider allowlist actual activation remains forbidden.
- SDK import activation remains forbidden.
- Key loading activation remains forbidden.
- Actual API calls, LLM calls, key usage, provider SDK imports, network calls, and live smoke remain zero.
- `AGENTS.md` and `CLAUDE.md` are expected to remain byte-identical.
- Runtime forbidden SDK/network/env-value imports in `aico_v0` are expected to remain absent.

## P3O Definition

P3O is the execution plan review and explicit approval gate documentation phase immediately before a possible future first live smoke phase.

P3O defines:

- actual approval phrase intake method.
- `approval_package.json` generation conditions.
- provider, model, and key_slot final decision method.
- `final_live_gate_result.json` and `approval_package.json` linkage plan.
- SDK import opening boundary.
- key loading opening boundary.
- provider allowlist activation boundary.
- `live_call_allowed` transition conditions.
- `model_call_count=1` allowance conditions.
- future P3P one-call execution-plan skeleton.
- stop conditions and rollback plan.

P3O does not:

- create `approval_package.json`.
- approve final provider/model/key_slot values.
- activate provider allowlist.
- permit provider SDK import.
- permit key loading.
- set `live_call_allowed=true`.
- set `model_call_count=1`.
- perform actual API, LLM, network, or live smoke calls.

## Explicit Approval Gate Definition

The P3O explicit approval gate means:

1. A user approval phrase is required before any actual call phase can be considered.
2. Missing approval phrase blocks progression to an actual-call phase.
3. Generic approval phrases are rejected.
4. A complete approval phrase still does not execute anything in P3O.
5. The approval phrase may be recorded as an artifact only in P3P or a later explicit approval phase.

Required future approval phrase format:

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

Failure mapping:

- approval missing -> `HUMAN_DECISION_REQUIRED`
- approval ambiguous -> `HUMAN_DECISION_REQUIRED`
- generic approval phrase -> `HUMAN_DECISION_REQUIRED`
- required field missing -> `HUMAN_DECISION_REQUIRED`
- allow_raw_output not false -> `SECURITY_BLOCKED`
- max_model_calls != 1 -> `SECURITY_BLOCKED`
- max_retries_per_call != 0 -> `SECURITY_BLOCKED`
- multiple key_slots -> `HUMAN_DECISION_REQUIRED`
- raw key/token/URL/endpoint/env var value in approval -> `SECURITY_BLOCKED`

## Approval Phrase Intake Policy

P3O documents the approval phrase intake method only. It does not record an actual approval phrase.

Policy:

1. The actual approval phrase is accepted only in P3P or a later explicit approval phase.
2. P3O documentation uses placeholders only.
3. The input surface for the approval phrase must be finalized before P3P.
4. The approval phrase is artifact safety scan input before it can be stored in any run directory artifact.
5. The raw approval phrase must not be copied into final gate result errors or messages.
6. The approval phrase must not contain raw key, token, endpoint URL, or env var value.
7. A complete approval phrase still requires all gates to be revalidated before any actual call.

Recommended future intake:

- User provides the exact approval phrase in chat or a controlled local file.
- Harness records safe parsed fields in `approval_package.json`.
- Harness records `approval_phrase_hash`, not raw approval phrase, in `final_live_gate_result.json`.
- Raw approval phrase is never copied into errors, summaries, or gate messages.

P3O documents this only. It does not create a controlled local file and does not create `approval_package.json`.

## Approval Package Plan

Future P3P or later phases may create `approval_package.json` only after explicit approval and required safety checks.

Recommended schema:

```json
{
  "schema_version": "p3_first_live_smoke_approval_v1",
  "run_id": "<run_id>",
  "approval_scope": "first_live_smoke_this_run_only",
  "approved_by_user": true,
  "provider": "google_gemini",
  "model": "<exact_model_string>",
  "key_slot": "<single_key_slot>",
  "max_model_calls": 1,
  "max_retries_per_call": 0,
  "max_runtime_seconds": 60,
  "allow_raw_output": false,
  "approval_phrase_hash": "<safe_hash>",
  "raw_output_saved": false,
  "live_call_allowed": false,
  "model_call_count_before_execution": 0
}
```

P3O rules:

1. P3O does not create `approval_package.json`.
2. `approval_package.json` creation is deferred to P3P or a later explicit approval phase.
3. `approval_package.json` must not store the raw approval phrase.
4. `approval_package.json` must not store raw key, env var value, or endpoint URL.
5. `approval_package.json` is artifact safety scan input.
6. `approval_package.json` alone does not transition `live_call_allowed`.
7. P3O keeps `model_call_count=0`.

## Final Provider Decision Plan

P3O provider plan:

```text
provider candidate = google_gemini
provider status = candidate_only
actual activation = forbidden in P3O
```

Rules:

1. Exact provider name is finalized only in P3P or a later explicit approval phase through the approval phrase.
2. P3O records `google_gemini` as a candidate only.
3. Provider allowlist actual activation is forbidden in P3O.
4. Endpoint URL is not recorded.
5. `endpoint_url` must be `null`.
6. Provider URL or arbitrary URL maps to `SECURITY_BLOCKED`.
7. Unknown provider maps to `SECURITY_BLOCKED`.
8. Provider candidate still keeps `live_call_allowed=false`.

## Final Model Decision Plan

P3O model plan:

```text
model candidate = user-approved later
actual model string = not fixed in P3O
```

Rules:

1. P3O does not finalize the exact model string.
2. Exact model string is finalized only in P3P or a later explicit approval phase through the approval phrase.
3. Model value must not contain URL, token, key-like value, or endpoint.
4. Missing model maps to `HUMAN_DECISION_REQUIRED`.
5. Model candidate still keeps `live_call_allowed=false`.
6. Model candidate still keeps `model_call_count=0`.

Before P3P, decide:

- exact Gemini model string.
- whether model string is stored only in `approval_package.json`.
- whether model string appears in `final_live_gate_result.json`.
- model string artifact safety scan result.

## Final Key Slot Decision Plan

P3O key_slot plan:

```text
key_slot candidate = user-approved later
actual key_slot = not fixed in P3O
```

Allowed key_slot list:

- `manager_1`
- `worker_1`
- `worker_2`
- `worker_3`
- `worker_4`
- `auditor_1`
- `reserve_1`

Default recommendation: do not use `reserve_1` for the first live smoke. `reserve_1` has recovery semantics, so using it as the primary one-call smoke slot can blur the meaning of reserve policy.

Rules:

1. P3O does not finalize the exact key_slot.
2. Exact key_slot is finalized only in P3P or a later explicit approval phase through the approval phrase.
3. First live smoke allows exactly one key_slot.
4. Multiple key_slots maps to `HUMAN_DECISION_REQUIRED`.
5. Unknown key_slot maps to `SECURITY_BLOCKED`.
6. Raw key-like key_slot maps to `SECURITY_BLOCKED`.
7. Env var name used as key_slot maps to `SECURITY_BLOCKED`.
8. Key_slot candidate does not permit actual key loading.
9. Key_slot candidate still keeps `live_call_allowed=false`.
10. Key_slot candidate still keeps `model_call_count=0`.

## Final Gate Result Linkage Plan

P3O documents the future linkage between P3M `final_live_gate_result.json` and future `approval_package.json`.

Recommended linkage:

`approval_package.json` fields:

- `run_id`
- `approval_phrase_hash`
- `provider`
- `model`
- `key_slot`
- `max_model_calls`
- `max_retries_per_call`
- `max_runtime_seconds`
- `allow_raw_output`

`final_live_gate_result.json` fields:

- `run_id`
- `approval_package_ref`
- `approval_phrase_hash`
- `final_gate_result_ref`
- `live_call_allowed=false`
- `model_call_count=0` before execution

Rules:

1. `run_id` must match across both artifacts.
2. Only `approval_phrase_hash` is used for approval phrase linkage.
3. Raw approval phrase is not copied into final gate result.
4. Final gate result errors and messages must not contain raw secrets.
5. `raw_output` field in final gate result maps to `SECURITY_BLOCKED`.
6. Raw key, env value, or endpoint URL in final gate result maps to `SECURITY_BLOCKED`.
7. Linkage still keeps `live_call_allowed=false` in P3O.
8. Linkage still keeps `model_call_count=0` in P3O.

## Live Call Permission Boundary

P3O documents the live call permission boundary only.

Rules:

1. P3O keeps `live_call_allowed=false`.
2. P3O keeps `model_call_count=0`.
3. `live_call_allowed=true` may be reviewed only in P3P or a later explicit approval phase.
4. `model_call_count=1` may be reviewed only in P3P or a later explicit approval phase.
5. `live_call_allowed=true` and `model_call_count=1` must be explicitly linked in the same approved phase.
6. Even if `live_call_allowed=true` is later approved, `max_model_calls=1` and `max_retries_per_call=0` remain required.
7. `live_call_allowed=true` in P3O maps to `SECURITY_BLOCKED`.
8. `model_call_count>0` in P3O maps to `SECURITY_BLOCKED`.

## SDK Import Opening Boundary

P3O documents the SDK import opening boundary only.

Rules:

1. Provider SDK import is forbidden in P3O.
2. SDK import activation is forbidden in P3O.
3. SDK boundary state may be only `disabled`, `not_approved`, or `candidate_only`.
4. `approved`, `active`, `enabled`, `live`, `sdk_ready`, or `import_ready` maps to `SECURITY_BLOCKED`.
5. Provider SDK imported in runtime path maps to `SECURITY_BLOCKED`.
6. Network-capable SDK import in runtime path maps to `SECURITY_BLOCKED`.
7. Opening actual SDK import may be reviewed only in P3P or a later explicit approval phase.
8. If later opened, SDK import must be isolated inside the minimal provider adapter boundary.

## Key Loading Opening Boundary

P3O documents the key loading opening boundary only.

Rules:

1. Actual key loading is forbidden in P3O.
2. Actual key read is forbidden in P3O.
3. Env var value read is forbidden in P3O.
4. Key existence remains boolean metadata only.
5. `value_loaded=true` maps to `SECURITY_BLOCKED`.
6. `raw_key_present` field maps to `SECURITY_BLOCKED`.
7. Env var value found maps to `SECURITY_BLOCKED`.
8. Opening actual key loading may be reviewed only in P3P or a later explicit approval phase.
9. If later opened, key loading must be isolated inside the minimal provider adapter boundary.

## Provider Allowlist Activation Boundary

P3O documents the provider allowlist activation boundary only.

Rules:

1. Provider allowlist actual activation is forbidden in P3O.
2. Candidate provider is not activation.
3. Provider allowlist summary is artifact safety scan input.
4. `endpoint_url` must be `null`.
5. Endpoint URL or arbitrary URL maps to `SECURITY_BLOCKED`.
6. `live_calls_allowed=true` maps to `SECURITY_BLOCKED`.
7. `sdk_import_allowed=true` maps to `SECURITY_BLOCKED`.
8. `key_loading_allowed=true` maps to `SECURITY_BLOCKED`.
9. Provider allowlist actual activation may be reviewed only in P3P or a later explicit approval phase.

## Runtime Flags Execution Boundary

Required future flags:

- `AICO_ENABLE_REAL_PROVIDER=true`
- `AICO_ALLOW_LIVE_CALLS=true`
- `AICO_ALLOW_FIRST_LIVE_SMOKE=true`

P3O rules:

1. P3O does not read actual env var values.
2. Runtime flags are reviewed only as injected or simulated metadata.
3. Missing flag maps to `CONFIG_ERROR`.
4. False flag maps to `CONFIG_ERROR`.
5. True flags still keep `live_call_allowed=false` in P3O.
6. True flags still keep `model_call_count=0` in P3O.
7. Secret-like flag value maps to `SECURITY_BLOCKED`.
8. P3O does not activate flag execution paths.

## Artifact Creation Plan

P3O documents artifact creation plans only.

Future P3P candidate artifacts:

- `approval_package.json`
- `final_live_gate_result.json`
- `live_smoke_result.json`
- `artifact_safety_report.json`
- `run_log.jsonl`
- `ceo_report.md`

Forbidden artifacts remain:

- `final_report.md`
- `failed_draft.md`
- `manager_summary.json`
- `audit_report.json`
- `worker_results.jsonl`

P3O rules:

1. P3O does not create `approval_package.json`.
2. P3O does not create `live_smoke_result.json` as an actual live smoke result.
3. P3O documents artifact package schema and path policy only.
4. Every artifact path must stay inside `run_dir`.
5. Path traversal maps to `SECURITY_BLOCKED`.
6. Raw key, raw output, env var value, or endpoint URL maps to `SECURITY_BLOCKED`.
7. Artifact write failure maps to `REPORT_ERROR`.

## Artifact Safety Plan

P3O documents artifact safety linkage.

Scan targets:

- approval phrase.
- approval package schema.
- provider/model/key_slot summary.
- runtime flags summary.
- provider allowlist summary.
- SDK boundary summary.
- key loading boundary summary.
- `final_live_gate_result` summary.
- artifact package summary.
- `live_smoke_result` summary if created in a future phase.

Rules:

1. Artifact safety scan missing maps to `CONFIG_ERROR`.
2. Artifact safety scan failed maps to `SECURITY_BLOCKED`.
3. Raw key-like value found maps to `SECURITY_BLOCKED`.
4. Bearer token found maps to `SECURITY_BLOCKED`.
5. Private key block found maps to `SECURITY_BLOCKED`.
6. Env var value found maps to `SECURITY_BLOCKED`.
7. Endpoint URL found maps to `SECURITY_BLOCKED`.
8. `raw_output_saved=True` found maps to `SECURITY_BLOCKED`.
9. `raw_output` field found maps to `SECURITY_BLOCKED`.
10. Success-like live status before actual approved execution maps to `SECURITY_BLOCKED`.

## Execution Plan for Future P3P

If P3P or a later explicit approval phase is separately approved for actual first live smoke, the candidate execution plan is:

1. Read explicit approval phrase from the approved intake surface.
2. Parse provider, model, key_slot, max_model_calls, max_retries, max_runtime, and allow_raw_output.
3. Build `approval_package.json` inside `run_dir`.
4. Run artifact safety scan on approval package.
5. Run final all-gates validator.
6. Confirm `live_call_allowed` remains false until final explicit execution gate.
7. If P3P is approved to execute, flip `live_call_allowed` only inside the minimal execution boundary.
8. Allow exactly one provider call.
9. Allow no retries.
10. Allow no reserve.
11. Allow no fallback provider.
12. Record `model_call_count=1` only after the single attempted call.
13. Save only masked and safe output metadata.
14. Run artifact safety post-scan.
15. Generate `ceo_report.md`.
16. Stop immediately after one call attempt.

This plan is not executed in P3O. P3O documents only the future execution plan.

## Stop Conditions

Stop conditions and canonical failure types:

- approval phrase missing -> `HUMAN_DECISION_REQUIRED`
- approval phrase ambiguous -> `HUMAN_DECISION_REQUIRED`
- generic approval phrase -> `HUMAN_DECISION_REQUIRED`
- required approval field missing -> `HUMAN_DECISION_REQUIRED`
- approval package location unsafe -> `SECURITY_BLOCKED`
- approval package contains raw key -> `SECURITY_BLOCKED`
- approval package contains env var value -> `SECURITY_BLOCKED`
- approval package contains endpoint URL -> `SECURITY_BLOCKED`
- provider missing -> `HUMAN_DECISION_REQUIRED`
- unknown provider -> `SECURITY_BLOCKED`
- provider URL requested -> `SECURITY_BLOCKED`
- endpoint URL requested -> `SECURITY_BLOCKED`
- arbitrary URL requested -> `SECURITY_BLOCKED`
- model missing -> `HUMAN_DECISION_REQUIRED`
- model contains URL/token/key/endpoint -> `SECURITY_BLOCKED`
- key_slot missing -> `HUMAN_DECISION_REQUIRED`
- multiple key_slots -> `HUMAN_DECISION_REQUIRED`
- unknown key_slot -> `SECURITY_BLOCKED`
- raw key-like key_slot -> `SECURITY_BLOCKED`
- runtime flag missing -> `CONFIG_ERROR`
- runtime flag false -> `CONFIG_ERROR`
- provider allowlist actual activation attempted in P3O -> `SECURITY_BLOCKED`
- sdk_import_allowed true in P3O -> `SECURITY_BLOCKED`
- key_loading_allowed true in P3O -> `SECURITY_BLOCKED`
- live_calls_allowed true in P3O -> `SECURITY_BLOCKED`
- SDK import activation attempted in P3O -> `SECURITY_BLOCKED`
- key loading activation attempted in P3O -> `SECURITY_BLOCKED`
- actual key read attempted -> `SECURITY_BLOCKED`
- env var value read attempted -> `SECURITY_BLOCKED`
- live_call_allowed true in P3O -> `SECURITY_BLOCKED`
- model_call_count > 0 in P3O -> `SECURITY_BLOCKED`
- raw_output_saved true -> `SECURITY_BLOCKED`
- raw_output field present -> `SECURITY_BLOCKED`
- success-like status present -> `SECURITY_BLOCKED`
- artifact safety scan missing -> `CONFIG_ERROR`
- artifact safety scan failed -> `SECURITY_BLOCKED`
- path traversal attempted -> `SECURITY_BLOCKED`
- artifact write outside run_dir -> `SECURITY_BLOCKED`
- forbidden artifact attempted -> `SECURITY_BLOCKED`

## Failure Handling and Rollback Plan

For a future actual first live smoke failure:

1. Do not retry.
2. Do not use reserve.
3. Do not use fallback provider.
4. Do not widen allowlist.
5. Do not change key_slot.
6. Do not make a second call.
7. Record failure cause with canonical `failure_type`.
8. Attempt to generate `ceo_report.md`.
9. Run artifact safety scan.
10. Preserve failure artifacts without preserving raw key or raw output.
11. Decide the next step only after a separate review.

## Required Decisions Before P3P

Before P3P, decide:

1. Whether P3P is actual first live smoke or another code activation skeleton.
2. Where to intake the actual approval phrase.
3. Whether to create `approval_package.json`.
4. Exact provider name.
5. Exact model string.
6. Exact single key_slot.
7. Whether `reserve_1` is forbidden for first smoke.
8. Whether to implement real linkage between `final_live_gate_result.json` and approval package.
9. Whether to allow provider allowlist actual activation.
10. Whether to allow SDK import.
11. Whether to allow key loading.
12. Whether P3P is the phase that may set `live_call_allowed=true`.
13. Whether P3P is the phase that may allow `model_call_count=1`.
14. Whether live smoke failure review document is mandatory.
15. Whether every automatic follow-up call after the first call is absolutely forbidden.

## P3P Entry Requirements

P3P entry requires:

1. P3O execution plan review complete.
2. P3O completion review complete.
3. Actual approval phrase intake method decided.
4. Exact provider/model/key_slot decision method decided.
5. Approval package artifact creation decision made.
6. Final gate linkage implementation decision made.
7. Provider allowlist actual activation decision made.
8. SDK import decision made.
9. Key loading decision made.
10. `live_call_allowed` transition decision made.
11. `model_call_count=1` allowance decision made.
12. Rollback/review method decided.
13. P3P entry YES decision.

P3P entry YES is not actual live smoke approval. Actual execution requires separate explicit approval, passing tests, clean git state, and all gates satisfied.

## Final Rule

P3O does not authorize or execute a live smoke. P3O only defines the execution plan review and explicit approval gate required before a future first live smoke. P3O keeps `live_call_allowed=false` and `model_call_count=0`. Any actual live smoke requires P3P or a later explicit approval phase, passing tests, clean git state, all gates satisfied, and an exact user approval phrase.
