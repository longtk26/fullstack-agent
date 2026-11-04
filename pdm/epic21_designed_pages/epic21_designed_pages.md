# Epic 21 — Designed pages: element trees for static and dynamic sites (proposal)

**Status:** approved by the user 2026-11-03 (all proposed decisions below); nothing implemented yet. Starts after
18.10 (drafts through the API), with 21.1 (measurement). **Requirements:** FR-33, FR-22, FR-20.

## Why

Our sites look like templates because the model picks from a menu: a FrontendSpec page is a list of library sections
(Hero, Features, Stats, …) with typed props and a few variants. Epic 20 enlarged the menu (8 hero layouts, section
forms, tone tokens, icons, motion) but the layout is still ours, not the model's.

`sample.json` (a Frontend-Agent site JSON, the format FR-20 already imports) shows the other way. For a four-page
Japanese anniversary site the model wrote **811 nodes**, up to 10 levels deep:

- every block designed: a 12-column grid with reordered columns, a product card overlapping the headline
  (`lg:-mt-14`), blurred colour blobs, a rotated badge, mono "LOT #01" labels, a serif-italic line over a black
  headline, a wavy underline, an opening sequence;
- its own decoration per page (`.picnic-gingham-bg`, `.picnic-rug-pattern`: patterns from theme tokens);
- motion per element (`animate: {on: "view", type: "fade-up", delay: 0.2}`);
- data where it is needed, as components inside the tree: `CollectionBrowser`, `ItemList`, `RecordField`,
  `RecordImage`, `RecordPrice`, `FacetFilter`, `SearchBox`, `Pagination`, `AddToCartButton`;
- Lucide icons by name; shadcn primitives (`Tabs`, `Sheet`) by name.

The variety comes from **who designs the layout**. This epic lets the model design it, keeps everything that must be
exact in code, and works for dynamic apps as well as static sites.

## The format (as `sample.json` and the importer use it)

```json
{ "name": "…", "language": "ja",
  "collections": [{ "key": "products", "kind": "products", "name": "…", "records": [{ "id": "…", "name": "…", "price": 1200 }] }],
  "chrome": <node>, "footer": <node>,
  "pages": [{ "slug": "home", "name": "…", "tree": <node>, "css": ".picnic-gingham-bg { … }" }] }
```

A node is `{ "type", "props", "children" }`: an HTML element (`section`, `div`, `h1`, `img`, …), a Lucide icon
(`Sparkles`), a primitive (`Tabs`, `Sheet`, `Link`), or a **data component** (`CollectionBrowser`, `RecordField`, …).
Props are `className` (Tailwind), attributes, `animate`, and the data component's own props.

## Static mode

1. **Draft** (one API request per page, in parallel, from 18.10's engine): the requirement and the chosen direction
   (fonts, palette, tone, icons, motion from the direction cards, now a design brief) → `chrome`, `footer`, the pages'
   trees and CSS, collections for any lists (menus, products, team).
2. **Check and fix in code** (no model): allowed types, class rules, CSS scope, links, images, contrast (below).
3. **Render** deterministically: a tree renderer maps nodes to elements, icons, primitives and data components;
   collections are local data. No engine call, seconds, as today's section renderer.

## Dynamic mode

The same trees; the difference is where data comes from and goes to. **The tree's data components declare what the
app needs; code derives the API from them.** This is the frontend-first flow discussed on 2026-11-03 (the frontend
shapes the API, the backend completes it), done deterministically by the importer instead of two negotiating agents.

```
requirement ──(API)──▶ site tree + collections (entities with sample records)
                           │
                           ▼  importer (code, extended)
                      BackendSpec ──▶ OpenAPI contract ──▶ mocks (collections' records = seed + examples)
                           │                    │
                           ▼                    ▼
          backend: CRUD + aggregates      frontend: tree renderer; data components
          from templates; engine only     bound to the contract's operations
          for truly custom logic          (mock API until the backend is live)
```

### Data components for dynamic apps

| Kind | Components | Derived operation (importer) |
|---|---|---|
| Read lists (exist) | `CollectionBrowser`, `CollectionStrip`, `ItemList`, `SearchBox`, `CategoryFilter` / `FacetFilter`, `SortControl`, `Pagination`, `ResultCount` | `list` with the filters, search fields and sort fields the controls use |
| Read one (exists) | `CollectionDetail`, `RecordField`, `RecordImage`, `RecordPrice`, `RecordLink`, `RecordStars` | `get` by id (detail pages `/x/[id]`) |
| **Write (new)** | `RecordForm` (`mode: create / edit`, fields), `RecordAction` (`delete`, `set` a field such as status), `AddToCartButton` | `create`, `update`, `delete`; required fields and types from the form |
| **Aggregate (new)** | `Metric` (`count` / `sum` / `avg` / `min` / `max` of a field, with a filter, e.g. active members, total spent this month), `Chart` (series grouped by a field or by day / week / month) | an **aggregate operation** generated from templates, no engine |
| **States (new)** | `Loading`, `Empty`, `Error` slots inside any data component | none; the renderer shows them |
| **App chrome (new)** | `AppShell` (sidebar with icons, top bar), `ThemeToggle` | none |

### What this changes for the backend

- **Aggregates stop being custom operations.** Today's two slow backends were aggregates: the gym's figures
  (active members, bookings today, average fill) and the money tracker's summary (total spent, budget, remaining).
  Each was a custom operation: an engine call (~8 min), engine-written tests and repairs. With `Metric` and `Chart`
  the importer emits `aggregate` operations (`GET /consumptions/aggregate?fn=sum&field=amount&period=month`, or one
  named operation per metric), and the backend templates write them like CRUD: seconds, always correct.
- **Custom logic stays possible** (`spotsLeft` = capacity − bookings, recalculating budgets): a data component may
  name an operation the importer cannot derive; it becomes a custom operation with a description, as today, and the
  engine writes only that (with 18.11's focused prompt).
- The contract, mocks, previews, conformance check and integration lane are unchanged: they already work from the
  BackendSpec.

### Example: the money tracker's dashboard as a tree (abridged)

```json
{ "type": "main", "props": { "className": "flex flex-col gap-6 p-6" }, "children": [
  { "type": "div", "props": { "className": "flex items-end justify-between gap-4" }, "children": [
    { "type": "div", "children": [
      { "type": "h1", "props": { "className": "font-heading text-2xl font-semibold" }, "children": ["Dashboard"] },
      { "type": "p", "props": { "className": "text-sm text-muted-foreground" }, "children": ["This month at a glance"] } ] },
    { "type": "Link", "props": { "to": "page:record", "className": "btn-primary" }, "children": ["Record expense"] } ] },
  { "type": "div", "props": { "className": "grid gap-4 sm:grid-cols-2 lg:grid-cols-4" }, "children": [
    { "type": "Metric", "props": { "collection": "expenses", "fn": "sum", "field": "amount", "period": "month",
      "label": "Spent this month", "format": "money", "icon": "Wallet" } },
    { "type": "Metric", "props": { "collection": "expenses", "fn": "count", "period": "month", "label": "Transactions" } } ] },
  { "type": "Chart", "props": { "collection": "expenses", "kind": "bar", "fn": "sum", "field": "amount",
    "groupBy": "category", "className": "h-72 rounded-xl border p-4" } },
  { "type": "CollectionBrowser", "props": { "collection": "expenses", "pageSize": 10, "sortBy": "-spentAt" }, "children": [
    { "type": "ItemList", "props": { "className": "divide-y rounded-xl border" }, "children": [
      { "type": "div", "props": { "className": "flex items-center justify-between p-3" }, "children": [
        { "type": "RecordField", "props": { "field": "title", "className": "font-medium" } },
        { "type": "RecordPrice", "props": { "field": "amount" } } ] } ] },
    { "type": "Empty", "children": ["No expenses yet"] } ] } ] }
```

From this the importer derives `expense.list` (sort `spentAt`), two aggregates (sum of `amount` this month, count
this month), one grouped aggregate (sum by `category`), the `expenses` entity from the collection's records, and the
seed. The design (layout, density, colour) is the model's; the data is ours.

## Guard rails (all code, before rendering)

- **Allowed types:** HTML elements (no `script`, `iframe`, `form` outside `RecordForm`), Lucide icons that exist in
  the pinned index, a list of shadcn primitives, our data components. Unknown → removed with a note.
- **Classes:** Tailwind only; colours only through theme tokens (`bg-primary/10`, `text-muted-foreground`), no raw
  hex or arbitrary colour values; arbitrary sizes allowed within limits.
- **Page CSS:** scoped to the page, only backgrounds, patterns, masks, gradients from tokens; no `position: fixed`
  outside the chrome, no external URLs.
- **`animate`:** mapped onto 20.6's motion engine (reduced motion and no-JavaScript keep everything visible; the
  hero and primary action within 600 ms).
- **Accessibility:** one `h1` per page, alt text on images, link text, contrast measured in the design check (light
  and dark).
- **Data components:** every one must resolve to a contract operation (the pair check, as today); unresolved ones are
  repaired by code first, then by one patch round (18.10).

## What stays and what changes

| Part | Fate |
|---|---|
| Contract, mocks, previews, conformance, integration lane | Unchanged |
| Backend templates (CRUD) | Unchanged; plus `aggregate` operations |
| Importer (2.5) | Becomes the core of dynamic mode: extended for writes, aggregates, states |
| FrontendSpec | Pages may be `tree` pages (additive); section pages keep working |
| Section library | Kept: usable as nodes inside trees (`{"type": "Faq", …}`) and for existing specs |
| Direction cards (20.4), tone, fonts, icons, motion (20.3–20.6) | The design brief for the tree prompt; theme tokens unchanged |
| Story 20.11 (app pages) | Mostly superseded: app pages are trees with `AppShell`, `Metric`, `Chart`, `RecordForm`; its route-order bug fix and calm-app theme rules stay |
| Epic 16 (revisions) | Revisions become region edits on a tree ("redo this block", "calmer"), with the visual feedback loop there |

## Cost and speed

- Output per page ≈ 5–12 k tokens (`sample.json`: 5–12 k per page, ~35 k for four pages) against 1–2 k for a section
  page. Through the API (18.10) with pages in parallel: ~1–2 min for a site.
- Backend for apps like the gym or the money tracker: from ~20 min (two custom operations through the engine) to
  ~1–2 min when their figures are aggregates.
- Quality depends on the model; Flash may write plainer trees than the model behind `sample.json`. Measure first.

## Risks

- Free trees can break responsiveness or accessibility: the guard rails and the design check (overflow at 375 px,
  contrast, one `h1`) must be strict.
- Larger outputs mean more chances of malformed JSON: one request per page, JSON mode, a patch round for errors.
- Revisions on trees are less structured than on typed props (Epic 16 has to plan region edits).

## Decisions (approved by the user, 2026-11-03)

| # | Question | Answer |
|---|---|---|
| 1 | Tree pages for static, dynamic or both | Both; dynamic is where the gain is largest (aggregates) |
| 2 | Keep section pages | Yes, as building blocks and for existing specs; new drafts write trees |
| 3 | Aggregates as templated operations | Yes: `Metric` and `Chart` derive them; no engine |
| 4 | Model for trees | The API's Flash first; compare with a stronger model on the same requirements |
| 5 | 20.11 | Keep its route-order fix and app theme rules; build app pages as trees |
| 6 | Order | 18.10 → this epic's measurement story → the rest |

## Stories

| # | Story | State (2026-11-04) |
|---|---|---|
| 21.1 | [Measurement: section pages against designed pages](story21.1_measurement.md) | ready to run; needs the user's yes (paid) |
| 21.2 | [Tree renderer](story21.2_tree_renderer.md) | done |
| 21.3 | [Guard rails](story21.3_guard_rails.md) | done |
| 21.4 | [Data components](story21.4_data_components.md) | done (no `AppShell`: sidebar shells keep their own sidebar) |
| 21.5 | [Aggregates without the engine; the trees' operations in the BackendSpec](story21.5_aggregates_and_importer.md) | done |
| 21.6 | [Drafting designed pages](story21.6_drafting_trees.md) | done for the flow and the fake engine |
| 21.7 | [Design check and diversity report on designed pages](story21.7_checks_on_trees.md) | done for the fixture and the checklist |

## Status

**Implemented (2026-11-04)** on `feat/story18.10-api-drafts`, with 18.10, not committed: the user reviews the
static and dynamic output with `make up` first. What the user will see: every draft (fake or real engine) designs
its pages as trees (`FRONTEND_TREES=true`); the section-library fixture's `/designed` page shows the renderer's
range; a dashboard's figures come from templated aggregate operations. Open: 21.1's paid measurement, a real-engine
tree's quality (the prompt is written for the Gemini API engine, one request per page), and the `AppShell`.

**Fixes (2026-11-04)**, on `feat/story18.12-lane-previews`, from the first real dynamic run with trees
(`gen_01M6J88EY82D746ZG01MB7WE77`, draft `a4c35e2f…`: 5 of 6 pages and the chrome drawn as trees):
- **Old Lucide names.** The engine wrote `AlertTriangle`, `AlertCircle`, `CheckCircle2`, `Sliders`, `History`: names
  lucide-react still exports as aliases but the icon index did not know, so `fix_trees` unwrapped them (10 icons
  silently gone). `scripts/icon-index.mjs` now records lucide-react's 267 aliases (`lucide.aliases`;
  `make icon-index` rebuilds only the index), `icons.lucide_current` maps an old name to the current one, and
  `fix_trees` renames the node (`AlertTriangle` → `TriangleAlert`) with a note; `resolve_icon` accepts old names too.
- **One wrong Metric cost the home page its tree.** "Designed page dropped (Metric 'fn' is one of count, sum, avg,
  min, max)". `fix_trees` now maps a Metric's `fn` (`average` → `avg`, `total` → `sum` with a field, else `count`,
  …; an unknown `fn` without a field counts) and a Chart's `kind` (`pie` → `donut`, an unknown kind → `bar`); a
  Metric that stays unclear is dropped alone, so the page keeps its design.
- **Sites without trees did not typecheck.** `PageRenderer.tsx` and `SiteShell.tsx` import `tree/TreeRenderer`, but
  `library_files` skipped the whole tree folder for them (8 frontend sandbox tests failed: TS2307). Such a site now
  gets `TreeRenderer.none.tsx` (renders nothing) as `tree/TreeRenderer.tsx`.
