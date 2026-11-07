# Story 26.5 — Business evaluation after the app is ready

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 26.3

## User story

As a business owner, I want to know, for each step of my main workflows, whether the running app lets the right people
do it, refuses the wrong ones and shows each person what they should see, with the proof, without it ever blocking my
app.

## Context

The lab's checker (`lab/business-value/checker.py`, `api.py`, `walker.py`) and the rules it needed:
one result rule (no answer → unbound; else pass / fail on the status code); refusals before the real action, and a real
action that fails because a wrong actor already changed the record is *blocked* with that cause; a second user per role
through the app's sign-up, kept only if `/auth/me` confirms the role; too-early checks only once the record exists; a
path with no record of its own reads one listed by the step's actor, and its "cannot see" checks are `n/a`; an empty
filtered setup falls back with a finding; `automatic` steps check their outcome only; the score is met / total and met
/ decided (blocked and unbound are unknown, not failures); one second look per path ("app" or "binding") with one
corrected retry.

## Steps

1. **Evaluator** (`orchestrator/evaluation/`): the checker's rules as code, run against the backend preview with the
   demo users; screenshots per step through a Playwright process in `bga-runner-node` (the lab's `walk.mjs`, signed in
   per role); screen judging and the summary through the provider (24.2).
2. **When:** after `integrate` succeeded and both previews are up, as a background task (like 18.12's integration), for
   generations with `business.json`; "Run again" via `POST /api/v1/generations/{id}/evaluation/run`.
3. **Information only (D4):** the result never changes the generation's status, never adds warnings to it and never
   triggers a repair; a failing evaluation run (an error in the evaluator) is shown in the tab, not as a job failure.
4. **Stored:** `evaluation_runs` (status, score, counts, started / finished, provider usage) and artifacts
   (`evaluation.json`: lines with evidence, paths, binding problems, judged screens, summary; screenshots under the
   generation's artifacts); events `evaluation.status` for the UI.
5. **Cost:** model calls only for the second look, screen judging and the summary; with the Antigravity provider none
   is billed per token; the calls are accounted to the generation (`model_calls`, purpose `evaluate_*`).
6. Tests: each checker rule with a fake backend (FastAPI test app with the lab's failure cases: wrong-role success,
   chain effect, missing second user, borrowed record, automatic step), the background start, status untouched.

## Acceptance criteria

- [ ] A dynamic generation with workflows gets an evaluation automatically after its previews are up.
- [ ] The generation's status and validation are identical with and without the evaluation (test).
- [ ] Each line carries its evidence (call, actor, status, detail); the score is computed, not written by a model.
- [ ] The lab's three runs, re-run through the evaluator, give the same results as the lab's checker (± lines the
      binding differs on, listed).

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up` with a lab requirement end to end.
