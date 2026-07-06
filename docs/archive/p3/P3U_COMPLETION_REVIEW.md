# P3U Completion Review

## Verdict

P3V entry: YES

This YES is limited to P3V final live-fire checklist / still-no-call review. It is not approval to run live smoke, activate a provider, import provider SDKs, load or read real keys, read env var values, open network transport, execute `call_model`, set `fired=true`, set `execution_allowed=true`, set `live_call_allowed=true`, record `model_call_count=1`, or record `call_model_count=1`.

Default recommendation: P3V should remain still-no-call. P3V should lock the last live-fire checklist, last-stop guard, one-shot fire plan, rollback/non-retry policy, and expected observable artifacts without opening SDK, key, API, network, `call_model`, or live smoke paths.

## Reviewed Documents and Files

- `aico_v0/explicit_approval_gate.py`
- `aico_v0/final_live_approval_packet.py`
- `aico_v0/pre_live_package.py`
- `aico_v0/live_execution_boundary.py`
- `aico_v0/no_call_integration.py`
- `aico_v0/approval_package.py`
- `aico_v0/approval_phrase.py`
- `aico_v0/activation_guards.py`
- `aico_v0/artifact_safety.py`
- `aico_v0/final_live_gate.py`
- `aico_v0/live_gate.py`
- `aico_v0/live_smoke.py`
- `aico_v0/live_smoke_artifacts.py`
- `aico_v0/provider_allowlist.py`
- `aico_v0/sdk_boundary.py`
- `aico_v0/key_loading_boundary.py`
- `aico_v0/key_registry.py`
- `aico_v0/p3_real_provider.py`
- `aico_v0/provider_base.py`
- `tests/test_p3u_explicit_approval_gate.py`
- `tests/test_p3u_armed_state.py`
- `tests/test_p3u_no_call_gate_safety.py`
- `tests/test_p3t_final_live_approval_packet.py`
- `tests/test_p3t_human_confirmation.py`
- `tests/test_p3t_no_call_packet_safety.py`
- `tests/test_p3s_pre_live_package.py`
- `tests/test_p3s_artifact_assembly.py`
- `tests/test_p3s_package_no_call_safety.py`
- `tests/test_p3r_live_execution_boundary.py`
- `tests/test_p3r_call_attempt_state.py`
- `tests/test_p3r_no_execute_dry_run.py`
- `tests/test_p3q_no_call_integration.py`
- `tests/test_p3q_activation_wiring.py`
- `tests/test_p3q_linkage_integration.py`
- `tests/test_p3p_approval_package.py`
- `tests/test_p3p_activation_guards.py`
- `tests/test_p3p_no_call_safety.py`
- `tests/test_p3m_final_live_gate.py`
- `tests/test_p3l_sdk_key_boundary.py`
- `tests/test_p3k_provider_allowlist_skeleton.py`
- `tests/test_p3j_live_smoke_artifacts.py`
- `tests/test_p3g_live_smoke_skeleton.py`
- `tests/test_p3e_live_gate.py`
- `tests/test_p3e_artifact_safety.py`
- `tests/test_p3e_offline_policy.py`
- `tests/test_v0_harness.py`
- `P3T_COMPLETION_REVIEW.md`
- `P3S_COMPLETION_REVIEW.md`
- `P3R_COMPLETION_REVIEW.md`
- `P3Q_COMPLETION_REVIEW.md`
- `P3P_COMPLETION_REVIEW.md`
- `P3O_EXECUTION_PLAN_REVIEW.md`
- `P3O_COMPLETION_REVIEW.md`
- `P3N_DRY_AUTHORIZATION_REVIEW.md`
- `P3N_COMPLETION_REVIEW.md`
- `P3M_COMPLETION_REVIEW.md`
- `P3L_COMPLETION_REVIEW.md`
- `P3K_COMPLETION_REVIEW.md`
- `P3J_COMPLETION_REVIEW.md`
- `P3I_FINAL_PREFLIGHT_APPROVAL_REVIEW.md`
- `P3H_LIVE_SMOKE_APPROVAL_PACKAGE.md`
- `P3F_FIRST_LIVE_SMOKE_POLICY.md`
- `P3D_LIVE_CALL_POLICY.md`
- `AICO_P3_CANON.md`
- `AICO_MASTER_CANON.md`
- `HANDOFF.md`
- `CONTEXT_NOTES.md`
- `checklist.md`
- `pyproject.toml`

## Summary

P3U implements the requested final explicit approval gate / armed-but-not-fired no-call phase. The implementation adds an explicit human approval gate schema, armed-but-not-fired state model, one-shot budget lock, single-call / no-retry / no-reserve / no-fallback / no-second-call policy locks, final approval packet to execution boundary linkage checks, approval phrase hash/ref validation, gate-level no-call invariant validation, armed state artifact reference validation, artifact safety pre/post scan wiring, and explicit write helpers for safe test/run directory use.

The implementation remains closed. It does not auto-create approval or gate artifacts on the default/runtime path. It does not execute live smoke, does not call `call_model`, does not activate providers, does not import provider SDKs, does not read key values or env var values, does not open network transport, and does not record model or call-model counts above zero.

No blocking issue was found for entering P3V as final live-fire checklist / still-no-call review only.

## Critical Issues

None.

## Required Fixes Before P3V

None for P3V as a final live-fire checklist / still-no-call review phase.

## Non-blocking Recommendations

- Keep P3V still-no-call. Do not make P3V the first real live smoke.
- In P3V, allow only checklist, last-stop guard, one-shot fire plan, rollback/non-retry policy, and observable artifact planning.
- Keep actual first call deferred to P3W or a later explicit approval phase unless a later phase separately authorizes a tightly scoped one-call execution.
- Do not permit `fired=true`, `execution_allowed=true`, `live_call_allowed=true`, `model_call_count=1`, `call_model_count=1`, provider allowlist actual activation, SDK import, key loading, network transport, or executable live command skeletons in P3V.

## P3U Scope Compliance Review

P3U stayed within final explicit approval gate / armed-but-not-fired no-call scope. `aico_v0/explicit_approval_gate.py` provides local data validation, safe summaries, linkage checks, and explicit test-only write helpers. The default/runtime creation helpers return false for `explicit_approval_gate.json` and `armed_state.json`.

No actual live smoke, API call, LLM call, key value read, env var value read, provider SDK import, HTTP/network import, provider endpoint connection, provider response receipt, token usage receipt, provider allowlist activation, SDK activation, key loading activation, provider transport call, `call_model` execution, retry, reserve, fallback, second call, fired state, or execution permission path was opened.

The implementation keeps `armed=true` allowable only as `armed_not_fired`; `fired=false`, `execution_allowed=false`, `live_call_allowed=false`, `model_call_count=0`, `call_model_count=0`, and `raw_output_saved=false` remain mandatory.

## Explicit Human Approval Gate Skeleton Review

The explicit approval gate skeleton is implemented by `build_explicit_approval_gate`, `validate_explicit_approval_gate`, `write_explicit_approval_gate`, and related validators. It accepts the required input summaries: final live approval packet, human confirmation checklist, pre-live package manifest, live execution boundary, no-call integration summary, call attempt summary, final live gate result, runtime flags summary, test evidence summary, rollback plan summary, human decision summary, and artifact safety summary.

The gate output includes the requested safe fields: schema version, run id, status, human review readiness, armed state, armed/fired flags, execution/live no-call flags, model and call-model counters, human and explicit approval status fields, approval hash/ref, linked artifact refs, budget and policy locks, provider/model/key_slot, failure fields, `raw_output_saved`, and `created_for`.

P3U allows `armed=true` but requires `fired=false`. It rejects `execution_allowed=true`, `live_call_allowed=true`, `model_call_count>0`, `call_model_count>0`, `raw_output_saved=true`, raw output, provider response, token usage, endpoint URL, raw key/env values, and raw approval phrase fields. `explicit_approval_status` and `human_confirmation_status` are restricted to `pending`, `review_required`, and `not_granted`; approval-like statuses are blocked.

## Armed-but-not-fired State Model Review

The state model is implemented by `build_armed_but_not_fired_state`, `validate_armed_but_not_fired_state`, `validate_armed_state_machine`, and `validate_armed_state`.

Allowed states are limited to `not_armed`, `pre_armed_review`, `armed_not_fired`, `armed_blocked`, `disarmed`, and `review_required`. Forbidden states include `firing`, `fired`, `executing`, `executed`, `called`, `provider_called`, `network_called`, `sdk_imported`, `key_loaded`, `live_success`, `api_success`, `provider_success`, `completed_live_call`, `retrying`, `fallback_started`, `reserve_used`, `second_call_started`, and `armed_and_fired`.

The allowed `pre_armed_review -> armed_not_fired` path is review-only and does not grant execution permission. Unknown states map to `CONFIG_ERROR`; forbidden execution/live states map to `SECURITY_BLOCKED`.

## One-shot Budget Lock Review

The one-shot budget lock is implemented by `build_one_shot_budget_lock` and `validate_one_shot_budget_lock`.

The safe defaults are fixed: `max_model_calls=1`, `model_call_count=0`, `budget_locked=true`, `budget_spent=false`, `retry_allowed=false`, `reserve_allowed=false`, `fallback_allowed=false`, `second_call_allowed=false`, `budget_reset_allowed=false`, and `budget_widening_allowed=false`.

`max_model_calls=1` is future first-call budget documentation only. It does not grant execution permission. `budget_spent=true` or any widening flag maps to `SECURITY_BLOCKED`.

## Policy Locks Review

The policy locks are implemented by `build_single_call_policy_lock` and `validate_policy_lock`. The same safe lock is used for `single_call_policy_lock`, `no_retry_policy_lock`, `no_reserve_policy_lock`, `no_fallback_policy_lock`, and `no_second_call_policy_lock`.

The required policy is enforced: `single_call_only=true`, `retry_allowed=false`, `reserve_allowed=false`, `fallback_allowed=false`, `second_call_allowed=false`, `provider_rotation_allowed=false`, `key_rotation_allowed=false`, and `policy_widening_allowed=false`.

Policy lock pass is not live call permission. Retry, reserve, fallback, second call, provider rotation, key rotation, or policy widening maps to `SECURITY_BLOCKED`.

## Final Approval Packet ↔ Execution Boundary Linkage Review

Linkage is implemented by `validate_final_approval_linkage` and by the build path inside `build_explicit_approval_gate`.

The validator checks consistent `run_id` across final live approval packet, human confirmation checklist, pre-live package manifest, live execution boundary, no-call integration summary, call attempt summary, and final live gate result. It also checks consistent `approval_phrase_hash` across linked artifacts.

Missing `run_id`, missing `approval_phrase_hash`, run id mismatch, and approval hash mismatch map to `CONFIG_ERROR`. Missing artifact references map to `CONFIG_ERROR`; unsafe references such as URLs, absolute paths outside the run directory, or traversal attempts map to `SECURITY_BLOCKED`. Linkage pass remains no-call and does not grant execution.

## Explicit Approval Phrase Hash/Ref Policy Review

P3U stores only `approval_phrase_hash` and a safe `approval_phrase_ref`. It does not store raw approval phrase text. The same hash validation used by earlier P3 phases is applied, and `validate_approval_phrase_ref` rejects absolute paths, traversal, and URLs.

Raw approval phrase fields are explicitly forbidden in gate payloads and artifact scans. Hash/ref validation is a linkage check only and does not grant live call permission.

## Gate-level No-call Invariant Validator Review

The gate-level no-call invariant validator is implemented by `validate_gate_no_call_invariants`.

It blocks `fired=true`, `executed=true`, `called=true`, provider/network called markers, `execution_allowed=true`, `live_call_allowed=true`, `raw_output_saved=true`, provider activation, SDK import activation or import markers, key loading markers, network call markers, live smoke markers, `call_model_executed=true`, retry/reserve/fallback/second-call flags, and `budget_spent=true`.

It also blocks nonzero `model_call_count`, `model_call_count_before_execution`, `call_model_count`, actual API/LLM/key/env/SDK/network/live smoke counters, raw output fields, provider response, token usage, raw approval phrase, and unsafe secret-like values. The validator is local data inspection only; it imports no SDK, reads no env/key values, opens no network, and executes no `call_model`.

## Armed State Artifact Reference Validator Review

Artifact reference validation is implemented by `validate_armed_state_artifact_ref`, delegated through the P3T safe artifact reference rules.

The required references are safe relative refs: `final_live_approval_packet_ref`, `human_confirmation_checklist_ref`, `pre_live_package_manifest_ref`, `live_execution_boundary_ref`, `no_call_integration_summary_ref`, `call_attempt_summary_ref`, `final_gate_result_ref`, and `approval_phrase_ref`.

Missing references map to `CONFIG_ERROR`. Absolute paths, path traversal, and URL refs map to `SECURITY_BLOCKED`. Reference validation is not execution permission.

## Artifact Safety Pre/Post Scan Wiring Review

Artifact safety wiring is present in build, validation, and write paths. `build_explicit_approval_gate` requires a pre-scan style artifact safety summary. `validate_explicit_approval_gate` and `validate_armed_but_not_fired_state` scan the complete summary payload. `write_explicit_approval_gate` and `write_armed_state` require both pre-scan and post-scan summaries before writing.

Pre-scan missing maps to `CONFIG_ERROR`; post-scan missing maps to `CONFIG_ERROR`; scan failure maps to `SECURITY_BLOCKED`. Raw key-like values, bearer/private-key-like secrets, env var values, endpoint URLs, raw output fields, provider response fields, token usage fields, raw approval phrase fields, `raw_output_saved=true`, `execution_allowed=true`, `live_call_allowed=true`, positive model/call-model counters, `fired=true`, success-like statuses, and approval-like statuses are blocked.

## Explicit Approval Gate Write Helper Review

`write_explicit_approval_gate` and `write_armed_state` are explicit helpers only. The default/runtime creation helpers return false, so neither `explicit_approval_gate.json` nor `armed_state.json` is auto-created on the normal runtime path.

The write helpers constrain output to the run directory and exact expected artifact name. Path traversal, URL paths, and outside absolute paths are blocked. Write failure maps to `REPORT_ERROR`. The helpers require pre/post scans, validate payload safety before writing, and do not execute live smoke.

## Failure Priority Review

P3U keeps the existing canonical failure priority through `aggregate_gate_failure_type`, using the priority inherited from the pre-live package path:

1. `SECURITY_BLOCKED`
2. `BUDGET_EXCEEDED`
3. `REPORT_ERROR`
4. `CONFIG_ERROR`
5. `HUMAN_DECISION_REQUIRED`
6. `MODEL_ERROR`
7. `SCHEMA_ERROR`
8. `WORKER_BAD_OUTPUT`

Security violations dominate. Artifact write failures map to `REPORT_ERROR`. Missing config/schema/linkage/gate items map to `CONFIG_ERROR`. Pending/review-required/not-granted approval states remain non-executing human decision states; approval-like, success-like, and fired states are `SECURITY_BLOCKED`. No new failure type was introduced.

## Test Coverage Review

P3U targeted coverage is direct and regression coverage is retained.

- Items 1-8 are covered by `test_explicit_approval_gate_validates_safe_inputs`, `test_gate_allows_armed_true_only_when_fired_false`, and `test_gate_keeps_all_no_call_fields_closed`.
- Items 9-13 are covered by `test_gate_allows_only_non_granted_explicit_approval_status`, `test_gate_rejects_approval_like_statuses`, and `test_gate_rejects_success_like_status`.
- Items 14-23 are covered by `test_gate_rejects_live_raw_secret_provider_and_approval_fields`.
- Items 24-29 are covered by `test_armed_state_allows_pre_armed_review_to_armed_not_fired`, `test_armed_state_rejects_firing_and_execution_states`, `test_armed_state_rejects_sdk_and_key_states`, `test_armed_state_rejects_retry_fallback_reserve_and_second_call_states`, `test_armed_state_rejects_success_like_states`, and `test_unknown_armed_state_maps_config_error`.
- Items 30-37 are covered by `test_one_shot_budget_lock_validates_safe_defaults` and `test_one_shot_budget_lock_rejects_widening_and_spent_flags`.
- Items 38-41 are covered by `test_policy_locks_validate_safe_defaults` and `test_policy_locks_reject_widening_and_call_expansion_flags`.
- Items 42-48 are covered by `test_final_approval_packet_to_execution_boundary_linkage_validates_safe_matching_refs`, `test_linkage_rejects_missing_run_id`, `test_linkage_rejects_missing_approval_phrase_hash`, `test_linkage_rejects_run_id_mismatch`, `test_linkage_rejects_approval_phrase_hash_mismatch`, and `test_linkage_rejects_missing_artifact_reference`.
- Items 49-51 are covered by `test_approval_phrase_ref_rejects_unsafe_refs` and `test_armed_state_artifact_ref_rejects_unsafe_refs`.
- Items 52-60 are covered by `test_gate_helpers_keep_armed_but_not_fired_no_call_counters_closed` and `test_gate_no_call_invariant_rejects_execution_markers`.
- Items 61-63 are covered by `test_explicit_approval_gate_write_requires_pre_and_post_scan`, `test_armed_state_write_requires_pre_and_post_scan`, and `test_explicit_approval_gate_rejects_scan_failure`.
- Items 64-70 are covered by `test_explicit_approval_gate_write_helper_stays_inside_run_dir`, `test_explicit_approval_gate_write_helper_blocks_unsafe_paths`, `test_explicit_approval_gate_write_helper_blocks_outside_absolute_path`, `test_explicit_approval_gate_write_failure_maps_report_error`, `test_armed_state_write_helper_stays_inside_run_dir`, `test_armed_state_write_helper_blocks_unsafe_paths`, and `test_armed_state_write_failure_maps_report_error`.
- Items 71-78 are covered by `test_default_runtime_paths_do_not_create_approval_or_gate_artifacts`, plus artifact-specific default runtime creation tests.
- Items 79-85 are covered by `test_p3u_runtime_imports_no_provider_sdk_or_network_modules`, `test_p3u_source_reads_no_env_or_key_value_and_uses_no_network_strings`, and `test_p3u_p3t_p3s_p3r_boundaries_do_not_call_call_model`.
- Items 86-88 are covered by the full `pytest -q` regression run, offline-only marker policy in `pyproject.toml`, and `test_agents_and_claude_remain_byte_identical`.

The latest recorded P3U targeted suite passed with `117 passed`; the latest full suite passed with `875 passed` before this review. This review also requires a fresh full verification run.

## Regression Review

P3U does not conflict with P3T, P3S, P3R, P3Q, P3P, P3M, P3L, P3K, P3J, P3G, P3E, P3C, P3B, P3A, or V0 harness constraints.

The preceding P3T/P3S/P3R/P3Q layers remain no-call. Default/runtime artifact creation remains disabled for approval package, no-call integration summary, call attempt summary, pre-live package manifest, final live approval packet, human confirmation checklist, explicit approval gate, armed state, and live smoke result. Default pytest remains offline-only; live-smoke marked tests do not execute a real live call.

`AGENTS.md` and `CLAUDE.md` remain byte-identical by test and required verification. Runtime forbidden import checks and boundary `call_model` string checks are part of the verification requirements.

## P3V Entry Risk Review

P3V should not be the actual first live smoke phase. The safer next phase is final live-fire checklist / still-no-call review.

Risks to keep blocked before any real fire transition:

- `armed=true` must not be treated as execution permission.
- `fired=true`, `execution_allowed=true`, `live_call_allowed=true`, `model_call_count=1`, and `call_model_count=1` should remain forbidden in P3V.
- Provider allowlist actual activation, SDK import, key loading, env value read, network transport, and `call_model` execution should remain forbidden in P3V.
- Command skeletons must remain non-executable and must not introduce `--execute`, `--live`, `--use-key`, `--load-key`, `--call-model`, `--network`, `--sdk-import`, `--fire`, or equivalent semantics.
- Before a real first call, one more last-stop checklist should define the exact one-shot fire plan, expected artifacts, rollback/non-retry behavior, and post-failure review requirements.

P3V entry is acceptable only for a no-call final live-fire checklist. The first real call should remain deferred to P3W or a later explicit approval phase.

## Final Decision

P3U completion review finds no blocking code, test, or documentation issue for P3V entry as final live-fire checklist / still-no-call review only.

P3V entry: YES.

This is not approval for live smoke or any real provider, SDK, key, API, network, `call_model`, fired, execution, or positive call-count path.
