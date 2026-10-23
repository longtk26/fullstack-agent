# Story 2.3 — Spec validation API & persistence

**Epic:** [2 — BackendSpec](epic2_backend_spec.md) · **Requirements:** FR-01 (preserve original), FR-02 · **Depends on:** 2.2, 1.4

## User story

As a UI user, I want live validation while I edit JSON, and my exact submitted spec stored, so that I can
reproduce any generation later.

## Acceptance criteria

- [ ] `POST /api/v1/specs/validate` (body: raw JSON text) → 200 with `ValidationReport`. Nothing is persisted.
      Used by the UI editor, debounced.
- [ ] `POST /api/v1/specs` → 201 `{specId}` if valid. 422 with the same error envelope if invalid.
      Stores `raw_json` byte-for-byte plus `normalized_json` and `spec_version`.
- [ ] `GET /api/v1/specs/{id}` returns raw and normalized versions. Scoped to the owner.
- [ ] Error envelope matches the global `BaseException` handler format:
      `{error: {code, message, details: [...issues]}}`.
- [ ] Request size limit (default 1 MB) → 413.
