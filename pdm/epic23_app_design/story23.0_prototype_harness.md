# Story 23.0 — Prototype harness: see the epic's output before building it

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37 · **Depends on:** Epic 22

A gate before Checkpoint A, asked for by the user on 2026-11-06: run the epic's flow end to end on a few real
requirements with throwaway code, look at the UI, and decide whether the epic goes ahead as planned.

## User story

As the user, I want to give a few requirements to a prototype of the new flow (requirement → spec with a design
brief → UI) and look at the screens it produces, so that I know the epic gives the layouts and UX I expect before it
is implemented.

## Steps

1. **Requirements.** Three requirements in `agent-api/scripts/app_design_proto/requirements/`: a developer news feed,
   a video library, a learning platform (one area; areas wait for 23.10). They are written like the user's own
   requirements, not after a named product.
2. **Draft (real Gemini API, one call each, about $0.06).** A prototype prompt (`draft_app` v2 plus the design brief
   section, `scripts/app_design_proto/prompts/`) and the answer schema with `design` in the outline (enums only). The
   rest is the real app flow (`drafting/app.draft_app`: code fixes, repairs, `complete_outline`, aggregates,
   contract, screens). The prompt also asks for 6–9 seed rows per main entity so the screenshots show real content
   (prototype only). The draft is stored in `.data/prototypes/app-design/drafts/<app>/` and later builds reuse it
   (no new call).
3. **apply_design (prototype, code).** Checks the brief against the BackendSpec: a view needs its fields (media grid
   an image or a title, board a status flow, calendar a date); what doesn't fit is replaced and noted. Board and
   calendar are always replaced in the prototype (they need 23.4's backend work first).
4. **Build.** The real scaffold of the app (`scaffold_frontend`), plus a prototype overlay that changes only
   presentation and reads `src/content/design.json`: the top bar shell, media grid / feed / role-aware cards views, and
   twelve style recipes as CSS over the kit's `data-slot` components. `?look=<recipe>` switches the look at run time,
   `?proto=off` shows today's kit. Data hooks, bindings, forms and mocks are untouched. Built in the Node sandbox
   (`bga-runner-node`) like `make design-check-app`.
5. **Screens.** First-screen screenshots of the home, the main list and one detail, at 1440 and 375 px, light and
   dark: today's kit, then the brief's layout in each of its three looks. Written with `index.html` (side by side) to
   `.data/prototypes/app-design/<date>/`.
6. **Review (the gate).** The user looks at the screens and decides: go on with the epic as planned, change the
   design space, or stop.

## Acceptance criteria

- [ ] Three real drafts (three Gemini calls in total, plus repairs only if a draft is invalid) with a design brief each.
- [ ] Each app builds on the kit with the prototype overlay and passes its build.
- [ ] The review page shows, per app: the brief in words, what code replaced, and today's kit next to the brief's
      layout in three looks.
- [ ] No product code changes: everything lives in `scripts/app_design_proto/`; static golden passes.
- [ ] The user's decision is recorded in this Status.

## Verify

`make app-design-proto ARGS="draft"` (paid: three Gemini calls), then `make app-design-proto ARGS="build"` (no call),
open `.data/prototypes/app-design/<date>/index.html`.

## Status

**Done (2026-11-06). The user's decision: go, implement Epic 23** (with sample requirements for several product
types at the end). Built and reviewed: Harness: `agent-api/scripts/app_design_proto/` (`check`,
`draft`, `build`, `page`), `make app-design-proto`. Review page:
`.data/prototypes/app-design/2026-11-06/index.html` (129 screenshots: per app the home, the main list and one record,
today's kit next to the brief's layout in its three looks, at 1440 and 375 px, light and dark, plus six recipes the
brief did not pick on the same layout).

Drafts (Gemini API, `draft_app` v3proto, one call each, no repair; every BackendSpec valid):

| App | Time | Tokens in → out | Cost | Brief |
|---|---|---|---|---|
| news feed (DevPulse) | 60 s | 7.7K → 8.9K | $0.039 | feed · top bar · bottom tabs · home: feed · Post as feed (cover, summary, source, upvotes) |
| video library (StudioTube) | 52 s | 7.7K → 8.3K | $0.037 | catalogue · top bar · home: catalogue · Video as media grid (thumbnail, category, date, views) |
| learning platform (Learnly) | 124 s | 7.7K → 21.3K | $0.086 | learning · sidebar · home: dashboard · Course as media grid (cover, level, category, price) |

A fourth call ($0.03) drafted a smoke-test file left in the requirements folder by mistake; it was deleted. Total
$0.19 for four calls.

Findings for the epic:
- **The brief fits the data.** Each app got a different frame and main view, and each choice matches its records; code
  replaced nothing except where the answer's shape was off (below). Builds: 27–38 s each, 0 engine calls.
- **The answer schema was not followed exactly.** All three answers wrote `design.entities` as an object keyed by
  entity and `meta` as one string, not the schema's lists. The prototype reads both. 23.6 must find out whether Gemini
  received the schema (22.8 left this open) and keep code that accepts both shapes.
- **The model picks only safe looks.** Its nine looks were minimal (3), swiss (2), editorial (2), enterprise, soft; never
  glass, aurora, brutalist, neon, clay or playful, though the prompt lists them. If varied looks matter, 23.7 needs a
  rule (for example one bold look per draft) or code-picked alternatives; the gallery rows show those recipes on the
  same layouts.
- **Code's product ranking is weak for some requirements.** For the video library, UI UX Pro Max's ranking matched
  "library" to "Design System/Component Library"; the archetype was right by luck. 23.6 should not lean on it.
- **Duplicate roles.** The video brief used `category` as both subtitle and badge; `apply_design` should drop a field
  that already has a role.
- **Seen in the BackendSpec (not design):** Learnly's `Enrolment` copies `courseTitle` and `learnerName` instead of
  reading them from its parents.

**Round 2 (2026-11-06, the user asked for three more products and one that proves different UI per role).** The
prototype gained board, calendar and agenda views (display only over the loaded page: moving a card is the record's
menu, and date ranges need 23.4) and `areas` in the brief: the area follows the signed-in role at run time (Story
23.10 gives areas their own routes); screenshots sign in as each area's demo user.

| App | Calls | Cost | Brief |
|---|---|---|---|
| Studio Flow (agency projects) | 1 | $0.062 | back office · sidebar · home: dashboard · Task as a **board** by status |
| Bright Smile Clinic | 1 | $0.039 | booking · home: **agenda** · Appointment on a **calendar**; areas: front desk (sidebar, calendar, tables) and patient (top bar, dentists as a media grid) |
| Leafy Corner (plant shop) | 2 (1 repair) | $0.138 | storefront · top bar · home: catalogue · Plant as a media grid; areas: shopper (storefront) and owner (back office, sidebar, tables, dashboard) |
| Gather (event tickets) | 2 (1 repair) | $0.069 | areas: attendee (top bar, bottom tabs, poster grid) and organizer (sidebar, tables, dashboard) |

Ten Gemini calls over both rounds, $0.50 in total.

Findings, round 2:
- **The model chose areas on its own** for three of the four apps, including two whose requirements do not say the
  roles use the app differently (the clinic, the plant shop). Each area's layout fits its role.
- **The kit reads one list style per entity for the whole app**, so an area's table had to be forced per section
  (23.10 must carry the view per area, not per entity).
- **Permissions show through.** In Gather, attendees see the organizers' dashboard (revenue per event) and a status
  filter (drafts): the draft put no role policy on the aggregates and no visibility rule on events. The design is
  right, the backend rules are missing: Story 23.9, and `draft_app` should guard aggregates by role.
- The patient's appointment list is empty on mocks, which is right: ownership scopes it to the demo patient, who has
  no seeded appointment.
- Looks are still the safe set (swiss, minimal, editorial, soft) in all four.

Not prototyped: bento home, rail shell, Japanese, fonts per look (one font pairing is loaded per build, so a look
changes surfaces, not typefaces), images (the mock API has no files, so media are placeholders), dragging on the board.
