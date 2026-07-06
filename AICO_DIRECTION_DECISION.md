# AICO Direction Decision

## Verdict

AICO is not a vibe-coding skill pack.

AICO is not merely a multi-agent starter.

AICO is a file-based operating harness for deciding when an AI task may safely be dispatched, audited, and shipped.

One-line identity:

```text
AICO is not a system for calling more AI.
AICO is a system for deciding when AI is allowed to be called.
```

## Core Identity

AICO should be developed as an AI work operating harness.

The core flow is:

```text
mission.md
-> Harness
-> Manager
-> work_orders.json
-> Worker Pool
-> Auditor
-> final_report / failed_draft / ceo_report / run_log
```

The worker does small scoped work.

The auditor checks the worker output against the original mission.

The harness prevents unsafe execution until explicit approval, bounded scope, artifact safety, and no-call or live-call policy checks have passed.

AICO's strength is not many skills, agents, or automations. AICO's strength is to block before calling, audit after calling, and not hide failure.

## Relationship To Reference Projects

### VibeLabs

VibeLabs is useful as a reference for tasking UX. AICO should not copy skill-pack branding or compete on skill count.

AICO should extract:

- Mission interview patterns.
- `mission.md` templates.
- Policy pack templates.
- Task clarification prompts.
- Operator-facing task UX.

In AICO, these improve how a rough goal becomes a safe `mission.md`.

### multi-agent-starter

multi-agent-starter is useful as a reference for file-based multi-agent operating structure.

AICO should extract:

- Re-entry protocol.
- Acceptance ladder.
- Adapter registry as a data structure.
- Worker brief structure.
- Update mode.
- File-based handoff patterns.

The most directly useful idea is the acceptance ladder:

```text
L1: schema / artifact validity
L2: no-call dry-run
L3: controlled single-call live smoke
L4: negative safety tests
```

This maps naturally to AICO's current no-call and live-call gate progression.

### Ponytail

Ponytail is useful as a reference for preventing AI overbuilding. The useful direction is to write less code, reuse existing code, avoid unnecessary abstraction, delete overbuilt parts, prefer stdlib/native solutions, and block YAGNI expansion.

AICO should extract:

- Minimality ladder.
- Overbuild audit.
- Delete / stdlib / native / YAGNI / shrink review tags.

This should become part of the auditor layer as `overbuild_risk` or `ponytail_audit`. It must not replace correctness, safety, or mission compliance review.

The Ponytail-style audit asks:

- Was this work necessary?
- Did the worker create too much?
- Can this be reduced?
- Can existing code or stdlib do it?
- Did the worker add abstractions that the mission did not require?

Possible audit tags:

- `delete`
- `stdlib`
- `native`
- `yagni`
- `shrink`
- `reuse_existing`
- `too_many_files`
- `unneeded_abstraction`

## Positioning

AICO should be positioned as an AI work operating harness that breaks a mission into work orders, dispatches small worker tasks, audits worker outputs, and blocks dangerous execution until explicit approval and safety checks pass.

Comparison:

```text
VibeLabs              = skill / education / tasking templates
multi-agent-starter  = multi-agent work folder generator
Ponytail             = anti-overbuild coding policy
AICO                 = approval / audit / no-call / controlled-call harness
```

AICO should not compete on:

- Number of skills.
- Number of agents.
- Automatic coding claims.
- GUI-first experience.
- Automatic parallel development.

AICO should compete on:

- Clear mission contracts.
- Safe dispatch boundaries.
- Auditable artifacts.
- Explicit approval gates.
- No-call default behavior.
- Controlled live-call transition.
- Failure visibility.
- Minimal worker authority.

## Structures Worth Adding

These structures are worth adding only in controlled phases.

### mission_interview

Purpose: turn a rough user goal into a clear `mission.md`.

Rules:

- No execution.
- No worker dispatch.
- No file mutation by workers.
- No shell.
- No network.

Output:

- `mission.md` candidate.
- Mission assumptions.
- Missing constraints.
- Risk notes.
- Acceptance criteria.

### skill_registry

Purpose: define reusable task templates. AICO skills are task templates, not executable plugins by default.

Examples:

- `repo_review`
- `pdf_to_excel`
- `code_repair`
- `phase_review`
- `completion_review`
- `artifact_safety_review`

A skill may define:

- Mission template.
- Required inputs.
- Allowed files.
- Forbidden actions.
- Expected artifacts.
- Auditor checklist.
- Acceptance ladder.

### policy_pack

Purpose: attach safety and operating policy to a mission or work order.

Initial policy packs:

- `no_call_default`
- `local_file_only`
- `one_call_live_smoke`
- `repo_patch_with_tests`
- `overbuild_minimality`

Policy packs must be explicit data, not hidden hooks.

### acceptance_ladder

Purpose: separate artifact existence from dry-run behavior, live boundary behavior, and bad-input blocking.

Recommended ladder:

```text
L1: schema / artifact validity
L2: no-call dry-run
L3: controlled single-call live smoke
L4: negative safety tests
```

### ponytail_audit

Purpose: prevent overbuilding before and after worker execution.

Before worker dispatch:

- Is this worker task necessary?
- Can this be answered by reading existing files?
- Can this be done by editing fewer files?
- Can this be delayed?

After worker result:

- Did the worker create too much?
- Did it add unnecessary abstractions?
- Can anything be deleted?
- Did it ignore existing code?
- Did it violate the mission scope?

## Things AICO Must Not Copy Too Early

AICO should not adopt the following before the controlled live-call boundary is proven:

- Skill count competition.
- GUI-first development.
- `call_worker.sh`-style real dispatcher cloning.
- Direct Claude/Codex/Gemini CLI integration.
- Worker file modification authority.
- Worker shell execution authority.
- External repo write scope.
- Hidden hook/context injection.
- Automatic parallel development.
- Repo clone.
- GitHub Issue automation.
- Automatic PR or merge.

The current P3 boundary remains intact:

- No worker file modification authority.
- No worker shell authority.
- No web search.
- No external URL access.
- No repo clone.
- No GitHub Issue integration.
- No CLI agent orchestration.
- No automatic PR or merge.

## Meaning Of No-call Phases

The no-call phases were meaningful. They established L1 and L2 safety:

- Artifact schemas exist.
- Approval gates exist.
- No-call invariants are enforced.
- Artifact safety scanning exists.
- Execution boundaries are blocked.
- `call_model` stays at 0.
- `live_call_allowed` stays false.
- Provider SDK imports are forbidden.
- Env value reads are forbidden.
- Network calls are forbidden.

AICO should not remain no-call forever. The acceptance ladder should be:

```text
no-call = L1/L2 safety proof
controlled single-call = L3 live boundary proof
negative safety tests = L4 bad-input blocking proof
```

## Next Direction

After P3V completion review, the next meaningful step is not another broad no-call document phase.

The next meaningful step is:

```text
P3W: controlled single-call live smoke
```

P3W is not running AICO for real. P3W is not dispatching a worker pool. P3W is not performing useful work. P3W is only a proof that the live-call boundary behaves correctly once.

P3W requires a separate explicit approval phase before any actual call.

## P3W Controlled Single-call Live Smoke Constraints

P3W should use:

- `provider`: 1
- `model`: 1
- `key_slot`: 1
- `worker`: 1
- `max_model_calls`: 1
- `retry`: 0
- `reserve`: false
- `fallback`: false
- `second_call`: false

P3W must prohibit:

- File modification by worker.
- Shell execution.
- Web access.
- Repo clone.
- GitHub integration.
- External write scope.
- Multi-worker dispatch.
- Parallel execution.
- Repair loop.
- `semantic_preflight`.
- Raw output persistence.

The mission should be a toy text task. The goal is not final report quality. The goal is to verify:

- The key slot can be used once.
- The provider boundary can make exactly one call.
- `model_call_count` increments to exactly 1 and stops.
- Retry, reserve, and fallback do not occur.
- Raw output is not stored.
- Masked summary is stored.
- `call_attempt_summary` is correct.
- `live_smoke_result` is correct.
- `artifact_safety_report` is correct.
- Failure paths remain safe.

## P3W Success Criteria

P3W success means:

- One and only one provider call happened.
- No second call happened.
- No retry happened.
- No reserve key was used.
- No fallback provider was used.
- No shell was used.
- No file modification occurred.
- No raw secret was stored.
- No raw output was stored.
- Artifacts were generated safely.
- Artifact safety scan passed.
- `call_attempt_summary` matches actual call count.
- `live_smoke_result` is bounded and masked.

P3W failure is acceptable if it fails safely. A safe failure is better than an uncontrolled success.

## Final Direction

AICO should move forward as:

```text
mission interview
-> policy pack
-> work order
-> no-call validation
-> controlled single-call
-> auditor review
-> negative safety tests
-> broader worker orchestration only after the boundary is proven
```

The correct long-term direction remains:

```text
AICO is not a system for calling more AI.
AICO is a system for deciding when AI is allowed to be called.
```
