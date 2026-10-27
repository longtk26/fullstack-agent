# Epic 16 — Site revisions & feedback

## Overview

A finished generation is not the end: the user looks at the preview and wants changes — "darker primary
colour", "make the hero shorter", "cards in two columns on mobile". This epic turns that feedback into
**revisions**: small jobs that start from the finished frontend, change it, validate it with the same checks and
repair loop, and redeploy the preview. Each revision is a commit in the frontend repository, so it can be diffed
and restored.

Two kinds of revision:

| Kind | Examples | How | Engine call |
|---|---|---|---|
| **Spec edit** | theme colours, fonts, radius, light/dark; section text; navigation labels; swapping an asset | patch the FrontendSpec, regenerate the owned files with the same code as the scaffold (theme CSS, content JSON, site config, asset registry) | **no** (generated SVGs only when their prompt changes) |
| **Feedback** | "make the hero shorter", "show the price under the title" | the user's comment plus the files of the targeted section / component / page go to the engine, scoped to those files | yes |

The frontend plan already maps every component to its file, hook and pages, which is what makes the scope narrow.
Owned files stay protected: feedback that would need generated code (API client, types, mocks, forms) to change
is a spec change, not an edit.

Scope: **frontend only** (static and dynamic). In dynamic mode the contract is fixed (FR-23): a revision cannot
add operations or change bindings to unknown ones; the report says the change needs a backend spec change.
Backend revisions, adding or removing pages, and new data bindings are out of scope here.

**Requirements:** FR-29 (revisions and feedback) — requirements v1.3

```
 preview (inspect mode) ─click a section─▶ comment ─┐
 theme / content editor (live preview) ─────────────┤
                                                    ▼
                    POST /generations/{id}/revisions   (kind: spec | feedback | restore)
                                                    │
                restore_workspace  (kept 72 h; afterwards from frontend.zip + frontend.bundle)
                                                    │
        spec:     patch FrontendSpec ─▶ regenerate owned files            ┐
        feedback: revise_frontend (engine, scoped to the target's files)  ┘─▶ validate_frontend ⇄ repair_frontend
                                                    │
                       package (revision N) ─▶ preview rebuilt (image tag per revision)
                                                    │
                      commit "revision:N" · history · diff · restore   (failure: preview keeps revision N-1)
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 16.1 | [Revisions: model, jobs & workspace restore](story16.1_revision_jobs.md) | 13.5, 4.3 |
| 16.2 | [Spec edits: theme, content & assets](story16.2_spec_edits.md) | 16.1, 15.1 |
| 16.3 | [Feedback on a section, component or page](story16.3_feedback_edits.md) | 16.1, 13.3 |
| 16.4 | [Inspect mode in the preview](story16.4_inspect_mode.md) | 16.3, 9.9 |
| 16.5 | [Revision history, diff & restore](story16.5_history_and_restore.md) | 16.1, 9.5 |

## Epic acceptance

- `static-landing` generated with the fake engine → change the primary colour and radius in the theme editor →
  revision 1 completes **without an engine call** in under 2 minutes; the preview shows the new colours, generated
  SVG illustrations recolour with it, and the diff touches only `globals.css` and the manifest.
- Inspect mode: click the hero, comment "shorter heading, add a second button" → revision 2 (fake engine) changes
  only the hero's files, passes every frontend check, and the preview refreshes; restoring revision 1 works.
- After the workspace retention cleanup, a new revision still works (restored from the artifacts).
- `project-tracker-dynamic`: feedback that needs an endpoint the contract does not have fails cleanly with the
  contract explanation, and the preview keeps serving the previous revision.
