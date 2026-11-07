# Story 26.1 — Workflow discovery and the brief

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 24.2

## User story

As a business owner who writes only what my business does, I want the agent to find the main workflows my app must
support (who does what, in which order, with which rules) and build the app around them.

## Context

The lab's `discover` and `brief` stages (`lab/business-value/prompts.py`: `discover_prompt`, `BUSINESS_SCHEMA`,
`rediscover_prompt`, `brief`) after three iterations: no fixed number of workflows; a workflow has its own trigger,
outcome and values; refusals and exceptions are branches; list upkeep is not a workflow; every value is delivered by a
step (`delivers`), checked in code with one retry; `core` / `later` priority; a golden path.

## Steps

1. **Discovery call** (`drafting/business.py`, prompt `discover_workflows@v1`) through the provider (24.2) before
   `draft_app`, for dynamic drafts when `options.businessWorkflows` is on: `business.json` with app, values, actors
   (`signsIn`), workflows (`priority`, `values`, `trigger`, `steps` with actor / action / record / statusAfter / rule /
   delivers, `branches` with `after` and `condition`, `outcome`, `acceptance`) and scope (`goldenPath`, included,
   excluded). Schema checked in code; the "every value has a step" check with one re-ask (the lab's `rediscover`).
2. **The brief.** The requirement plus the core workflows in plain words (roles, numbered steps with status changes and
   rules, branches as "If … after step N", status flows, later and excluded items) is what `draft_app` receives as the
   requirement; the user's own text stays the draft's `requirement_text`.
3. **Stored with the draft**: `spec_drafts.business` (JSON, migration); packaged as `business.json`; the draft's usage
   counts the calls.
4. **Draft review** shows the workflows (core first, branches indented, the golden path marked) read-only.
5. Tests: the schema, the value check and re-ask (fake provider), the brief text (snapshot), the option off keeps
   today's draft unchanged.

## Acceptance criteria

- [x] A dynamic draft has `business.json` with at least one core workflow; every value has a step that delivers it, or
      the draft notes which one has none.
- [x] Refusals and exceptions appear as branches, not as workflows (the lab saw a refusal counted as a workflow).
- [x] With `businessWorkflows` off, drafting is exactly today's (snapshots).

## Verify

`make lint`, `make test`, `make up`, one draft of a lab requirement on the provider the user chooses.

## Status

**Done 2026-11-07.** `orchestrator/business/` (`model.py`: the schemas and helpers from the lab; `flow.py`:
`BusinessFlow.discover` with one second ask when a value has no step) and `drafting/business.py` (before `draft_app`,
through the draft's provider; the brief replaces the requirement in the draft prompt, the user's text stays the
draft's). Prompt `discover_workflows@v1`. Stored in `spec_drafts.business` (migration `d4f8a2c6e9b1`), shown read-only
in the draft review (`WorkflowsPanel`). `BUSINESS_WORKFLOWS` (default on) and the draft's `businessWorkflows` switch it.
Tests: `tests/test_business_layer.py` (paths and the brief, the second ask, a draft with the option on and off).

Real run (HomeFix, `agy` on the account login): 2 core workflows, a "reopen" branch (not a workflow of its own), every
value delivered by a step; 73 s, $0. Deviation: the business data is not packaged as `business.json` in the
generation's artifacts; the evaluation reads it from the draft (`options.draftId`).
