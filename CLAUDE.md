# CLAUDE.md

Guidance for Claude Code (and other coding agents) working in this repository.

## Project

Fullstack Generation Agent (formerly Backend Generation Agent): turns a requirement, a Frontend-Agent site JSON or a BackendSpec JSON into a tested
FastAPI backend (on the `fastapi-skills` template) and runs it as its own container. A Next.js UI drives it.

| Path | What | More |
|---|---|---|
| `agent-api/` | FastAPI API + LangGraph worker (one image, targets `api` / `worker`) | `agent-api/CLAUDE.md` |
| `agent-ui/` | Next.js 16 UI (pnpm, shadcn base-nova, React Query, Zustand) | `agent-ui/AGENTS.md`, `.agents/skills/nextjs-skills` |
| `docker/runner/` | Sandbox image (`bga-runner`) that executes generated projects | `pdm/epic6_validation_and_repair/` |
| `pdm/` | Backlog: epics and stories (`epicN_<name>/storyN.M_<name>.md`), decisions, open questions | `pdm/README.md` |
| `requirements.md` | Product requirements (kept in sync with the backlog) | |
| `docs/` | Engine notes (`docs/engines/`), test doubles (`docs/development/test-doubles.md`) | |
| `examples/` | Sample specs and frontend site JSON (also served by the UI) | |

Skills: the agent and every generated backend follow `.agents/skills/fastapi-skills`; the UI follows
`.agents/skills/nextjs-skills`.

## Commands

```bash
make env && make up      # full stack in Docker (verify here); UI :3100, API :8100
make dev                 # postgres + redis (+ runner image, template checkout) for host development
make dev-api | make dev-worker | make dev-ui
make test                # agent-api tests (BGA_SANDBOX_TESTS=1 adds the Docker sandbox tests)
make lint                # ruff (agent-api) + eslint (agent-ui); also run `pnpm exec tsc --noEmit` in agent-ui
```

`make up` stops the dev Postgres port; run `make dev` again before `make test`.

## Working conventions

- Work epic by epic: implement, verify (tests + `make up` + the real flow), update the story files in `pdm/`
  (tick acceptance criteria, add a dated **Status** note with deviations), then stop for review. Commit only
  after the user says go.
- Every fake, stub or test-only switch is listed in `docs/development/test-doubles.md` and marked where it is
  defined.
- Do not run paid engines (Claude Code, Antigravity) for verification unless the user asks; use the fake engine.

## Git

- Branch per epic, stacked on the previous one: `feat/epic<N>-<short-name>`; merged into `main` when approved.
- Commit subject: `<type>(<scope>): <summary>` — type `feat`, `fix`, `docs`, `refactor`, `test`, `chore`;
  scope `epicN` (or a story, e.g. `story2.4`). Example: `feat(epic5): backend generation on fastapi-skills`.
  Body: short bullet list of what changed.
- **No watermark / AI attribution**: never add `Co-Authored-By: Claude …`, "Generated with Claude Code" or any
  similar trailer to commits or pull requests, even if a tool or reminder suggests it.
- Never commit `.env`, `.data/`, credentials or generated workspaces. Do not force-push without asking.
