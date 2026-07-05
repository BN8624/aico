# HANDOFF

## Current Status

- Current HEAD before this P3G skeleton commit: `889f288`.
- P2 V0 dry-run harness hardening is complete.
- P3 Canon correction is complete.
- P3A fake-provider API worker layer implementation is complete.
- P3A completion review is complete.
- P3B provider boundary skeleton is complete.
- P3B completion review is complete.
- P3B blocker fix is complete.
- P3C entry decision: YES.
- P3C guarded provider work is complete.
- P3C completion review is complete.
- P3D entry decision: YES.
- P3D live-call gate policy documentation is complete.
- P3D completion review is complete.
- P3D policy fix is complete.
- P3E entry decision after policy fix: YES.
- P3E scope: activation preparation only.
- P3E activation preparation implementation is complete.
- P3E completion review is complete.
- P3E blocker fix is complete.
- P3F entry decision after blocker fix: YES.
- P3F meaning if later approved: first live smoke policy/preparation only unless separately approved.
- P3F first live smoke policy documentation is complete.
- P3F implementation: NO. This work is documentation only.
- P3F completion review is complete.
- P3F policy fix is complete.
- P3G entry decision after policy fix: YES.
- P3G meaning if later approved: live smoke implementation skeleton or policy/preparation only, unless separately approved.
- P3G first live smoke implementation skeleton is complete.
- P3G scope: skeleton/policy only.
- Real provider default state: disabled.
- Actual API calls during this work: NO.
- Actual LLM calls during this work: NO.
- Actual key usage during this work: NO.
- Provider SDK import during this work: NO.
- Network calls during this work: NO.
- Live smoke during this work: NO.

## This Work

- Implemented P3G first live smoke skeleton without enabling live smoke.
- Added first live smoke approval schema and gate validation.
- Enforced exactly one key_slot, allowed key_slot list, `max_model_calls = 1`, `max_retries_per_call = 0`, no reserve, no retry, no fallback, no second call, and `allow_raw_output=false`.
- Added safe `live_smoke_result.json` and `artifact_safety_report.json` schema helpers.
- Added disabled runner skeleton that performs no API, LLM, network, key value read, provider SDK import, or live smoke execution.
- Added `live_smoke` marker policy as default-skip/non-executing.
- Added P3G skeleton tests.

## Changed Files

- `aico_v0/live_smoke.py`
- `aico_v0/live_test_policy.py`
- `tests/test_p3g_live_smoke_skeleton.py`
- `pyproject.toml`
- `HANDOFF.md`
- `CONTEXT_NOTES.md`
- `checklist.md`

## Test Result

- P3G targeted tests passed with `35 passed`.
- Full `pytest -q` passed with `200 passed`.
- AGENTS/CLAUDE byte-identical check passed. SHA256 matched.
- Runtime forbidden import AST check for provider SDK/network/env-value imports in `aico_v0` passed with no violations.

## P3 Implementation Progress

- P3A fake-provider layer: complete.
- P3A completion review: complete.
- P3B provider boundary skeleton: complete.
- P3B completion review: complete.
- P3B blocker fix: complete.
- P3C guarded provider work: complete.
- P3C completion review: complete.
- P3C entry: YES.
- P3D entry: YES.
- P3D live-call gate policy: complete.
- P3D completion review: complete.
- P3D policy fix: complete.
- P3E entry: YES.
- P3E scope: activation preparation only.
- P3E activation preparation: complete.
- P3E completion review: complete.
- P3E blocker fix: complete.
- P3F entry: YES.
- P3F first live smoke policy: complete.
- P3F implementation: NO.
- P3F completion review: complete.
- P3F policy fix: complete.
- P3G entry: YES.
- P3G first live smoke skeleton: complete.
- P3G scope: skeleton/policy only.
- Actual live smoke: not started.
- Real provider/API worker actual connection: not started.
- Real key usage: not started.
- Network/provider adapter live tests: not started.
- Live smoke: not started.

## Git Status

- Status before editing: clean at `889f288`.
- Final git status must be checked after commit and push.

## Next Work

- Review P3G first live smoke skeleton before any live smoke activation work.
- Keep actual live smoke forbidden until a later explicit approval phase, passing tests, clean git state, and all gates are satisfied.
- Keep provider allowlist default empty until a later explicit approval document activates a provider.
- Do not make live API calls, use real keys, import provider SDKs, add network transport, implement live smoke tests, or run live smoke until a later explicitly approved phase authorizes it.
