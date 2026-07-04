# AICO P2 V0 Dry-Run Completion Review

## Review Scope

- Canon basis: `AICO_MASTER_CANON.md` and `AICO_V0_CANON.md`.
- Reviewed implementation files: `aico_v0/harness.py`, `aico_v0/fixtures.py`, `aico_v0/cli.py`.
- Reviewed tests: `tests/test_v0_harness.py`.
- No implementation code was changed during this review.

## Verdict

P3 entry possible: **NO**.

Reason: the v0 harness is offline and mostly aligned with P2 dry-run constraints, but P2 should not be treated as complete until the uncovered V0 Required Tests are added and the `ceo_report.md` failure fallback records `REPORT_ERROR`.

## Canon Compliance Review

### No External Execution

- API calls: no API client, provider SDK, network client, or request path found in `aico_v0`.
- LLM calls: no model/provider call path found. `RunResult.api_call_count` and `RunResult.llm_call_count` default to `0`.
- `semantic_preflight`: no function or execution path exists. Only `deterministic_preflight` is implemented.
- repair loop: no loop or repair execution path exists. `RunResult.repair_loop_executed` defaults to `False`.
- worker file edit/shell: generated WorkOrders set `can_edit_files=False` and `can_run_shell=False`; preflight blocks either flag when explicitly `True`.
- network/repo/web/dashboard/Issue: no implementation path found for web dashboard, issue integration, repo clone, or network calls.

### Harness Structure

- `run_dry_run` creates `runs/<run_id>/` before mission load is finalized.
- mission input and mission path are accepted.
- deterministic scenario fixtures drive manager, worker, auditor, and report outputs.
- `work_orders.json`, `preflight_audit.json`, `worker_results.jsonl`, `manager_summary.json`, `audit_report.json`, reports, and `run_log.jsonl` are generated according to the scenario path.
- `deterministic_preflight` checks schema, forbidden keywords, permission flags, references, secret regex, and budget.
- `final_report.md` and `failed_draft.md` are mutually exclusive by promotion structure.
- mid-flight failure preserves partial `worker_results.jsonl` and skips manager/auditor/final artifacts.
- run log entries use `model=null`, `key_slot=null`, and zero token counts.

## Findings

### P1: `REPORT_ERROR` fallback is declared but not implemented.

Canon requires every run to attempt `ceo_report.md`, and if creation fails, record `REPORT_ERROR` in `run_log.jsonl`. Current calls to `_write_ceo_report` are not wrapped. If writing `ceo_report.md` fails, execution raises before a `REPORT_ERROR` event can be logged.

Affected paths:

- `aico_v0/harness.py`: config error path calls `_write_ceo_report` before logging final failure.
- `aico_v0/harness.py`: preflight failure path calls `_write_ceo_report` without fallback.
- `aico_v0/harness.py`: mid-flight failure path calls `_write_ceo_report` without fallback.
- `aico_v0/harness.py`: normal post-audit path calls `_write_ceo_report` and then logs `CEO_REPORT_CREATED`.

Impact: failure-path reporting is not canon-complete under report write failure.

### P2: V0 Required Tests are only partially mapped.

The current suite verifies the core seven scenarios and major artifact rules, but it does not directly cover all 42 V0 Canon Runtime Tests. Several canon tests are covered only indirectly or not covered.

Impact: P2 completion cannot be claimed against the full V0 Required Tests list.

### P2: Worker result schema validation is not implemented or directly tested.

Canon includes worker output schema error and schema-valid bad output paths. Current worker output is generated internally and not validated through a schema gate. `mid_flight_failure` returns `WORKER_BAD_OUTPUT`, but there is no malformed worker result path that becomes `SCHEMA_ERROR`.

Impact: Required Tests 7 and 8 are not fully demonstrated.

### P2: Secret masking is present, but secret blocking/masking tests are incomplete.

`_write_text` masks all writes via `_mask_secrets`, and preflight blocks secret-like WorkOrder content. Existing tests only assert that a hard-coded sample secret does not appear, but they do not inject secret-bearing mission, WorkOrder, or worker output data to verify masking/blocking behavior.

Impact: Required Tests 21 and 28 need stronger tests before P3.

## Required Tests Mapping

| # | V0 Canon Required Test | Current Coverage |
|---|---|---|
| 1 | dry-run creates run directory | Covered by parametrized scenario test |
| 2 | missing mission input/path creates run directory and becomes CONFIG_ERROR | Covered |
| 3 | invalid WorkOrder fails deterministic_preflight | Covered for forbidden shell wording |
| 4 | deterministic_preflight uses only allowed deterministic checks | Partially covered; needs direct assertions for each check type |
| 5 | v0 does not run LLM-based semantic_preflight | Covered by result flag and absence of trace |
| 6 | semantic_preflight trace does not exist in v0 run | Partially covered by no explicit trace assertion |
| 7 | worker output schema error becomes SCHEMA_ERROR | Missing |
| 8 | schema-valid but empty/irrelevant worker output becomes WORKER_BAD_OUTPUT | Partially covered by mid-flight failure, not by bad content |
| 9 | audit fail creates no final_report | Covered |
| 10 | audit fail creates failed_draft only if draft_report exists | Covered for draft exists; missing no-draft fail case |
| 11 | audit pass creates final_report | Covered |
| 12 | audit conditional creates final_report and ceo_report includes warnings | Covered |
| 13 | required_fixes prevents final_report | Covered through fail scenario |
| 14 | required_fixes + ceo_decision_needed=false becomes FAIL | Covered through fail scenario |
| 15 | required_fixes + ceo_decision_needed=true becomes NEEDS_DECISION | Missing |
| 16 | needs_decision creates ceo_report and no final_report | Covered |
| 17 | manager_summary.ceo_decision_needed true creates NEEDS_DECISION | Covered indirectly; manager and auditor are both true |
| 18 | audit_report.ceo_decision_needed true creates NEEDS_DECISION | Covered indirectly; manager and auditor are both true |
| 19 | ceo_report exists or REPORT_ERROR is logged | Partially covered for success; missing REPORT_ERROR failure simulation |
| 20 | run_log failure event includes failure_type | Covered |
| 21 | raw API key never appears in logs | Partially covered; needs injected secret cases |
| 22 | worker cannot request shell/file edit | Covered for generated WorkOrders; needs direct preflight true-flag cases |
| 23 | repair loop is not executed | Covered by result flag and code search |
| 24 | mission.md has highest priority within a run | Missing |
| 25 | v0 makes zero API calls | Covered by result field and code search |
| 26 | v0 never emits MODEL_ERROR | Covered by artifact text scan |
| 27 | final_report.md and failed_draft.md are mutually exclusive | Covered |
| 28 | raw_output is masked or blocked when secrets are detected | Partially covered; needs injected worker/raw output secret case |
| 29 | references cannot access paths outside allowed workspace/run scope | Missing |
| 30 | confidence < 0.5 is not used as sole support for final_report | Missing |
| 31 | budget exceeded becomes BUDGET_EXCEEDED | Covered |
| 32 | mid-flight failure preserves partial worker_results and skips unavailable downstream artifacts | Covered |
| 33 | v0 happy path creates 4 WorkOrders | Covered |
| 34 | deterministic_preflight allows 1~4 WorkOrders | Partially covered; 1, 2, and 3 are not directly tested |
| 35 | more than 4 WorkOrders becomes BUDGET_EXCEEDED | Covered |
| 36 | pass scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |
| 37 | conditional scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |
| 38 | fail scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |
| 39 | needs_decision scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |
| 40 | config_error scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |
| 41 | budget_exceeded scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |
| 42 | mid_flight_failure scenario is deterministic | Partially covered; should compare repeated artifact content excluding timestamps/run_id |

## Missing Test List

1. `ceo_report.md` write failure logs `REPORT_ERROR` to `run_log.jsonl`.
2. malformed worker result becomes `SCHEMA_ERROR`.
3. schema-valid but empty or irrelevant worker result becomes `WORKER_BAD_OUTPUT`.
4. audit fail with no `draft_report` does not create `failed_draft.md`.
5. `required_fixes` plus `ceo_decision_needed=true` becomes `NEEDS_DECISION`.
6. manager-only `ceo_decision_needed=true` becomes `NEEDS_DECISION`.
7. auditor-only `ceo_decision_needed=true` becomes `NEEDS_DECISION`.
8. explicit semantic preflight trace file is absent from every run.
9. worker permission flags set to `True` are blocked by deterministic preflight.
10. secret-bearing WorkOrder is blocked as `SECURITY_BLOCKED`.
11. secret-bearing output is masked or blocked.
12. out-of-workspace/out-of-run `references` are blocked.
13. `deterministic_preflight` allows exactly 1, 2, 3, and 4 WorkOrders.
14. `confidence < 0.5` is not used as sole support for `final_report.md`.
15. mission path and mission input priority behavior is tested.
16. repeated runs of each required scenario are compared for deterministic artifacts, ignoring timestamps and run directory names.

## API/LLM Risk

Current risk: low.

Evidence:

- Runtime imports are standard library only.
- No network, provider SDK, API key loading, subprocess shell execution, repo clone, web server, dashboard, or Issue integration path was found in `aico_v0`.
- The CLI only parses local arguments and calls `run_dry_run`.

Residual risk: no explicit guard prevents future code from adding network imports or provider calls. Keep code-search tests or static guard tests before P3.

## Report Rules

- `final_report.md` is created only when preflight passes, audit status is pass/conditional, blocking is false, required fixes are empty, and no CEO decision is needed.
- `failed_draft.md` is created only when promotion is blocked, status is FAIL or NEEDS_DECISION, and `draft_report` exists.
- Current structure prevents both files from being created in the same run.
- Missing: a dedicated no-draft fail scenario test.

## Mid-Flight Failure

Current behavior matches the core canon rule:

- `worker_results.jsonl` is written with two partial worker results.
- `manager_summary.json`, `audit_report.json`, `final_report.md`, and `failed_draft.md` are skipped.
- `ceo_report.md` is attempted.
- `run_log.jsonl` records failure with `failure_type=WORKER_BAD_OUTPUT`.

## Raw Key and Secret Handling

Current behavior:

- `_mask_secrets` is applied to all text and JSON writes through `_write_text`.
- deterministic preflight blocks secret-like values in WorkOrder text or serialized WorkOrder JSON.
- worker `raw_output` is not persisted; `masked_raw_output` is used instead.

Gaps:

- tests do not inject actual secret-like mission text, WorkOrder text, or raw worker output.
- tests do not verify the exact masking token in generated artifacts.

## P3 Entry Decision

P3 entry possible: **NO**.

Required before P3:

1. Add tests listed in the Missing Test List.
2. Implement and test `REPORT_ERROR` logging when report generation fails.
3. Add worker result validation paths for `SCHEMA_ERROR` and bad-content `WORKER_BAD_OUTPUT`.
4. Add deterministic repeat-run comparisons for all required scenarios.
