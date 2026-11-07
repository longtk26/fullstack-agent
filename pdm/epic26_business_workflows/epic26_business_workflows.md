# Epic 26 — Main business workflows: discovered, shown as a guided tour, evaluated

## Overview

Proposed 2026-11-07 for the user's review, from the business-value lab (`lab/business-value/`). Today a dynamic app is
drafted from the requirement as entities, operations and screens; nothing names the **business workflows** the app
exists for (what a user starts, who acts next, and the outcome it ends with), nothing shows a user how to walk them,
and validation checks endpoints, not whether the workflow works end to end for the right people.

This epic brings the lab's business layer into the product:

1. **Discover** the main workflows from the requirement (values, actors, workflows marked core or later, branches for
   refusals and exceptions, the value each step delivers), and give them to the draft as a brief.
2. **Freeze the expectations** of every core workflow step in business words, before anything is generated.
3. **Bind** each step to the contract (operation, page, action) when the draft is made, checked by code.
4. **Guide** users through their role's workflow steps with a react-joyride tour in the generated app.
5. **Evaluate** the running app against the frozen expectations, automatically, and show it in a **Business** tab.
   The evaluation is information only (D4).

Every LLM call here goes through Epic 24's provider (Antigravity JSON or the Gemini API).

| Finding (lab, 2026-11-06/07) | Effect on this epic |
|---|---|
| A fixed "2–3 workflows" made Gemini count a refusal as a workflow and drop requirement parts that no workflow covered | discovery decides the number; refusals are branches; every value needs a step that delivers it (26.1) |
| Expectations written after the app existed adapted to it | expectations are frozen at draft time (26.2) |
| Gemini's mapping of steps to calls varied run to run; it picked a 1,200 amount for the "above 2,000" path | the binding is made once, gets the paths' rules, and code validates it against the contract (26.3) |
| The lab's checker needed ~10 fixes to be trustworthy: a wrong actor's success changing the record, borrowed records, a second user per role, too-early checks before the record exists, steps the app does automatically | those rules are part of the evaluator from the start (26.5) |
| Screenshots judged by a model are useful, but opinions | screens are judged, but the score is computed only from checked lines (26.5) |

**Requirements:** FR-40 (new, proposed: business workflows, guided tour, evaluation), FR-36, FR-37, FR-38.

## Decisions (proposed 2026-11-07)

| # | Decision | Instead of |
|---|---|---|
| D1 | **Discovery is its own one-turn call before the draft**, its result (`business.json`) is kept with the draft and folded into the draft prompt as a brief | Asking `draft_app` to also discover workflows in the same answer |
| D2 | **Expectations are frozen at draft time** and never rewritten by the evaluation | Writing them against the generated app |
| D3 | **One binding, at draft time, on the contract**, validated by code; the tour and the evaluation both read it | Two mappings (tour and evaluation) that can disagree |
| D4 | **The evaluation is information only**: it never fails a generation, never triggers a repair and never changes the job's status; its result is a report in its own tab | A gate, warnings or repairs from business checks |
| D5 | **It runs automatically** once both previews are up, after `integrate`, in the background; a "Run again" button re-runs it | On demand only |
| D6 | **The tour starts once per role on first sign-in and can be replayed** from the user menu; it covers the role's steps of the core workflows | A required walkthrough; a manual-only tour |
| D7 | **An option to turn the business layer off** (`options.businessWorkflows`, default on) so its effect can be compared on the same requirement | Shipping it with no way to measure it |

## Stories

| Checkpoint | # | Story | Depends on |
|---|---|---|---|
| **A: the business layer in the draft** | 26.1 | [Workflow discovery and the brief](story26.1_workflow_discovery.md) | 24.2 |
| | 26.2 | [Frozen expectations](story26.2_frozen_expectations.md) | 26.1 |
| | 26.3 | [Workflow binding at draft time](story26.3_workflow_binding.md) | 26.2 |
| **B: the guided tour** | 26.4 | [Guided tour of the workflows (react-joyride)](story26.4_guided_tour.md) | 26.3 |
| **C: the evaluation** | 26.5 | [Business evaluation after the app is ready](story26.5_business_evaluation.md) | 26.3 |
| | 26.6 | [The Business tab](story26.6_business_tab.md) | 26.5 |
| **D: acceptance** | 26.7 | [Final check](story26.7_final_check.md) | 26.1–26.6, Epic 25 |

## The flow after this epic

```
requirement ──discover (26.1)──▶ business.json ──expect (26.2)──▶ expected.json (frozen)
     └─ brief ──▶ draft_app ──▶ BackendSpec + outline ──▶ contract ──bind (26.3)──▶ app.workflows (+ binding problems)
generation ──▶ … ──▶ integrate ──▶ previews up ──▶ evaluate (26.5, background, information only)
                                                      └─▶ evaluation report + screenshots ──▶ Business tab (26.6)
generated app: AppTour (26.4) reads app.json `workflows`: first sign-in per role, replay from the user menu
```
