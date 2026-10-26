# Epic 8 — Observability & tracing

## Overview

Trace every generation end to end in **LangSmith** (graph nodes, CLI invocations as child spans, **every model
call** inside them with model, tokens, latency and cost, validation checks, repair attempts), so you can see how
long each node and step takes, how many model calls it makes and what it costs. Mirror the same span tree into a **local trace store** so the UI can render a trace
view even when LangSmith is not configured. Mask secrets everywhere.

**Requirements:** FR-13, NFR 8.5 · **Open question:** Q7

## Trace shape (per generation)

```
generation gen_01H… (root, metadata: generation_id, owner, mode, engine, spec hash, prompt versions;
│                     totals: wall time, model calls, tokens, cost)
├── lane:backend            (dynamic mode: lanes run in parallel; backend-only mode has no lane level)
├── validate_spec
├── plan_architecture
├── generate_database
│   ├── engine:claude_code purpose=generate_database   (tokens, cost, turns, exit)
│   │   ├── llm:claude-opus-… #1   (input/output/cache tokens, latency, cost)
│   │   │   └── tool:Write src/modules/shared/infrastructure/models/task_model.py
│   │   ├── llm:claude-opus-… #2
│   │   └── …
│   └── sandbox:alembic_autogenerate
├── generate_backend …
├── run_validation#1 ── check:syntax ── check:lint ── … ── check:tests (failed)
├── repair_code#1 ── engine:claude_code purpose=repair_code
├── run_validation#2 …
├── package_artifacts
├── deploy_preview
├── lane:frontend           (Epic 13: frontend_plan, generate_frontend, validate_frontend, …)
└── integrate               (Epic 14: backend health, MOCK_TEST_API switch, live smoke)
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 8.1 | [LangSmith workflow tracing & secret masking](story8.1_langsmith_tracing.md) | 4.3 |
| 8.2 | [CLI invocation & validation spans](story8.2_cli_and_validation_spans.md) | 8.1, 3.2, 6.2 |
| 8.3 | [Local trace store & trace API](story8.3_local_trace_store.md) | 8.2 |
| 8.4 | [Model-call spans & cost accounting](story8.4_model_calls_and_cost.md) | 8.2 |

## Epic acceptance

- One generation creates one LangSmith trace whose run URL is stored on the job. The span tree matches the diagram.
- For any node the UI and LangSmith show the same wall time, number of model calls, tokens and cost; Antigravity
  costs are labelled *estimated*.
- A planted secret (`sk-ant-…`, `JWT_SECRET` value) appears in neither LangSmith, the local trace store, SSE events nor logs.
