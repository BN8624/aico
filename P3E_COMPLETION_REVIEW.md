# P3E Completion Review

## Verdict

P3F entry: NO

P3E successfully implements activation-preparation structures without enabling live calls. However, P3F should not begin yet because the live approval object can still carry raw secret-like values in free-form fields, and no direct test currently blocks that path.

This NO does not invalidate the P3E preparation work. It identifies a narrow blocker to fix before any P3F first-live-smoke policy or preparation step.

## Reviewed Documents and Files

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `P3D_LIVE_CALL_POLICY.md`
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
- `aico_v0/live_gate.py`
- `aico_v0/provider_allowlist.py`
- `aico_v0/artifact_safety.py`
- `aico_v0/live_test_policy.py`
- `aico_v0/key_registry.py`
- `aico_v0/provider_base.py`
- `aico_v0/p3_real_provider.py`
- `aico_v0/response_normalizer.py`
- `tests/test_p3e_live_gate.py`
- `tests/test_p3e_artifact_safety.py`
- `tests/test_p3e_offline_policy.py`
- `tests/test_p3_real_provider_guard.py`
- `tests/test_p3_provider_boundary.py`
- `tests/test_p3_fake_provider.py`
- `tests/test_v0_harness.py`

## Summary

P3E adds activation-preparation modules only:

- `live_gate.py` defines approval, budget, gate validation, key availability checks, and canonical failure mapping.
- `provider_allowlist.py` defines an empty default allowlist and non-authorizing `google_gemini` candidate metadata.
- `artifact_safety.py` scans artifact payloads for raw key-like values, bearer tokens, private key blocks, raw provider output markers, `raw_output_saved=True`, `raw_output`, and final/failed report coexistence.
- `live_test_policy.py` defines a registered but default-disabled `live_provider` marker policy.

No actual API call path, LLM call path, key value read, provider SDK import, network import/call, live smoke, semantic preflight, repair loop, worker file edit permission, or worker shell permission was introduced.

## Critical Issues

1. `LiveApproval` does not block raw secret-like values in approval fields.

`LiveApproval` includes free-form fields such as `provider`, `model`, `reason`, `run_id`, `expires_at`, and `approval_phrase`. `validate_approval` blocks missing fields, ambiguous phrases, invalid scope, and URL-like provider/endpoint values, but it does not scan the approval object for raw key-like or token-like values.

This conflicts with the P3E requirement that the approval object must not contain raw keys. A raw key in `reason` or `model` could be represented in memory and in `repr` unless another layer catches it.

2. No direct test asserts that raw secrets in `LiveApproval` become `SECURITY_BLOCKED`.

P3E tests cover artifact secrets and provider boundary secret masking, but not approval-object secret ingress.

## Required Fixes Before P3F

1. Add approval object secret scanning.

`validate_approval` or a dedicated approval sanitizer should reject any raw key-like value, bearer token, env var value pattern, or private key block in all approval fields.

2. Map approval-object secret ingress to canonical failure.

Recommended mapping: `raw key leaked -> SECURITY_BLOCKED`.

3. Add direct tests.

Required tests before P3F:

- raw key-like value in approval `reason` becomes `SECURITY_BLOCKED`.
- bearer token in approval `approval_phrase` becomes `SECURITY_BLOCKED`.
- env var value pattern in approval free-form field becomes `SECURITY_BLOCKED`.
- approval object `repr` or loggable rendering does not expose raw secret after validation path.

4. Consider removing or constraining `LiveApproval.endpoint`.

The current code blocks URL-like endpoint values, which is good. Before P3F, decide whether endpoint should remain a symbolic allowlist key or be removed from the approval object entirely.

## Non-blocking Recommendations

1. Remove the unused `Sequence` import from `live_gate.py`.
2. Either use `SAFE_ENV_VAR_NAMES` in `artifact_safety.py` or remove it to avoid confusion.
3. Make `ArtifactSafetyResult.to_run_log_event` include the full P3 run_log field set or explicitly document that the harness must wrap it.
4. Add a P3F policy document before any live smoke. P3F should not itself imply live execution.
5. Keep `google_gemini` as candidate metadata only until explicit provider allowlist activation is approved.

## P3E Scope Compliance Review

P3E stays inside activation preparation scope.

- Actual API call path: not found.
- Actual LLM call path: not found.
- Actual key value usage: not found.
- Provider SDK import: not found.
- HTTP/network import or call path: not found.
- Live smoke execution: not found.
- Provider allowlist default: empty.
- Real provider remains disabled by default.
- P3F or later explicit approval is still required before any live call.
- `semantic_preflight` execution was not introduced.
- Repair loop execution was not introduced.

## Live Gate Review

`live_gate.py` implements the P3D failure mapping as a constant table and exposes validators that classify failure conditions. It does not execute a live call after a successful validation.

Mappings are present:

| Condition | Failure type |
| --- | --- |
| explicit approval missing | `HUMAN_DECISION_REQUIRED` |
| approval phrase ambiguous | `HUMAN_DECISION_REQUIRED` |
| provider not specified in approval | `HUMAN_DECISION_REQUIRED` |
| key slots not specified in approval | `HUMAN_DECISION_REQUIRED` |
| max_model_calls not specified in approval | `HUMAN_DECISION_REQUIRED` |
| max_runtime_seconds not specified in approval | `HUMAN_DECISION_REQUIRED` |
| `AICO_ENABLE_REAL_PROVIDER` missing | `CONFIG_ERROR` |
| `AICO_ALLOW_LIVE_CALLS` missing | `CONFIG_ERROR` |
| `AICO_ENABLE_REAL_PROVIDER=false` | `CONFIG_ERROR` |
| `AICO_ALLOW_LIVE_CALLS=false` | `CONFIG_ERROR` |
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
| budget missing | `CONFIG_ERROR` |
| budget invalid | `CONFIG_ERROR` |
| budget exceeded | `BUDGET_EXCEEDED` |
| artifact safety scan missing | `CONFIG_ERROR` |
| raw key found in artifact | `SECURITY_BLOCKED` |
| unmasked raw provider output found in artifact | `SECURITY_BLOCKED` |
| `raw_output_saved=True` detected | `SECURITY_BLOCKED` |
| provider SDK import before approved phase | `SECURITY_BLOCKED` |
| network call in default tests | `SECURITY_BLOCKED` |
| live call attempted in default pytest | `SECURITY_BLOCKED` |
| `ProviderResult` safety rule broken | `SECURITY_BLOCKED` |
| final_report and failed_draft both generated | `REPORT_ERROR` |
| ceo_report generation failed | `REPORT_ERROR` |

The validator is classification-only. It returns `LiveGateResult` and does not call a provider.

Blocking gap: the `raw key leaked` mapping exists in the table but is not applied to `LiveApproval` fields.

## Approval Object and Schema Review

Implemented required fields:

- `provider`
- `key_slots`
- `max_model_calls`
- `max_runtime_seconds`
- `approval_scope`
- `approved_by_user`

Optional fields are also present:

- `model`
- `max_input_tokens`
- `max_output_tokens`
- `max_retries_per_call`
- `run_id`
- `expires_at`
- `reason`
- `approval_phrase`
- `endpoint`

The default approval scope is `this_run_only`. If `approved_by_user` is not true, validation returns `HUMAN_DECISION_REQUIRED`. Ambiguous phrases such as `continue`, `proceed`, `go ahead`, `진행해`, and `계속해` are rejected as `HUMAN_DECISION_REQUIRED`.

URL-like provider or endpoint values become `SECURITY_BLOCKED` through `arbitrary URL requested`.

Blocking gap: raw key-like values in approval free-form fields are not scanned or rejected.

## Provider Allowlist Review

`provider_allowlist.py` provides a safe allowlist structure.

- `DEFAULT_PROVIDER_ALLOWLIST` is empty.
- Empty allowlist authorizes no provider.
- Missing allowlist maps to `CONFIG_ERROR`.
- Empty allowlist maps to `CONFIG_ERROR`.
- Unknown provider maps to `SECURITY_BLOCKED`.
- Provider not in allowlist maps to `SECURITY_BLOCKED`.
- Unknown endpoint maps to `SECURITY_BLOCKED`.
- URL-like provider/endpoint requests map to `SECURITY_BLOCKED`.
- `CANDIDATE_PROVIDER_METADATA` marks `google_gemini` as non-authorizing.
- No provider SDK import exists.
- No endpoint URL call path exists.

The candidate/provider distinction is clear enough for P3E.

## Artifact Safety Scan Review

`artifact_safety.py` detects:

- raw key-like values.
- env var value patterns.
- bearer token patterns.
- private key blocks.
- unmasked raw provider output markers.
- `raw_output_saved=True`.
- `raw_output` field.
- `final_report.md` and `failed_draft.md` coexistence.

It allows:

- `key_slot`.
- env var name.
- `masked_raw_output`.
- `mask_reason`.
- `raw_output_saved=false`.

Scan failures map to `SECURITY_BLOCKED`, except final/failed report coexistence maps to `REPORT_ERROR`. Missing scan input maps to `CONFIG_ERROR`. `ArtifactSafetyResult.to_run_log_event` provides a run-log-ready event fragment.

The scanner does not connect to live runs in P3E, which matches scope.

## Offline Test Policy Review

`live_test_policy.py` and `pyproject.toml` keep default tests offline.

- `live_provider` marker is registered.
- `LIVE_PROVIDER_DEFAULT_ENABLED = False`.
- `should_skip_live_provider_test()` returns `True` by default.
- Even `explicit_enable=True` still skips because P3E does not enable the marker.
- Default `pytest -q` has no live provider test file.
- Runtime AST checks find no provider SDK or network imports.

P3E targeted tests run without live calls.

## Key Loading Skeleton Review

Key loading remains isolated and disabled.

- `KeyRegistry.raw_key_value` still raises.
- P3E validators use `KeyRegistry.has_key`, which is boolean-only.
- Env var names remain static strings in `KEY_SLOT_ENV_VARS`.
- Env var values are not read.
- No `os.environ` use exists in `aico_v0`.
- Key slots are the external identifiers.

P3F key loading should remain behind a dedicated key isolation review before any actual key value read is introduced.

## ProviderResult and Provider Boundary Compatibility Review

Provider boundary safety remains intact.

- `ProviderResult` rejects unknown constructor fields through dataclass construction.
- `ProviderResult` has no `raw_output` field.
- `raw_output_saved=True` raises `ValueError`.
- Secret-like recursive masking remains in `ProviderResult`.
- `response_normalizer` keeps `raw_output_saved=False`.
- P3B and P3C tests still cover provider boundary behavior.

P3E artifact safety scanning complements provider masking and does not conflict with it.

## P3D Policy Compatibility Review

P3E mostly satisfies the P3D policy fix.

- P3E is activation preparation only.
- No first live smoke is performed.
- Provider allowlist default is empty.
- Candidate provider remains non-authorizing metadata.
- Live-gate failure mapping exists in policy and code.
- Artifact safety scan implementation and tests exist.
- Default pytest remains offline-only.

P3D completion blockers are largely resolved, except approval-object raw-secret blocking remains incomplete before P3F.

## Test Coverage Review

| Required item | Coverage | Status |
| --- | --- | --- |
| approval missing becomes HUMAN_DECISION_REQUIRED | `test_approval_failures_map_to_human_decision_required` | Direct |
| ambiguous approval becomes HUMAN_DECISION_REQUIRED | `test_approval_failures_map_to_human_decision_required` | Direct |
| missing provider in approval becomes HUMAN_DECISION_REQUIRED | `test_approval_failures_map_to_human_decision_required` | Direct |
| missing key_slots in approval becomes HUMAN_DECISION_REQUIRED | `test_approval_failures_map_to_human_decision_required` | Direct |
| missing max_model_calls in approval becomes HUMAN_DECISION_REQUIRED | `test_approval_failures_map_to_human_decision_required` | Direct |
| missing max_runtime_seconds in approval becomes HUMAN_DECISION_REQUIRED | `test_approval_failures_map_to_human_decision_required` | Direct |
| missing AICO_ENABLE_REAL_PROVIDER becomes CONFIG_ERROR | `test_runtime_flag_failures_map_to_config_error` | Direct |
| missing AICO_ALLOW_LIVE_CALLS becomes CONFIG_ERROR | `test_runtime_flag_failures_map_to_config_error` | Direct |
| false AICO_ENABLE_REAL_PROVIDER becomes CONFIG_ERROR | `test_runtime_flag_failures_map_to_config_error` | Direct |
| false AICO_ALLOW_LIVE_CALLS becomes CONFIG_ERROR | `test_runtime_flag_failures_map_to_config_error` | Direct |
| both flags true are still insufficient without approval/allowlist/budget/artifact safety | `test_both_flags_true_are_insufficient_without_other_gates` | Direct |
| missing provider allowlist becomes CONFIG_ERROR | `test_provider_allowlist_failures` | Direct |
| empty provider allowlist becomes CONFIG_ERROR | `test_provider_allowlist_failures` | Direct |
| unknown provider becomes SECURITY_BLOCKED | `test_provider_allowlist_failures` | Direct |
| provider not in allowlist becomes SECURITY_BLOCKED | `test_provider_allowlist_failures` | Direct |
| arbitrary URL requested becomes SECURITY_BLOCKED | `test_provider_allowlist_failures` | Direct |
| missing budget becomes CONFIG_ERROR | `test_budget_validation` | Direct |
| invalid budget becomes CONFIG_ERROR | `test_budget_validation` | Direct |
| budget exceeded becomes BUDGET_EXCEEDED | `test_budget_validation` | Direct |
| first live smoke budget max_model_calls = 1 | `test_first_live_smoke_budget_defaults` | Direct |
| artifact safety scan detects raw key-like value | `test_artifact_safety_scan_detects_raw_key_like_value` | Direct |
| artifact safety scan detects bearer token pattern | `test_artifact_safety_scan_detects_bearer_token_pattern` | Direct |
| artifact safety scan detects private key block | `test_artifact_safety_scan_detects_private_key_block` | Direct |
| artifact safety scan detects unmasked raw provider output marker | `test_artifact_safety_scan_detects_unmasked_raw_provider_output_marker` | Direct |
| artifact safety scan detects raw_output_saved=True | `test_artifact_safety_scan_detects_raw_output_saved_true` | Direct |
| artifact safety scan detects raw_output field | `test_artifact_safety_scan_detects_raw_output_field` | Direct |
| artifact safety scan passes masked_raw_output | `test_artifact_safety_scan_passes_masked_raw_output_and_safe_metadata` | Direct |
| artifact safety scan allows key_slot | `test_artifact_safety_scan_passes_masked_raw_output_and_safe_metadata` | Direct |
| artifact safety scan allows env var name | `test_artifact_safety_scan_passes_masked_raw_output_and_safe_metadata` | Direct |
| artifact safety scan rejects final_report when raw secret is found | `test_artifact_safety_scan_rejects_final_report_with_raw_secret` | Direct |
| artifact safety scan rejects failed_draft when raw secret is found | `test_artifact_safety_scan_rejects_failed_draft_with_raw_secret` | Direct |
| artifact safety scan detects final_report and failed_draft coexistence as REPORT_ERROR | `test_artifact_safety_scan_detects_final_and_failed_draft_coexistence_as_report_error` | Direct |
| default pytest remains offline-only | `test_default_pytest_remains_offline_only` plus full `pytest -q` | Direct |
| live_provider marker is default-skip or non-executing by default | `test_live_provider_marker_is_registered_but_non_executing_by_default` | Direct |
| no network/provider SDK import appears in runtime package | `test_runtime_package_has_no_forbidden_sdk_network_or_env_value_imports` plus AST check | Direct |
| actual API call count remains 0 | `test_p3e_runtime_has_no_live_call_counters_or_key_usage` and no live provider execution | Direct |
| actual LLM call count remains 0 | `test_p3e_runtime_has_no_live_call_counters_or_key_usage` and no live provider execution | Direct |
| actual key usage remains 0 | `test_p3e_runtime_has_no_live_call_counters_or_key_usage` | Direct |
| existing P3C tests pass | `tests/test_p3_real_provider_guard.py` | Direct |
| existing P3B tests pass | `tests/test_p3_provider_boundary.py` | Direct |
| existing P3A tests pass | `tests/test_p3_fake_provider.py` | Direct |
| existing V0 tests pass | `tests/test_v0_harness.py` | Direct |
| AGENTS.md and CLAUDE.md remain byte-identical | P3E/P3B/P3C/V0 tests and SHA256 check | Direct |

Coverage gap before P3F: raw secret in `LiveApproval` fields is not directly tested.

## P3F Entry Risk Review

P3F should not go directly to live smoke yet.

Required before P3F:

1. Fix approval object secret scanning.
2. Add a direct test for raw secret-like values inside `LiveApproval`.
3. Write `P3F_LIVE_SMOKE_POLICY.md` or equivalent before any live smoke.
4. Decide whether `google_gemini` remains only a candidate or becomes an approved allowlist entry.
5. Decide whether provider SDK import is allowed in P3F or deferred to another preparation phase.
6. Decide whether actual key loading is allowed in P3F or requires a separate key isolation review.
7. Limit any first live smoke to one key slot and `max_model_calls = 1`, retry 0.
8. Define live smoke artifacts before execution.
9. Prove raw provider response cannot persist unmasked.
10. Preserve default `pytest -q` offline-only after any P3F work.

## Final Decision

P3F entry: NO

P3E activation preparation is useful and mostly complete, but P3F should wait until approval-object secret ingress is blocked and tested. Actual live smoke, provider SDK import, network transport, and real key loading remain forbidden.
