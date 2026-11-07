# Story 26.7 — Final check

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 26.1–26.6, Epic 25

## User story

As the user, I want to see the whole business layer work on real requirements before it becomes the default.

## Steps

1. The three lab requirements and Epic 25's fresh requirement (four workflow shapes), end to end on the provider the user chooses (Epic 24)
   and the Antigravity code engine: discovery, expectations, binding, generation, tour, evaluation, Business tab.
2. The same four with `businessWorkflows` off (D7): the evaluation still runs against the frozen expectations of the
   first run, so both apps are measured the same way; compare met / decided, paths completed, refused, hidden.
3. Each demo role's tour on each app, on mocks and live.

## Acceptance criteria

- [ ] All four apps show the tour per role and a complete Business tab.
- [ ] The comparison with the option off is written in this story's Status; the user decides whether the business
      layer stays on by default.
- [ ] No generation's status changed because of the evaluation.

## Verify

Real runs with the user's go.

## Status

**In progress (2026-11-07).** Run on the user's machine limit: one requirement at a time, `agy` (account login) for
every LLM step and the Antigravity code engine. The user decided: **the business layer stays on by default for
dynamic mode** (`BUSINESS_WORKFLOWS=true`, static sites never have it).

HomeFix (the lab requirement), with and without the business layer:

- With it (`gen_01M6TG77VPNCX1KGB5TZNDE9RH`): COMPLETED, all lanes. Evaluation: 72 of 81 lines met, 92 % of the
  decided ones; every "can do it" (10), "refused" (24), "hidden" (14), "too early" (4) and "status after" (6) line
  passed. The 6 failures were the checker's (the assigned contractor reads through their own operation; fixed, 26.5);
  the 3 unchecked lines are the app's real gap (monitoring figures are dashboard aggregates, no report record).
- Without it (`gen_01M6TF17DNTGEXCDY87RDX2QWX`): COMPLETED; its evaluation against the first run's frozen expectations
  (`expectationsFrom`, bound to its own contract and screens) was running when this was written.
- No generation's status changed because of an evaluation (a failed evaluation left COMPLETED as it was).

What the runs found and fixed in the generator and the layer (each with a test): two keys to the same model
(relationships named after their keys, Epic 25), an update without the file field (storage plugin), the preview start
race, the evaluation's provider scratch dir (inside `WORKSPACE_ROOT`), the checker's read per role, the tour opening
record pages itself and anchoring "look at" steps (26.4), and failed drafts now store where they crashed.

Open, for the next session:

- The on/off comparison's numbers (the run above), then the first criterion's other apps: six requirements of other
  shapes and styles are written (volunteer shifts, bakery wholesale, pet adoption, coworking rooms, a clinic in
  Japanese, dark-themed event tickets); the user will run them next.
- On HomeFix's first evaluation the judged screens showed "Could not load this" on record pages and the tenant's
  tour did not start; both ran while the backend preview was stuck (the preview race), so they are to be checked again
  on cleanly started previews before they count either way.
- The Docker worker image still has the preview race (its rebuild failed on Docker Desktop's credential helper);
  `make up` after signing in to Docker Desktop deploys the fix.
