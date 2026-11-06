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

- [x] No app form uses a native date input; `date` and `datetime` are picked in a calendar and sent in the contract's
      format.
- [x] Enum, boolean, number and text fields use the components above, with labels, limits and help.
- [x] Every app form has a Zod schema with the contract's types and required fields.
- [x] A 422 or a unique-field 409 shows under the field that caused it.
- [x] The forms pass the design checklist in light and dark, at 375 px and 1440 px.
- [x] Agent tests (pytest, no Node) check the generated form code for each field kind: the calendar for a date, the
      Select for an enum, the Zod schema, and a server error mapped to a field (decision FE-TESTS).
- [x] Static golden passes.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`; `make up` and generate `flashcards-dynamic` and
`project-tracker-dynamic` with the fake engine, then fill in the forms in the App tab.

## Status

**Done (2026-11-06).** The kit's form folder (`files/dynamic/app/src/components/app/form/`; the story's
`files/dynamic/app/form/` is the same folder under the app's source tree): `DateField` / `DateTimeField` (Popover +
Calendar with year and month dropdowns, shown with date-fns in `project.locale`, sent as `YYYY-MM-DD` / ISO 8601 with
the browser's offset; a clear button when optional), `ChoiceField` (a segmented ToggleGroup for up to 3 short values,
RadioGroup up to 5, else Select), `NumberField` (contract `min` / `max`, step 1 / 0.01 / any, an InputGroup currency
prefix or unit suffix), `TextAreaField` (character count with `maxLength`), `TextField` (email / url / tel inputs with
their keyboards and autocomplete; password with show / hide), `BooleanField` (a Switch beside its label). `AppForm`
lays them out in a container grid (two columns from 32 rem, text areas full width), marks required fields, shows the
outline's `help` (or the error), Cancel and Submit with a Spinner; an edit form sends only changed fields and its
Submit stays disabled until something changes.

Planner and generated files: `screens.input_kind` types each field from the contract's format, the BackendSpec's
type, then the name (email, website / url, phone, password); `form_field` adds `help` and a `currency` (the paid
amount of `payments`) or `unit` (the last word of the name, which then leaves the label: `durationMinutes` →
"Duration" + "min"). `FormField.help` / `currency` / `unit` are app-only schema fields, removed from the site schema
(the static and legacy digest is unchanged). `app.json` gains `locale`; `src/components/app/date-locale.ts` imports
only that date-fns locale. App forms' Zod uses `z.iso.date()` / `z.iso.datetime({ offset: true })`
(`codegen._zod(..., app=True)`; static forms unchanged), and an optional field reads `""` and `null` as not given
(`z.preprocess(blank, …)`; the live walk found an empty optional due date refused as "Pick a date"); an edit sends a
cleared field as `null`. A create form starts from the contract's defaults (`screens.prefill`: status `TODO`,
priority 3; never a date). `errors.fieldErrors` also reads a 409's `details.fields`.
`FieldValue`, `AppDetail` and `AppDashboard` format in `app.locale` too (the server and the browser format alike).

Verified: `tests/test_app_forms.py` (19 tests on a venue-bookings fixture with every field kind,
`tests/fixtures/app-forms/`), the app kit sandbox build, `make design-check-app` on the fixture (36 views; the form
metrics added to `scripts/design-check.mjs`: no native date input, no unlabelled control, 2 columns at 1440 px and 1 at
375 px, no sideways scroll; DESIGN_CHECKLIST "Forms"), full suite, lint. Live (`make up`, fake engine, `DYNAMIC_FRONTEND=app`): the project tracker and flashcards both COMPLETED with every check (215 s), and `scripts/app-walk.mjs` (now picking dates in the calendar and choosing radios or segments) passed 12/12 and 20/20 steps (one list emptied by a review, skipped).

Deviations: enum labels are the value title-cased (the outline has labels per field, not per value); a currency
comes only from `payments` (the BackendSpec has no money type), units from a fixed list of name endings.
