# Epic 8 — Observability & tracing

## Overview

Trace every generation end to end in **LangSmith** (graph nodes, CLI invocations as child spans, validation
checks, repair attempts). Mirror the same span tree into a **local trace store** so the UI can render a trace
view even when LangSmith is not configured. Mask secrets everywhere.

**Requirements:** FR-13, NFR 8.5 · **Open question:** Q7

## Trace shape (per generation)

```
generation gen_01H… (root, metadata: generation_id, owner, engine, spec hash, prompt versions)
├── validate_spec
├── plan_architecture
├── generate_database
│   ├── engine:claude_code purpose=generate_database   (tokens, cost, turns, exit)
│   │   ├── tool:Write src/modules/shared/infrastructure/models/task_model.py
│   │   └── …
│   └── sandbox:alembic_autogenerate
├── generate_backend …
├── run_validation#1 ── check:syntax ── check:lint ── … ── check:tests (failed)
├── repair_code#1 ── engine:claude_code purpose=repair_code
├── run_validation#2 …
├── package_artifacts
└── deploy_preview
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 8.1 | [LangSmith workflow tracing & secret masking](story8.1_langsmith_tracing.md) | 4.3 |
| 8.2 | [CLI invocation & validation spans](story8.2_cli_and_validation_spans.md) | 8.1, 3.2, 6.2 |
| 8.3 | [Local trace store & trace API](story8.3_local_trace_store.md) | 8.2 |

## Epic acceptance

- One generation creates one LangSmith trace whose run URL is stored on the job. The span tree matches the diagram.
- A planted secret (`sk-ant-…`, `JWT_SECRET` value) appears in neither LangSmith, the local trace store, SSE events nor logs.
