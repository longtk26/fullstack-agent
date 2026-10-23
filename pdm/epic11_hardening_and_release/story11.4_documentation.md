# Story 11.4 — Documentation

**Epic:** [11 — Hardening](epic11_hardening_and_release.md) · **Requirements:** §12.11

## User story

As a new user, I want to go from clone to a running generated backend by following one README.

## Acceptance criteria

- [ ] Root `README.md`: prerequisites (Docker, engine credentials), `.env` setup, `make up`, first generation through the UI
      and through curl, preview usage, and `make dev` for development.
- [ ] `docs/backend-spec.md` (field reference + examples), `docs/architecture.md` (diagrams from these epics,
      kept up to date), `docs/engines/{claude-code,antigravity}.md`, `docs/operations.md` (limits, retention, cleanup).
- [ ] Agent API OpenAPI available at `/docs`, with every endpoint described.
