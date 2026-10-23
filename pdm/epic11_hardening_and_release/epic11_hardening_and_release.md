# Epic 11 — Hardening, benchmark & release

## Overview

Prove the MVP Definition of Done (§10) automatically, measure the ≥ 90% success target on a benchmark set,
verify the security NFRs, and document setup and usage.

**Requirements:** §10, §12, NFR 8.1–8.5

## Stories

| # | Story | Depends on |
|---|---|---|
| 11.1 | [End-to-end MVP acceptance test](story11.1_e2e_mvp_acceptance.md) | Epics 4–9 |
| 11.2 | [Benchmark set & LangSmith evaluation](story11.2_benchmark_and_evaluation.md) | 11.1, 8.1 |
| 11.3 | [Security hardening review](story11.3_security_hardening.md) | Epics 3, 6, 7 |
| 11.4 | [Documentation](story11.4_documentation.md) | all |

## Epic acceptance

- §10 scenario passes in `make e2e`. Benchmark pass rate is reported, with a 90% target. The security checklist is signed off.
