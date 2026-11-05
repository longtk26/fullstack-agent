# Epic 22 — Dynamic app frontend: screens from the contract, separate from static sites

## Overview

Planned 2026-11-05 with the user. Today a dynamic app's frontend is drafted like a static site: direction cards,
library sections, then one designed element tree per page (Epic 21). The result is slow to draft and hard to use. This
epic gives dynamic mode **its own frontend flow**: the model drafts a small app outline next to the BackendSpec, and
code builds every screen from the contract with one app kit on shadcn. **Static mode does not change**: it keeps
Epics 20 and 21 as they are, and a static golden test proves it.

Starts after Epic 10's backend checkpoints (the user's order: backend first).

| Finding (2026-11-05) | Effect |
|---|---|
| The book club draft (Gemini Flash) took 4 min 16 s: draft 64 s, one repair 39 s, then 6 page trees, 4 at a time, 30–96 s each (~147 s) | More than half the draft is designing page layouts |
| Three sources of style: UI UX Pro Max data picks a direction, each tree is "a designer with a free hand over Tailwind and shadcn", library sections and shadcn components bring their own spacing | Pages that do not agree with each other, and a UI that is hard to use (the user's review) |
| Each tree is drafted alone, in parallel, by a fast model, with no view of the other pages and no visual check | Headers, spacing and density drift from page to page |
| Trees cannot hold `form` or `input`; writes are a generic `RecordForm` placed wherever the tree puts it; fields are guessed from a sample record (22.5 evidence) | Forms that ask for ids, text boxes for every type, no validation |
| Operations no screen uses go to a generated Manage area (19.7) | Two UIs in one app: designed pages and an admin area |

**Requirements:** FR-36 (new), FR-35, FR-32, FR-25; requirements v1.9.

## Decisions (2026-11-05)

| # | Decision | Instead of |
|---|---|---|
| D1 | **Static and dynamic are separate frontend flows** from the draft on. Dynamic-only code, prompts and overlay files live apart (`orchestrator/frontend/app/`, `prompts/draft_app/`, overlay `files/dynamic/app/`); a change to shared code must leave the static golden output unchanged | One flow for both modes, where a fix for apps changes sites |
| D2 | **Code designs the screens; the model drafts what the app is**: entities to show, navigation, labels, which fields a list shows, the dashboard figures. No trees and no direction cards in dynamic mode | The model designing each page's layout |
| D3 | **One app kit on shadcn** (sidebar, table, card, field, calendar, command, chart, empty, breadcrumb, sheet, dialog: all already in the base). The theme comes from the code-picked direction (UI UX Pro Max data, no model call): colours, fonts, radius, density only | Free Tailwind layouts per page |
| D4 | **Every operation has a screen or an action** by construction (list, detail, create, edit, delete, custom operations as actions, aggregates on the dashboard); the Manage area is not used in dynamic mode | Coverage checks plus a fallback admin area |
| D5 | **No engine call in the dynamic frontend lane**: anything the kit cannot show is noted in `unresolved`, not handed to the engine | Custom components written by the engine (17.3) |
| D6 | The current dynamic flow stays behind `DYNAMIC_FRONTEND=legacy` until 22.8 is accepted, then it is removed from dynamic mode (static keeps it) | A hard switch |

Generated frontend tests and journeys stay off (decision FE-TESTS); the criteria are proven by agent tests on the
generated code, build and typecheck, and the preview.

## Stories

Four checkpoints; stop for the user's review after each one.

| Checkpoint | # | Story | Depends on |
|---|---|---|---|
| **A: the flow** | 22.1 | [Separate flows and a static guard](story22.1_separate_flows.md) | Epic 21 |
| | 22.2 | [Drafting a dynamic app](story22.2_app_drafting.md) | 22.1 |
| | 22.3 | [Screens from the contract](story22.3_screen_planner.md) | 22.2, 10.0b |
| | 22.4 | [App kit: shell, lists, details, dashboard](story22.4_app_kit.md) | 22.3 |
| **B: forms** | 22.5 | [Form kit](story22.5_form_kit.md) (was 10.0a) | 22.4 |
| | 22.6 | [Reference pickers and readable references](story22.6_reference_pickers.md) (frontend half of 10.0b) | 22.5 |
| **C: plugins** | 22.7 | [Plugin frontends: auth, roles, rules, uploads, payments, relations](story22.7_plugin_frontends.md) | 22.6, Epic 10 |
| **D: switch over** | 22.8 | [Design checks, measurement and switch-over](story22.8_switch_over.md) | 22.7 |

## The flow

```
requirement ──(one API call)──▶ BackendSpec + app outline        (static: unchanged, Epics 20–21)
                                      │
                    code: direction (theme only), screen planner (22.3), field sources (10.0b)
                                      │
                                      ▼
            FrontendSpec pages of app sections ──▶ contract-bound kit components (22.4–22.7)
                                      │
                              renderer (no engine) ──▶ build, typecheck, preview on mocks, then live
```

The FrontendSpec stays the one format: the planner writes ordinary pages whose sections are the kit's app sections
(`AppList`, `AppDetail`, `AppForm`, `AppDashboard`, `AppActions`), so the spec editor, revisions (Epic 16) and the
pair check keep working. App sections are accepted only in dynamic mode.

## Epic acceptance

- A dynamic draft makes one model call (plus a repair only when validation fails) and takes about 90 s or less on
  Gemini Flash for the book club, flashcards and project-tracker requirements; the static draft is unchanged.
- The static golden test passes at every step of this epic: the static examples draft and render byte for byte as
  before.
- Every operation of the contract is reachable from a screen; no form shows an id input; dates use the calendar;
  parents show by label; server errors show on their field.
- The workshop-bookings app (Epic 10's golden spec): sign-up and sign-in, a booking created from the workshop's page,
  an image uploaded, a fake payment, and actions hidden from users without the role, on mocks and live.
- The user reviews screenshots of three apps (light and dark, 375 px and 1440 px) against the legacy flow and accepts
  the switch.
