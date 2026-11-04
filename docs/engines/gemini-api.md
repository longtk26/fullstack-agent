# Gemini API engine (`gemini_api`)

Story 18.10. Drafts specs from a requirement with **one `generateContent` request per step**: no agent loop, no
files, no tools. It cannot write a project: the engine list marks it `draftsOnly`, the Options page offers it only
as the *Draft engine*, and a code purpose sent to it is refused.

## How a step runs

1. `drafting.py` sees the engine's `inline_inputs` and renders the inline prompt versions (`draft_frontend_spec@v10`,
   `draft_spec@v4`, `repair_spec@v3`, `repair_direction@v2`): the requirement, the schema digests, an example spec,
   the section catalogue and the design facts travel in the prompt (the same `.bga/` files the CLI engines read).
2. The engine posts the prompt to `https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent`
   with `responseMimeType: application/json`, `maxOutputTokens` (`GEMINI_API_MAX_OUTPUT_TOKENS`, default 65536) and,
   when set, `thinkingConfig.thinkingBudget` (`GEMINI_API_THINKING_BUDGET`).
3. The answer is one JSON envelope: `{"files": {"frontend-spec.json": {...}, "notes.json": {...}}, "patches":
   {"backend-spec.json": [RFC 6902 operations]}, "message": "..."}`. Files are written into the draft's work
   directory; patches apply to the JSON files already there (`src/libs/jsonpatch.py`). A patch that does not apply is
   skipped and reported in the message; the operations before it still apply.
4. The usual checks run on the files (validation, pair check, difference test, autofix); a repair round sends the
   errors with the current files and asks for patches. A round whose errors are exactly the previous round's ends
   the loop ("changed nothing"), instead of buying the same answer again.

Each attempt is a `ModelCall` priced from `pricing.py` (`gemini-3.8-flash`); the draft's `usage` and the trace tab
show tokens and cost. 429 and 5xx answers retry (3 attempts, backoff); an answer that is not JSON is asked again
once with the parse error; `MAX_TOKENS` is `limit_exceeded`; a safety block is a `crash`. The raw answers (key
redacted) are in `<draft>/state/logs/<invocation>.gemini_api.jsonl`.

Epic 21 adds `draft_tree@v1`: one request per page (and one for the chrome) after the spec is valid, run in parallel
(`FRONTEND_TREE_CONCURRENCY`, default 4); the answer is `{"files": {"trees/<page>.json": {"tree", "css"}}}`.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | — | Shared with Antigravity's `gemini_api_key` auth; without it the engine is unavailable |
| `DRAFT_ENGINE` | empty | The engine that drafts when the request names none: `gemini_api` when the key is set, else `DEFAULT_ENGINE` |
| `GEMINI_API_MODEL` | `gemini-3.8-flash` | The API model id (`GET /v1beta/models` lists them; agy's `-medium` suffix is not an API id) |
| `GEMINI_API_THINKING_BUDGET` | empty | Thinking tokens per request; empty = the model's default |
| `GEMINI_API_MAX_OUTPUT_TOKENS` | 65536 | Output cap per request |
| `GEMINI_API_TIMEOUT_SECONDS` | 600 | Per request |

Health: `GET /v1beta/models/<model>` with the key, cached for 10 minutes. Which worker runs it: any worker whose
`WORKER_ENGINES` lists `gemini_api` (the Docker worker when a host worker runs Antigravity, see the Makefile).
