# Story 12.5 — Frontend ↔ contract consistency check

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-23 · **Depends on:** 12.1, 12.3

## User story

As the workflow, I want to reject a dynamic job whose frontend asks for data the backend will never provide,
before spending any engine time.

## Acceptance criteria

- [ ] Every `sections[].data.operationId` and `forms[].operationId` exists in the contract; `params` match the
      operation's parameters; form fields exist in the request schema with compatible types and `required`.
- [ ] Display bindings that name fields (e.g. a card shows `price`) are checked against the response schema.
- [ ] Errors use stable codes (`CONTRACT_UNKNOWN_OPERATION`, `CONTRACT_PARAM_MISMATCH`, `CONTRACT_FIELD_MISSING`)
      and point at both specs (JSON pointers), so the UI can mark them in either editor.
- [ ] Runs in `validate_inputs` (14.1) and in `POST /api/v1/frontend-specs/validate?backendSpecId=…`.
