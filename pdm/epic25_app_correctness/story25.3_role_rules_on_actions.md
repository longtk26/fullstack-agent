# Story 25.3 — Role rules on actions

**Epic:** [25 — App correctness](epic25_app_correctness.md) · **Requirements:** FR-39 · **Depends on:** 10.3

## User story

As a business owner, I want each action of a workflow to be done only by the role it belongs to (the record's owner
confirms what is theirs to confirm, each approver acts only at their own step), so the POC shows the process the
business really runs.

## Context

- F2 in 3 / 3 apps: staff roles performed the owner's own action; a later approver acted at an earlier approver's
  step; a second user of the owner's role acted on another user's record; in one draft, approval was a plain
  `PATCH status` anyone could send.
- Ownership policies have `bypassRoles` for staff; a bypass meant for reading lets staff perform the owner's actions too.

## Steps

1. **An action's role.** Each custom or transition operation gets the role(s) that perform it, from the draft (the
   operation's description, the outline's areas) and, when Epic 26 runs, from the workflow step that names it
   (`actor`). Code adds a role policy when the draft has none.
2. **Owner-only actions.** An action the owner performs (any action whose role is the owner's role) is ownership
   **without** staff bypass; the read bypass stays on get and list.
3. **Status changes are actions.** A status that moves through a flow (`transition` rule) is never writable through the
   generic update: the update leaves `status` out, and each move is its own operation with its role (or, when the draft
   has none, code adds one per transition target).
4. **Contract, mocks, scenarios, `allowedActions`:** a role that may not act gets 403 (or 404 when it may not see the
   record); scenarios "<other role> → 403" per action; the kit hides the action (22.7).
5. Tests on synthetic specs: role inference from descriptions and areas; owner-only actions without bypass; a
   two-step approval chain (each approver only at their step); a transition field dropped from update; scenarios on
   mocks.

## Acceptance criteria

- [ ] Every role that does not own an action is refused it (403, or 404 when it may not see the record), on mocks and
      live.
- [x] No app accepts a status change through the generic update when the status has a flow.
- [x] The right role still performs each action; the app walk and scenarios pass.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, the lab set re-checked in 25.6.

## Status

Criteria marked open need the live apps: they are checked by the real generations of 26.7.

**Done 2026-11-07.** In `drafting/access.py`: a record action whose policy names only the owner's role, or is the
ownership policy with a staff bypass, becomes ownership without bypass (`<entity>OwnerOnly`); an action given to the
role of a second person field becomes that person's (`<entity>Assigned<Role>`); an entity whose `transition` rule has
record actions loses the status from the generic update (and the rule from it), and the kit plans no "Mark as …"
buttons when the update cannot write the status (`screens.py`). The policies plugin now takes the owner from the field
that guards the reads, not from the last ownership policy it saw (a worker's action made the worker the owner).

Not covered: the order of approvers on one entity (a later approver acting at an earlier one's step) needs a rule per
status, which the rules plugin's transition has no role for; the lab's finding stays open for that case.
