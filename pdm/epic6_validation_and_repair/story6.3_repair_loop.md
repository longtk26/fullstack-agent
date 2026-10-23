# Story 6.3 — Repair loop (`repair_code`)

**Epic:** [6 — Validation & repair](epic6_validation_and_repair.md) · **Requirements:** FR-12, FR-09 (limit), §8.2 diagnostics · **Depends on:** 6.2

## User story

As a user, I want the agent to fix its own failures with targeted edits, within a limit, and if it gives up, to
explain exactly why.

## Acceptance criteria

- [ ] `repair_code` increments `repair_attempts`. The prompt (`repair_code` v1) includes the failure digest, the
      skill reminder (the repair must keep fastapi-skills conventions), the list of implicated files (from tracebacks or lint locations; tests are only editable when the failure is
      in a test and the plan says the behaviour is wrong), and the rule "fix the root cause, don't delete tests
      or weaken assertions".
- [ ] Guardrail diff check after the engine runs: deleted or skipped tests, `# noqa` or `pytest.skip` additions, or changes to
      template- and overlay-owned files (`src/libs/**`, `src/configs/**`, `src/main.py`, `alembic/env.py`, `tests/conftest.py`,
      `docker-entrypoint.sh`) → the attempt is rejected and recorded as `repair_rejected`, and still counts toward the limit.
- [ ] Records `git diff --stat` + the full patch as artifact `repair-<n>.patch` and commits `node:repair_code attempt:<n>`.
- [ ] Routing: back to `run_validation` while `attempts < max`. Otherwise → END FAILED.
- [ ] On FAILED: `diagnostic-report.md` + `.json` artifact with the last results per check, failure digests per attempt,
      patches applied, an engine vs. validation failure split (NFR 8.5), and the unresolved spec items.
- [ ] An engine error (`cli_error`) during repair does not count as a code failure. It retries once, then FAILED `ENGINE_ERROR`.
