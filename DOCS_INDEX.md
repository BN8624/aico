# AICO Docs Index

## Current Entry Points

- `HANDOFF.md` — current state and next action
- `CONTEXT_NOTES.md` — working context and phase constraints
- `checklist.md` — current checklist
- `AICO_MASTER_CANON.md` — master Canon
- `AICO_P3_CANON.md` — Phase 3 Canon
- `AICO_V0_CANON.md` — v0 Canon
- `AICO_DIRECTION_DECISION.md` — direction decision retained as standalone decision doc

## Current Phase Status

- P3 closure: YES
- P4 entry: YES, no-call/data-only P4A only
- Recommended next phase: P4A mission_interview no-call implementation

## P3 Evidence Archive

Archived P3 evidence is under:

- `docs/archive/p3/`

Key evidence:

- `docs/archive/p3/P3Y_FINAL_INTEGRATION_REVIEW.md`
- `docs/archive/p3/P3X_COMPLETION_REVIEW.md`
- `docs/archive/p3/P3X_NEGATIVE_SAFETY_REPORT.md`
- `docs/archive/p3/P3W_COMPLETION_REVIEW.md`
- `docs/archive/p3/P3W_LIVE_SMOKE_RESULT.md`

The complete P3 archive includes P3A-P3Y completion reviews, live-call policies, live smoke approval/package documents, execution plan review, dry authorization review, negative safety report, and final integration review.

## P3 Proof Ladder

- L1 schema/artifact proof: completed
- L2 no-call dry-run proof: completed
- L3 controlled single-call live smoke: completed
- L4 negative safety tests / bad-input blocking proof: completed

## P4 Entry Guardrails

P4A is allowed only as no-call/data-only work.

Not allowed in P4A:

- additional live call
- worker orchestration
- worker file write authority
- worker shell authority
- shell execution
- web access
- repo clone
- GitHub automation
- parallel execution
- retry/reserve/fallback/second call

## Notes

`AICO_DIRECTION_DECISION.md` stays outside Canon for now. Any Canon absorption should happen in a separate, explicit Canon alignment phase.
