# Epic 24 — Draft provider: Antigravity or Claude Code (one-turn JSON), or the Gemini API

## Overview

Proposed and **done 2026-11-07** (Status in each story; the user's default: `LLM_PROVIDER=antigravity`). Since Story 22.8, drafting is API-only: only the Gemini API engine (and the
fake) may draft. The reason was cost and time: `agy` drafted as an agent loop that read files, and one app draft
took 22 turns and 1.3M input tokens ($0.53), because every turn re-sends what it read. But the Gemini API bills every
draft, repair and (with Epic 26) every evaluation call per token, which is too much for the user's daily testing.

This epic adds the two CLIs back as **draft providers in a one-turn JSON mode**: `agy` (Antigravity) and `claude`
(Claude Code). Each gets the same inline prompt the API engine gets (every input in the prompt, no files, no tools),
answers once with structured output against the same answer schema, and returns the same JSON envelope (`files` +
`patches`), validated in code as well. On the user's account / subscription logins they have no per-token cost. One
setting chooses the provider for **every LLM-only step**: spec drafting and its repairs, and Epic 26's workflow
discovery, expectations, binding, screen judging and summary. Code generation stays on the CLI engines as today.

| Finding (2026-11-07) | Effect |
|---|---|
| `EngineRegistry.check_draft_engine` refuses every engine without `drafts` (22.8); `AntigravityEngine` runs `--mode accept-edits` with read/write permissions on the workdir | `agy` cannot draft at all today |
| `GeminiApiEngine` has `inline_inputs`, `drafts`, `drafts_only`; drafting renders inline prompt versions and parses one JSON envelope (`engines/gemini_api/`, `drafting/drafts.py`) | the one-turn contract already exists; a second engine can implement it |
| The answer schema (`drafting/answer_schema.py`) is sent as `responseJsonSchema`. `agy` 1.5.2 has `--json-schema` ("a JSON schema string or path to a schema file to enforce structured output"; with stream-json, on the final result), `--output-format json`, `--mode plan` and `--disable-slash-commands` | `agy` can take the same schema as the API; code still checks it (D3) |
| Claude Code 2.1.220 has `--print --output-format json` (one result), `--json-schema <schema>`, `--tools ""` (no tools), `--permission-mode plan`, `--strict-mcp-config`, `--no-session-persistence`; `--bare` (no hooks, plugins, CLAUDE.md discovery, auto-memory) works only with `ANTHROPIC_API_KEY`, never with the subscription login | `claude` can answer in the same one-turn JSON mode; on a subscription it is isolated without `--bare` |
| The lab (`lab/business-value/`, 2026-11-06/07) made ~120 Gemini calls for discovery, expectations, binding and judging across 6 runs | Epic 26 multiplies the per-token cost unless those calls can use `agy` too |

**Requirements:** FR-38 (new, proposed: draft provider), FR-30 (spec drafting), FR-37.

## Decisions (proposed 2026-11-07)

| # | Decision | Instead of |
|---|---|---|
| D1 | **One-turn JSON, never an agent loop, for drafting.** A CLI provider gets the inline prompt, no tools, an empty scratch directory, and answers once. Refines 22.8: the agent-loop draft stays refused | A CLI reading files over many turns (22.8's 22 turns, 1.3M tokens) |
| D2 | **One provider switch for every LLM-only step** (`LLM_PROVIDER=antigravity\|claude_code\|gemini_api`, per request too) | A setting per step |
| D3 | **Structured output on every provider, and checked in code**: the same answer schema goes to the API as `responseJsonSchema` and to `agy` and `claude` as `--json-schema`; code validates every answer anyway; a schema the provider refuses is retried once without it | Trusting the model's JSON |
| D4 | **Same prompts, same envelope.** Every provider renders the inline prompt versions and answers `files` + `patches`; no provider-specific prompt unless a measured failure needs one | A prompt family per provider |

## Stories

| # | Story | Depends on |
|---|---|---|
| 24.1 | [One-turn JSON answers from the CLIs (`agy`, `claude`)](story24.1_agy_json_answers.md) | Epic 3, 18.10 |
| 24.2 | [One LLM provider for every LLM-only step](story24.2_llm_provider.md) | 24.1 |
| 24.3 | [Choosing the provider: settings, API and UI](story24.3_provider_setting.md) | 24.2 |
| 24.4 | [Measure the providers on the lab requirements](story24.4_measure_providers.md) | 24.3 |

## The flow after this epic

```
LLM-only step (draft, repair, discover, expect, bind, judge, summary)
      └─▶ LlmProvider.json(prompt, schema, images?)            (24.2)
             ├─ gemini_api: one generateContent request (responseJsonSchema as an extra)
             ├─ antigravity: one agy turn (--print, --output-format json, --json-schema, --mode plan)
             └─ claude_code: one claude turn (-p, --output-format json, --json-schema, --tools "")
                    inline prompt, no tools, scratch dir → the final result → JSON (24.1)
      ◀── checked against the schema in code (D3); a schema error → one repair round on the same provider
code generation ──▶ CLI engines (claude_code, antigravity in agent mode), unchanged
```
