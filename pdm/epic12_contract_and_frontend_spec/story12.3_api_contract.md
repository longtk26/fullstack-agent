# Story 12.3 — API contract generation (contract first)

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-23, FR-17 · **Depends on:** 5.1

## User story

As the frontend and backend lanes, we want one machine-readable contract created before either of us starts,
so that we can be generated in parallel and still fit together.

## Acceptance criteria

- [x] Pure function `contract(plan) → OpenAPI 3.1` (no LLM): every planned operation with its exact
      `operationId`, method and path; request and response schemas from the plan's DTOs (camelCase); the list
      envelope `{items,total,limit,offset}`; the error envelope `{error:{code,message,details}}` per planned error
      status; query parameters for pagination, filters, sort and search; `examples` built from the spec's
      `seed[]` (or synthesized from field types when there is no seed).
- [x] Stored as `contract.json` (artifact kind `contract`, versioned with a sha256) at the start of the job, and
      copied into both workspaces (`.bga/contract.json`).
- [x] Backend validation (6.2 `openapi` check) is extended from "same operations" to **schema conformance**:
      the generated app's OpenAPI must be compatible with the contract (same parameters, required fields, types,
      status codes). A mismatch is a repair item for the backend, never a silent contract change.
- [x] Byte-identical for the same spec (snapshot tests per example).

**Status (2026-10-27):** done. `src/orchestrator/contract.py` (`build_contract(spec, plan)`: it also needs the
normalized spec for seed examples, request field lists and custom payloads), `checks/conformance.py`, node
`build_contract` (dynamic mode), snapshots `tests/fixtures/contracts/*.contract.json`. Notes and deviations:
- Contract content: request schemas leave out generated keys and `now` timestamps; update bodies are partial;
  nullable columns are `[type, "null"]`; `decimal` is `["number", "string"]` (Pydantic returns Decimal as a
  string); one error response per planned error status with the shared `ErrorResponse`; `x-bga` on each
  operation (entity, action, module) and at the top (`contractVersion`, `planVersion`, `specSha256`,
  `fixtures`: one record set per entity, seed rows completed or three synthesized rows, foreign keys pointing
  at the parent's records, for the mock layer in 13.2).
- Stored as artifact `contract.json` (kind `contract`, sha256 in the artifact row and the `contract.ready`
  event), in the project as `.bga/contract.json` and canonically outside the project; every validation restores
  the project copy, so an engine edit cannot change the contract. The manifest lists the contract artifact. The
  frontend workspace copy comes with 13.2. Backend mode has no contract (the table: OpenAPI exported after
  generation), so its validation is unchanged.
- Conformance (`openapi` check, dynamic mode): parameters (name, in, required, type), request fields (same
  required set, compatible types, enums), every contract status code declared, success response fields and
  types (`null` only where allowed). Extra optional parameters/fields are allowed; error bodies are not compared
  (the generated apps document them by description only). Calibrated on two real two-entity exports (golden
  project and an engine-generated one, `tests/fixtures/openapi/`): both conform; ten kinds of drift are caught.
- Backend prompts `generate_backend` and `repair_code` are now `v3`: v2 plus a contract section rendered only
  when a contract exists.
