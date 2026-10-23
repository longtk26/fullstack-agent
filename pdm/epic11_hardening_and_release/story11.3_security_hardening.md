# Story 11.3 — Security hardening review

**Epic:** [11 — Hardening](epic11_hardening_and_release.md) · **Requirements:** NFR 8.1

## User story

As the security owner, I want every NFR 8.1 control verified by a test or a documented decision.

## Acceptance criteria

- [ ] Checklist with evidence (test name or doc link) for: workspace isolation, per-job sandbox, no production secrets
      in the sandbox, filesystem restriction, container limits, network allowlist (PyPI only during install,
      none during checks), CLI tool restriction (no shell for the engine), no auto-deploy beyond local previews bound to
      127.0.0.1, and untrusted-input handling (prompt delimiting, argv arrays, path traversal tests).
- [ ] Known risks documented with mitigations: Docker socket on the worker (root-equivalent), engine API keys present
      in the worker, and prompt injection through spec text.
- [ ] Redaction tests for SSE, logs, traces and artifacts using planted secrets (see the 8.x acceptance criteria).
