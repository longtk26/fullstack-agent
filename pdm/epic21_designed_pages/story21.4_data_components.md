# Story 21.4 — Data components for designed pages

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 21.2, 19.6

## User story

As a user, I want a designed page to show my records, figures and charts, and in a dynamic app to create, edit and
delete them, from components the engine places anywhere in its layout, so that app screens can be designed as freely
as marketing pages.

## Scope (`renderer/tree/tree-data.tsx`, `tree-metrics.tsx`, `tree-forms.tsx`)

| Kind | Components |
|---|---|
| Read lists | `CollectionBrowser` (search, category filter, sort and pages in the URL; client-side on a static site, request parameters on an app), `CollectionStrip` (`limit`, `sortBy`, `order`), `ItemList` (its children once per record), `SearchBox`, `CategoryFilter` / `FacetFilter`, `SortControl`, `Pagination`, `ResultCount` |
| Read one | `CollectionDetail` (the route's `id`), `RecordField` (`format`), `RecordImage`, `RecordPrice` (`currency`), `RecordStars`, `RecordLink` (the record's page) |
| Figures | `Metric` (`count` / `sum` / `avg` / `min` / `max` of a field, `period`, `format`), `Chart` (bar / line / area / donut by `groupBy`, recharts in the theme's chart colours); computed in the browser from the records, or served by an aggregate operation when the app declares one |
| Writes (apps) | `RecordForm` (`create` / `edit`, fields as written or from the collection; the Form section renders it), `RecordAction` (`delete`, `set` a field, confirm) |
| States | `Empty`, `Loading`, `Error` |

Containers mark themselves `data-bga-collection` / `data-bga-records` for the checks.

## Acceptance criteria

- [x] On a static site every component reads its `content` collection; the fixture's `/designed` page shows 2
      products in a strip, a searchable, sortable, paged browser, a count and a max figure and a bar chart.
- [x] On an app every component binds to the contract (`tree_bindings.bind_tree`): list / get / create / update /
      delete operations by entity, figures to aggregate operations or the list.
- [x] Nothing renders empty without saying so: a container with no records shows its `Empty` child.

## Status

**Done (2026-11-04)**. Probed in the built fixture: metrics `2` and `30`, chart drawn, strip and browser populated,
"2 results", pages 1 of 2. Deviations: `AppShell` (a designed sidebar) is not a component; sidebar shells keep their
own sidebar and the chrome tree replaces only the header-footer shell's header. `FacetFilter` is `CategoryFilter`.
