# AICO Agent Rules

## Document Priority

1. `AICO_MASTER_CANON.md`
2. `AICO_V0_CANON.md`
3. `AGENTS.md` and `CLAUDE.md`
4. `HANDOFF.md`
5. `CONTEXT_NOTES.md`

## Working Rules

- Treat `AICO_MASTER_CANON.md` and `AICO_V0_CANON.md` as canon.
- Do not summarize or reinterpret canon documents when storing them.
- Keep v0 as a dry-run harness.
- Make zero API calls and zero LLM calls.
- Do not run `semantic_preflight`.
- Do not run repair loops.
- Do not grant workers file edit permission.
- Do not grant workers shell execution permission.
- Do not use external URLs, web search, or repo clone.
- Do not use 22 keys.
- Do not create a web dashboard.
- Record implementation decisions in `CONTEXT_NOTES.md`.
- Keep handoff status in `HANDOFF.md`.
