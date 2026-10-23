# Story 3.4 — Versioned prompts & engine context files

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08 (what Claude is given), NFR 8.4 (prompts version-controlled)

## User story

As a maintainer, I want every prompt and convention the engine sees to live in the repo with a version, so
that generation behaviour is reviewable and reproducible.

## Acceptance criteria

- [ ] `agent-api/prompts/<purpose>/v1.md` (Jinja2) for: `draft_spec`, `generate_database`,
      `generate_backend`, `generate_tests`, `repair_code`. A shared `conventions.md` holds only the **additions** to
      fastapi-skills: `operation_id` rule, error envelope, no hardcoded secrets, spec-to-module naming. It does not restate the skill.
- [ ] Each prompt receives: a reference to the validated spec (file path in the workspace, not inlined if large),
      plan path, permitted directory, current file tree, required scope (which files and entities), and
      validation errors (repair only).
- [ ] **The fastapi-skills skill is the generation foundation (decision Q1).** Before each call the workspace gets:
  - the skill copied from the worker image (pinned with the agent repo) to `.claude/skills/fastapi-skills/` for Claude Code,
    and to the skills location confirmed in spike 3.3 for Antigravity (inlined into its context file if there is none);
  - the template's own `CLAUDE.md` kept, plus a generated section appended from `conventions.md`. Antigravity gets
    the same content in its context file.
  - Each prompt tells the engine to follow the skill's "Adding a New Feature Module" steps and 6-pillar checklist.
- [ ] Skill files and engine context files are excluded from `backend.zip` (7.1) except the template's `CLAUDE.md`.
- [ ] The skill's content hash is recorded with the prompt version, so generations can be traced to the skill revision.
- [ ] `prompt_id@version` and its content hash are recorded on each `cli_invocations` row and in trace metadata.
- [ ] Spec text is inserted inside clear delimiters and the prompt states it is data, not instructions
      (NFR 8.1, untrusted input).
