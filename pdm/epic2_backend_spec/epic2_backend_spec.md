# Epic 2 — BackendSpec schema, validation & drafting

## Overview

Define the versioned `BackendSpec` contract and validate it deterministically before any LLM or CLI
runs. Also support two more input modes that both end in a BackendSpec draft the user reviews and edits
before generating:
- a **natural-language requirement**, drafted by the code engine;
- an imported **Frontend-Agent site JSON** (`collections` + `pages`, e.g. `json.json`), converted deterministically.

**Requirements:** FR-01, FR-02, FR-07 (assumptions), NFR 8.4 (schema-versioned)

## Input modes

```
 Requirement text ──▶ spec draft job (2.4) ──────────────▶ draft BackendSpec + assumptions ──┐
 Frontend site JSON ─▶ frontend importer (2.5) ─[optional AI refine via 2.4]─▶ draft + seed ──┤
                                                                                             ▼
 BackendSpec JSON ─────────────────────────────────────────────▶ validate (2.2/2.3) ──▶ user reviews ──▶ submit generation (4.1)
```

**Status (2026-10-23):** 2.1, 2.2, 2.3 and 2.5 done (branch `feat/epic2-backend-spec`). 2.4 and 2.5's "Refine with AI" wait for 3.2 + 4.2.

**Status (2026-10-30):** 2.4 done (requirement drafting for all three modes, with 12.4); \"Refine with AI\" works in the API, its UI button is open.

## Stories

| # | Story | Depends on |
|---|---|---|
| 2.1 | [BackendSpec v1.0 schema & JSON Schema export](story2.1_backend_spec_schema.md) | 1.1 |
| 2.2 | [Semantic spec validation](story2.2_semantic_validation.md) | 2.1 |
| 2.3 | [Spec validation API & persistence](story2.3_spec_validation_api.md) | 2.2, 1.4 |
| 2.4 | [Requirement → BackendSpec drafting](story2.4_requirement_to_spec_drafting.md) | 2.3, 3.2 |
| 2.5 | [Frontend site JSON → BackendSpec import](story2.5_frontend_json_import.md) | 2.3 |

## Epic acceptance

- The §5 example and the two-entity example validate cleanly.
- Every validation rule in FR-01 and FR-02 has at least one failing fixture with the expected error code.
- A plain-English requirement produces a valid draft spec, with assumptions listed separately.
- Importing `examples/frontend/revue-de-mode.json` produces a valid spec with a `Post` entity, list and get operations
  matching the page bindings, and its 8 records as seed data.
