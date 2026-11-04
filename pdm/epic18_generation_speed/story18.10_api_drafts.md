# Story 18.10 — Spec drafts through the Gemini API (no agent loop)

**Epic:** [18 — Generation speed](epic18_generation_speed.md) · **Requirements:** FR-30 · **Depends on:** 2.4, 12.4,
20.4, 20.9

## User story

As a user, I want a requirement drafted into its specs in two to four minutes instead of eight to twelve, at the same
quality, so that I can try a requirement, read the result and try again without waiting most of a quarter hour.

## Evidence (2026-11-03, Antigravity on `gemini-3.8-flash-medium`)

| Draft | Draft call | Repairs | Total | Model calls | Input tokens | Output tokens | Cost |
|---|---|---|---|---|---|---|---|
| Static, "introduce Japanese" (`2c5eb097`) | 285 s | 29 s + 141 s | 455 s | — | — | — | — |
| Dynamic, gym (`8c6f72c1`) | 459 s | 87 s + 130 s | 676 s | 65 | 2 780 k (2 430 k cached) | 106 k | $0.84 |

- A draft is one agent session: the engine **reads** the inputs file by file (`.bga/`: requirement, schema digests,
  example spec, section catalogue, design fact pack), then writes `frontend-spec.json`, `backend-spec.json` and
  `notes.json`. Each turn re-sends the growing conversation, hence 34 model calls and 1.6 M input tokens for one
  draft.
- What it needs is small: prompt v9 (12.5 k chars), the two schema digests (17 k), one example spec (5–6 k), the
  section catalogue (4.5 k), the design fact pack (a few k) and the requirement: about 50 k characters, roughly
  15 k tokens. What it writes is small too: the gym's specs are 27 k characters together (about 8 k tokens), plus
  notes and three direction cards.
- A repair re-reads and rewrites whole files, although the errors name exact paths.
- The drafting code already does all the checking (validation, pair check, difference test, contrast, stock
  phrases, icons); the agent loop adds turns, not checks.
- `GEMINI_API_KEY` is already configured (Antigravity's `gemini_api_key` auth); `src/images/gemini.py` already
  calls the Generative Language API with `httpx`.

## Steps

1. **Engine.** A `gemini_api` engine (`src/engines/gemini_api/`) implementing `ICodeEngine`, so the drafting code and
   the registry stay as they are: `run()` sends one `generateContent` request (`httpx`, like the image adapter) with
   JSON output (`responseMimeType: application/json`, a response schema for the envelope only:
   `{"files": {"<name>": <object>}}`), writes each returned file into `workdir`, and fills `EngineResult` (status,
   duration, `changed_files`, usage with input / output / thinking / cached tokens, one `ModelCall`, cost through
   `pricing.py`). Errors map to the existing reasons: timeout, rate limit (429: retry with backoff, at most 3),
   blocked, malformed JSON (one retry with the parse error appended). The key is never logged (redaction).
   `health()` checks the key with a models request; `cancel()` cancels the request task.
2. **Inline inputs.** New prompt versions that carry the inputs instead of naming paths: `draft_frontend_spec@v10`,
   `draft_spec@v4`, `repair_spec@v3`, `repair_direction@v2` (released versions stay). `write_inputs` still writes
   `.bga/` (the CLI engines keep using it); the rendered prompt for `gemini_api` embeds the requirement, digests,
   example, catalogue and fact pack, each in a fenced, labelled block, and asks for the files as JSON objects. The
   full JSON Schemas are not sent (the digests are enough; the validators catch the rest).
3. **Repairs as patches.** `repair_spec@v3` gets the errors with their excerpts (as today) and returns RFC 6902 JSON
   Patch operations per file (`{"patches": {"frontend-spec.json": [...], "backend-spec.json": [...]}}`); code
   applies them. A patch that does not apply counts as that round's failure and the round's errors are sent again
   with the reason. Same for `repair_direction` (patches to `notes.json`'s cards).
4. **Stop on errors the engine cannot fix.** Before a repair round, split the errors: the ones in what the engine
   wrote go to `repair_spec`; the ones that come from our code (the contract built from the BackendSpec, files the
   generator owns, an autofix the validators undo) end the loop at once as a generator bug, with the errors in the
   draft's notes, instead of spending repair rounds on them. (Found 2026-11-03: two repair rounds, 3.6 minutes, on
   custom operations the contract had dropped; in generation, 30 minutes of frontend repairs on a generator-owned
   test file.)
5. **Settings.** `DRAFT_ENGINE` (engine for spec drafts; default `gemini_api` when `GEMINI_API_KEY` is set, else the
   generation engine as today), `GEMINI_API_DRAFT_MODEL` and an optional thinking budget, both in `config.py` with a
   comment and in `.env.example`. Generation keeps Antigravity / Claude Code: writing and fixing code needs an agent
   with files and tools. The model id and its price are confirmed with a models request when the story starts
   (agy's `gemini-3.8-flash-medium` is an agy alias, not an API id) and added to `pricing.py`.
6. **UI.** Options shows the draft engine next to the generation engine; the Requirement tab says which one drafts
   ("Drafting with gemini_api"). The fake engine stays selectable for both.
7. **Split if needed (measured, not by default).** One call drafts both specs, as today. If a dynamic draft's output
   exceeds the model's output limit or the measurement shows the backend half losing quality, draft the BackendSpec
   first and the FrontendSpec second with the contract built from it (the order the contract already follows).
8. **Observability.** Each call is a `tool` span under the draft trace and a record in the draft's `usage` (as
   today); the trace tab's Drafting Usage shows them.
9. **Tests and doubles.** The engine runs against `httpx.MockTransport` in tests (listed in
   `docs/development/test-doubles.md`, marked where defined): envelope written as files, usage and cost, 429 retry,
   malformed JSON retry, blocked response, timeout, cancel, patch application and a failing patch, prompt rendering
   with inline inputs (snapshot), settings defaults. The fake engine keeps working for drafts.

## Acceptance criteria

- [x] Drafts and repairs run through `gemini_api` with one request per step; no agent loop, no file reads.
- [x] Repairs send patches and change only what the errors name.
- [ ] Draft validity is at least as good as Antigravity's on the golden requirements (same validators, same
      difference test, same content rules).
- [ ] Median total draft time ≤ 180 s for a dynamic draft and ≤ 120 s for a static one, repairs included.
- [x] Usage, cost and the trace are recorded per call as today.
- [x] The draft engine is a setting; Antigravity and the fake engine still draft.
- [x] Errors from our own code end the repair loop at once (a round that changes nothing ends it; see Status).

## Verify

`make lint`, `make test` (mock transport only). Then, **with the user's yes** (paid API calls): draft the golden
requirements of the diversity report (`make design-diversity` with `DRAFT_ENGINE=gemini_api`), plus the gym and the
"introduce Japanese" requirements, and record per draft: total time, calls, tokens, cost, valid on first check or
after how many repair rounds, difference test, stock phrases, icon warnings. Compare with the Antigravity numbers
above in this story's Status note.

## Decisions to confirm (proposed defaults)

| # | Question | Proposed |
|---|---|---|
| 1 | Draft engine when `GEMINI_API_KEY` is set | `gemini_api` by default; Antigravity selectable |
| 2 | Draft model | The API's Flash model (closest to today's quality and cost); Pro only if the measurement asks for it |
| 3 | Branch | `feat/story18.10-api-drafts`, stacked on `feat/epic20-design-diversity` |

## Related

The same "stop on errors the engine cannot fix" rule for generation repairs, and the `complete_backend` context pack, are in [18.11](story18.11_lean_validation.md).

## Status

**Implemented (2026-11-03)**, on `feat/story18.10-api-drafts`; the paid comparison (Verify) waits for the user's yes.

- **Engine:** `src/engines/gemini_api/` (`GeminiApiEngine`, `name = "gemini_api"`, `drafts_only`, `inline_inputs`):
  one `generateContent` request per step with JSON output; the answer is an envelope of `files` and RFC 6902
  `patches` (`src/libs/jsonpatch.py`, add / replace / remove / move / copy / test); 429 and 5xx retry three times
  with backoff; a non-JSON answer is asked again once with the parse error; `MAX_TOKENS` → `limit_exceeded`, a safety
  block → `crash`; cancel aborts the request; the key is redacted from errors and the per-invocation log
  (`<state>/logs/<id>.gemini_api.jsonl`). Each attempt is a priced `ModelCall` (`gemini-3.8-flash`, confirmed on the
  API's model list; 1 M in / 65 k out). Health: `GET /models/<model>`, cached 10 min. `docs/engines/gemini-api.md`.
- **Inline prompts:** `draft_frontend_spec@v10`, `draft_spec@v4`, `repair_spec@v3`, `repair_direction@v2` take
  `inline`: the digests, example, catalogue, design facts (and for repairs the current files) travel in the prompt;
  in path mode they render as v9 / v3 / v2 / v1 did (one blank line apart), so the CLI engines moved to them too.
  The full JSON Schemas are not sent.
- **Repairs as patches:** `repair_spec@v3` asks for patches per file; the engine applies the operations up to the
  first that fails and reports the rest in its message. A round whose errors repeat the previous round's ends the
  loop ("Repair n changed nothing") instead of buying the same answer again (step 4: the generator-side cases are
  covered by this and by the validator / contract fixes of 2026-11-03 rather than by classifying error codes).
  `autofix_draft` now reconciles against the normalized BackendSpec (the raw spec made the contract throw, so the
  heals never ran).
- **Settings:** `DRAFT_ENGINE` (empty: `gemini_api` when `GEMINI_API_KEY` is set), `GEMINI_API_MODEL`,
  `GEMINI_API_THINKING_BUDGET`, `GEMINI_API_MAX_OUTPUT_TOKENS`, `GEMINI_API_TIMEOUT_SECONDS`; `registry.draft_default`;
  `/api/v1/engines` returns `draftDefault` and `draftsOnly` per engine; `POST /spec-drafts` without `engine` and a
  one-click generation without `options.draftEngine` draft with it (the fake engine drafts for itself).
  `make up` lists `gemini_api` on the Docker worker when a host worker runs Antigravity.
- **UI:** Options has a *Draft engine* select beside *Engine* (which hides drafts-only engines); the Requirement tab
  says "Drafting with …".
- **Also fixed (20.11's step 0):** mock handlers register literal segments before parameters
  (`/consumptions/summary` before `/consumptions/:id`), so dashboard figures bound to a custom operation get their
  values; `complete_backend@v3` tells the engine to declare such routes above `/{id}` and about `list[...]`
  annotations in repository classes.
- **Not done:** step 6 (split draft) stays measured-first; step 7 is as before (the draft's `usage` and the trace
  tab already show each call).
- Tests: `tests/test_gemini_api_engine.py` (envelope, patches, retries, non-JSON retry, blocked / truncated /
  timeout / auth, redaction, refused code purposes, cancel, health, the patch applier, a static draft end to end
  through `DraftRunner` on a mock transport, a repair round with patches, the no-progress stop). `make test`,
  `make lint`, `tsc` pass.

**Fix (2026-11-04)**, from the first `make up` run: a requirement generation was queued on its draft's engine once
the draft finished, so with `ANTIGRAVITY_AUTH=account` the Docker worker took it from the `gemini_api` queue and
failed with `ENGINE_UNAVAILABLE`. `_chain_generation` now queues (and reports) the generation's own engine;
regression test in `test_one_click_generation.py`.

**Fix (2026-11-04)**: a dynamic draft (`167c28e1…`) ended in review on one pair error, a section reading
`totalValue` from an operation that returns `totalStockValue`, which two repair rounds did not fix. Such mismatches
are now fixed in code before any repair: `reconcile_spec_pair` renames section `data.fields` and Stats `value`s the
response lacks to the clearly closest response field (`closest_field`: same words, contained words, or a near
spelling; no guess on a tie), else drops them, with a note each.

**Change (2026-11-04)**, at the user's request after a third draft (`a5820749…`) stopped on eight pair errors
(each spec valid on its own): a dynamic draft no longer stops for the pair. `orchestrator/pair_fixes.py` first makes
the BackendSpec follow the pages (custom operations get the request a form sends and the list response a section
shows, lists get the filters / sort / search pages ask for, form fields join their entity), before every check and
so before any repair call; what the backend cannot provide is cut from the frontend after the repair rounds, with a
note each. On that draft: seven errors answered by the backend, one parameter (`lowStock`, no such field) cut. The
UI drops the Consistency card and badge (only the two specs' validity shows; the contract tab stays), and a
dynamic generation's submit no longer waits on the pair check. Also fixed: a custom operation's enum response
property crashed the contract's sample rows. Tests: `test_pair_fixes.py`.
