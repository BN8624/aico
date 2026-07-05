# P3D Completion Review

## Verdict

P3E entry: NO

P3D successfully documents a policy-only live-call gate model and does not authorize live calls. However, P3E should not begin yet because the policy still leaves pre-activation failure typing and concrete provider allowlist decisions unresolved.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3D_LIVE_CALL_POLICY.md`
- `P3C_COMPLETION_REVIEW.md`
- `P3B_COMPLETION_REVIEW.md`
- `P3A_COMPLETION_REVIEW.md`
- `AICO_V0_CANON.md`
- `HANDOFF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_NOTES.md`
- `checklist.md`
- `aico_v0/p3_real_provider.py`
- `aico_v0/provider_base.py`
- `aico_v0/key_registry.py`
- `aico_v0/response_normalizer.py`
- `tests/test_p3_real_provider_guard.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

`P3D_LIVE_CALL_POLICY.md` is consistent with the P3D scope. It states that P3D is policy-only, does not implement provider activation, and keeps actual API calls, LLM calls, key usage, provider SDK imports, network calls, live-call flag implementation, provider adapter implementation, and harness code changes forbidden.

The policy defines live-call scope, default-off rules, eight required gates, key loading boundaries, SDK and network restrictions, token accounting policy, raw output policy, artifact rules, logging rules, test isolation, P3E entry requirements, required tests, stop conditions, and a final rule that P3D does not authorize live calls.

The review found no evidence that P3D changed runtime code or introduced live-call paths. The remaining blockers are policy precision issues that should be resolved before P3E.

## Critical Issues

1. Gate failure outcomes are not mapped to canonical `failure_type` values.

`P3D_LIVE_CALL_POLICY.md` says missing approval, missing flags, missing allowlist, unknown provider, missing budget, and other gate failures forbid live calls. It does not consistently specify whether each condition must be recorded as `CONFIG_ERROR`, `SECURITY_BLOCKED`, `BUDGET_EXCEEDED`, or another existing failure type.

2. Provider allowlist is required but not decided.

The policy requires a provider adapter allowlist and says P3E entry requires provider allowlist decision. No concrete provider names, adapter identifiers, or endpoint constraints are fixed yet.

3. P3E scope remains too broad for direct activation.

The policy correctly states that P3D does not authorize live calls, but P3E entry requirements still mix policy approval, implementation preparation, SDK import decision, artifact safety scan tests, and possible activation. P3E should be split or explicitly defined before any live provider activation preparation starts.

## Required Fixes Before P3E

1. Add a gate failure mapping table before P3E.

At minimum, the policy should map these conditions:

| Condition | Required mapping to decide |
| --- | --- |
| Canon approval missing | `CONFIG_ERROR` or `SECURITY_BLOCKED` |
| explicit user approval missing | `CONFIG_ERROR` or `SECURITY_BLOCKED` |
| live flag missing or false | `CONFIG_ERROR` |
| provider allowlist missing | `CONFIG_ERROR` |
| unknown provider requested | `SECURITY_BLOCKED` or `CONFIG_ERROR` |
| key unavailable | `CONFIG_ERROR` |
| budget missing | `CONFIG_ERROR` |
| budget exceeded | `BUDGET_EXCEEDED` |
| default test attempts network | `SECURITY_BLOCKED` |
| provider SDK import appears before approved phase | `SECURITY_BLOCKED` |

2. Decide the initial provider allowlist before P3E.

The allowlist should include provider adapter identifiers and must prohibit arbitrary provider names, arbitrary endpoints, and arbitrary URLs.

3. Clarify P3E as either policy/skeleton-only or activation-prep.

If P3E is activation-prep, it still must not perform live calls until all gates, tests, explicit user approval, and clean git state are satisfied. If P3E is only policy correction, that should be named directly.

4. Define artifact safety scan requirements as testable rules.

P3D states artifact safety scan is required before `final_report.md` promotion, but P3E needs a concrete test plan or skeleton boundary before any live activation work.

## Non-blocking Recommendations

1. Add a dedicated `P3E_LIVE_ACTIVATION_PREP.md` or equivalent Canon before code work.
2. Keep `pytest -q` permanently offline and add live tests only under an explicit non-default marker.
3. Keep real key access behind a tiny adapter-local boundary with no public raw-key-returning API.
4. Prefer a single-call smoke phase before any manager/worker/auditor live run.
5. Preserve the current fake/stub transport tests as the default provider boundary safety net.

## P3D Scope Compliance Review

P3D scope is compliant.

- P3D is explicitly policy-only.
- P3D does not authorize live calls.
- P3D states provider activation requires a later explicit phase and approval.
- Actual API calls remain forbidden.
- Actual LLM calls remain forbidden.
- Actual key use remains forbidden.
- Provider SDK imports remain forbidden.
- Network calls remain forbidden.
- P3D does not require existing code implementation.
- P3D defines gates required before future live calls.

No runtime or harness code change was found for this P3D work.

## Live-call Definition Review

The live-call definition is clear and complete.

The policy defines each of these as a live call:

- Actual provider API endpoint call.
- Model call through actual SDK.
- Actual API key value use.
- Actual network transport use.
- Actual provider response receipt.
- Actual provider token usage receipt.

The policy states all of the above are forbidden in P3D.

Fake provider, fake transport, stub transport, and disabled transport remain outside live-call scope as long as they do not use network, SDKs, actual key values, actual provider responses, or actual provider token usage.

Live smoke is differentiated from full live run through the budget section. First live call is limited to a single-call smoke with `max_model_calls = 1`, and manager/worker/auditor full live run requires separate approval.

## Absolute Defaults Review

The absolute defaults are present and compatible with P3C.

- live call default = OFF.
- real provider default = disabled.
- default transport = `DisabledTransport`.
- real key loading default = disabled.
- provider SDK import default = forbidden.
- network default = forbidden.
- raw output saving default = forbidden.
- `raw_output_saved = false`.

These defaults match `RealProvider`, `ProviderResult`, `KeyRegistry`, and the P3C guard tests.

## Gate Review

All eight required gates are documented:

1. Canon approval.
2. Explicit user approval.
3. Runtime flag.
4. Key availability check.
5. Provider adapter allowlist.
6. Budget limit.
7. Artifact safety.
8. Test isolation.

The policy states that if any gate fails, live call is forbidden.

The gate model does not conflict with P3C's disabled-by-default structure. `AICO_ENABLE_REAL_PROVIDER=true` alone is still insufficient, and `DisabledTransport` remains the default.

Blocking gap: gate failure outcomes are not mapped to canonical `failure_type` values. This should be fixed before P3E.

## Explicit User Approval Review

The approval policy is mostly clear.

- General phrases such as "continue", "proceed", or "go ahead" are explicitly not approval.
- Approval must include actual API call permission, provider name, key slots, and call limits.
- The recommended approval format is limited to "this run only".
- Missing or incomplete approval forbids live call.

Blocking gap: missing explicit approval is not assigned a specific failure type. P3E should define whether this is `CONFIG_ERROR`, `SECURITY_BLOCKED`, or another Canon-compatible failure type.

## Runtime Flag Review

The runtime flag policy is clear.

Required flags:

```text
AICO_ENABLE_REAL_PROVIDER=true
AICO_ALLOW_LIVE_CALLS=true
```

The policy states:

- Both flags are required before a live call can be considered.
- Missing flag means disabled.
- False flag means disabled.
- Both flags true are still insufficient without Canon approval and explicit user approval.
- P3D documents flags only and does not implement them.

Blocking gap: missing or false live-call flags are not explicitly mapped to a failure type.

## Key Loading Policy Review

The key loading policy is compatible with P3B/P3C safety boundaries.

- Key loading is isolated to `KeyRegistry` or a dedicated key loader.
- A public raw-key-returning API is forbidden.
- Future raw key access may only occur inside the smallest provider adapter boundary.
- Raw key must not enter prompt, log, report, exception, `ProviderResult`, worker output, or artifact.
- Raw key value must not appear in `repr`, `asdict`, loggable dictionaries, failure events, or error strings.
- Env var names may be listed.
- Env var values must not be listed.
- Key existence must be represented as boolean only.

The current `KeyRegistry.raw_key_value` remains disabled in code and tests.

## Provider SDK and Network Policy Review

The SDK and network policy is safe for P3D.

- Provider SDK imports are forbidden in P3D.
- P3E or a later phase must explicitly approve SDK imports.
- If later allowed, SDK imports must be isolated inside provider adapter files.
- Runtime-wide or top-level SDK imports are forbidden.
- Tests must use fake/stub transport without SDK imports.
- Network import and network call are forbidden in P3D.
- P3E or a later phase may allow network only after all live-call gates pass.
- Arbitrary URL calls are forbidden.
- Provider allowlist outside endpoint calls are forbidden.

Blocking gap: the provider allowlist is required but not concretely decided.

## Budget and Token Accounting Review

The budget policy is suitable for a first live smoke.

- `max_model_calls = 1`.
- `max_retries_per_call = 0`.
- `max_consecutive_model_errors = 1`.
- `max_runtime_seconds = 60`.
- Full manager/worker/auditor live run requires separate approval after the first live smoke.
- Unknown token usage may be represented as `null`.
- Token accounting failure is recorded separately from live call success.
- If token accounting failure prevents budget judgment, the run stops as `BUDGET_EXCEEDED` or `MODEL_ERROR`.

Blocking gap: missing budget is a stop condition but does not yet have a fixed failure type.

## Raw Output and Secret Masking Review

The raw output and masking rules are strong.

- Raw provider output is forbidden by default.
- `raw_output` field is forbidden.
- `raw_output_saved=True` is forbidden.
- Only `masked_raw_output` is allowed.
- Malformed response must not be stored unmasked.
- Debug raw dumps are forbidden.
- Secret-like values are recursively masked before persistence.
- Raw key-like values must not survive in `masked_raw_output`.
- If safe masking cannot be guaranteed, the run stops as `SECURITY_BLOCKED`.
- Raw key or unmasked provider response in artifacts becomes `SECURITY_BLOCKED`.

These rules align with `ProviderResult`, `response_normalizer`, and current provider boundary tests.

## Failure Mapping Review

Existing provider and artifact failure mappings are preserved:

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

Blocking gap: live-call gate failures are not fully mapped. In particular, explicit approval missing, live flag missing, provider allowlist missing, unknown provider requested, and budget missing need canonical failure types before P3E.

## Live Artifact and Logging Review

Live artifact and logging rules are mostly complete.

Allowed artifact names are documented:

- `run_log.jsonl`
- `ceo_report.md`
- `worker_results.jsonl`
- `manager_summary.json`
- `audit_report.json`
- `final_report.md`
- `failed_draft.md`

The policy preserves these rules:

- Every artifact is subject to secret scan.
- Raw key discovery becomes `SECURITY_BLOCKED`.
- Unmasked raw output discovery becomes `SECURITY_BLOCKED`.
- `final_report.md` and `failed_draft.md` remain mutually exclusive.
- `failure_type` must be a canonical enum value.
- Only `key_slot` may be recorded.
- Raw key recording is forbidden.
- `run_log.jsonl` keeps timestamp, event_type, actor, model, key_slot, input_tokens, output_tokens, status, failure_type, error, artifact_path, and parent_event_id.
- Unknown tokens may be `null`.
- Retry, fallback, and report errors must be traceable with `parent_event_id`.

Remaining issue: gate failure events need a fixed failure type and logging rule before P3E.

## Test Policy Review

The test policy is safe.

- Default tests are offline only.
- Default tests use fake provider, fake transport, stub transport, or disabled transport only.
- Live-call tests are excluded from the default suite.
- Live-call tests require a separate marker and separate command.
- A live test file must not run under default `pytest -q`.
- CI/default local tests must never use actual API keys, provider SDKs, or network.

Current tests support this baseline:

- `tests/test_p3_real_provider_guard.py` verifies disabled-by-default behavior, fake transport boundary, forbidden imports, key-slot-only behavior, `ProviderResult` safety, and byte-identical agent docs.
- `tests/test_p3_provider_boundary.py` verifies shared provider interface, key registry safety, response normalization, and boundary safety.
- `tests/test_p3_fake_provider.py` verifies P3A fake-provider behavior, masking, reserve/budget rules, and offline constraints.
- `tests/test_v0_harness.py` verifies V0 dry-run behavior remains offline.

## P3E Entry Requirements Review

The P3E entry list is directionally correct but not satisfied yet.

| Requirement | Status |
| --- | --- |
| `P3D_LIVE_CALL_POLICY.md` review complete | Completed by this review |
| live-call gate policy approved | Not yet recorded |
| provider allowlist decided | Missing |
| key loading isolation design complete | Policy-level only |
| live call approval wording finalized | Drafted, but not approved |
| live smoke budget finalized | Drafted |
| live tests default-skip policy finalized | Policy-level only |
| artifact safety scan tests finalized | Missing |
| provider SDK import allowance decided | Missing |
| P3E entry YES decision | NO in this review |

P3E should not be direct live activation. It should first be a policy correction or activation-prep phase that fixes gate failure typing, provider allowlist, key loading isolation design, default-skip test policy, artifact safety scan tests, and SDK import allowance. Actual live calls should remain forbidden until a later explicit approval and passing tests.

Artifact safety scan is not implemented. This is not a blocker for policy correction work, but it is a blocker for any live provider activation.

## Stop Conditions Review

The required stop conditions are present:

- Raw key appears anywhere.
- Unmasked raw provider output appears anywhere.
- Unknown provider requested.
- Provider allowlist missing.
- Live flag missing.
- Explicit approval missing.
- Budget missing.
- Budget exceeded.
- SDK import appears before approved phase.
- Network call appears in default tests.
- `ProviderResult` safety rules are broken.
- `final_report.md` and `failed_draft.md` are both generated.

Most stop conditions are testable in P3E with fake/stub boundaries and static import checks. However, P3E must first define expected failure types for each stop condition so tests can assert canonical behavior instead of only asserting "blocked".

## Final Decision

P3E entry: NO

P3D is complete as a policy-only document, but P3E should not begin until the gate failure type mapping, provider allowlist, P3E scope, and artifact safety scan test requirements are clarified. Actual provider activation, real API calls, real key use, provider SDK imports, and network calls remain forbidden.
