# Story 17.1 — Typed section props & layout nodes

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-22 · **Depends on:** 12.1

## User story

As the frontend lane, I want every section's `content` checked against a schema for its component, so that a
spec that validates always renders, and errors show up in the spec editor instead of in `tsc` or `next build`.

## Acceptance criteria

- [ ] Each entry of `BUILTIN_SECTIONS` gets a props model (Pydantic) for its `content`: required and optional
      fields, lengths, links (`page` id or URL), asset references (`asset:<id>`), lists with limits. Unknown keys
      are a warning, wrong types an error, both with the JSON path of the field.
- [ ] Layout nodes `Columns`, `Stack`, `Grid`, `Tabs` join the catalogue with a `children: Section[]` field and
      their own props (column count, gap, tab labels). Nesting depth is at most 3 (Q18); a layout node
      inside a layout node is allowed, an empty `children` is an error. Section ids stay unique within a page,
      nested ones included, so `<pageId>/<sectionId>` names any section.
- [ ] The FrontendSpec JSON Schema served to the UI (12.1, 9.7a) includes the props schemas, so the Monaco
      editor completes and checks section content as it is typed.
- [ ] The props models are exported as TypeScript types for the overlay's section library (one generated file,
      byte-identical between runs, snapshot-tested like the contract).
- [ ] The schema stays `specVersion: "1.0"` (additive); the bundled examples validate with no warning.

**Status:** open.
