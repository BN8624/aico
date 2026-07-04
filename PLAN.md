# PLAN

1. Create the required document set and verify `AGENTS.md` and `CLAUDE.md` are byte-identical.
2. Implement a standard-library Python dry-run harness that creates `runs/<run_id>/` artifacts from deterministic scenario fixtures.
3. Enforce deterministic preflight only, including schema, forbidden action, permission, path scope, secret, and budget checks.
4. Add scenario tests for pass, conditional, fail, needs_decision, config_error, budget_exceeded, and mid_flight_failure.
5. Verify zero API calls, zero LLM calls, report mutual exclusion, failure logging, secret exclusion, and required document presence.
6. Update `HANDOFF.md` and `CONTEXT_NOTES.md` with final state and next work.
