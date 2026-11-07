# Story 24.2 — One LLM provider for every LLM-only step

**Epic:** [24 — Draft provider](epic24_draft_provider.md) · **Requirements:** FR-38 · **Depends on:** 24.1

## User story

As the agent's maintainer, I want one interface for every step that only needs an answer from a model (no files, no
tools), so drafting and the business-workflow steps (Epic 26) switch provider together and are tested the same way.

## Context

- Today drafting calls the engine through `ctx.run_engine`-like helpers in `drafting/drafts.py` and `drafting/app.py`
  (`call("draft", prompt, response_schema=...)`).
- Epic 26 adds discovery, expectations, binding, screen judging (with an image) and a summary; the lab made these as
  direct Gemini REST calls (`lab/business-value/clients.py`).

## Steps

1. **`LlmProvider` port** (`engines/llm.py`): `json(step, prompt, schema=None, images=None) -> LlmAnswer` (the parsed
   object, the raw text, usage). Implementations: Gemini API (from `GeminiApiEngine`'s request code), `agy` JSON and
   `claude` JSON (24.1). Each validates against `schema` in code (Epic 24 D3) and raise one error type with the reason.
2. **Images.** Gemini: inline image parts. `agy` and `claude`: find out whether their stream-json input accepts an
   image part; if not, copy the image into the scratch directory and allow reading that one file only (`agy`:
   `read_file` on it; `claude`: `--tools Read` limited to the scratch directory). Record which way works in this
   story's Status.
3. **Drafting through the port.** `drafting/drafts.py` and `drafting/app.py` call the provider for draft and repair
   steps (the inline prompts); the engine names stay in the draft's `usage` and `engine` fields.
4. **Accounting.** Every provider call is recorded where its owner records calls today: on the draft (`usage`) for
   drafting; on the generation (`model_calls`, purpose `evaluate_*`) for Epic 26's evaluation.
5. Tests: one contract test suite run against every provider with its fake (a fake Gemini transport, the fake `agy`
   and `claude`), and the fake engine still drafts.

## Acceptance criteria

- [x] Drafts and repairs go through `LlmProvider`; the draft results on the fake engine are unchanged (snapshots).
- [x] All three providers pass the same contract tests, including a schema failure and an image input.
- [x] Every call is accounted to its draft or generation with provider, model, tokens and cost source.

## Verify

`make lint`, `make test`.

## Status

**Done 2026-11-07.** `engines/llm.py`: `LlmProvider.json(step, prompt, schema, images)` returns `LlmAnswer` (the object,
the text, the calls, `structured`, notes) or raises `LlmError` (reason and status as the engines'); a wrong shape is
asked again once with its errors. Providers: `AgyJsonProvider`, `ClaudeJsonProvider` (`engines/json_cli.py`),
`GeminiLlmProvider` (`engines/gemini_api/llm.py`, the engine's request code, inline image parts) and `FakeLlmProvider`
(`engines/fake_llm.py`, responders per step, else the schema's skeleton). `build_llm_provider()` /
`get_llm_provider()` choose by `LLM_PROVIDER`.

- Images: `agy` and `claude` get each image as a file in the step's scratch directory, named in the prompt (`agy`:
  `read_file` allowed on that directory only; `claude`: `--tools Read`, its working directory being the scratch one).
  Checked with the fake CLIs; a real image step runs with Epic 26's screen judging.
- Deviation: the Gemini API draft engine keeps its own `run` (it already does one request per step with the envelope);
  the new providers draft through `LlmDraftEngine`, so drafting code (`drafts.py`, `app.py`) is unchanged and still
  calls engines. Both share `engines/envelope.py`.
- Accounting: a draft's calls are on the draft (`usage`, `costSource: account` for the logins without per-token cost);
  Epic 26 records its calls on the generation.
