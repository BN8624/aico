# P3D Live-call Gate Policy

## Status

P3D is policy-only.

No live provider activation is implemented in P3D. Actual API calls remain forbidden. Actual key use remains forbidden. Provider SDK imports remain forbidden. Network calls remain forbidden.

P3D does not change harness code, provider adapter code, runtime flags, key loading, SDK imports, network transport, semantic preflight, or repair loop behavior.

## Purpose

P3D defines the gates required before any future AICO live provider call can be considered. It fixes the default-off policy, approval requirements, key isolation boundary, provider allowlist requirement, budget guard, artifact safety rules, test isolation rules, and P3E entry requirements.

## Non-goals

- No actual API call.
- No actual LLM call.
- No actual API key use.
- No `.env` file creation.
- No `.env` value based live call.
- No actual key loading implementation.
- No provider SDK import.
- No HTTP or network import or call.
- No real provider connection.
- No live-call flag implementation.
- No provider adapter implementation.
- No harness code change.
- No semantic_preflight implementation or execution.
- No repair loop implementation or execution.
- No 22-key usage.
- No worker file edit permission.
- No worker shell permission.
- No external URL access, web search, or repo clone.
- No GitHub Issue integration, web dashboard, CLI agent orchestration, automatic PR, or automatic merge.

## Document Priority

For P3D policy work, document priority is:

1. `AICO_MASTER_CANON.md`
2. `AICO_P3_CANON.md`
3. `P3D_LIVE_CALL_POLICY.md`
4. `P3C_COMPLETION_REVIEW.md`
5. `P3B_COMPLETION_REVIEW.md`
6. `P3A_COMPLETION_REVIEW.md`
7. `AICO_V0_CANON.md`
8. `P3_CANON_REVIEW.md`
9. `HANDOFF.md`
10. `AGENTS.md` / `CLAUDE.md`
11. `CONTEXT_NOTES.md`
12. `checklist.md`

If this policy conflicts with `AICO_MASTER_CANON.md` or `AICO_P3_CANON.md`, the higher-priority Canon document wins.

## Current Safety Baseline

- P2 V0 dry-run is complete and offline.
- P3A fake-provider layer is complete and offline.
- P3B provider boundary skeleton is complete and offline.
- P3C guarded real-provider boundary is complete and disabled by default.
- `RealProvider` defaults to disabled.
- Default transport remains `DisabledTransport`.
- `ProviderResult` has no `raw_output` field.
- `raw_output_saved` defaults to `false` and `raw_output_saved=True` is rejected.
- `KeyRegistry.raw_key_value` remains disabled.
- Default tests are offline and fake/disabled-only.

## Live-call Definition

A live call is any one of the following:

- Calling an actual provider API endpoint.
- Making a model call through an actual provider SDK.
- Using an actual API key value.
- Using an actual network transport.
- Receiving an actual provider response.
- Receiving actual token usage from a provider.

All of the above are forbidden in P3D.

## Absolute Defaults

- live call default = OFF.
- real provider default = disabled.
- default transport = `DisabledTransport`.
- real key loading default = disabled.
- provider SDK import default = forbidden.
- network default = forbidden.
- raw output saving default = forbidden.
- `raw_output_saved = false`.

## Required Gates Before Any Live Call

A future live call is allowed only if all gates pass:

1. Canon approval.
2. Explicit user approval.
3. Runtime flag enabled.
4. Key availability check.
5. Provider adapter allowlist.
6. Budget limit.
7. Artifact safety check.
8. Test isolation guarantee.

If any gate fails, live call is forbidden.

## Live-call Gate Failure Type Mapping

Live-call gate failures must use existing canonical failure types only. No new `failure_type` is added by P3D.

Mapping rules:

- Human approval or judgment problem: `HUMAN_DECISION_REQUIRED`.
- Missing or incomplete configuration: `CONFIG_ERROR`.
- Security, permission, allowlist, SDK, network, or secret violation: `SECURITY_BLOCKED`.
- Budget exceedance: `BUDGET_EXCEEDED`.
- Report or mutually exclusive artifact generation failure: `REPORT_ERROR`.

Required mappings:

| Gate failure condition | Canonical failure_type |
| --- | --- |
| explicit approval missing | `HUMAN_DECISION_REQUIRED` |
| approval phrase ambiguous | `HUMAN_DECISION_REQUIRED` |
| provider not specified in approval | `HUMAN_DECISION_REQUIRED` |
| key slots not specified in approval | `HUMAN_DECISION_REQUIRED` |
| max_model_calls not specified in approval | `HUMAN_DECISION_REQUIRED` |
| max_runtime_seconds not specified in approval | `HUMAN_DECISION_REQUIRED` |
| required approval field missing | `HUMAN_DECISION_REQUIRED` |
| `AICO_ENABLE_REAL_PROVIDER` missing | `CONFIG_ERROR` |
| `AICO_ALLOW_LIVE_CALLS` missing | `CONFIG_ERROR` |
| `AICO_ENABLE_REAL_PROVIDER=false` | `CONFIG_ERROR` |
| `AICO_ALLOW_LIVE_CALLS=false` | `CONFIG_ERROR` |
| live flag missing | `CONFIG_ERROR` |
| live flag false | `CONFIG_ERROR` |
| provider allowlist missing | `CONFIG_ERROR` |
| provider allowlist empty | `CONFIG_ERROR` |
| unknown provider requested | `SECURITY_BLOCKED` |
| provider not in allowlist | `SECURITY_BLOCKED` |
| unknown endpoint requested | `SECURITY_BLOCKED` |
| arbitrary URL requested | `SECURITY_BLOCKED` |
| key availability check failed | `CONFIG_ERROR` |
| key slot missing | `CONFIG_ERROR` |
| raw key leaked | `SECURITY_BLOCKED` |
| env var value logged | `SECURITY_BLOCKED` |
| env var value appears anywhere | `SECURITY_BLOCKED` |
| budget missing | `CONFIG_ERROR` |
| budget invalid | `CONFIG_ERROR` |
| budget exceeded | `BUDGET_EXCEEDED` |
| artifact safety scan missing | `CONFIG_ERROR` |
| artifact safety scan internal failure | `CONFIG_ERROR` |
| artifact safety scan failed | `SECURITY_BLOCKED` |
| raw key found in artifact | `SECURITY_BLOCKED` |
| unmasked raw provider output found in artifact | `SECURITY_BLOCKED` |
| `raw_output_saved=True` detected | `SECURITY_BLOCKED` |
| provider SDK import before approved phase | `SECURITY_BLOCKED` |
| network call in default tests | `SECURITY_BLOCKED` |
| live call attempted in default pytest | `SECURITY_BLOCKED` |
| `ProviderResult` safety rule broken | `SECURITY_BLOCKED` |
| `final_report.md` and `failed_draft.md` both generated | `REPORT_ERROR` |
| `ceo_report.md` generation failed | `REPORT_ERROR` |

Gate failure events must be recorded in `run_log.jsonl` when a run directory exists. If failure occurs before a run directory exists, the failure must be represented in the nearest available pre-run error result without raw secrets.

## Gate 1: Canon Approval

- A Phase Canon or policy document that explicitly allows live calls must exist.
- `P3D_LIVE_CALL_POLICY.md` alone does not authorize actual live calls.
- Actual activation is only possible in P3E or a later explicit approval document.
- If Canon approval is absent or ambiguous, live call is forbidden.

## Gate 2: Explicit User Approval

- Live call is forbidden without explicit user approval.
- General phrases such as "continue", "proceed", or "go ahead" are not live-call approval.
- Approval text must include actual API call permission, provider name, key slots, and call limits.

Recommended approval format:

```text
I approve AICO live provider calls for this run only:
provider = <provider_name>
key_slots = <allowed_slots>
max_model_calls = <number>
max_runtime_seconds = <number>
```

If approval does not specify provider, key slots, and limits, live call is forbidden.

## Gate 3: Runtime Flag

Recommended flags:

```text
AICO_ENABLE_REAL_PROVIDER=true
AICO_ALLOW_LIVE_CALLS=true
```

Rules:

- Both flags must be true before a live call can even be considered.
- If either flag is missing, live call is disabled.
- If either flag is false, live call is disabled.
- If both flags are true but Canon approval or explicit user approval is missing, live call is still forbidden.
- P3D documents these flags only and does not implement new flag behavior.

## Gate 4: Key Availability Check

- Only `key_slot` may be exposed outside the key boundary.
- Env var names may be recorded.
- Env var values must never be recorded.
- Key existence must be represented as boolean only.
- Missing key must be handled without raw value exposure, as `CONFIG_ERROR` or `SECURITY_BLOCKED` according to the failure stage.
- Raw key value access may only occur inside the smallest future provider adapter boundary after later approval.
- Raw key value must never enter prompt, log, report, exception, `ProviderResult`, worker output, or artifact.

## Gate 5: Provider Adapter Allowlist

- Only explicitly allowed provider adapters may perform live calls.
- Arbitrary provider names are forbidden.
- Arbitrary endpoints are forbidden.
- Arbitrary URLs are forbidden.
- Provider allowlist must be fixed in both documentation and code before activation.
- P3D documents the allowlist requirement only and does not implement an allowlist.
- P3D policy fix default allowlist is empty.
- Empty allowlist means no live provider can be called.
- Missing or empty allowlist is `CONFIG_ERROR`.
- Unknown provider is `SECURITY_BLOCKED`.
- Provider not in allowlist is `SECURITY_BLOCKED`.
- Actual allowlist activation is only possible in P3E or a later explicit approval document.

P3E first live smoke candidate metadata is non-authorizing:

```text
candidate_provider = google_gemini
candidate_model = user-approved later
candidate_key_slots = user-approved later
```

The candidate above is not an allowlist entry. It does not permit SDK import, key loading, network access, or live calls.

## Gate 6: Budget Limit

Minimum live budget gate fields:

- `max_model_calls`
- `max_input_tokens`
- `max_output_tokens`
- `max_runtime_seconds`
- `max_retries_per_call`
- `max_consecutive_model_errors`

Recommended first live-call defaults:

```text
max_model_calls = 1
max_retries_per_call = 0
max_consecutive_model_errors = 1
max_runtime_seconds = 60
```

Rules:

- The first live call must be limited to a single-call smoke test.
- A manager/worker/auditor full live run requires separate approval after the first live smoke.
- Retries are disabled for the first live smoke.
- Budget exceedance becomes `BUDGET_EXCEEDED`.
- If budget is missing, live call is forbidden.

## Gate 7: Artifact Safety

- Raw output saving is forbidden.
- `raw_output_saved = false` must be preserved.
- Only `masked_raw_output` may be stored.
- Secret-like values must be recursively masked.
- If a raw key or unmasked provider response enters any artifact, the run becomes `SECURITY_BLOCKED`.
- Artifact safety scan is required before any `final_report.md` promotion.
- Debug raw dumps are forbidden.

## Artifact Safety Scan Test Requirements

Artifact safety scan is a P3E pre-activation implementation requirement. If the scan is missing, no later live smoke is allowed.

Required tests before any live provider activation:

- artifact safety scan detects raw key-like value.
- artifact safety scan detects env var value pattern.
- artifact safety scan detects bearer token pattern.
- artifact safety scan detects private key block.
- artifact safety scan detects unmasked raw provider output marker.
- artifact safety scan detects `raw_output_saved=True`.
- artifact safety scan passes `masked_raw_output`.
- artifact safety scan allows `key_slot`.
- artifact safety scan allows env var name.
- artifact safety scan rejects `final_report.md` when raw secret is found.
- artifact safety scan rejects `failed_draft.md` when raw secret is found.
- artifact safety scan runs before `final_report.md` promotion.
- artifact safety scan result is recorded in `run_log.jsonl`.

Rules:

- Missing artifact safety scan is `CONFIG_ERROR`.
- Artifact safety scan internal failure is `CONFIG_ERROR`.
- Artifact safety scan detection failure is `SECURITY_BLOCKED`.
- Scan failure blocks `final_report.md` promotion.

## Gate 8: Test Isolation

- Normal `pytest -q` must never run live calls.
- Live-call tests must be excluded from the default test suite.
- Live-call tests, if added later, require a separate marker or command.
- CI and default local tests must remain offline, fake, or disabled-only.

Recommended default:

```text
pytest -q
```

The command above must always be offline/fake/disabled-only.

## Key Loading Policy

- Key loading must be isolated to `KeyRegistry` or a dedicated key loader.
- The key loader must not provide a public API that returns raw key values.
- Future raw key access may only occur inside the smallest provider adapter boundary.
- Raw key must never enter prompt, log, report, exception, `ProviderResult`, worker output, or artifact.
- Raw key value must not appear in `repr`, `asdict`, loggable dictionaries, failure events, or error strings.
- Env var names may be listed.
- Env var values must not be listed.

## Provider SDK Import Policy

- Provider SDK import is forbidden in P3D.
- P3E or a later phase must explicitly approve any provider SDK import.
- If later allowed, SDK imports must be isolated inside provider adapter files.
- Runtime-wide or top-level SDK imports are forbidden.
- Tests must use fake/stub transport without SDK imports.

## Network Policy

- Network import and network call are forbidden in P3D.
- P3E or a later phase may allow network only after all live-call gates pass.
- Arbitrary URL calls are forbidden.
- Provider allowlist outside endpoint calls are forbidden.
- Default tests must fail or block if they attempt network calls.

## Token Accounting Policy

- `ProviderResult` must keep `input_tokens` and `output_tokens` fields.
- Unknown token usage may be represented as `null`.
- If a future live provider returns token usage, it must be recorded in `run_log.jsonl`.
- Token accounting failure must be recorded separately from live call success.
- If token accounting failure prevents budget judgment, the run must stop as `BUDGET_EXCEEDED` or `MODEL_ERROR`.

## Raw Output Policy

- Raw provider output is forbidden by default.
- `raw_output` field is forbidden.
- `raw_output_saved=True` is forbidden.
- Only `masked_raw_output` is allowed.
- Malformed response must not be stored unmasked.
- Debug raw dumps are forbidden.
- Any unmasked raw provider output in an artifact becomes `SECURITY_BLOCKED`.

## Secret Masking Policy

- Secret scan remains mandatory for logs, reports, worker results, run summaries, and any live response-derived field.
- Secret-like values must be recursively masked before persistence.
- Raw key-like values must not survive in `masked_raw_output`.
- If safe masking cannot be guaranteed, the run must stop as `SECURITY_BLOCKED`.
- Secret masking must apply before final report promotion.

## Failure Mapping

Existing P3 failure mapping remains:

| Condition | Failure type |
| --- | --- |
| timeout | `MODEL_ERROR` |
| 429 | `MODEL_ERROR` |
| 500 | `MODEL_ERROR` |
| provider unavailable | `MODEL_ERROR` |
| no response | `MODEL_ERROR` |
| non-json response | `SCHEMA_ERROR` |
| schema-invalid json | `SCHEMA_ERROR` |
| schema-valid but empty | `WORKER_BAD_OUTPUT` |
| security leak | `SECURITY_BLOCKED` |
| budget exceeded | `BUDGET_EXCEEDED` |
| report failure | `REPORT_ERROR` |

Provider-specific errors must be normalized into these canonical failure types before run-level handling.

## Live Run Artifact Rules

Allowed live-run artifact names:

- `run_log.jsonl`
- `ceo_report.md`
- `worker_results.jsonl`
- `manager_summary.json`
- `audit_report.json`
- `final_report.md`
- `failed_draft.md`

Rules:

- Every artifact is subject to secret scan.
- Raw key discovery becomes `SECURITY_BLOCKED`.
- Unmasked raw output discovery becomes `SECURITY_BLOCKED`.
- `final_report.md` and `failed_draft.md` remain mutually exclusive.
- `failure_type` must be recorded as a canonical enum value.
- Only `key_slot` may be recorded.
- Raw key recording is forbidden.
- `failed_draft.md` is not canon.

## Live Run Logging Rules

`run_log.jsonl` must preserve these fields:

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

- Only `key_slot` may be recorded.
- Raw key is forbidden.
- Unknown token usage may be `null`.
- Provider errors must be recorded as canonical `failure_type`.
- Retry, fallback, and report errors must be traceable with `parent_event_id`.
- Non-failure events must use `failure_type = null`.

## Test Policy

- Default tests are offline only.
- Default tests use fake provider, fake transport, stub transport, or disabled transport only.
- Live-call tests are excluded from the default suite.
- Live-call tests require a separate marker and separate command.
- A live test file must not run under default `pytest -q`.
- CI/default local test must never use actual API keys, provider SDKs, or network.

## P3E Scope

P3E is not full live provider activation.

P3E is live-call activation preparation only.

P3E may include:

- live-call gate implementation preparation.
- approval object/schema definition.
- provider allowlist structure implementation.
- artifact safety scan implementation.
- default `pytest -q` offline-only guarantee.
- live test marker default-skip structure design.
- key loading isolation skeleton hardening.
- provider SDK import allowance final decision documentation.

P3E must exclude:

- actual API calls.
- actual LLM calls.
- actual key use.
- actual provider SDK imports.
- actual network calls.
- full manager/worker/auditor live run.
- 22-key rotation.

P3E does not authorize a live smoke. First live smoke is deferred to P3F or a later explicitly approved phase.

## P3E Entry Requirements

P3E entry requires:

1. P3D completion review complete.
2. Live-call gate `failure_type` mapping complete.
3. Provider allowlist default policy decided.
4. P3E scope limited to activation preparation.
5. Artifact safety scan test requirements defined.
6. Default `pytest -q` remains offline-only.
7. Provider SDK import remains forbidden.
8. Actual API, key, and network use remain forbidden.
9. P3E entry decision recorded as YES.

If any item is missing, P3E work must not begin.

P3E may prepare activation gates only. P3E must not perform live provider activation.

## Required Tests Before Live Provider Activation

Before P3E or any actual activation, tests must cover:

- live calls are disabled by default.
- `AICO_ENABLE_REAL_PROVIDER` alone is insufficient.
- `AICO_ALLOW_LIVE_CALLS` alone is insufficient.
- both flags without explicit approval are insufficient.
- default `pytest -q` never performs live call.
- live test marker is excluded by default.
- key_slot is logged, raw key is not.
- env var value is never logged.
- provider SDK import is isolated.
- network calls are blocked unless live gates pass.
- provider allowlist rejects unknown provider.
- raw provider output is not saved.
- `raw_output_saved=True` remains rejected.
- artifact safety scan catches raw key-like value.
- artifact safety scan detects env var value pattern.
- artifact safety scan detects bearer token pattern.
- artifact safety scan detects private key block.
- artifact safety scan catches unmasked raw output.
- artifact safety scan detects `raw_output_saved=True`.
- artifact safety scan passes `masked_raw_output`.
- artifact safety scan allows `key_slot`.
- artifact safety scan allows env var name.
- artifact safety scan rejects `final_report.md` when raw secret is found.
- artifact safety scan rejects `failed_draft.md` when raw secret is found.
- artifact safety scan runs before `final_report.md` promotion.
- artifact safety scan result is recorded in `run_log.jsonl`.
- first live smoke `max_model_calls = 1`.
- budget exceeded becomes `BUDGET_EXCEEDED`.
- timeout/429/500 become `MODEL_ERROR`.
- malformed response becomes `SCHEMA_ERROR`.
- schema-valid empty response becomes `WORKER_BAD_OUTPUT`.

## Stop Conditions

Stop immediately if any condition occurs:

- Explicit approval missing.
- Approval phrase ambiguous.
- Required approval field missing.
- Provider allowlist missing.
- Provider allowlist empty.
- Provider not in allowlist.
- Unknown provider requested.
- Arbitrary URL requested.
- Live flag missing.
- Live flag false.
- Key availability check failed.
- Key slot missing.
- Raw key appears anywhere.
- Env var value appears anywhere.
- Unmasked raw provider output appears anywhere.
- Artifact safety scan missing.
- Artifact safety scan failed.
- Budget missing.
- Budget invalid.
- Budget exceeded.
- SDK import appears before approved phase.
- Network call appears in default tests.
- Live call appears in default pytest.
- `ProviderResult` safety rules are broken.
- `final_report.md` and `failed_draft.md` are both generated.

Each stop condition must map to the canonical `failure_type` table in this policy. If a stop condition is not mapped, implementation must stop as `CONFIG_ERROR` until the policy is corrected.

## Final Rule

P3D does not authorize live calls.

P3D only defines the gates required before future live calls.

Any actual provider activation requires a later explicit phase, explicit user approval, passing tests, and clean git state.

P3E is activation preparation only. Actual live smoke is deferred to P3F or a later explicitly approved phase.
