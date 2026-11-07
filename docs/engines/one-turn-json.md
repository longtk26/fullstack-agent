# One-turn JSON providers (Epic 24)

Every **LLM-only step** (spec drafting and its repairs; Epic 26's workflow discovery, expectations, binding, screen
judging and summary) asks a model once and gets one JSON object back. `LLM_PROVIDER` picks who answers:

| Provider | Draft engine | How | Cost |
|---|---|---|---|
| `antigravity` | `antigravity_json` | one `agy` turn: `--input-format stream-json --output-format stream-json --json-schema <file> --disable-slash-commands`, the prompt on stdin, deny-all permissions, an empty scratch directory | `ANTIGRAVITY_AUTH=account`: none per token (recorded as `account`, $0) |
| `claude_code` | `claude_code_json` | one `claude -p --output-format json --json-schema '<schema>' --tools "" --strict-mcp-config --no-session-persistence`, the prompt on stdin, a fresh `CLAUDE_CONFIG_DIR`, an empty scratch directory; `--bare` and `--max-budget-usd` only with `ANTHROPIC_API_KEY` | subscription login: $0 (`account`); API key: the reported cost |
| `gemini_api` | `gemini_api` | one `generateContent` request with `responseJsonSchema` | per token (estimated) |
| `fake` | `fake` | `engines/fake_llm.py` (tests only) | $0 |

Code: `engines/llm.py` (`LlmProvider.json`: ask, check against the schema in code with `libs/json_schema_check.py`,
ask once more with the errors), `engines/json_cli.py` (the CLIs), `engines/gemini_api/llm.py`,
`engines/llm_engine.py` (`LlmDraftEngine`: a provider as a draft engine: the envelope of `files` + `patches` applied
by `engines/envelope.py`, as the Gemini API engine does). Code generation stays on the CLI engines in agent mode.

## Measured (agy 1.5.2, 2026-11-07)

- `--output-format json` with `--print` works too (`structured_output`, `usage`), but the prompt is an argv string
  (an app draft prompt is larger than Linux allows for one argument) and a trivial prompt took 80 s and 95k input
  tokens; `stream-json` on stdin took 7 s and 7k tokens for the same prompt.
- The final `result` event carries `structured_output`; the schema is enforced through a `finish` step, which is not
  a tool the permissions see.
- `--mode plan` has no effect with `--disable-slash-commands` (agy warns), so tools are refused by the permissions
  (`command(*)`, `read_file(*)`, `write_file(*)`, `read_url(*)`, `execute_url(*)`, `mcp(*)`). An image step allows
  `read_file` on its scratch directory only.
- The account login lives in the desktop keyring: `antigravity_json` runs on the host worker (`make up` with
  `ANTIGRAVITY_AUTH=account` serves `antigravity,antigravity_json` there).
