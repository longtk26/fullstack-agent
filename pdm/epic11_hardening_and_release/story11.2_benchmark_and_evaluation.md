# Story 11.2 — Benchmark set & LangSmith evaluation

**Epic:** [11 — Hardening](epic11_hardening_and_release.md) · **Requirements:** §10 success criterion, Phase 5 "better automated evaluation"

## User story

As the team, I want a fixed benchmark of in-scope CRUD specs scored automatically, so that we can track progress
towards ≥ 90% pass rate and compare engines and prompt versions.

## Acceptance criteria

- [ ] `benchmarks/specs/` holds ≥ 20 valid in-scope specs (including ones imported from frontend site JSON) (1–6 entities, all relationship types, filters and sorting,
      enums, defaults). It is versioned.
- [ ] `make bench ENGINE=claude_code|antigravity` runs them with bounded concurrency and uploads them as a LangSmith dataset and experiment.
      Evaluators: all checks passed (binary), `conventions` violations count, number of repair attempts, duration, cost, and operationId parity.
- [ ] Local summary `benchmarks/results/<date>-<engine>.md` (pass rate, failures by check, mean repairs, cost).
- [ ] The result is reported as measured, with no claim beyond the data.
