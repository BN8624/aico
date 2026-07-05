# P3N Dry Authorization Review
## Status

P3N is dry authorization review documentation only.

P3N does not authorize a live smoke run. P3N does not open provider allowlist. P3N does not implement provider activation. P3N does not permit actual API calls. P3N does not permit actual key use. P3N does not permit provider SDK imports. P3N does not permit network calls. P3N does not change `live_call_allowed=false`. P3N does not change `model_call_count=0`.

Actual first live smoke requires P3O or a later explicit approval phase.

## Purpose

P3N defines the final dry authorization review package used before any future first live smoke can be considered. It documents where the future explicit approval phrase may be recorded, how dry provider/model/key_slot candidates are represented, how an approval package should link to `final_live_gate_result.json`, and why all-gates pass still does not authorize execution.

## Non-goals

- No actual API call.
- No actual LLM call.
- No actual key use.
- No raw key value read.
- No env var value read.
- No `.env` file creation.
- No `.env` value usage.
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
- No full manager/worker/auditor live run.
- No 22-key use or rotation.
- No semantic preflight or repair loop.
- No worker file edit permission or worker shell permission.
- No external URL access, web search, repo clone, GitHub Issue integration, web dashboard, CLI agent orchestration, automatic PR, or automatic merge.

## Document Priority

For P3N dry authorization review work, document priority is:

1. `AICO_MASTER_CANON.md`
2. `AICO_P3_CANON.md`
3. `P3N_DRY_AUTHORIZATION_REVIEW.md`
4. `P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md`
5. `P3M_COMPLETION_REVIEW.md`
6. `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`
7. `P3F_FIRST_LIVE_SMOKE_POLICY.md`
8. `P3L_COMPLETION_REVIEW.md`
9. `P3K_COMPLETION_REVIEW.md`
10. `P3J_COMPLETION_REVIEW.md`
11. `P3I_COMPLETION_REVIEW.md`
12. `P3G_COMPLETION_REVIEW.md`
13. `P3F_COMPLETION_REVIEW.md`
14. `P3D_LIVE_CALL_POLICY.md`
15. `P3E_COMPLETION_REVIEW.md`
16. `P3D_COMPLETION_REVIEW.md`
17. `P3C_COMPLETION_REVIEW.md`
18. `P3B_COMPLETION_REVIEW.md`
19. `P3A_COMPLETION_REVIEW.md`
20. `AICO_V0_CANON.md`
21. `HANDOFF.md`
22. `AGENTS.md` / `CLAUDE.md`
23. `CONTEXT_NOTES.md`
24. `checklist.md`

If `P3N_DRY_AUTHORIZATION_REVIEW.md` conflicts with `P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md` or `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`, the P3N dry authorization review rule wins for final dry authorization package shape and review conditions.

If this document conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`, the higher-priority Canon document wins.

`P3N_DRY_AUTHORIZATION_REVIEW.md` is not an actual live smoke approval document. P3N is dry authorization review documentation only. Actual live smoke remains forbidden until P3O or a later explicit approval phase.

## Current Safety Baseline

- P2 V0 dry-run is complete and offline.
- P3A fake-provider layer is complete and offline.
- P3B provider boundary skeleton and blocker fix are complete and offline.
- P3C guarded real-provider boundary is complete, disabled by default, and offline.
- P3D live-call gate policy and policy fix are complete.
- P3E activation preparation and blocker fix are complete.
- P3F first live smoke policy and policy fix are complete.
- P3G first live smoke skeleton and completion review are complete.
- P3H approval package documentation, review, and policy fix are complete.
- P3I final preflight / approval review and completion review are complete.
- P3J live smoke execution skeleton / artifact write integration and completion review are complete.
- P3K live provider activation skeleton / allowlist opening skeleton and completion review are complete.
- P3L SDK/key-loading boundary skeleton and completion review are complete.
- P3M final live-call gate implementation skeleton and completion review are complete.
- `live_call_allowed=false`.
- `model_call_count=0`.
- Provider allowlist actual activation remains forbidden.
- SDK import activation remains forbidden.
- Key loading activation remains forbidden.
- Actual API calls, LLM calls, key usage, provider SDK imports, network calls, and live smoke remain zero.

## Dry Authorization Definition

P3N dry authorization review is a documentation package used immediately before a future first live smoke to compare the approval package shape against the final gate result shape without executing anything.

It includes:

- approval phrase recording location.
- dry provider candidate.
- dry model candidate.
- dry key_slot candidate.
- `final_live_gate_result` linkage.
- all-gates pass interpretation.
- runtime flags dry summary.
- provider allowlist dry summary.
- SDK boundary dry summary.
- key loading boundary dry summary.
- artifact package dry summary.
- artifact safety dry summary.
- execution boundary.
- stop conditions.
- rollback and review plan.

Rules:

1. Passing dry authorization review does not automatically execute live smoke.
2. Dry authorization review is not live smoke execution authorization.
3. Dry authorization review must be reviewed again in P3O or a later explicit approval phase.
4. Raw key, env var value, endpoint URL, and arbitrary URL must not appear.
5. Only `key_slot` may be recorded, never a raw key.
6. Provider, model, and key_slot candidates may be recorded, but they do not authorize an actual provider call.
7. If final gate result is `ready_for_review`, `live_call_allowed=false` still applies.
8. `model_call_count` must remain `0`.

## Approval Phrase Recording Policy

The future first live smoke approval phrase must use this exact shape:

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

P3N does not use this phrase as an actual approval. P3N only defines where and how a later phase may record and validate it.

Approval phrase recording policy:

1. The actual approval phrase is recorded only in P3O or a later explicit approval phase.
2. P3N does not write the approval phrase as a final value.
3. P3N records placeholders or dry candidates only.
4. The approval phrase must not contain raw key, token, URL, endpoint, or env var value.
5. The approval phrase is artifact safety scan input before it is stored in any run artifact.
6. The approval phrase storage location must be a safe artifact inside the run directory.
7. Generic approval phrase maps to `HUMAN_DECISION_REQUIRED`.
8. Missing approval phrase maps to `HUMAN_DECISION_REQUIRED`.
9. Even a complete approval phrase does not grant live-call permission in P3N.

Recommended future recording location:

```text
runs/<run_id>/approval_package.json
```

P3N does not create `approval_package.json`. P3N documents only the location and schema expectation. Actual creation is deferred to P3O or a later explicit approval phase.

## Final Candidate Provider

P3N dry candidate:

```text
provider = google_gemini
provider_status = candidate_only
```

Rules:

1. `google_gemini` is a provider-name candidate only, not actual activation.
2. Provider allowlist actual activation is forbidden in P3N.
3. Endpoint URL is not recorded.
4. Endpoint URL or arbitrary URL maps to `SECURITY_BLOCKED`.
5. Unknown provider maps to `SECURITY_BLOCKED`.
6. Provider candidate still keeps `live_call_allowed=false`.

## Final Candidate Model

P3N dry candidate:

```text
model = user-approved later
```

Rules:

1. P3N does not finalize the real model string.
2. The exact model string is finalized only in P3O or a later explicit approval phase.
3. Model value containing URL, token, key, or endpoint maps to `SECURITY_BLOCKED`.
4. Missing model maps to `HUMAN_DECISION_REQUIRED`.
5. Model candidate still keeps `live_call_allowed=false`.

P3O must decide the exact model string, confirm model string safety scan result, and decide whether the model is recorded only in the approval phrase.

## Final Candidate Key Slot

P3N dry candidate:

```text
key_slot = user-approved later
```

Allowed key_slot list:

- `manager_1`
- `worker_1`
- `worker_2`
- `worker_3`
- `worker_4`
- `auditor_1`
- `reserve_1`

Rules:

1. P3N does not finalize the real key_slot.
2. The exact key_slot is finalized only in P3O or a later explicit approval phase.
3. First live smoke allows exactly one key_slot.
4. Multiple key_slots maps to `HUMAN_DECISION_REQUIRED`.
5. Unknown key_slot maps to `SECURITY_BLOCKED`.
6. Raw key-like key_slot maps to `SECURITY_BLOCKED`.
7. Using an env var name instead of key_slot maps to `SECURITY_BLOCKED`.
8. Key_slot candidate does not permit actual key loading.
9. Key_slot candidate still keeps `live_call_allowed=false`.

P3O must decide the exact single key_slot, whether `reserve_1` is disallowed for first smoke, and the safest slot choice for one-call smoke.

## Final Gate Result Linkage

P3N documents how `final_live_gate_result.json` should link to the future approval package.

Linkage rules:

1. `final_live_gate_result.json` and approval package must share the same `run_id`.
2. `final_live_gate_result.json` may record only an approval phrase hash or safe reference.
3. The raw approval phrase is always secret-scan input.
4. The raw approval phrase must not be copied into final gate result error or message fields.
5. If `final_live_gate_result.status=ready_for_review`, `live_call_allowed=false` must still hold.
6. `final_live_gate_result.model_call_count` must be `0`.
7. `final_live_gate_result.raw_output_saved` must be `false`.
8. Any `raw_output` field in final gate result maps to `SECURITY_BLOCKED`.
9. Raw key, env value, or endpoint URL in final gate result maps to `SECURITY_BLOCKED`.
10. Passing final gate result does not execute live smoke.

Recommended linkage fields:

- `approval_package_ref`
- `approval_phrase_hash`
- `final_gate_result_ref`
- `run_id`

The hash is not secret storage. P3N does not create an actual approval package file.

## All-Gates Pass Interpretation

If the P3M final gate passes or reaches `ready_for_review`, these values must remain:

```text
live_call_allowed = false
model_call_count = 0
raw_output_saved = false
```

Rules:

1. All-gates pass means additional approval review is possible, not execution is possible.
2. `ready_for_review` is not live-call permission.
3. `prepared` is not live-call permission.
4. `success`, `live_success`, `api_success`, and `provider_success` map to `SECURITY_BLOCKED`.
5. Interpreting all-gates pass as actual call authorization in P3N maps to `SECURITY_BLOCKED`.

## Runtime Flags Dry Review

Future first live smoke requires these flags:

```text
AICO_ENABLE_REAL_PROVIDER=true
AICO_ALLOW_LIVE_CALLS=true
AICO_ALLOW_FIRST_LIVE_SMOKE=true
```

P3N rules:

1. P3N does not read actual env var values.
2. Runtime flags are reviewed only as injected or simulated metadata.
3. Missing flag maps to `CONFIG_ERROR`.
4. False flag maps to `CONFIG_ERROR`.
5. True flags still keep `live_call_allowed=false`.
6. Secret-like flag value maps to `SECURITY_BLOCKED`.
7. P3N does not activate flag execution paths.

## Provider Allowlist Dry Review

P3N rules:

1. Provider allowlist actual activation is forbidden.
2. Candidate provider is not activation.
3. Provider allowlist summary is artifact safety scan input.
4. `endpoint_url` must be `null`.
5. Endpoint URL or arbitrary URL maps to `SECURITY_BLOCKED`.
6. `live_calls_allowed=true` maps to `SECURITY_BLOCKED`.
7. `sdk_import_allowed=true` maps to `SECURITY_BLOCKED`.
8. `key_loading_allowed=true` maps to `SECURITY_BLOCKED`.
9. Allowlist candidate still keeps `live_call_allowed=false`.

## SDK Boundary Dry Review

P3N rules:

1. SDK import activation is forbidden.
2. SDK boundary may be only `disabled`, `not_approved`, or `candidate_only`.
3. `approved`, `active`, `enabled`, `live`, `sdk_ready`, and `import_ready` map to `SECURITY_BLOCKED`.
4. Provider SDK imported in runtime path maps to `SECURITY_BLOCKED`.
5. Network-capable SDK import in runtime path maps to `SECURITY_BLOCKED`.
6. Passing SDK boundary still does not permit SDK import.

## Key Loading Boundary Dry Review

P3N rules:

1. Key loading activation is forbidden.
2. Actual key read is forbidden.
3. Env var value read is forbidden.
4. Key existence uses boolean metadata only.
5. `value_loaded=true` maps to `SECURITY_BLOCKED`.
6. `raw_key_present` field maps to `SECURITY_BLOCKED`.
7. Env var value found maps to `SECURITY_BLOCKED`.
8. Passing key boundary still does not permit key value read.

## Artifact Package Dry Review

Allowed future artifact candidates:

- `approval_package.json`
- `final_live_gate_result.json`
- `live_smoke_result.json`
- `artifact_safety_report.json`
- `run_log.jsonl`
- `ceo_report.md`

Forbidden artifacts:

- `final_report.md`
- `failed_draft.md`
- `manager_summary.json`
- `audit_report.json`
- `worker_results.jsonl`

P3N rules:

1. P3N does not create `approval_package.json`.
2. P3N does not create `live_smoke_result.json` as a real live smoke result.
3. P3N documents artifact package schema and path policy only.
4. Every artifact path must remain inside `run_dir`.
5. Path traversal maps to `SECURITY_BLOCKED`.
6. Raw key, raw output, env var value, or endpoint URL maps to `SECURITY_BLOCKED`.
7. Artifact write failure maps to `REPORT_ERROR`.

## Artifact Safety Dry Review

P3N documents artifact safety scan linkage for these dry inputs:

- approval phrase.
- approval package dry schema.
- provider/model/key_slot dry summary.
- runtime flags dry summary.
- provider allowlist dry summary.
- SDK boundary dry summary.
- key loading boundary dry summary.
- `final_live_gate_result` dry summary.
- artifact package dry summary.

Rules:

1. Artifact safety scan missing maps to `CONFIG_ERROR`.
2. Artifact safety scan failed maps to `SECURITY_BLOCKED`.
3. Raw key-like value found maps to `SECURITY_BLOCKED`.
4. Bearer token found maps to `SECURITY_BLOCKED`.
5. Private key block found maps to `SECURITY_BLOCKED`.
6. Env var value found maps to `SECURITY_BLOCKED`.
7. Endpoint URL found maps to `SECURITY_BLOCKED`.
8. `raw_output_saved=True` maps to `SECURITY_BLOCKED`.
9. `raw_output` field found maps to `SECURITY_BLOCKED`.

## Execution Boundary

P3N execution boundary:

1. P3N performs dry authorization review only.
2. P3N does not open actual call path.
3. P3N does not open provider activation.
4. P3N does not open SDK import.
5. P3N does not open key loading.
6. P3N does not open network transport.
7. P3N does not execute live smoke.
8. In P3N, `live_call_allowed` must be `false`.
9. In P3N, `model_call_count` must be `0`.
10. After P3N, actual first call is possible only in P3O or a later explicit approval phase.

## Stop Conditions

Stop conditions and canonical failure types:

- approval phrase missing -> `HUMAN_DECISION_REQUIRED`
- approval phrase ambiguous -> `HUMAN_DECISION_REQUIRED`
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
- provider allowlist actual activation attempted -> `SECURITY_BLOCKED`
- sdk_import_allowed true -> `SECURITY_BLOCKED`
- key_loading_allowed true -> `SECURITY_BLOCKED`
- live_calls_allowed true -> `SECURITY_BLOCKED`
- SDK import activation attempted -> `SECURITY_BLOCKED`
- key loading activation attempted -> `SECURITY_BLOCKED`
- actual key read attempted -> `SECURITY_BLOCKED`
- env var value read attempted -> `SECURITY_BLOCKED`
- live_call_allowed true -> `SECURITY_BLOCKED`
- model_call_count > 0 -> `SECURITY_BLOCKED`
- raw_output_saved true -> `SECURITY_BLOCKED`
- raw_output field present -> `SECURITY_BLOCKED`
- success-like status present -> `SECURITY_BLOCKED`
- artifact safety scan missing -> `CONFIG_ERROR`
- artifact safety scan failed -> `SECURITY_BLOCKED`
- path traversal attempted -> `SECURITY_BLOCKED`
- artifact write outside run_dir -> `SECURITY_BLOCKED`
- forbidden artifact attempted -> `SECURITY_BLOCKED`

## Rollback and Review Plan

If a future first live smoke fails:

1. Do not retry.
2. Do not use reserve.
3. Do not use fallback provider.
4. Do not widen the allowlist.
5. Do not change key_slot.
6. Do not make a second call.
7. Record the failure cause with canonical `failure_type`.
8. Attempt `ceo_report.md` generation.
9. Run artifact safety scan.
10. Preserve failure artifacts, but do not preserve raw key or raw output.
11. Decide the next step only after a separate review.

## Required Decisions Before P3O

Before P3O, these decisions are required:

1. Whether P3O is the actual first live smoke phase or one more execution-plan review.
2. Where to record the actual approval phrase.
3. Exact provider name.
4. Exact model string.
5. Exact single key_slot.
6. Whether to actually create `approval_package.json`.
7. Whether to implement actual `final_live_gate_result` and approval package linkage.
8. Whether to permit provider allowlist actual activation.
9. Whether to permit SDK import.
10. Whether to permit key loading.
11. When `live_call_allowed` may become `true`.
12. When `model_call_count=1` may be allowed.
13. Whether a live smoke failure review document is mandatory.

## P3O Entry Requirements

P3O entry requires:

1. P3N dry authorization review complete.
2. P3N completion review complete.
3. Actual approval phrase recording method decided.
4. Provider/model/key_slot finalization method decided.
5. Provider allowlist actual activation decision made.
6. SDK import permission decision made.
7. Key loading permission decision made.
8. `live_call_allowed` change decision made.
9. `model_call_count=1` allowance decision made.
10. Approval package artifact creation decision made.
11. Final gate linkage implementation decision made.
12. Rollback/review method finalized.
13. P3O entry YES decision.

P3O entry YES is not actual live smoke approval. Actual execution requires separate explicit approval, passing tests, clean git state, and all gates satisfied.

## Final Rule

P3N does not authorize a live smoke.

P3N only defines the dry authorization review required before a future first live smoke.

P3N keeps `live_call_allowed=false` and `model_call_count=0`.

Any actual live smoke requires P3O or a later explicit approval phase, passing tests, clean git state, and all gates satisfied.
