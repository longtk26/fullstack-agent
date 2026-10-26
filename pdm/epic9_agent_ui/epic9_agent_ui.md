# Epic 9 — Agent UI (Next.js)

## Overview

A Next.js app (nextjs-skills conventions) for driving the agent: **input** a requirement, BackendSpec JSON, or an
imported Frontend-Agent site JSON,
**watch** the LangGraph steps live, **inspect** the trace, **review** validation and artifacts, and **explore**
the generated OpenAPI with try-it calls against the running preview container.

**Requirements:** user UI requirements, FR-14, FR-15, FR-17

## Screens

```
 /login
 /generations                     list + status badges + "New generation"
 /usage                           Usage & traces: time, model calls, tokens, cost by engine / model / node (9.10)
 /generations/new                 mode: [Static website] [Dynamic web app] [Backend API only] (9.7)
                                  → [Requirement] [Import frontend JSON] [JSON] / [FrontendSpec] tabs → options → Submit
 /generations/[id]                header (status, engine, duration, cost, Cancel, LangSmith link)
     ├── Steps     (default)      live LangGraph diagram + event log
     ├── Trace                    per-node time / model calls / tokens / cost summary, waterfall, span drawer (9.4)
     ├── Results                  validation checks, artifacts, manifest, source browser
     ├── API                      OpenAPI explorer + try-it against preview, preview controls
     └── App                      the generated web app embedded and usable (frontend ↔ live backend),
                                  device sizes, page jumper, Mock/Live API switch, network + data panels (9.9)
```

## Library choices (beyond the skill defaults)

| Need | Choice | Note |
|---|---|---|
| JSON editing | `@monaco-editor/react` | JSON Schema from 2.1 gives autocomplete and inline markers |
| Graph view | `@xyflow/react` (React Flow) + `dagre` layout | nodes and edges from `GET /generations/graph` |
| OpenAPI explorer | `@scalar/api-reference-react` | try-it with the server URL set to the preview; alternative `swagger-ui-react` |
| SSE | native `EventSource` through a Next.js route-handler proxy | the cookie JWT is forwarded server-side |

## Stories

| # | Story | Depends on |
|---|---|---|
| 9.1 | [UI scaffold, auth & generations list](story9.1_ui_scaffold_auth_list.md) | 1.4, 4.1 |
| 9.2 | [Spec input: requirement, frontend import & JSON](story9.2_spec_input.md) | 9.1, 2.3 (2.4 Requirement tab, 2.5 Import tab) |
| 9.3 | [Live workflow step visualization](story9.3_step_visualization.md) | 9.1, 4.5 |
| 9.4 | [Trace viewer](story9.4_trace_viewer.md) | 9.3, 8.3 |
| 9.5 | [Results: validation, artifacts & source](story9.5_results_view.md) | 9.3, 7.2 |
| 9.6 | [OpenAPI explorer & try-it against preview](story9.6_openapi_explorer.md) | 9.5, 7.3 |
| 9.7 | [Mode selection & FrontendSpec review](story9.7_mode_selection_frontend_spec.md) | 9.2, 12.1, 12.2, 12.4 |
| 9.8 | [Parallel run view & live-API switch](story9.8_parallel_run_view.md) | 9.3, 14.1, 14.2 |
| 9.9 | [App tab: use the generated web app](story9.9_app_preview_tab.md) | 13.5, 14.2, 9.8 |
| 9.10 | [Usage & traces page](story9.10_usage_and_traces_page.md) | 8.4, 9.4 |

**Status (2026-10-23):** 9.1–9.3 done on `feat/epic9-agent-ui` (Requirement tab and "Refine with AI" wait for 2.4).
Trace, Results and API tabs exist with placeholders for 9.4–9.6; Results already lists the latest validation checks.
Code: `agent-ui/src/features/{auth,generations,specs}`, `agent-ui/src/app/api/proxy`.

## Epic acceptance

- From the UI alone, a user can paste the two-entity spec, generate, watch the steps live, see the repair
  loop if one happens, open the trace, download the ZIP, and successfully call `POST /tasks` then `GET /tasks`
  on the running preview.
