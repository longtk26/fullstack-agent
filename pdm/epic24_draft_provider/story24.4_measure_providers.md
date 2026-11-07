# Story 24.4 — Measure the providers on the lab requirements

**Epic:** [24 — Draft provider](epic24_draft_provider.md) · **Requirements:** FR-38 · **Depends on:** 24.3

## User story

As the user, I want to know what I lose or gain by drafting with Antigravity or Claude Code instead of the Gemini
API, measured on the same requirements, before I make it my default.

## Context

The lab (2026-11-07) showed that the draft model changes the app: `gemini-3.1-flash-lite` answered 1,311 output tokens
against `gemini-3.8-flash`'s 14,430 for the same prompt and dropped whole entities, a plugin and every role rule. A
provider can do the same.

## Steps

1. Draft the three lab requirements (`lab/business-value/requirements/`, one per workflow shape) with each
   provider: valid on the first try or after repairs, attempts, time, output size, cost.
2. Generate from each draft (Antigravity code engine) and run Epic 26's evaluation (or the lab's checker until 26.4 is
   done) against the same frozen expectations per requirement (the lab's `--business-from`).
3. Write the comparison into this story's Status and choose the default with the user.

## Acceptance criteria

- [ ] A table per requirement and provider: draft validity and attempts, time, output tokens, cost, expectations met
      (of decided), entities and rules kept from the requirement.
- [x] The default provider is the user's decision, recorded in `.env.example` and FR-38.

## Verify

Real runs only with the user's go (Antigravity on the account login; the Gemini API costs per token).

## Status

**Measured 2026-11-07 (reduced, the user's limits: `agy` only, at most two requirements per run).** FixPoint
(`lab/business-value/requirements/fixpoint-repairs.md`), app draft:

| Provider | Valid / attempts | Time | Tokens in / out | Cost | Entities, roles, operations |
|---|---|---|---|---|---|
| `gemini_api` (lab run `fixpoint-2`, `gemini-3.8-flash`) | valid after 1 repair | 104 s + 28 s | 17.5k / 18.3k | $0.082 | 3 entities, 4 roles, 26 operations, 5 policies, 2 rules |
| `antigravity_json` (`gemini-3.8-flash-medium`, account login) | valid, no repair | 169 s | 19.4k / 49.7k | $0 | 3 entities, 4 roles, 24 operations, 5 policies, 2 rules |

`claude_code_json` was not run (the user uses `agy` only). Expectations met per provider are measured with Epic 26's
evaluation in 26.7. The default is the user's decision: **`antigravity`** (`.env`, `.env.example`, FR-38).
