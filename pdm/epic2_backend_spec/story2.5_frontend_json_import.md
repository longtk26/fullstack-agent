# Story 2.5 — Frontend site JSON → BackendSpec import

**Epic:** [2 — BackendSpec](epic2_backend_spec.md) · **Requirements:** FR-01, FR-07 (assumptions, not invention), FR-17 / §11 (frontend ↔ backend mapping) · **Decision:** Q5 · **Depends on:** 2.3

## User story

As a user who already has a Frontend-Agent site (e.g. `json.json`), I want to import it and get an example
BackendSpec whose entities, operations and seed data match what the pages actually display, so that the generated
backend can serve that site.

## Input shape (from `examples/frontend/revue-de-mode.json`)

- `collections[]` {id, key, kind, name, records[]}: data source, e.g. `posts` with 8 records
  (`id, title, excerpt, body, date, tags[], image, author, category`).
- `pages[].tree`: component tree whose data-bound components show what the frontend needs:

| Component (props) | Derived backend need |
|---|---|
| `CollectionBrowser` {pageSize, sortFields[], searchFields[], categoryField, detailSlug} | list op with pagination (`limit` default = pageSize), sort on `sortFields`, `q` search over `searchFields`, filter on `categoryField` |
| `CategoryFilter`, `SortControl`, `SearchBox`, `Pagination`, `ResultCount` | filter on the category field, sort/search/pagination params, `total` in the response |
| `CollectionStrip` {sortBy, order, limit} / {like: field, limit} | list op sorted/limited, plus "related" filter on `like` field excluding the current id |
| `CollectionDetail`, `RecordLink`, `detailSlug` | get-by-id op |
| `RecordField` {field, format}, `RecordImage` {altField}, `RecordEach` {field} | fields that must be in the response schema (`format: date` → date type, `RecordEach` → array) |

## Acceptance criteria

- [ ] `POST /api/v1/spec-imports/frontend` (raw JSON, ≤ 5 MB) → 200
      `{backendSpec, seed, assumptions[], unresolved[], bindings[], validation}`. It is **deterministic** (no LLM) and nothing is persisted
      until the user submits.
- [ ] Entity mapping: one entity per collection. The name is the singular PascalCase of `key` (`posts` → `Post`),
      and the label comes from `name`. Field types are inferred across all records: ISO date → `date`/`datetime`, int/float/bool,
      string > 255 chars or multi-paragraph → `text`, otherwise `string` (+ `maxLength`), array of scalars → `json`
      array. A field is required if it is present and non-null in every record. The existing `id` becomes the string PK.
- [ ] Operations are derived from the bindings table above, with stable operationIds (`post.list`, `post.get`,
      `post.listRelated` only if a `like` strip exists). Write operations (`create/update/delete`) are added only when
      the UI's "Include admin CRUD" toggle is on (default **on**), with an assumption entry noting that the frontend has no
      write UI.
- [ ] `seed`: all collection records, converted to the inferred types. Image paths are kept as strings, and an assumption
      notes that assets are not uploaded.
- [ ] Assumptions instead of guessing (FR-07). Each of these produces an entry rather than a silent choice:
      `category` with few distinct values (6 in the fixture; kept as an indexed `string`, enum suggested); `author` and `tags` (kept inline,
      separate `Author`/`Tag` entities suggested); a non-UUID id format.
- [ ] `bindings[]`: `{page, componentPath, component, operationId, params}` for every data-bound component, stored in
      the spec under `x-frontendBindings` and copied into the manifest (7.1) for the future Integration Agent (§11).
- [ ] Unknown components or collection kinds → `unresolved[]`. The import still succeeds.
- [ ] "Refine with AI" (optional): sends the deterministic draft and the site JSON to the 2.4 draft job
      (`mode: frontend`). The engine may rename or normalize (e.g. `Tag` M:N) but must keep operationIds and bindings intact.
      The result is re-validated.
- [ ] Fixture test: `revue-de-mode.json` → a snapshot of the expected spec (`Post`, `post.list` with sort `date|title|category`,
      search `title|excerpt|author|category`, filter `category`, pageSize 8; `post.get`; `post.listRelated` by `category`; 8 seed rows) that passes 2.2.

## Technical notes

- The importer lives in `modules/specs/usecases/import_frontend_spec_usecase.py` with a pure converter in `modules/specs/domain/`.
- Site JSON is untrusted. It is parsed with size and depth limits, and strings are never interpolated into prompts outside delimiters (3.4).
