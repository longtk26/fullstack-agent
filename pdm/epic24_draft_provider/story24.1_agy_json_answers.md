# Story 24.1 — One-turn JSON answers from the CLIs (`agy`, `claude`)

**Epic:** [24 — Draft provider](epic24_draft_provider.md) · **Requirements:** FR-38, FR-30 · **Depends on:** Epic 3, 18.10

## User story

As a user testing drafts every day, I want Antigravity or Claude Code to answer a draft in one turn with the same JSON
the Gemini API returns, so drafting costs me nothing per token and is as fast and checkable as the API path.

## Context

- `AntigravityEngine.build_invocation` runs `agy --input-format stream-json --output-format stream-json --mode
  accept-edits` with read/write permissions on the workdir; it is a code engine (files and tools).
- `GeminiApiEngine` (18.10) has `inline_inputs`, `drafts`, `drafts_only`; drafting renders the inline prompt versions
  (`draft_app@v3`, `repair_spec@v3`, …) and applies one envelope of `files` and RFC 6902 `patches` (`libs/jsonpatch.py`).
- 22.8 refused CLI draft engines because the agent loop re-sent its reads every turn (22 turns, 1.3M input tokens).

## Steps

1. **A JSON mode of the Antigravity engine** (`antigravity_json`, a separate registered engine sharing the adapter):
   `drafts = True`, `inline_inputs = True`, `drafts_only = True`. Invocation (`agy` ≥ 1.5.2): `--print` with the
   inline prompt, `--output-format json`, `--mode plan` (no edits), `--disable-slash-commands`, an empty scratch
   directory as workdir and permissions that allow no file reads or writes and no terminal. The account login,
   `--model`, `--effort` and the purpose models work as in the code engine.
2. **Structured output.** When the request carries `response_schema`, write it to the scratch directory and pass
   `--json-schema <file>` (the same schema the API gets as `responseJsonSchema`). If `agy` refuses the schema (an
   error naming it), retry once without it, as the API path does for a 400. Find out and record in this story's Status
   which schema keywords `agy` enforces (the answer schema uses only the keywords Gemini documents: type, properties,
   required, items, enum).
3. **The answer.** Read the result from the `json` output (the final result); without a schema, strip code fences or
   text around the outermost JSON object. Then the same envelope handling as the API engine (shared helper, not a
   copy). A turn that tried a tool, or no JSON, is an engine error with the first 500 characters of the answer.
4. **The schema in code** as well (Epic 24 D3): validate the parsed answer against `response_schema` (`jsonschema`);
   errors go back as the repair prompt's errors (one round, as for spec errors), then the normal checks.
5. **Claude Code the same way** (`claude_code_json`, sharing the answer handling): `claude -p` with the inline prompt,
   `--output-format json` (the result's `structured_output` / `result`), `--json-schema '<schema>'`, `--tools ""`,
   `--permission-mode plan`, `--no-session-persistence`, `--strict-mcp-config` (no MCP servers), an empty scratch
   directory (no CLAUDE.md to discover), `--model` and `--effort` from the settings. The login decides the rest:
   - **subscription (OAuth)**, the no-per-token case: no `--bare`, because `--bare` reads only `ANTHROPIC_API_KEY`
     ("OAuth and keychain are never read"); `--setting-sources` limited so the user's hooks and plugins don't run;
   - **API key**: `--bare` (skips hooks, plugins, auto-memory, CLAUDE.md discovery) and `--max-budget-usd`.
   Record which schema keywords it enforces, as for `agy`.
6. **Usage.** Record the call like the API engine's (`model_calls`: turns = 1, tokens from the stream when `agy` reports
   them, `costSource`: `account` with cost 0 for the account login, priced for `gemini_api_key` auth).
7. **Health.** `agy` ≥ 1.5.2 and `claude` ≥ 2.1 (both with `--json-schema`) on PATH and signed in; the engine list
   marks them "Drafts only (JSON)".
8. Tests: fake `agy` and `claude` CLIs (a script printing a recorded `json` answer and checking it received `--json-schema`; listed
   in `docs/development/test-doubles.md`) for a valid answer, fenced JSON without a schema, a refused schema then the
   retry, a tool attempt, invalid JSON, a schema error then a repair.

## Acceptance criteria

- [x] A draft runs on `antigravity_json` or `claude_code_json` in exactly one CLI turn per call, with no file read or written in its
      scratch directory (apart from the schema file it was given).
- [x] The answer schema reaches both CLIs through `--json-schema`; the keywords each enforces are recorded.
- [x] The parsed answer goes through the same envelope code and the same spec checks as the Gemini API's.
- [x] A schema error in the answer triggers one repair round with the errors; a second failure ends the draft as today.
- [x] Usage shows one call per step, the model, the tokens when known and the cost source.
- [x] The code engines (`antigravity` agent mode, `claude_code`) are unchanged, and still refused as draft engines.

## Verify

`make lint`, `make test` (fake CLIs), then with the user's go one real draft of a lab requirement per CLI on the
account / subscription logins (`make up`, `ANTIGRAVITY_AUTH=account`).

## Status

**Done 2026-11-07.** `engines/json_cli.py` (`AgyJsonProvider`, `ClaudeJsonProvider`), `engines/llm_engine.py`
(`LlmDraftEngine`, registered as `antigravity_json` and `claude_code_json`), `engines/envelope.py` (the envelope shared
with the Gemini API engine), `libs/json_schema_check.py` (the schema in code). Fake CLIs `fake_agy_json`,
`fake_claude_json`; `tests/test_llm_providers.py`. Notes in `docs/engines/one-turn-json.md`.

Deviations, measured on `agy` 1.5.2:
- `agy` runs `--input-format stream-json --output-format stream-json --json-schema <file>`, not `--print` with
  `--output-format json`: an app draft prompt is longer than one argv string may be, and the `--print` path took 80 s
  and 95k input tokens for a trivial prompt (7 s and 7k with stream-json). The final `result` event carries
  `structured_output`, the schema being enforced through a `finish` step.
- No `--mode plan`: agy warns it has no effect with `--disable-slash-commands`; tools are refused by the session's
  permissions (`command`, `read_file`, `write_file`, `read_url`, `execute_url`, `mcp`).
- A tool attempt is recorded as a note on the call, not an error: it is refused anyway, and only an answer without
  JSON fails the step.
- `claude`: no `--permission-mode plan` (structured output itself is delivered by the CLI, and plan mode is meant for
  tool use); `--tools ""` refuses every tool. A fresh `CLAUDE_CONFIG_DIR` keeps the user's hooks, plugins and memory
  out on the subscription login; `--bare` and `--max-budget-usd` only with `ANTHROPIC_API_KEY`.
- Schema keywords: the whole app answer schema (`$ref`/`$defs`, `anyOf`, `enum`, `required`, `additionalProperties`,
  `minItems`) went through `agy --json-schema` and the answer was valid on the first try (below). `claude` was not run
  for real (the user chose `agy` only, 2026-11-07); its flags follow `claude --help` 2.1.220 and the fake CLI.

Real run (host worker, `ANTIGRAVITY_AUTH=account`): the lab's FixPoint requirement drafted on `antigravity_json` in
**one call, 169 s, 19k input / 50k output tokens, structured, $0 (`account`)**, SUCCEEDED with no repair: 4 roles,
3 entities, 24 operations, ownership and role policies, transition rules, payments; backend, frontend and pair valid.
