# Story 10.0a — Form kit

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-35, FR-25 · **Depends on:** Epic 21

## User story

As a user of a generated app, I want forms that look designed and are easy to fill in (dates in a calendar, real
labels, the right input for each field, errors on the field that caused them), on section pages and designed pages
alike.

## Evidence (code, 2026-11-04)

- The libraries are in the base (`react-hook-form` 7.91, `@hookform/resolvers`, `zod` 4, `react-day-picker`,
  `date-fns`, `cmdk`, `sonner`; shadcn `calendar`, `popover`, `command`, `select`, `switch`, `radio-group`,
  `toggle-group`, `input-group`, `field`, `spinner`), but `sections/Form.tsx` uses only `Input`, `Textarea`,
  `Select` and `Checkbox`.
- `date` is the native `<input type="date">`; `datetime` is in `FormFieldType` but not in `INPUT_TYPES` (a text box)
  nor in the renderer's `FORM_FIELD_TYPES` (`frontend_renderer.py`).
- Tree forms (`renderer/tree/tree-forms.tsx`): `guessFields` types fields from `typeof` of the first record; their
  form id (`<page>-<collection>-new|edit`) is not in `plan["forms"]`, so `form_schemas_ts` writes no schema for them
  and `useSectionForm` runs without a resolver; edit forms set `value` on every field instead of using `load`.
- `useSectionForm` shows server errors as a toast only. 422 `details` is FastAPI's `exc.errors()` (with `loc`); the
  templated repositories raise `ConflictException("A … with this … already exists")` with no field.

## Steps

1. **Field components**, one per kind, in the overlay (`renderer/src/components/sections/form/`), used by `Form.tsx`:

   | Kind | Component |
   |---|---|
   | `date` | Popover + Calendar, shown with `date-fns` in `project.locale` (only that locale imported), sent as `YYYY-MM-DD` |
   | `datetime` | Calendar + time input, sent as ISO 8601 with offset; added to the renderer's `FORM_FIELD_TYPES` |
   | `enum` | Select; RadioGroup or ToggleGroup for ≤ 5 values; labels from FormField `labels` (new, additive), else the value title-cased |
   | `boolean` | Switch in a horizontal `Field` |
   | `integer` / `number` / `decimal` | `min`, `max`, `step` from the spec; InputGroup prefix / suffix for currency and units (`prefix`, `suffix`, new) |
   | `text` | Textarea with a character count when `maxLength` is set |
   | `email` / `url` / `tel` / `password` | typed inputs; password with show / hide |

2. **Layout:** the form in a Card using theme and tone tokens (`cardStyle`), short fields in two columns from `md`,
   text areas full width; required marker, `FieldDescription` (FormField `help`, new), placeholder; Cancel (back, or
   reset) and Submit with a Spinner while pending; an edit form with no changes does not submit.
3. **Server errors on fields:** 422 `details[].loc` → `setError` on that field; codegen's conflict errors gain
   `details: {"fields": [...]}` (the unique columns) and map to those fields; anything else stays a toast.
4. **Tree forms use the same path:** `RecordForm` gets its fields from the bound operation's request schema in the
   contract (types, required, enum values, limits), written into `site.json` by the renderer; tree forms join
   `plan["forms"]` so they get a Zod schema; edit forms use `load` and send only changed fields, like section forms.
5. **Static sites:** client-only forms use the same field components.
6. **Design checklist** (`templates/nextjs_overlay/DESIGN_CHECKLIST.md`) gains the form rules; `scripts/design-check.mjs`
   measures a form fixture.

## Acceptance criteria

- [ ] No generated form uses a native date input; `date` and `datetime` are picked in a calendar and sent in the
      contract's format.
- [ ] Enum, boolean, number and text fields use the components above, with labels, limits and help from the spec.
- [ ] Every form (section and tree) has a Zod schema; tree forms have the contract's types and required fields.
- [ ] A 422 or a unique-field 409 shows under the field that caused it.
- [ ] The forms pass the design checklist in light and dark, at 375 px and 1440 px.
- [ ] Generated form tests (`forms_unit_test`) cover a date picked in the calendar, an enum, and a server error
      mapped to a field; journeys still pass on mocks.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up` and generate
`flashcards-dynamic` and `project-tracker-dynamic` with the fake engine, then check the forms in the App tab.

## Status

**Planned (2026-11-04).**
