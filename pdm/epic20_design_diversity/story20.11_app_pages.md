# Story 20.11 — App pages look like apps (dynamic mode)

**Epic:** [20 — Design diversity](epic20_design_diversity.md) · **Requirements:** FR-33, FR-22 · **Depends on:** 20.2,
20.3, 20.4, 20.5, 20.8, 19.6

## User story

As a user generating a dynamic app (a tracker, a dashboard, a back office), I want screens that look like a
well-made product (a page header with actions, figures with values, charts, tables, a calm palette and a clear
sidebar), not like a marketing page, so that the app is acceptable to show without rework, as an app vibe-coded
with `nextjs-skills` would be.

## Context: what a generated app looks like today (2026-11-03)

The money tracker (`gen_01M6G7E72P1TREWZ95T76WWYGP`, direction "Precision Ledger", sidebar shell), screenshot of its
dashboard at 1440 px:

| What you see | Why (from the spec and the code) |
|---|---|
| A 70 px, three-line headline "Money consumption dashboard" with an eyebrow and two buttons | The dashboard page starts with a `Hero`; the library and the drafting prompt treat every page like a landing page, and Epic 20 pushed for distinctive heroes |
| A large empty gradient box beside it | `keyVisual: "product"`: an image slot with no image (photos off or not drawn), shown as a placeholder |
| The four figure cards show only an icon and a label | **A bug:** the mock API registers `GET /consumptions/:id` before `GET /consumptions/summary`, so the summary request is answered by "get one record" with id `summary` (404) and the stat values stay empty. The backend router may order them the same way |
| A solid green band behind the figures, dark text on it, cards a darker green, icons barely visible | `colorArea: "block"` from the tone; contrast is checked for text pairs only, not for balance |
| Mint background, mint sidebar, green everywhere | `background: #f0fdf4` (a tinted background from the card); nothing keeps app backgrounds neutral |
| Light only | `colorScheme: "light"` from the card |
| Sidebar: plain text items; top bar: only the collapse button | The sidebar shell draws labels only; the top bar has no page title or actions |

What makes agent-ui (and apps vibe-coded with the skills) look good is mostly convention, not artistry: shadcn
base-nova on a neutral background, one accent colour, compact type, a page header with the main actions, cards with a
hairline border, real-looking data in every figure and table, icons in the navigation, light and dark. All of that is
deterministic and fits the renderer.

## Proposal

### 0. Fix the route order (bug, before anything else)

Static path segments before parameters, everywhere routes are registered: the mock handlers (`operations.json`
order), the generated backend routers (plan order), and the Next.js bindings if they match paths. A test with a
`/x/summary` beside `/x/{id}`.

### 1. App pages versus site pages

A page is an **app page** when the site is dynamic and the page reads or writes data (a section bound to an operation,
a form with an operation), or when the shell is `sidebar`. Site pages (landing, about, pricing) keep everything
Epic 20 built. On app pages:

- **No Hero.** A new `PageHeader` section: title, one line of description, the page's main actions on the right
  (primary + secondary), optional breadcrumbs on detail pages. The drafting prompt asks for it; the validator flags a
  Hero on an app page (`FE_DESIGN_RULE`); code converts one to a `PageHeader` (heading, text and actions carry over).
- **No key visual.** Image slots on app pages are left out (no placeholders).
- **Layout:** sections stack with app spacing (24–32 px), not marketing rhythm; page width full with a max width for
  readability on forms and details.

### 2. App sections the library lacks

- **`Stats` form `kpi`:** label, large value, optional change (`delta` with up/down tone) and icon; skeleton while
  loading; "—" with a muted tone when there is no value; never an empty card. Number formatting by field type
  (money, percent, count).
- **`Chart`:** bar, line, area or donut from a list operation (or a custom list) with `x`, `y` and an optional
  `groupBy` / aggregate (`count`, `sum`); shadcn's `chart` primitive and `recharts` are already in the base. Colours
  from `--chart-1…5` tokens derived from the primary.
- **`EmptyState`:** an icon, one sentence and the action that fills it ("No expenses yet · Record expense"); every
  list section shows it on an empty result instead of a blank table.
- **`DataTable` app defaults:** compact rows, sticky header, right-aligned numbers, status as badges, row actions in a
  menu.

### 3. A calm theme for apps

When the site is an app (dynamic with app pages), the direction's tone is mapped with app limits:

| Token | Site (today) | App |
|---|---|---|
| Background | any card colour | neutral: white / zinc-950 (a 1–2% tint of the primary at most) |
| `colorArea` | minimal … block | `minimal` (primary on buttons, the active nav item, links, charts, focus) |
| `surface` | flat / outline / raised | `outline` (hairline cards), `raised` only for popovers |
| `colorScheme` | from the card | `system` (light and dark) unless the requirement says otherwise |
| Display sizes | hero steps | none; page title ~24–30 px |
| `density` | from the tone | compact or default |
| Heading weight | 400–800 | 600 |

Directions for apps still differ (accent hue, heading font, radius, density, icon set and weight, sidebar style:
plain, tinted, or inverse), and the difference test uses those fields instead of hero layout and key visual.

### 4. The app frame

- Sidebar: an icon for every item (resolved from its label with `frontend_spec/icons.py`, e.g. "Budgets" → wallet),
  a clear active state, groups when there are more than six items, the app name with a small logo mark, a footer slot
  for the theme toggle.
- Top bar: the page title (or breadcrumbs) and the page's primary action on wide screens; the sidebar trigger on
  narrow ones.
- No site footer in app shells.

### 5. Never empty, never fake

- A figure, chart or table with no data shows its loading or empty state, never a blank.
- Previews of dynamic apps run on the mock API until the backend is live (as today); the mock serves the seed and the
  contract's examples for every operation, so a dashboard always has numbers.
- The drafting prompt gives each figure a realistic seed (records that make the sums meaningful), not one record.

### 6. Measuring it

- A dashboard fixture in `design_check_fixture` (sidebar, PageHeader, KPI stats, chart, table, empty state), light and
  dark, in every app direction; the checklist gains the app rules (no hero, no image placeholder, no empty figure,
  neutral background, nav icons).
- The diversity report gets an "app" set (tracker, dashboard, back office) and measures the app rules.

## Decisions for the user (proposed answers)

| # | Question | Proposed |
|---|---|---|
| 1 | What makes a page an app page | Dynamic mode and the page reads or writes data, or the shell is `sidebar` |
| 2 | Hero on app pages | Never; converted to `PageHeader` |
| 3 | App background | Neutral (white / zinc), at most a faint tint |
| 4 | Dark mode for apps | Light and dark by default (`system`) |
| 5 | Charts in the library | Yes: bar, line, area, donut |
| 6 | Order | Route-order fix now; the rest after 18.10 |

## Steps (once the decisions are agreed)

1. Route order (mocks, backend routers) with a test.
2. `PageHeader`, `Stats` `kpi` form, `Chart`, `EmptyState` in `section_props.py` and the library; DataTable app
   defaults; `FE_DESIGN_RULE` for a Hero on an app page and its code conversion.
3. App theme limits in `design_tone.py` / `design_cards.py` (fill and floor) and `frontend_theme.py`; difference test
   fields for apps.
4. Sidebar icons, active state, groups; top bar title and action (`SiteShell.sidebar.tsx`).
5. Drafting prompt (next version): app pages are built from PageHeader, KPI stats, charts, tables and forms; realistic
   seeds for figures.
6. Fixture, checklist, report; tests for each of the above.

## Acceptance criteria

- [ ] Figures bound to an operation show their values in previews (route order fixed, with a test).
- [ ] App pages have no Hero and no image placeholder; they open with a PageHeader.
- [ ] KPI figures, charts, tables and empty states render from operations, in light and dark.
- [ ] App themes are neutral with one accent; every sidebar item has an icon.
- [ ] Marketing and static sites render as before.
- [ ] The design check passes on the dashboard fixture in every app direction.

## Status

**Mostly superseded (2026-11-03)** by [Epic 21](../epic21_designed_pages/epic21_designed_pages.md) (approved): app
pages, sections and chrome are built as trees there. What stays: the route-order fix (0), done with 18.10, and the app
theme limits (3), applied in Epic 21's app pages.
