# Story 26.6 — The Business tab

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 26.5

## User story

As a business owner, I want one place to read how well my app supports my business: the workflows, what was checked,
what works, what doesn't and why, with the screens.

## Context

- The generation page has tabs Steps, Trace, Results, API, App (`GenerationDetailView.tsx`).
- The lab's report (`lab/business-value/report.py`) after review: the score as met / total and met / decided; "review
  first" (the binding: actors → roles, records → entities and statuses, binding problems); a checklist per workflow
  path (step headers, each expectation with its result and evidence, the step's screenshot and screen judgment); the
  outcome per actor; values delivered, gaps, what the generator should do next; the frozen expectations and the
  business at the bottom.

## Steps

1. **API:** `GET /api/v1/generations/{id}/evaluation` (the latest run: status, score, lines, paths, binding, judged
   screens, summary) and the screenshots through the artifact endpoint; owner checks as for other generation reads.
2. **Tab "Business"** (dynamic generations with workflows): the lab report's sections as React components (shadcn,
   React Query), live while running (`evaluation.status` events), "Run again", and a short note that the evaluation is
   information only and does not affect the generation.
3. **Draft review:** the workflows (26.1) and the expectations (26.2) are readable before generating.
4. Tests: API (owner, not found, running, done); components with a recorded evaluation (vitest); `tsc`.

## Acceptance criteria

- [ ] The tab shows the score, the binding to review, the checklist with evidence and screenshots, values and gaps.
- [ ] It updates while the evaluation runs; "Run again" starts a new run.
- [ ] Generations without workflows show no Business tab.

## Verify

`make lint`, `pnpm exec tsc --noEmit`, `make test`, `make up` with an evaluated generation.
