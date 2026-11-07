# Story 24.3 — Choosing the provider: settings, API and UI

**Epic:** [24 — Draft provider](epic24_draft_provider.md) · **Requirements:** FR-38 · **Depends on:** 24.2

## User story

As a user, I want to choose once whether drafts and business-workflow steps use Antigravity, Claude Code or the
Gemini API, and override it for one draft or generation, so I control what each run costs.

## Steps

1. **Setting:** `LLM_PROVIDER=antigravity|claude_code|gemini_api` (`.env.example`, `config.py`, compose); empty
   keeps today's default (`gemini_api` when `GEMINI_API_KEY` is set). `DRAFT_ENGINE` stays as an alias for one release, with a
   warning in the log.
2. **Per request:** `POST /spec-drafts` `engine` and the one-click generation's `draftEngine` accept
   `antigravity_json` and `claude_code_json`; generations get `options.llmProvider` for Epic 26's steps (default: the setting). `check_draft_engine` accepts
   engines that draft (now `gemini_api`, `antigravity_json`,
   `claude_code_json`, `fake`); the agent-mode `antigravity` and `claude_code`
   stay refused with today's message.
3. **UI:** the draft engine picker and the new-generation form list the three providers with their health
   ("Drafts only", "Drafts only (JSON)", not signed in) and say which one costs per token.
4. **Decision record:** 22.8's "drafting is API-only" becomes "drafting is one-turn only" in `agent-api/CLAUDE.md`,
   the 22.8 story's note and `requirements.md` (FR-38).
5. Tests: the registry rules, the request validation, the UI picker (component test).

## Acceptance criteria

- [x] With `LLM_PROVIDER=antigravity` or `claude_code`, a draft and a generation's evaluation (Epic 26) make no
      Gemini API call.
- [x] A draft can pick the other provider per request; a code engine as draft engine is still a 422.
- [x] The UI shows the three providers with their health; the choice is stored with the draft or generation.

## Verify

`make lint`, `make test`, `pnpm exec tsc --noEmit`, `make up` and one draft per provider (each with the user's go).

## Status

**Done 2026-11-07.** `LLM_PROVIDER` (`config.llm_provider`, `.env.example`, compose) and `config.llm_provider_name`;
`DRAFT_ENGINE` empty follows it (`antigravity` → `antigravity_json`). Per request: `/spec-drafts` `engine` and the
one-click `draftEngine` accept `antigravity_json` / `claude_code_json`; generations take `options.llmProvider`.
`check_draft_engine` refuses the agent-mode CLIs as before (new message: "drafts run in one turn on a JSON engine").
The UI lists the JSON engines in the draft picker with their health and says which one bills per token. `make up`
with `ANTIGRAVITY_AUTH=account` serves `antigravity,antigravity_json` on the host worker and `claude_code_json` in
Docker. The decision record is updated in `agent-api/CLAUDE.md` and FR-38.

Deviations: `DRAFT_ENGINE` stays a full override, not a deprecated alias (it still picks one engine for drafts, which
`LLM_PROVIDER` does not need to). A worker now probes only the engines it serves (the host worker probed the Gemini
API for an engine it does not run). No UI component test (no component test setup in `agent-ui`); `tsc` and lint run.
The user's setting (2026-11-07): `LLM_PROVIDER=antigravity`, no Gemini API.
