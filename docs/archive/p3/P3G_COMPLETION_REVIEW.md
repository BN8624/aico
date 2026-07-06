# P3G Completion Review
## Verdict

P3H entry: YES

This YES is only for a P3H live smoke approval package, policy, or preparation step. It is not approval to run a live smoke, use real keys, import provider SDKs, enable network transport, or call a provider.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3F_FIRST_LIVE_SMOKE_POLICY.md`
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
- `aico_v0/provider_base.py`
- `aico_v0/key_registry.py`
- `aico_v0/response_normalizer.py`
- `tests/test_p3g_live_smoke_skeleton.py`
- `tests/test_p3e_live_gate.py`
- `tests/test_p3e_artifact_safety.py`
- `tests/test_p3e_offline_policy.py`
- `tests/test_p3_real_provider_guard.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

P3G stays within the requested first live smoke skeleton scope. The implementation adds approval validation, first-smoke budget and key_slot checks, artifact schema helpers, a disabled runner, and a default-skip `live_smoke` marker policy. It does not add a real provider adapter, real key loading, SDK imports, network imports, live-call flag activation, or an executable live smoke path.

The P3G tests directly cover the required skeleton behavior and keep the broader P3E/P3C/P3B/P3A/V0 suites passing. No blocking issue was found for entering P3H as a documentation, approval-package, or preparation phase.

## Critical Issues

None.

No P3G blocker was found that must be fixed before a P3H policy/preparation step.

## Required Fixes Before P3H

None for P3H policy/preparation entry.

P3H must still not be treated as live smoke approval unless a later explicit approval phase authorizes provider, model, one key_slot, budget, raw-output ban, passing tests, clean git state, and all gates.

## Non-blocking Recommendations

1. Before any actual live smoke artifact write, tighten `build_live_smoke_result` or route all writes through the request validator so `model_call_count > 1`, `retry_count > 0`, or `reserve_used=True` cannot be represented accidentally.
2. In P3H, document where the future explicit approval package will record provider, model, single key_slot, runtime flags, allowlist status, and artifact safety scan result.
3. Keep provider SDK import, real key loading, and network transport deferred until a separate post-P3H approval or implementation phase.
4. Add a later test that a live smoke result file, when actually written, is scanned by `artifact_safety.py` before being accepted.

## P3G Scope Compliance Review

P3G is a skeleton only:

- Actual live smoke: not implemented and not executed.
- Actual API call path: absent.
- Actual LLM call path: absent.
- Actual key value usage: absent.
- Provider SDK import: absent.
- HTTP/network import or call path: absent.
- Live-call flag execution path: not activated.
- Full manager/worker/auditor live run: absent.
- 22-key usage or rotation: absent.
- semantic_preflight: not implemented or executed.
- repair loop: not implemented or executed.

The runtime package still relies on fake, disabled, or validation-only paths for P3G.

## live_smoke.py Skeleton Review

`aico_v0/live_smoke.py` is limited to first live smoke skeleton validation and schema helpers.

- `validate_first_live_smoke_request` composes approval, flag, allowlist, key availability, budget, retry/reserve/second-call, and artifact scan checks.
- `validate_first_live_smoke_approval` handles approval-object checks without calling any provider.
- `run_first_live_smoke_disabled` returns a blocked result with zero API calls, zero LLM calls, zero key reads, zero network calls, no provider SDK import, and `live_smoke_executed=False`.
- No SDK, network, or environment-value import is present.
- Failures are expressed through existing canonical failure types.

The skeleton does not write artifacts or run a provider.

## Approval Schema Review

The first live smoke approval schema contains the required fields:

- `provider`
- `model`
- `key_slot`
- `max_model_calls`
- `max_retries_per_call`
- `max_runtime_seconds`
- `allow_raw_output`
- `approval_scope`
- `approved_by_user`

Behavior review:

- Missing approval maps to `HUMAN_DECISION_REQUIRED`.
- Missing required approval fields map to `HUMAN_DECISION_REQUIRED`.
- `approval_scope` must be `this_run_only`.
- `approved_by_user` must be true.
- Raw secret-like values are blocked through the shared artifact-safety scanner.
- URLs in approval fields are blocked as `SECURITY_BLOCKED`.
- The P3E `LiveApproval` secret guard remains compatible with the P3G approval guard.

No blocker was found.

## Key Slot Validation Review

The first live smoke key_slot policy is enforced:

- Exactly one key_slot is required.
- Multiple key_slots map to `HUMAN_DECISION_REQUIRED`.
- Allowed slots are the existing seven slots: `manager_1`, `worker_1`, `worker_2`, `worker_3`, `worker_4`, `auditor_1`, and `reserve_1`.
- Unknown key_slot values map to `SECURITY_BLOCKED`.
- Raw key-like key_slot values map to `SECURITY_BLOCKED`.
- Env var names used as key_slot values are blocked.
- Key existence is checked through `KeyRegistry.has_key`, which returns a boolean and does not expose raw key values.
- Missing key maps to `CONFIG_ERROR`.

No raw key value read path was found.

## Budget, Retry, and Reserve Review

P3G enforces the first live smoke budget and no-retry policy:

- `max_model_calls = 1` is required.
- `max_model_calls > 1` maps to `CONFIG_ERROR` during approval validation.
- Runtime attempted calls greater than one map to `BUDGET_EXCEEDED`.
- `max_retries_per_call = 0` is required.
- Retry attempts map to `SECURITY_BLOCKED`.
- Reserve attempts map to `SECURITY_BLOCKED`.
- Fallback provider attempts map to a security/allowlist block.
- Second model call attempts map to `SECURITY_BLOCKED`.

This matches the P3F first live smoke policy.

## allow_raw_output Policy Review

`allow_raw_output` is locked down:

- Missing `allow_raw_output` maps to `HUMAN_DECISION_REQUIRED`.
- `allow_raw_output=True` maps to `SECURITY_BLOCKED`.
- `build_live_smoke_result` rejects `raw_output_saved=True`.
- `live_smoke_result` does not include a `raw_output` field.
- `masked_raw_output` is masked before being returned.
- ProviderResult safety rules remain compatible with this policy.

No blocker was found.

## Provider Allowlist Review

Provider allowlist behavior remains safe:

- Missing allowlist maps to `CONFIG_ERROR`.
- Empty allowlist maps to `CONFIG_ERROR`.
- Unknown provider maps to `SECURITY_BLOCKED`.
- Provider outside allowlist maps to `SECURITY_BLOCKED`.
- Unknown endpoint maps to `SECURITY_BLOCKED`.
- Arbitrary URL in approval maps to `SECURITY_BLOCKED`.
- Candidate provider metadata remains non-authorizing.
- The default allowlist remains empty in `provider_allowlist.py`.

P3G does not open the actual provider allowlist.

## Live Smoke Result Schema Review

`build_live_smoke_result` provides the required safe schema fields:

- `status`
- `provider`
- `model`
- `key_slot`
- `model_call_count`
- `max_model_calls`
- `retry_count`
- `max_retries_per_call`
- `reserve_used`
- `raw_output_saved`
- `masked_raw_output`
- `failure_type`
- `error`
- `artifact_safety_status`

It also includes optional token and trace fields:

- `input_tokens`
- `output_tokens`
- `run_id`
- `timestamp`
- `parent_event_id`

Safety review:

- No `raw_output` field is emitted.
- No raw key field is emitted.
- `raw_output_saved` is always false unless the caller attempts true, which raises `ValueError`.
- `key_slot` is the only key reference.
- Error and masked output values are masked.

Non-blocking risk: the helper accepts caller-provided `model_call_count`, `retry_count`, and `reserve_used` values. The request validator blocks those unsafe paths, but future file-writing code should either call the validator first or harden the helper before actual live smoke artifact creation.

## Artifact Safety Report Schema Review

`build_artifact_safety_report` provides the required fields:

- `status`
- `scanned_artifacts`
- `findings`
- `failure_type`
- `summary`

Each finding includes:

- `artifact_path`
- `finding_type`
- `severity`
- `failure_type`
- `message`

Safety review:

- Missing scan maps to `CONFIG_ERROR`.
- Failed scan maps to `SECURITY_BLOCKED` through the scan result.
- Finding messages are masked and do not expose raw secret values.
- Scan pass returns `status=pass`.
- Scan fail returns `status=fail`.
- The schema is compatible with `artifact_safety.py`.

No blocker was found.

## Artifact Policy Review

The allowed live smoke artifact set is limited to:

- `run_log.jsonl`
- `ceo_report.md`
- `live_smoke_result.json`
- `artifact_safety_report.json`

The forbidden full-run artifact set is rejected:

- `final_report.md`
- `failed_draft.md`
- `manager_summary.json`
- `audit_report.json`
- `worker_results.jsonl`

P3G does not create these artifacts. It only validates names and builds schema dictionaries.

## Live Smoke Marker and Offline Policy Review

`live_smoke` marker policy is present and safe:

- `pyproject.toml` registers the `live_smoke` marker.
- `live_test_policy.py` keeps `LIVE_SMOKE_DEFAULT_ENABLED = False`.
- `should_skip_live_smoke_test()` returns true by default.
- Even `explicit_enable=True` still skips because the default enabled flag is false.
- Default `pytest -q` remains offline-only.
- No provider SDK or network import appears in default tests.
- The existing `live_provider` marker policy remains compatible.

No live smoke test is executed.

## Failure Mapping Review

P3G uses existing canonical failure types only.

The required mappings are present and tested:

- Approval missing, ambiguous approval, and missing approval fields -> `HUMAN_DECISION_REQUIRED`.
- Runtime flag missing or false -> `CONFIG_ERROR`.
- Provider allowlist missing or empty -> `CONFIG_ERROR`.
- Key missing -> `CONFIG_ERROR`.
- Budget missing or invalid -> `CONFIG_ERROR`.
- Artifact safety scan missing -> `CONFIG_ERROR`.
- Unknown provider, provider not in allowlist, unknown endpoint, arbitrary URL, raw key, env value, unmasked raw provider output, `raw_output_saved=True`, `allow_raw_output` not false, default-test network call, ungated live call, retry, reserve, and second call -> `SECURITY_BLOCKED`.
- Budget exceeded -> `BUDGET_EXCEEDED`.
- Timeout, 429, 500, provider unavailable, and no response -> `MODEL_ERROR`.
- Non-JSON and schema-invalid JSON -> `SCHEMA_ERROR`.
- Schema-valid empty response -> `WORKER_BAD_OUTPUT`.
- CEO report generation and artifact write failure -> `REPORT_ERROR`.

No new failure type was added.

## Test Coverage Review

| Required item | Coverage |
| --- | --- |
| first live smoke requires explicit approval | Direct, `test_first_live_smoke_approval_human_decision_failures` |
| generic approval phrase is rejected | Direct, `test_first_live_smoke_approval_human_decision_failures` |
| exactly one key_slot is required | Direct, `test_first_live_smoke_requires_exactly_one_key_slot` |
| multiple key_slots rejected | Direct, `test_first_live_smoke_requires_exactly_one_key_slot` |
| unknown key_slot rejected | Direct, `test_first_live_smoke_rejects_unknown_or_raw_key_like_key_slot` |
| raw key-like key_slot rejected | Direct, `test_first_live_smoke_rejects_unknown_or_raw_key_like_key_slot` |
| `max_model_calls = 1` required | Direct, `test_first_live_smoke_budget_and_retry_policy` |
| `max_model_calls > 1` rejected | Direct, `test_first_live_smoke_budget_and_retry_policy` |
| `max_retries_per_call = 0` required | Direct, `test_first_live_smoke_budget_and_retry_policy` |
| retry > 0 rejected | Direct, `test_first_live_smoke_budget_and_retry_policy` |
| reserve usage rejected | Direct, `test_first_live_smoke_rejects_retry_reserve_and_second_model_call_attempts` |
| second model call rejected | Direct, `test_first_live_smoke_rejects_retry_reserve_and_second_model_call_attempts` |
| `allow_raw_output != false` rejected | Direct, `test_first_live_smoke_rejects_allow_raw_output_not_false` |
| provider allowlist non-empty required | Direct, `test_first_live_smoke_provider_allowlist_policy` |
| provider not in allowlist rejected | Direct, `test_first_live_smoke_provider_allowlist_policy` |
| unknown endpoint rejected | Direct, `test_first_live_smoke_rejects_unknown_endpoint_and_arbitrary_url` |
| arbitrary URL rejected | Direct, `test_first_live_smoke_rejects_unknown_endpoint_and_arbitrary_url` |
| pre-call artifact safety scan required | Direct, `test_first_live_smoke_requires_artifact_safety_scan_before_and_after_call` |
| post-call artifact safety scan required | Direct, `test_first_live_smoke_requires_artifact_safety_scan_before_and_after_call` |
| `live_smoke_result` has no raw key field | Direct, `test_live_smoke_result_schema_has_no_raw_key_or_raw_output` |
| `live_smoke_result` has no `raw_output` field | Direct, `test_live_smoke_result_schema_has_no_raw_key_or_raw_output` |
| `live_smoke_result` raw_output_saved is false | Direct, `test_live_smoke_result_schema_has_no_raw_key_or_raw_output` |
| artifact safety report masks findings | Direct, `test_artifact_safety_report_schema_masks_findings_and_maps_failures` |
| scan fail maps to `SECURITY_BLOCKED` | Direct, `test_artifact_safety_report_schema_masks_findings_and_maps_failures` |
| scan missing maps to `CONFIG_ERROR` | Direct, `test_artifact_safety_report_maps_missing_scan_to_config_error` |
| no `final_report.md` | Direct, `test_first_live_smoke_forbidden_full_run_artifacts_are_rejected` |
| no `failed_draft.md` | Direct, `test_first_live_smoke_forbidden_full_run_artifacts_are_rejected` |
| no `manager_summary.json` | Direct, `test_first_live_smoke_forbidden_full_run_artifacts_are_rejected` |
| no `audit_report.json` | Direct, `test_first_live_smoke_forbidden_full_run_artifacts_are_rejected` |
| no `worker_results.jsonl` | Direct, `test_first_live_smoke_forbidden_full_run_artifacts_are_rejected` |
| default pytest does not run live smoke | Direct, `test_live_smoke_marker_is_default_skip_and_non_executing` and full pytest |
| live_smoke marker default-skip/non-executing | Direct, `test_live_smoke_marker_is_default_skip_and_non_executing` |
| disabled runner performs no API call | Direct, `test_disabled_runner_performs_no_api_network_key_or_sdk_work` |
| disabled runner performs no network call | Direct, `test_disabled_runner_performs_no_api_network_key_or_sdk_work` |
| disabled runner performs no key access | Direct, `test_disabled_runner_performs_no_api_network_key_or_sdk_work` |
| disabled runner performs no SDK import | Direct, `test_disabled_runner_performs_no_api_network_key_or_sdk_work` |
| existing P3E tests pass | Verified by full `pytest -q` |
| existing P3C/P3B/P3A/V0 tests pass | Verified by full `pytest -q` |
| AGENTS.md and CLAUDE.md byte-identical | Direct P3G test and separate SHA256 check |

Coverage is sufficient for P3H policy/preparation entry.

## P3H Entry Risk Review

P3H should be a live smoke approval package or policy/preparation step, not an actual live smoke.

Risks to settle before any live smoke execution:

- Whether P3H opens the allowlist or only documents the future approval package.
- Whether `google_gemini` remains the candidate or still stays user-approved later.
- Whether provider SDK import remains deferred beyond P3H.
- Whether actual key loading remains deferred beyond P3H.
- Where the explicit approval package records provider, model, one key_slot, fixed budget, flags, and artifact safety scan status.
- Whether `live_smoke_result.json` and `artifact_safety_report.json` helpers need hardening before actual files are written.
- How a failed live smoke review or rollback document will be named and linked.
- How default `pytest -q` remains offline-only after any future live smoke tests are added.

Recommendation: P3H should document the approval package and execution checklist only. Keep actual live smoke, SDK imports, real key loading, network transport, and allowlist activation deferred unless a later explicit phase authorizes them.

## Final Decision

P3H entry: YES

P3G is complete enough to enter P3H as a live smoke approval package, policy, or preparation phase. This decision does not authorize live smoke execution, API calls, LLM calls, real key usage, provider SDK imports, network transport, or provider activation.
