# Epic 10 — Advanced generation (auth, policies, rules)

## Overview

Phase 5 features: JWT authentication, role and ownership authorization, and declarative business rules,
each generated with tests covering **expected and rejected** behaviour. External integrations and background
jobs are accepted in the spec, but in the MVP they produce stubs plus explicit `unresolved` entries rather than
invented behaviour.

**Requirements:** FR-06, FR-07, Phase 5

## Stories

| # | Story | Depends on |
|---|---|---|
| 10.1 | [JWT authentication generation](story10.1_jwt_auth.md) | Epic 5–6 |
| 10.2 | [Role & ownership authorization](story10.2_rbac_and_ownership.md) | 10.1 |
| 10.3 | [Declarative business rules](story10.3_business_rules.md) | 10.2 |
| 10.4 | [Integrations & background jobs (stub + unresolved)](story10.4_integrations_and_jobs.md) | Epic 7 |

## Epic acceptance

- A spec with auth, an `ownerOnly` policy and a `transition` rule generates a backend where the tests prove that
  non-owners get 403/404, unauthenticated users get 401, and illegal transitions get 409, and all of these pass in validation.
