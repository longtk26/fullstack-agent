# Epic 25 — App correctness: who may do it, who may see it, demo data that works

## Overview

Proposed 2026-11-07 for the user's review, from the business-value lab (`lab/business-value/`, 2026-11-06/07). The lab
wrote down, before each draft, what must be true at every step of a requirement's main workflows (who may do it, who
must be refused, the status after it, who may and may not see the record, its effects), then checked every line
against the running app as each role's demo user. It used three requirements outside `examples/`, chosen for three
different workflow shapes, not for their domains; the rules in this epic are about those shapes and apply to any
product:

| Workflow shape (lab run) | Met (of decided) | Paths completed | Wrong roles refused | Hidden from others |
|---|---|---|---|---|
| Staff create records on behalf of outside users, who then act on them (`runs/fixpoint-2`) | 25 / 73 (81%) | 0 / 2 | 8 / 16 | 2 / 7 |
| An internal approval chain with amount thresholds (`runs/buyright-1`) | 51 / 87 (91%) | 2 / 5 | 13 / 23 | 5 / 16 |
| Outside users report; two staff roles handle in turn (`runs/homefix-1`) | 38 / 63 (84%) | 1 / 3 | 14 / 18 | 0 / 10 |

The generator gets the mechanics right: the right actor can do each step, status flows hold, steps done too early are
refused (10 / 11). It fails on **who may do it and who may see it**, in every app, in ways today's validation passes
(every call returns a valid status). Each finding below has its call and response in the run's `check.json`.

| Finding | Seen in | Evidence |
|---|---|---|
| F1 Records are not hidden from other users of the same role | 3 / 3 | a second user of the owner's role reads a record that is not theirs: `GET …/{id}` → 200 |
| F2 Actions that belong to one role are not guarded by that role | 3 / 3 | staff roles perform the owner's own action (approve, decline, confirm) with 200; a later approver acts at an earlier approver's step; a second user of the owner's role acts on the first user's record |
| F3 A record one role creates on behalf of another user belongs to the creator | 1 / 3 (two independent drafts) | the owner field has `x-bga.source: currentUser`, so the creator becomes the owner; the intended owner gets 404 on view and on their own actions |
| F4 Demo data is not linked to the demo users | 1 / 3 | the seed's person-tied parent records belong to user ids that are no demo account; the demo user has nothing of their own to start the workflow from |
| F5 The generation refuses a draft the drafting accepted | 1 / 3 | `ensure_aggregates` appends aggregates past `MAX_DASHBOARD` (6) after `complete_outline` capped it; `validate_inputs`: "at most 6 items, not 7" |
| F6 The mock reads separately unique fields as one combined key | 1 / 3 | the contract's `CONFLICT` lists two separately unique columns; `mocks/plugins.ts` checks `fields.every`, so a duplicate of one of them gets 201, `frontend:scenarios` fails and `repair_frontend` cannot fix generator code |

**Requirements:** FR-39 (new, proposed: correct by default for roles, ownership, visibility and demo data), FR-36,
FR-37 (23.9 visibility rules), Epic 10 (policies, 10.3).

## Decisions (proposed 2026-11-07)

| # | Decision | Instead of |
|---|---|---|
| D1 | **General rules from what the spec declares**, never fixes for the lab's apps or any one domain: a record tied to a person, an action given to one role, a record one role creates on behalf of another user | Patching the lab's apps |
| D2 | **Private by default only for records tied to a person**; a catalogue (no person reference, or marked public) stays public | Making everything private |
| D3 | **The backend decides** (as 23's D7): code adds policies to the BackendSpec before the contract; the contract, mocks, scenarios and `allowedActions` carry them | Frontend-only hiding |
| D4 | **Measured by the lab set plus one fresh requirement** that was not used while designing the rules (25.6) | Judging on the three apps alone |

## Stories

| # | Story | Depends on |
|---|---|---|
| 25.1 | [Pipeline fixes: dashboard cap, unique fields in the mock, the draft check matches the generation's](story25.1_pipeline_fixes.md) | Epic 22 |
| 25.2 | [Private by default: records tied to a person](story25.2_private_by_default.md) | 10.3, 23.9 |
| 25.3 | [Role rules on actions](story25.3_role_rules_on_actions.md) | 10.3 |
| 25.4 | [Records created on behalf of another user](story25.4_created_for_someone.md) | 25.2, 22.6 |
| 25.5 | [Demo data linked to the demo users](story25.5_demo_data.md) | 25.2 |
| 25.6 | [Re-check: the lab set and a fresh requirement](story25.6_recheck.md) | 25.1–25.5 |

25.1 is independent and small; do it first.
