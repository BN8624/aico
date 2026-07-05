# P3H Completion Review
## Verdict

P3I entry: NO

P3H is correctly scoped as approval-package documentation only, but P3I should remain blocked until `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` fixes its Document Priority. The P3H document currently omits itself from its priority list, which leaves the approval package's authority unclear relative to P3F/P3D review documents.

This NO does not authorize any live smoke, API call, LLM call, real key usage, provider SDK import, network transport, or provider activation.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`
- `P3F_FIRST_LIVE_SMOKE_POLICY.md`
- `P3G_COMPLETION_REVIEW.md`
- `P3F_COMPLETION_REVIEW.md`
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
- `aico_v0/live_smoke.py`
- `aico_v0/live_gate.py`
- `aico_v0/provider_allowlist.py`
- `aico_v0/artifact_safety.py`
- `aico_v0/live_test_policy.py`
- `aico_v0/p3_real_provider.py`
- `aico_v0/key_registry.py`
- `aico_v0/provider_base.py`
- `tests/test_p3g_live_smoke_skeleton.py`
- `tests/test_p3e_live_gate.py`
- `tests/test_p3e_artifact_safety.py`
- `tests/test_p3e_offline_policy.py`
- `tests/test_p3_real_provider_guard.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

`P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` substantially captures the required approval package content. It keeps P3H as documentation-only, explicitly forbids live smoke execution, preserves the exact future approval phrase, keeps provider/model/key_slot candidate-only, maintains `max_model_calls = 1`, retry 0, `allow_raw_output=false`, raw key/raw output bans, artifact safety requirements, stop conditions, rollback rules, and P3I entry requirements.

The blocker is limited but important: the document priority section does not list `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` itself. Because P3H is the phase-specific approval package document, it should appear in its own priority list below `AICO_MASTER_CANON.md` and `AICO_P3_CANON.md`, and its relationship to `P3F_FIRST_LIVE_SMOKE_POLICY.md` should be explicit. Without that, P3I entry remains too ambiguous.

## Critical Issues

1. `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` omits itself from Document Priority.

The current priority list starts with `AICO_MASTER_CANON.md`, `AICO_P3_CANON.md`, then `P3F_FIRST_LIVE_SMOKE_POLICY.md`, but does not include `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`. This can make P3H approval-package-specific rules appear subordinate to prior-phase review documents or leave their precedence undefined.

## Required Fixes Before P3I

1. Add `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` to the P3H Document Priority list.
2. Place it below `AICO_MASTER_CANON.md` and `AICO_P3_CANON.md`.
3. State explicitly how conflicts are resolved between `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` and `P3F_FIRST_LIVE_SMOKE_POLICY.md`.
4. Preserve the rule that P3H is not a live smoke authorization and that actual execution still requires a later explicit approval phase, passing tests, clean git state, and all gates satisfied.

## Non-blocking Recommendations

1. In the next policy fix, keep P3F first-live-smoke safety limits controlling for execution scope while allowing P3H to control the approval package format.
2. Clarify that P3I should be final preflight or approval review package work, not actual live smoke.
3. Keep provider allowlist activation, SDK import, key loading, network transport, and first real call deferred until a separate explicit approval phase.
4. Before any real artifact write path is implemented, address the P3G review's non-blocking risk around hardening `live_smoke_result` values such as model call count, retry count, and reserve usage.

## P3H Scope Compliance Review

P3H scope is otherwise compliant.

- P3H is documented as approval-package documentation only.
- P3H does not authorize live smoke.
- P3H says actual first live smoke requires a later explicit approval phase.
- Actual API calls, LLM calls, key usage, SDK imports, and network calls are forbidden.
- P3H does not require code implementation.
- P3H does not change harness behavior.
- Approval package presence is explicitly not live smoke authorization.

No scope blocker beyond document priority was found.

## Document Priority Review

This section has the blocking issue.

Findings:

- `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md` does not include itself in Document Priority.
- Master Canon and P3 Canon are correctly stated as higher priority.
- The relationship to `P3D_LIVE_CALL_POLICY.md` is partially covered.
- The relationship between P3H approval-package rules and `P3F_FIRST_LIVE_SMOKE_POLICY.md` is not explicit enough because P3H is missing from the list.
- The omission does not directly authorize live smoke, but it makes P3H-specific authority ambiguous.

Required correction: add P3H itself to Document Priority and state that P3H controls approval package format while P3F controls first live smoke safety scope unless a higher Canon says otherwise.

## Approval Package Definition Review

The approval package definition covers the required fields:

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

It also correctly states:

- Approval package presence does not automatically execute live smoke.
- Approval package presence is not live smoke authorization.
- Raw key, env var value, endpoint URL, and arbitrary URL are forbidden.
- Only key_slot is recorded.
- Provider/model candidates do not authorize provider calls.

No blocker in this section.

## Required Approval Phrase Review

The required approval phrase is specific enough for later validation:

- provider.
- model.
- key_slot.
- `max_model_calls = 1`.
- `max_retries_per_call = 0`.
- `max_runtime_seconds`.
- `allow_raw_output = false`.
- this run only scope through the phrase.

The policy correctly maps missing provider/model/key_slot/budget fields to `HUMAN_DECISION_REQUIRED`, and `allow_raw_output` not false to `SECURITY_BLOCKED`. It also states that generic phrases are not approval.

No blocker in this section.

## Candidate Provider, Model, and Key Slot Review

Candidate handling is safe:

- `candidate_provider = google_gemini` is `candidate_only`.
- Candidate provider is not allowlist activation.
- Candidate provider is not actual API call approval.
- `candidate_model = user-approved later`.
- The actual model is not fixed in P3H.
- Model values containing URL/key/token/endpoint are `SECURITY_BLOCKED`.
- `candidate_key_slot = user-approved later`.
- Actual key_slot is not fixed in P3H.
- Exactly one key_slot is required for a future first live smoke.
- Allowed key_slots are the existing seven slots.
- Multiple key_slots are `HUMAN_DECISION_REQUIRED`.
- Unknown or raw key-like key_slot values are `SECURITY_BLOCKED`.
- Env var name used as key_slot is `SECURITY_BLOCKED`.

No blocker in this section.

## Budget and Runtime Flags Review

Budget policy is strict:

- `max_model_calls = 1`.
- `max_retries_per_call = 0`.
- `max_consecutive_model_errors = 1`.
- `max_runtime_seconds = 60`.
- `max_model_calls > 1` is `SECURITY_BLOCKED`.
- retry > 0 is `SECURITY_BLOCKED`.
- reserve, fallback provider, and second model call are forbidden.
- budget missing is `CONFIG_ERROR`, or `HUMAN_DECISION_REQUIRED` if the missing value is an approval phrase field.
- budget invalid is `CONFIG_ERROR`.
- budget exceeded is `BUDGET_EXCEEDED`.

Runtime flags are clear:

- `AICO_ENABLE_REAL_PROVIDER=true`.
- `AICO_ALLOW_LIVE_CALLS=true`.
- `AICO_ALLOW_FIRST_LIVE_SMOKE=true`.
- Missing or false flag is `CONFIG_ERROR`.
- All flags true are insufficient without approval, allowlist, budget, and artifact safety gates.
- P3H forbids implementing or activating flag execution paths.

No blocker in this section.

## Provider Allowlist, SDK, and Key Loading Review

Provider allowlist remains safe:

- Default is `provider_allowlist = empty`.
- Empty allowlist forbids live smoke.
- Missing or empty allowlist is `CONFIG_ERROR`.
- Provider not in allowlist, unknown provider, arbitrary URL, and unknown endpoint are `SECURITY_BLOCKED`.
- P3H does not open the allowlist.
- Opening allowlist from empty to candidate is deferred to P3I or a later explicit approval phase.

SDK policy is safe:

- Provider SDK imports are forbidden in P3H.
- Real SDK import allowance is deferred to P3I or later explicit approval.
- Future SDK imports must be isolated inside provider adapter files.
- Unapproved SDK import is `SECURITY_BLOCKED`.

Key loading policy is safe:

- Actual key loading is forbidden in P3H.
- `.env` file creation and `.env` value usage are forbidden.
- Key existence may be boolean only.
- Missing key is `CONFIG_ERROR`.
- Raw key leak is `SECURITY_BLOCKED`.
- Future key loading must be isolated to the smallest provider adapter boundary.

No blocker in this section.

## Prompt and Expected Output Review

Prompt package is constrained:

- No secret, API key, env value, endpoint URL, arbitrary URL, repo contents, user business data, file edit request, shell or command execution request, or external reference.
- Secret-like values, URLs, and file modification/execution requests are `SECURITY_BLOCKED`.
- Prompt is limited to provider-connection structured output smoke.

Expected output is constrained:

- Minimal JSON only.
- Non-JSON and schema-invalid response are `SCHEMA_ERROR`.
- Schema-valid empty response is `WORKER_BAD_OUTPUT`.
- Raw output storage is forbidden.
- Only `masked_raw_output` is allowed.

No blocker in this section.

## Artifact, Safety, and Logging Review

Artifact package is aligned with P3F/P3G:

- Allowed artifacts: `run_log.jsonl`, `ceo_report.md`, `live_smoke_result.json`, `artifact_safety_report.json`.
- Forbidden artifacts: `final_report.md`, `failed_draft.md`, `manager_summary.json`, `audit_report.json`, `worker_results.jsonl`.
- Full AICO run artifacts are forbidden.
- All artifacts are subject to secret scan.
- key_slot-only recording is required.
- Raw key and raw output recording are forbidden.

Artifact safety package is clear:

- Pre-smoke scan covers prompt, approval, and config.
- Post-smoke scan covers all artifacts.
- Missing scan is `CONFIG_ERROR`.
- Failed scan is `SECURITY_BLOCKED`.
- Raw key-like values, bearer tokens, private key blocks, unmasked raw provider output markers, and `raw_output_saved=True` are `SECURITY_BLOCKED`.
- Scan result is recorded in `artifact_safety_report.json`.

Logging package preserves required fields and adds approval package validation event. Unknown token counts may be null, and provider errors must use canonical failure types.

No blocker in this section.

## Stop, Rollback, and Checklist Review

Stop conditions cover the required categories:

- Approval package and approval phrase problems.
- Required approval field gaps.
- Provider/model/key_slot missing.
- Multiple, unknown, or raw key-like key_slot values.
- Allowlist missing, empty, unknown provider, provider not in allowlist, unknown endpoint, arbitrary URL.
- Runtime flag missing or false.
- Key missing.
- Raw key, env var value, raw output, or unsafe raw output settings.
- Artifact safety missing or failed.
- Budget missing, invalid, or exceeded.
- Retry, reserve, and second model call attempts.
- SDK import before approval.
- Network call in default tests.
- Live smoke in default pytest.
- ProviderResult safety rule break.

Rollback package is safe:

- No retry.
- No reserve.
- No fallback provider.
- No allowlist widening.
- No key_slot change.
- No second call.
- Record canonical failure_type.
- Attempt `ceo_report.md`.
- Run artifact safety scan.
- Preserve failure artifacts without raw key or raw output.
- Separate review before next step.

Pre-live and approval validation checklists are sufficient for P3I preflight/review planning.

No blocker in this section.

## P3I Entry Requirements Review

The P3I entry requirements include all requested items:

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

The document also states that P3I entry YES is not actual live smoke approval and that actual execution requires later explicit approval, passing tests, clean git state, and all gates satisfied.

However, P3I entry should remain NO until the Document Priority blocker is fixed.

## P3I Entry Risk Review

P3I should be final preflight or approval review package work, not the first real call.

Recommended P3I boundaries:

- Keep actual API calls forbidden.
- Keep actual key loading forbidden.
- Keep provider SDK imports forbidden unless a separate explicit approval document authorizes them.
- Do not open provider allowlist from empty to candidate until a dedicated approval/review states the provider, model, endpoint policy, and key_slot.
- Consider implementing artifact file write skeleton only if it remains offline and disabled.
- Connect artifact safety scan to future artifact write paths before any real call.
- Prepare a rollback review document template before live smoke execution.
- Defer the first real call to P3J or a separate explicit approval phase.

## Final Decision

P3I entry: NO

P3H is broadly sound but must fix its Document Priority before P3I can begin. This decision does not authorize live smoke execution, API calls, LLM calls, real key usage, provider SDK imports, network transport, provider activation, or real key loading.
