# Story 12.3 — API contract generation (contract first)

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-23, FR-17 · **Depends on:** 5.1

## User story

As the frontend and backend lanes, we want one machine-readable contract created before either of us starts,
so that we can be generated in parallel and still fit together.

## Acceptance criteria

- [ ] Pure function `contract(plan) → OpenAPI 3.1` (no LLM): every planned operation with its exact
      `operationId`, method and path; request and response schemas from the plan's DTOs (camelCase); the list
      envelope `{items,total,limit,offset}`; the error envelope `{error:{code,message,details}}` per planned error
      status; query parameters for pagination, filters, sort and search; `examples` built from the spec's
      `seed[]` (or synthesized from field types when there is no seed).
- [ ] Stored as `contract.json` (artifact kind `contract`, versioned with a sha256) at the start of the job, and
      copied into both workspaces (`.bga/contract.json`).
- [ ] Backend validation (6.2 `openapi` check) is extended from "same operations" to **schema conformance**:
      the generated app's OpenAPI must be compatible with the contract (same parameters, required fields, types,
      status codes). A mismatch is a repair item for the backend, never a silent contract change.
- [ ] Byte-identical for the same spec (snapshot tests per example).
