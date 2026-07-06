# P4A Mission Interview

## Purpose

P4A mission_interview turns a rough mission request into a deterministic no-call mission brief before any worker dispatch or live execution is considered.

It helps identify objective gaps, missing files, output format, success criteria, constraints, and safety boundaries.

## Scope

P4A includes:

- mission interview input and output schema.
- rule-based mission text normalization.
- clarification question generation.
- mission risk flag generation.
- normalized mission brief generation.
- JSON artifact writing with artifact safety validation.
- no-call invariants.

## Non-goals

P4A does not:

- call an LLM or provider.
- load keys or env values.
- import provider SDKs.
- access network or web.
- dispatch workers.
- run manager/auditor flows.
- grant file write or shell authority to workers.
- implement policy_pack, skill_registry, acceptance_ladder, or ponytail_audit.

## Input Schema

`MissionInterviewInput` fields:

- `mission_text`: user-provided mission text.
- `source_path`: optional metadata path for the mission source.
- `user_context`: optional non-secret metadata.
- `mode`: `draft` or `review`.
- `max_questions`: maximum clarification questions to return.

## Output Schema

`MissionInterviewResult` fields:

- `schema_version`: `p4a_mission_interview.v1`.
- `result`: `ready`, `needs_clarification`, or `blocked`.
- `normalized_brief`: normalized mission brief.
- `questions`: clarification questions.
- `risk_flags`: detected risks.
- `no_call`: always `true`.
- `worker_orchestration`: always `false`.
- `live_call_allowed`: always `false`.
- `call_model_count`: always `0`.

## Decision Rules

- `blocked`: one or more `BLOCKING` risks are present.
- `needs_clarification`: no blocking risk exists, but required questions, missing information, broad scope, or high/medium risk remains.
- `ready`: no blocking risk, no required questions, and objective/output/success criteria are sufficiently specified.

## Risk Flags

P4A detects:

- `live_call_requested`
- `worker_orchestration_requested`
- `file_write_requested`
- `shell_requested`
- `web_requested`
- `repo_or_github_requested`
- `parallel_requested`
- `secret_or_env_requested`
- `unclear_objective`
- `missing_output_format`
- `missing_success_criteria`
- `broad_scope`
- `destructive_action`

Blocking risks include live calls, worker orchestration, shell execution, secret/env/key access, and destructive action requests.

## Clarification Questions

Question categories:

- objective
- input_files
- output_format
- success_criteria
- constraints
- safety_boundary
- deadline_or_priority
- unknowns

Questions are prompts to the user, not execution instructions.

## No-call Invariants

P4A always keeps:

- `no_call=true`
- `worker_orchestration=false`
- `live_call_allowed=false`
- `call_model_count=0`

These outputs do not grant worker execution authority.

## Artifact Safety

`write_mission_interview_result` validates the result before writing JSON. It blocks raw key-like strings, bearer tokens, private key blocks, env dump patterns, endpoint URLs, raw output fields, provider response fields, and token usage dumps.

## Tests

P4A tests cover:

- ready mission.
- vague mission clarification.
- missing output format.
- missing success criteria.
- input file ambiguity.
- max question limits.
- blocking risks.
- high risks.
- broad scope.
- no-call invariants.
- JSON writing.
- raw leak rejection.
- AST/source checks for no env read, no provider SDK import, no network call, and no `call_model` execution.

## Next Phase

Next phase should be P4A completion review.

P4A completion review should decide whether mission_interview is ready to remain as the first P4 no-call layer and whether P4B should address policy_pack, acceptance_ladder, or another data-only structure.
