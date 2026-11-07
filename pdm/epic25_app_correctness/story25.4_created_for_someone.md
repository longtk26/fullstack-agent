# Story 25.4 — Records created on behalf of another user

**Epic:** [25 — App correctness](epic25_app_correctness.md) · **Requirements:** FR-39 · **Depends on:** 25.2, 22.6

## User story

As a user of a staff role, I want to create a record on behalf of a user of another role and have it belong to that
user, so they see it in their own account and carry on its workflow themselves.

## Context

- F3 (see the epic): when one role creates a record that belongs to a user of another role, the draft still gives the
  owner field `x-bga.source: currentUser`. The creator becomes the owner; the intended owner gets 404 on view and on
  every action of their own, and the workflow stops at its first step after creation. A field that names the intended
  owner (an e-mail, a name) can be in the form without being linked to any account.
- 25.2 decides which entities are tied to a person and which role that person has; 25.3 decides which roles perform
  each operation, create included.

## Steps

1. **Detect it.** A person-tied entity (25.2) whose create operation is performed by a role other than the owner's
   role, or by both (the owner creates their own records; staff also create them on the owner's behalf).
2. **Owner as input.** For the other role's create, the owner field becomes an input (`x-bga.source: reference` to the
   user entity, limited to users of the owner's role); when the owner's role creates, it stays `currentUser`. When both
   create through one operation, the field is an input that defaults to the current user and only the staff role may
   set it to someone else (the policy refuses it for the owner's role).
3. **Owners without an account yet.** When the draft identifies the owner by a contact field (e-mail) instead of a
   user, decide in this story between: requiring an existing user (picker only), or linking on first sign-up with that
   e-mail. Record the choice and the reason in the Status.
4. **The form.** The kit's reference picker (22.6) lists users of the owner's role by display name and e-mail, with
   search; the owner's own create form has no picker.
5. **Contract, mocks, scenarios:** the create example sets the owner; scenarios "staff creates for the demo owner, the
   owner then reads it and performs their next action" and "the owner's role cannot create for someone else".
6. Tests on synthetic specs, not on one domain: an entity created only by staff for an owner; one created by both;
   one created only by its owner (unchanged); detection, the contract field's source and policy, the picker binding,
   the scenarios on mocks.

## Acceptance criteria

- [ ] When a staff role creates a person-tied record, the record belongs to the user chosen in the form, who then sees
      it and performs their own actions on it, on mocks and live.
- [ ] A user of the owner's role cannot create a record that belongs to someone else.
- [ ] Records a user creates for themselves are unchanged (`currentUser`); the static and app golden tests pass.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`; measured on real requirements in 25.6.
