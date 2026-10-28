# Story 9.9 — App tab: use the generated web app

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-18, FR-26, FR-27 · **Depends on:** 13.5, 14.2, 9.8, 7.3 (preview request log)

## User story

As a user, I want a place in the agent UI where I can open and really use the generated web app (its frontend
talking to its generated backend), so that I can judge the result by clicking through it, not by reading code.

## Acceptance criteria

- [x] Generation detail gets an **App** tab (static and dynamic modes) next to Steps / Trace / Results / API.
- [x] Full-size embedded frontend preview (iframe on the preview URL, sandboxed: `allow-scripts allow-forms
      allow-same-origin` only for the local preview origin) with:
  - a toolbar: address bar showing the current route, back / forward / reload, **page jumper** listing the
    FrontendSpec pages (title + route), **device sizes** (mobile 390, tablet 820, desktop), open in a new tab;
  - the **Mock API / Live API** badge, the backend URL in use, and *Re-check backend* / *Use mocks* / *Use live
    API* actions (14.2);
  - preview status (starting, running, stopped, failed) with start / restart controls (7.4, 13.5).
- [x] Side panel **Network** (dynamic mode): the backend calls the app makes while you use it — method, path,
      `operationId`, status, duration — read from the backend preview's request log (redacted), with a link to the
      same operation in the API tab (9.6) to replay it.
- [x] Side panel **Data**: shortcuts to the backend preview's tables via its list endpoints (e.g. "Products: 12
      rows"), refreshed after form submissions, so the user sees the effect of what they did in the app.
- [x] Empty states: "Preview not running" with *Start*, "Static site — no backend" (no Network/Data panels),
      "Backend not ready — running on mocks" with the reason.
- [x] v0-style hand-off (Q13): when a static or dynamic generation reaches COMPLETED / COMPLETED_WITH_WARNINGS
      and the frontend preview is running, the detail page switches to the App tab automatically (once per visit).
- [x] Works from the generations list too: an *Open app* action on rows with a running frontend preview.

**Status (2026-10-28):** done. `AppTab` implements the full-size sandboxed preview iframe, navigation toolbar with
route address bar, page jumper dropdown from the FrontendSpec, responsive device toggles (desktop, tablet 820px, mobile 390px),
status and mock/live actions (`recheckIntegration`, `sendUseMocksIntegration`), dynamic mode side panels (`AppNetworkPanel`
polling request logs with API replay links, and `AppDataPanel` querying backend tables with record inspection sheets),
v0-style automatic hand-off on completed generations, and an *Open app* row action in `GenerationsTable`.
