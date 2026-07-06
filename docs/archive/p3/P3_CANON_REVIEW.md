# P3 Canon Review

## Verdict

P3 implementation entry: **NO**

The P3 Canon is directionally correct, but it has blocking ambiguity in document priority and API retry/budget semantics. Because P3 will introduce real API calls, these ambiguities should be fixed in `AICO_P3_CANON.md` before implementation starts.

## Reviewed Documents

- `AICO_MASTER_CANON.md`
- `AICO_P3_CANON.md`
- `AICO_V0_CANON.md`
- `HANDOFF.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_NOTES.md`
- `checklist.md`

Review HEAD: `48f0ebe`

## Critical Issues

### 1. P3 Canon document priority puts V0 Canon above P3 Canon.

`AICO_P3_CANON.md` currently lists priority as:

```text
1. AICO_MASTER_CANON.md
2. AICO_V0_CANON.md
3. AICO_P3_CANON.md
```

This is unsafe for P3 implementation. `AICO_V0_CANON.md` intentionally requires API calls 0, LLM calls 0, `MODEL_ERROR` forbidden, and `key_slot` null or mock. P3 intentionally introduces real API-capable workers and API call logging. If V0 Canon stays above P3 Canon during P3 implementation, the phase-specific P3 rules can be overridden by V0 dry-run rules.

Required fix: in `AICO_P3_CANON.md`, set implementation priority to:

```text
1. AICO_MASTER_CANON.md
2. AICO_P3_CANON.md
3. AICO_V0_CANON.md
4. HANDOFF.md
5. AGENTS.md / CLAUDE.md
6. CONTEXT_NOTES.md
7. checklist.md
```

### 2. Retry and reserve budget semantics are ambiguous.

`AICO_P3_CANON.md` proposes:

```text
max_model_calls = 6
max_retries_per_call = 1
max_consecutive_model_errors = 2
reserve_1 사용은 max_model_calls와 retry budget 안에서만 가능
```

But `max_model_calls = 6` exactly equals manager 1 + worker 4 + auditor 1. It leaves no obvious room for retry or `reserve_1` unless a failed original call does not count, a downstream call is skipped, or reserve calls consume a separate retry budget. The document must define whether attempted failed calls count toward `max_model_calls`, and how reserve retries interact with the 6-call default.

Required fix: state one of these explicitly:

- failed attempts count toward `max_model_calls`, so any retry may require skipping downstream calls or raising `BUDGET_EXCEEDED`;
- retry attempts use a separate retry budget but are still logged;
- `max_model_calls` default should be greater than 6 if one retry is allowed.

### 3. `masked_raw_output` handling is under-specified for malformed, non-JSON, and empty responses.

The Canon says raw output storage is forbidden by default and `masked_raw_output` is required, but P3 failure handling also allows malformed provider response to become `MODEL_ERROR` before schema stage. It does not clearly say whether malformed/non-JSON/empty provider responses should create a worker result with `masked_raw_output`, a failure-only run_log entry, or both.

Required fix: define artifact behavior for:

- timeout with no response body;
- HTTP 429/500 with provider error body;
- provider unavailable with no body;
- malformed non-JSON body;
- empty body;
- JSON body that fails worker schema validation.

## Required Fixes Before P3 Implementation

1. Fix `AICO_P3_CANON.md` document priority so P3 Canon is above V0 Canon for P3 implementation.
2. Define retry accounting, reserve slot behavior, and whether failed attempts count against `max_model_calls`.
3. Define `masked_raw_output` and artifact rules for malformed, non-JSON, empty, and no-body provider responses.
4. Clarify retry final failure type after retries are exhausted. Recommended: keep the original terminal failure type such as `MODEL_ERROR` or `BUDGET_EXCEEDED`, and log retry attempts as parent-linked events.
5. Clarify whether `max_consecutive_model_errors` is counted globally across the run or per key_slot/provider.

## Non-blocking Recommendations

- Add an explicit fake-provider testing rule: P3 tests must use fake/mock provider adapters and must not make network calls.
- Add an explicit provider error sanitization rule: provider error bodies may be stored only after secret scan and masking.
- Add a concrete `event_type` vocabulary for API calls, retries, provider failures, schema failures, report failures, and budget stops.
- Add a P3-specific note that `repair loop` remains P4 scope. This avoids confusion because `AICO_MASTER_CANON.md` has a later P4 section for Repair 1.
- Add a note that `checklist.md` is the canonical checklist filename in this repository. Do not introduce `CHECKLIST.md`.

## Required Test Coverage Review

The P3 Required Tests are mostly concrete and implementation-ready. They cover:

- raw key non-exposure;
- key_slot logging;
- timeout, 429, 500, provider unavailable;
- malformed response split between `MODEL_ERROR` and `SCHEMA_ERROR`;
- worker JSON/schema/bad-output failures;
- `masked_raw_output` and `raw_output_saved`;
- final/failed report mutual exclusion;
- `ceo_report.md` or `REPORT_ERROR`;
- `semantic_preflight` and repair loop non-execution;
- worker permission blocks;
- external URL/web search/repo clone blocks;
- mid-flight failure;
- budget enforcement;
- `AGENTS.md` and `CLAUDE.md` byte identity.

Missing or under-specified tests to add before implementation is accepted:

1. fake provider adapter proves no network call is made in tests.
2. failed API attempts count against the intended budget rule.
3. reserve_1 behavior is tested under the clarified budget rule.
4. max_consecutive_model_errors scope is tested, either global or per slot.
5. malformed non-JSON response artifact behavior is tested.
6. empty response artifact behavior is tested.
7. provider error body secret masking is tested.
8. retry events preserve parent_event_id.

## Key/Secret Safety Review

Strong points:

- raw API key is forbidden in prompt, log, report, worker output, manager/audit/final/failed/ceo reports, and `masked_raw_output`.
- Harness owns key management.
- worker does not know key values.
- logs use `key_slot` rather than raw key.
- key_slot examples are clear: `manager_1`, `worker_1`, `worker_2`, `worker_3`, `worker_4`, `auditor_1`, `reserve_1`.
- raw key in artifacts becomes `SECURITY_BLOCKED`.

Remaining ambiguity:

- masking versus `SECURITY_BLOCKED` needs a deterministic decision table. Recommended rule: raw key leak is always `SECURITY_BLOCKED`; non-key secret-like provider content may be masked if masking fully removes the secret.

## API Failure Handling Review

Clear enough:

- timeout, 429, 500, provider unavailable, transport failure map to `MODEL_ERROR`.
- JSON parse, missing fields, type mismatch, schema validation map to `SCHEMA_ERROR`.
- schema-valid but empty/out-of-scope/low-confidence output maps to `WORKER_BAD_OUTPUT`.
- shell/file/network/external URL/repo/web search/raw key leak maps to `SECURITY_BLOCKED`.
- budget limits map to `BUDGET_EXCEEDED`.
- report write failure maps to `REPORT_ERROR`.

Needs clarification before implementation:

- retry final failure type after retry exhaustion;
- reserve_1 handoff criteria;
- whether 429 is retried by default or only when retry budget exists;
- whether provider 500 and provider unavailable are retried;
- whether malformed provider response before schema stage stores sanitized body anywhere.

## State Transition Review

P3 Canon preserves the main P2 state rules:

- `final_report.md` and `failed_draft.md` remain mutually exclusive.
- `failed_draft.md` is not canon/final.
- `ceo_report.md` is attempted on all paths.
- `REPORT_ERROR` is logged when `ceo_report.md` generation fails.
- `required_fixes` blocks `final_report.md` promotion while repair is forbidden.
- `ceo_decision_needed=false` is required for final promotion.
- mid-flight failure preserves partial `worker_results.jsonl` and skips downstream artifacts when conditions are not met.

Gap:

- `AICO_P3_CANON.md` does not restate the full `ceo_decision_needed` merge rule from Master/V0: manager or auditor true means final status `NEEDS_DECISION`, and auditor true can override manager. Add this explicitly to avoid implementation drift.

## File Naming Review

Current repository uses `checklist.md`. No `CHECKLIST.md` exists.

Recommendation:

- Treat `checklist.md` as canonical for this repository.
- Do not introduce `CHECKLIST.md`.
- Add this convention to `AICO_P3_CANON.md` or `HANDOFF.md` before P3 implementation if checklist references are needed in CI or automation.

## Final Decision

P3 implementation entry: **NO**

Blocking reason: `AICO_P3_CANON.md` currently places `AICO_V0_CANON.md` above P3 Canon, which can override P3 API-worker behavior with V0 dry-run constraints. Retry/reserve budget and malformed response artifact behavior also need clarification before code is written.

## Correction Note

2026-07-05: The blocking items were addressed in `AICO_P3_CANON.md`: document priority was corrected, retry/reserve budget rules were clarified, malformed response artifact handling was specified, and P3 Required Tests were expanded. After this correction, P3 implementation entry is **YES**, subject to a clean worktree and explicit implementation instruction.
