# Story 12.5 — Frontend ↔ contract consistency check

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-23 · **Depends on:** 12.1, 12.3

## User story

As the workflow, I want to reject a dynamic job whose frontend asks for data the backend will never provide,
before spending any engine time.

## Acceptance criteria

- [x] Every `sections[].data.operationId` and `forms[].operationId` exists in the contract; `params` match the
      operation's parameters; form fields exist in the request schema with compatible types and `required`.
- [x] Display bindings that name fields (e.g. a card shows `price`) are checked against the response schema.
- [x] Errors use stable codes (`CONTRACT_UNKNOWN_OPERATION`, `CONTRACT_PARAM_MISMATCH`, `CONTRACT_FIELD_MISSING`)
      and point at both specs (JSON pointers), so the UI can mark them in either editor.
- [x] Runs in `validate_inputs` (14.1) and in `POST /api/v1/frontend-specs/validate?backendSpecId=…`.

**Status (2026-10-27):** done. `src/orchestrator/checks/consistency.py`. Notes and deviations:
- Extra codes: `CONTRACT_METHOD_MISMATCH` (a section bound to a write operation, a form bound to a GET) and
  `CONTRACT_FIELD_TYPE_MISMATCH` (form field type, date vs date-time, enum vs free text, enum values outside the
  contract, optional field the contract requires). Literal `params` values are checked against the parameter
  schema (type, enum, minimum/maximum); `$route.x` / `$query.x` values are not.
- Issues carry `path` (FrontendSpec pointer) and `backendPath` (BackendSpec pointer: the operation, the entity
  field, or `/operations` for unknown operations).
- `validate_inputs` is a node now (dynamic and static modes), ahead of 14.1: it runs 12.1, the BackendSpec
  validation and this check; any error fails the job with `SPEC_INVALID` before any engine call, and the
  `spec.invalid` event lists the issues with `spec: frontend | backend | consistency`.
