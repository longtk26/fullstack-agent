"""The form kit (Story 22.5): every app form field gets the kit's input for its kind (a calendar for dates, a choice
for enums, typed inputs, limits, help and units), every app form has a Zod schema with the contract's types, and
server errors land on the field that caused them. Agent tests, no Node (decision FE-TESTS): they read the generated
files and the kit's source."""

import json
import re
from pathlib import Path

import pytest

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.registry import frontend_spec_json_schema
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.frontend.app.files import date_locale, date_locale_ts
from src.orchestrator.frontend.app.outline import complete_outline
from src.orchestrator.frontend.app.screens import app_frontend_spec, ensure_aggregates, input_kind
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.integration.contract import build_contract

FIXTURE = Path(__file__).parent / "fixtures" / "app-forms"
KIT = Path(__file__).parents[1] / "templates/nextjs_overlay/files/dynamic/app/src/components/app"


def _app(backend: dict, raw: dict) -> tuple[dict, dict]:
    outline, _ = complete_outline(raw, backend, build_contract(backend, build_plan(backend)))
    backend, outline, _ = ensure_aggregates(backend, outline)
    contract = build_contract(backend, build_plan(backend))
    spec = app_frontend_spec(backend, outline, {"colorScheme": "light-dark"}, contract).spec
    result = validate_frontend_spec_data(spec)
    assert result.report.valid, result.report.errors
    return result.normalized, contract


@pytest.fixture(scope="module")
def venue(tmp_path_factory) -> tuple[dict, dict, Path]:
    from src.orchestrator.frontend.scaffold import scaffold_frontend

    backend = validate_spec_data(json.loads((FIXTURE / "backend.json").read_text())).normalized
    spec, contract = _app(backend, json.loads((FIXTURE / "outline.json").read_text()))
    out = tmp_path_factory.mktemp("venue")
    scaffold_frontend(out, plan_frontend(spec, contract), spec, contract)
    return spec, contract, out


def _fields(out: Path, form: str) -> dict[str, dict]:
    data = json.loads((out / "src/content/app.json").read_text())
    return {field["name"]: field for field in data["forms"][form]["fields"]}


def test_each_field_gets_the_input_for_its_kind(venue):
    _, _, out = venue
    booking = _fields(out, "booking_create_in_venue")
    kinds = {name: field["type"] for name, field in booking.items() if not field.get("hidden")}
    assert kinds == {
        "guestName": "string",
        "notes": "text",
        "guests": "integer",
        "deposit": "decimal",
        "durationMinutes": "integer",
        "eventDate": "date",
        "arrivesAt": "datetime",
        "visibility": "enum",
        "slot": "enum",
        "occasion": "enum",
        "confirmed": "boolean",
    }
    assert booking["venueId"]["hidden"] and booking["venueId"]["value"] == "$route.id"  # the parent from the route
    venue_form = _fields(out, "venue_create")
    assert {name: f["type"] for name, f in venue_form.items()} == {
        "name": "string",
        "contactEmail": "email",
        "website": "url",
        "phone": "tel",
        "capacity": "integer",
        "accessible": "boolean",
    }


def test_labels_limits_help_and_units_come_from_the_contract_and_the_outline(venue):
    _, _, out = venue
    booking = _fields(out, "booking_create_in_venue")
    assert booking["guestName"]["label"] == "Booked by" and booking["guestName"]["maxLength"] == 120
    assert (booking["guests"]["min"], booking["guests"]["max"], booking["guests"]["required"]) == (1, 500, True)
    assert booking["notes"]["maxLength"] == 500 and booking["notes"]["help"] == "Anything the venue should know"
    assert booking["durationMinutes"]["unit"] == "min" and "unit" not in booking["guests"]
    assert booking["durationMinutes"]["label"] == "Duration"  # the unit is beside the input, not in the label
    assert booking["occasion"]["values"][:2] == ["WEDDING", "BIRTHDAY"]
    # a new record starts from the contract's defaults; an edit form starts from the record
    assert (booking["visibility"]["value"], booking["slot"]["value"], booking["confirmed"]["value"]) == (
        "PRIVATE",
        "EVENING",
        False,
    )
    assert all("value" not in field for field in _fields(out, "booking_update").values())
    assert _fields(out, "venue_create")["capacity"]["help"] == "Standing guests the venue holds"
    assert _fields(out, "venue_create")["contactEmail"]["label"] == "Contact e-mail"


def test_the_paid_amount_takes_the_payments_currency():
    from src.orchestrator.frontend.app.screens import _Screens

    plain = validate_spec_data(json.loads((FIXTURE / "backend.json").read_text())).normalized
    backend = {**plain, "payments": {"entity": "Booking", "amountField": "deposit", "currency": "EUR"}}
    screens = _Screens(backend, {}, build_contract(plain, build_plan(plain)))
    assert screens.number_addon("Booking", "deposit") == {"currency": "EUR"}
    assert screens.number_addon("Booking", "guests") == {}
    assert screens.number_addon("Venue", "deposit") == {}


@pytest.mark.parametrize(
    ("name", "schema", "types", "backend_type", "expected"),
    [
        ("startsAt", {"format": "date-time"}, ["string"], "datetime", "datetime"),
        ("dueDate", {"format": "date"}, ["string"], "date", "date"),
        ("price", {"format": "decimal"}, ["number", "string"], "decimal", "decimal"),
        ("ratio", {}, ["number"], "float", "number"),
        ("email", {}, ["string"], "string", "email"),
        ("homepageUrl", {"format": "uri"}, ["string"], "string", "url"),
        ("mobilePhone", {}, ["string"], "string", "tel"),
        ("password", {}, ["string"], "string", "password"),
        ("bio", {"maxLength": 2000}, ["string"], "text", "text"),
        ("title", {"maxLength": 80}, ["string"], "string", "string"),
    ],
)
def test_input_kind(name, schema, types, backend_type, expected):
    assert input_kind(name, schema, types, backend_type, False) == expected


def test_no_form_field_is_a_native_date_input_and_each_kind_has_its_component():
    """The kit's dispatcher (`form/FieldInput.tsx`) picks the calendar for dates, the choice for enums; no kit file
    renders `<input type="date">` or `datetime-local`."""
    dispatch = (KIT / "form/FieldInput.tsx").read_text()
    for kind, component in [
        ("date", "DateField"),
        ("datetime", "DateTimeField"),
        ("enum", "ChoiceField"),
        ("boolean", "BooleanField"),
        ("integer", "NumberField"),
        ("decimal", "NumberField"),
        ("text", "TextAreaField"),
    ]:
        assert re.search(rf'case "{kind}":(\s*case "\w+":)*\s*return <{component} ', dispatch), kind
    date = (KIT / "form/DateField.tsx").read_text()
    assert "<Calendar" in date and "<Popover" in date and 'format(next, "yyyy-MM-dd")' in date
    assert "formatISO(next)" in date  # a datetime with the browser's offset
    for source in KIT.rglob("*.tsx"):
        text = source.read_text()
        assert 'type="date"' not in text and "datetime-local" not in text, source.name
    choice = (KIT / "form/ChoiceField.tsx").read_text()
    assert "<Select" in choice and "<RadioGroup" in choice and "<ToggleGroup" in choice
    inputs = (KIT / "form/InputFields.tsx").read_text()
    assert (
        't("showPassword")' in inputs and "{text.length} / {field.maxLength}" in inputs and "InputGroupAddon" in inputs
    )


def test_every_app_form_has_a_zod_schema_with_the_contracts_types(venue):
    spec, _, out = venue
    schemas = (out / "src/components/app/form-schemas.ts").read_text()
    forms = (out / "src/lib/forms.ts").read_text()
    for form in spec["forms"]:
        assert f'"{form["id"]}": {{ schema: ' in schemas, form["id"]
    block = forms[forms.index("export const bookingCreateInVenueSchema") :].split("});")[0]
    assert 'eventDate: z.iso.date("Pick a date"),' in block  # required
    # optional: "" and null are not given (an empty date or e-mail is valid; a cleared field is no value)
    assert "arrivesAt: z.preprocess(blank, z.iso.datetime({ offset: true" in block
    assert block.count("z.preprocess(blank, ") >= 5 and "const blank = (value: unknown) =>" in forms
    assert "guests: z.number().int().min(1).max(500)," in block
    assert 'z.enum(["WEDDING", "BIRTHDAY", "CONFERENCE", "CONCERT", "WORKSHOP", "MEETUP", "OTHER"])' in block
    assert "confirmed: z.boolean()," in block
    assert 'guestName: z.string().min(1, "Required").max(120),' in block
    venue_block = forms[forms.index("export const venueCreateSchema") :].split("});")[0]
    assert 'contactEmail: z.preprocess(blank, z.email("Enter a valid e-mail address").optional()),' in venue_block


def test_a_unique_field_conflict_and_a_422_map_to_their_fields(venue):
    """The backend's 409 on a unique column carries `details.fields` (Story 10.0b); FastAPI's 422 has `loc`. The kit's
    `fieldErrors` reads both; the form sets them on the field (`setError`), anything else is a toast."""
    errors = (KIT / "errors.ts").read_text()
    assert "(e.details as { fields?: unknown }).fields" in errors and "item.loc" in errors
    form = (KIT / "AppForm.tsx").read_text()
    assert "methods.setError(name, { message })" in form and "toast.error(errorMessage(" in form
    _, contract, _ = venue
    from src.orchestrator.backend.codegen import module_files
    from src.orchestrator.backend.planner import build_plan

    backend = validate_spec_data(json.loads((FIXTURE / "backend.json").read_text())).normalized
    plan = build_plan(backend)
    repository = module_files(plan, backend, next(m for m in plan["modules"] if m["name"] == "venues"))
    code = "\n".join(text for path, text in repository.items() if path.endswith("_repository.py"))
    assert 'details={"fields": ["name"]}' in code


def test_an_edit_form_sends_only_changes_and_cannot_submit_unchanged():
    form = (KIT / "AppForm.tsx").read_text()
    assert "names.filter((name) => dirty[name]).map((name) => [name, values[name] ?? null])" in form
    assert "disabled={mutation.isPending || unchanged}" in form and "<Spinner" in form


def test_the_calendar_imports_only_the_projects_locale():
    assert date_locale("en") == "en-US" and date_locale("en-gb") == "en-GB" and date_locale("vi-VN") == "vi"
    assert date_locale("zh") == "zh-CN" and date_locale("pt_BR") == "pt-BR" and date_locale("xx") == "en-US"
    assert date_locale_ts("fr-CA").count("import ") == 1 and 'from "date-fns/locale/fr-CA"' in date_locale_ts("fr-CA")
    assert "export const dateLocale = srLatn;" in date_locale_ts("sr-Latn")


def test_the_static_schema_has_no_app_form_fields():
    form_field = frontend_spec_json_schema(app=False)["$defs"]["FormField"]["properties"]
    assert not {"help", "currency", "unit"} & set(form_field)
    assert {"help", "currency", "unit"} <= set(frontend_spec_json_schema()["$defs"]["FormField"]["properties"])
