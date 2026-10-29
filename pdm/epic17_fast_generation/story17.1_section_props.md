# Story 17.1 — Typed section props & layout nodes

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-22 · **Depends on:** 12.1

## User story

As the frontend lane, I want every section's `content` checked against a schema for its component, so that a
spec that validates always renders, and errors show up in the spec editor instead of in `tsc` or `next build`.

## Acceptance criteria

- [x] Each entry of `BUILTIN_SECTIONS` gets a props model (Pydantic) for its `content`: required and optional
      fields, lengths, links (`page` id or URL), asset references (`asset:<id>`), lists with limits. Unknown keys
      are a warning, wrong types an error, both with the JSON path of the field.
- [x] Layout nodes `Columns`, `Stack`, `Grid`, `Tabs` join the catalogue with a `children: Section[]` field and
      their own props (column count, gap, tab labels). Nesting depth is at most 3 (Q18); a layout node
      inside a layout node is allowed, an empty `children` is an error. Section ids stay unique within a page,
      nested ones included, so `<pageId>/<sectionId>` names any section.
- [x] The FrontendSpec JSON Schema served to the UI (12.1, 9.7a) includes the props schemas, so the Monaco
      editor completes and checks section content as it is typed.
- [x] The props models are exported as TypeScript types for the overlay's section library (one generated file,
      byte-identical between runs, snapshot-tested like the contract).
- [x] The schema stays `specVersion: "1.0"` (additive); the bundled examples validate with no warning.

**Status (2026-10-29):** done.

- Props models in `frontend_spec/section_props.py` (`SECTION_PROPS`, item models `SECTION_ITEMS` for the list
  sections, `LAYOUT_SECTIONS`, `MAX_DEPTH = 3`); `Section.children` in `schema_v1.py`. The validator walks nested
  sections everywhere (`walk_sections` / `iter_sections`): component, data, form, asset and page checks, unique ids
  per page, and the new rules. New codes: `FE_INVALID_PROPS` (error), `FE_UNKNOWN_PROP` (warning),
  `FE_INVALID_LAYOUT` (error: children on a non-layout section, an empty layout node, data or a form on a layout
  node, deeper than 3 levels). Tabs `labels` must match the children.
- List sections (`Features`, `Testimonials`, `Faq`, `Pricing`, `Stats`, `Gallery`) take `content.items` or a
  `data` binding; the records of a bound content collection are checked against the item model, with the record's
  own path (`/content/1/records/0/price`). Unknown keys in records are not reported (collections are shared data).
- A built-in redeclared in `components` as a non-section (e.g. `kind: composite`) keeps free-form content, as the
  planner already treated it.
- The served JSON Schema adds every props model to `$defs` and an `if component = X then content = XProps` rule
  per built-in to `Section` (`registry.frontend_spec_json_schema`). Props models allow unknown keys
  (`additionalProperties: true`) so the editor does not mark a warning as an error.
- **Deviation:** the TypeScript types are generated into each rendered site (`src/components/sections/types.ts`,
  `frontend_renderer.section_props_ts`) instead of being checked into the overlay, so the Pydantic models stay the
  only source; the snapshot is `tests/fixtures/section-props.ts`.
- `FeatureItem` has no `icon` field: icons come with Epic 15's `lucide:` sources, and a field that renders nothing
  would mislead.
- Planner, codegen, contract consistency (12.5), integration and the frontend nodes walk nested sections.
- Tests: `tests/test_section_renderer.py` (props errors and warnings, layout rules, editor schema, types snapshot);
  existing FrontendSpec, planner and consistency tests unchanged.
