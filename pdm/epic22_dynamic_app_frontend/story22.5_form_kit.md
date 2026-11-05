# Story 22.5 — Form kit

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-35, FR-36 · **Depends on:** 22.4

Was story 10.0a (planned 2026-11-04); moved here on 2026-11-05 so that forms are built once, for the app kit, and
static sites keep their forms unchanged (decision D1).

## User story

As a user of a generated app, I want forms that look designed and are easy to fill in: dates in a calendar, real
labels, the right input for each field, and errors on the field that caused them.

## Evidence (code, 2026-11-04)

- The libraries are in the base (`react-hook-form` 7.91, `@hookform/resolvers`, `zod` 4, `react-day-picker`,
  `date-fns`, `cmdk`, `sonner`; shadcn `calendar`, `popover`, `command`, `select`, `switch`, `radio-group`,
  `toggle-group`, `input-group`, `field`, `spinner`), but `sections/Form.tsx` uses only `Input`, `Textarea`,
  `Select` and `Checkbox`.
- `date` is the native `<input type="date">`; `datetime` is in `FormFieldType` but not in `INPUT_TYPES` (a text box)
  nor in the renderer's `FORM_FIELD_TYPES` (`frontend/renderer.py`).
- Tree forms (`renderer/tree/tree-forms.tsx`) type fields from `typeof` of the first record and get no Zod schema.
  App screens do not use trees (22.3), so this story does not fix tree forms.
- `useSectionForm` shows server errors as a toast only. 422 `details` is FastAPI's `exc.errors()` (with `loc`); the
  templated repositories raise `ConflictException("A … with this … already exists")` with no field.

## Steps

1. **Field components**, one per kind, in the app kit (`files/dynamic/app/form/`), used by `AppForm`; the fields come
   from the operation's request schema in the contract (types, required, enum values, limits) and the outline's labels
   and help:

   | Kind | Component |
   |---|---|
   | `date` | Popover + Calendar, shown with `date-fns` in `project.locale` (only that locale imported), sent as `YYYY-MM-DD` |
   | `datetime` | Calendar + time input, sent as ISO 8601 with offset |
   | `enum` | Select; RadioGroup or ToggleGroup for ≤ 5 values; labels from the outline's `fieldLabels`, else the value title-cased |
   | `boolean` | Switch in a horizontal `Field` |
   | `integer` / `number` / `decimal` | `min`, `max`, `step` from the contract; InputGroup prefix / suffix for currency and units |
   | `text` | Textarea with a character count when `maxLength` is set |
   | `email` / `url` / `tel` / `password` | typed inputs; password with show / hide |

2. **Layout:** the form in a Card on the kit's scale; short fields in two columns from `md`, text areas full width;
   required marker, `FieldDescription` (outline `help`), placeholder; Cancel (back) and Submit with a Spinner while
   pending; an edit form loads the record (`get`), sends only changed fields, and does not submit with no changes.
3. **Zod schema for every app form**, from the request schema (`form_schemas_ts` gains the app forms).
4. **Server errors on fields:** 422 `details[].loc` → `setError` on that field; codegen's conflict errors gain
   `details: {"fields": [...]}` (the unique columns) and map to those fields; anything else stays a toast. The backend
   half (`details.fields` on 409) is done in Epic 10 (10.0b) so it is ready here.
5. **Design checklist** gains the form rules; `scripts/design-check.mjs` measures a form fixture.

Static sites keep `sections/Form.tsx` as it is; adopting the kit there would be a separate, static story.

## Acceptance criteria

- [ ] No app form uses a native date input; `date` and `datetime` are picked in a calendar and sent in the contract's
      format.
- [ ] Enum, boolean, number and text fields use the components above, with labels, limits and help.
- [ ] Every app form has a Zod schema with the contract's types and required fields.
- [ ] A 422 or a unique-field 409 shows under the field that caused it.
- [ ] The forms pass the design checklist in light and dark, at 375 px and 1440 px.
- [ ] Agent tests (pytest, no Node) check the generated form code for each field kind: the calendar for a date, the
      Select for an enum, the Zod schema, and a server error mapped to a field (decision FE-TESTS).
- [ ] Static golden passes.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`; `make up` and generate `flashcards-dynamic` and
`project-tracker-dynamic` with the fake engine, then fill in the forms in the App tab.

## Status

**Planned (2026-11-05)**, moved from 10.0a.
