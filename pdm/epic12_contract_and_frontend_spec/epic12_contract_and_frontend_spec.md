# Epic 12 — Generation modes, FrontendSpec & API contract

## Overview

The agent no longer generates only backends. A user picks one of three **generation modes**:

| Mode | Builds | Contract | Backend |
|---|---|---|---|
| `backend` | FastAPI backend only (Epics 5–7, unchanged) | OpenAPI exported after generation | yes |
| `static` | Frontend only: static pages, content baked in | none | **no** |
| `dynamic` | Frontend **and** backend, generated **in parallel** | **contract first**: one OpenAPI document both sides are generated from | yes |

The frontend is described by a new **FrontendSpec** JSON (pages, theme, layout, components, data bindings,
forms, content), the frontend counterpart of BackendSpec. In `dynamic` mode the **API contract** (OpenAPI 3.1)
is derived deterministically from the BackendSpec plan *before* either side is generated, so the frontend can
start immediately against mocks of that contract while the backend is being built (Epic 14).

**Requirements:** FR-21 (modes), FR-22 (FrontendSpec), FR-23 (API contract), FR-24 (drafting) — requirements v1.2

```
 requirement ──draft (12.4)──▶ FrontendSpec ──┐
                                 (dynamic) ──▶ BackendSpec ──plan (5.1)──▶ API contract (12.3)
                                               │                             │
                         consistency check (12.5): every frontend binding exists in the contract
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 12.1 | [FrontendSpec 1.0 schema & validation](story12.1_frontend_spec_schema.md) | 2.1, 2.3 |
| 12.2 | [Generation modes & job model](story12.2_generation_modes.md) | 4.1 |
| 12.3 | [API contract generation (contract first)](story12.3_api_contract.md) | 5.1 |
| 12.4 | [Requirement → FrontendSpec (+ BackendSpec) drafting](story12.4_requirement_drafting.md) | 12.1, 2.4, 3.2 |
| 12.5 | [Frontend ↔ contract consistency check](story12.5_consistency_check.md) | 12.1, 12.3 |

## Epic acceptance

- A requirement such as "a small shop: product catalogue, product detail, cart, contact page" drafted in
  `dynamic` mode yields a valid FrontendSpec (pages, theme, components) and BackendSpec; their contract passes
  the consistency check; the same requirement in `static` mode yields a FrontendSpec with inline content and no
  backend or contract.
