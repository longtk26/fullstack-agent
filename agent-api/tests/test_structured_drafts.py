"""Story 22.8: fewer spec repairs. An API draft answers in the shape of its files (structured output: the Gemini API
engine sends the answer's JSON Schema as `responseJsonSchema`); code fixes the mechanical mistakes before any check
(a field list written as one string, a missing primary key); the validator reports such a string once, not per letter.
The live soccer draft (Antigravity) needed a 293 s repair for one mistake: `"scope": "pitchId"`, 16 errors."""

import json

import httpx
from test_gemini_api_engine import answer, engine, request, run

from src.engines import EngineStatus
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.drafting.answer_schema import KEPT, RULE_PARAMS, app_answer_schema
from src.orchestrator.drafting.app import fix_backend_defaults
from tests.generation_helpers import EXAMPLES


def _keywords(node, found: set[str]) -> set[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("properties", "$defs"):
                for item in value.values():
                    _keywords(item, found)
            else:
                found.add(key)
                _keywords(value, found)
    elif isinstance(node, list):
        for item in node:
            _keywords(item, found)
    return found


def test_the_answer_schema_has_the_three_files_and_typed_rules():
    schema = app_answer_schema("backend-spec.json", "app-outline.json", "notes.json")
    files = schema["properties"]["files"]
    assert files["required"] == ["backend-spec.json", "app-outline.json", "notes.json"]
    assert files["additionalProperties"] is False
    assert _keywords(schema, set()) <= KEPT | {"$defs"}, "only the keywords structured output documents"
    variants = {v["properties"]["kind"]["enum"][0]: v for v in schema["$defs"]["Rule"]["anyOf"]}
    assert set(variants) == set(RULE_PARAMS)
    no_overlap = variants["noOverlap"]["properties"]["params"]["properties"]
    assert no_overlap["scope"]["type"] == "array", "the soccer draft wrote it as a string"
    assert "description" in variants["custom"]["required"]
    renamed = app_answer_schema("b.json", "o.json", "n.json")["properties"]["files"]["required"]
    assert renamed == ["b.json", "o.json", "n.json"]


def test_the_api_engine_sends_the_schema_and_answers_without_it_when_refused(tmp_path):
    schema = {"type": "object", "properties": {"files": {"type": "object"}}}
    made = engine(tmp_path, [answer({"files": {"a.json": {"x": 1}}, "message": "ok"})])
    result, _ = run(made, request(tmp_path, purpose="draft_app", response_schema=schema))
    sent = json.loads(made.requests[-1].content)["generationConfig"]
    assert result.status == EngineStatus.OK and sent["responseJsonSchema"] == schema
    assert sent["responseMimeType"] == "application/json"

    refused = engine(
        tmp_path,
        [
            httpx.Response(400, json={"error": {"message": "schema too complex"}}),
            answer({"files": {"a.json": {"x": 2}}, "message": "ok"}),
        ],
    )
    result, events = run(refused, request(tmp_path, purpose="draft_app", response_schema=schema))
    bodies = [json.loads(r.content)["generationConfig"] for r in refused.requests if r.method == "POST"]
    assert result.status == EngineStatus.OK and "responseJsonSchema" in bodies[0]
    assert "responseJsonSchema" not in bodies[1], "a refused schema never fails the draft"
    assert any("answer schema was refused" in event.summary for event in events)
    plain = engine(tmp_path, [answer({"files": {"a.json": {}}, "message": "ok"})])
    run(plain, request(tmp_path, purpose="draft_app"))
    assert "responseJsonSchema" not in json.loads(plain.requests[-1].content)["generationConfig"]


def test_an_app_draft_on_an_api_engine_asks_for_the_schema(tmp_path):
    """The app flow passes the answer schema to an inline (API) engine; a CLI engine gets none."""
    from src.orchestrator.drafting import app as app_flow

    seen = []

    async def call(step, prompt, response_schema=None):
        seen.append((step, response_schema))
        raise RuntimeError("stop after the first call")

    import asyncio

    async def progress(*args, **kwargs):
        return None

    for inline in (True, False):
        try:
            asyncio.run(
                app_flow.draft_app(
                    tmp_path, {"inline": inline, "notes_path": "notes.json"}, _Prompts(), call, progress,
                    None, None, "backend-spec.json", "frontend-spec.json",
                )
            )  # fmt: skip
        except RuntimeError:
            pass
    assert seen[0][1]["properties"]["files"]["required"] == ["backend-spec.json", "app-outline.json", "notes.json"]
    assert seen[1][1] is None


class _Prompts:
    def render(self, *args, **kwargs):
        from src.engines.port import PromptRef
        from src.engines.prompts import RenderedPrompt

        return RenderedPrompt(ref=PromptRef(id="draft_app", version="v2", sha256="x"), text="draft it")


def _write(tmp_path, spec: dict) -> None:
    (tmp_path / "backend-spec.json").write_text(json.dumps(spec))


def test_code_fixes_a_field_list_written_as_one_string_and_a_missing_key(tmp_path):
    spec = json.loads((EXAMPLES / "specs" / "workshop-bookings.json").read_text())
    spec["rules"].append(
        {"id": "noDoubleBooking", "kind": "noOverlap", "entity": "Booking",
         "params": {"start": "createdAt", "end": "createdAt", "scope": "workshopId"}}
    )  # fmt: skip
    listing = next(op for op in spec["operations"] if op["operationId"] == "booking.list")
    listing["filters"] = "status"
    tag = next(entity for entity in spec["entities"] if entity["name"] == "Tag")
    tag["fields"] = [field for field in tag["fields"] if not field.get("primary")]
    _write(tmp_path, spec)
    notes = fix_backend_defaults(tmp_path, "backend-spec.json")
    fixed = json.loads((tmp_path / "backend-spec.json").read_text())
    assert fixed["rules"][-1]["params"]["scope"] == ["workshopId"]
    assert next(op for op in fixed["operations"] if op["operationId"] == "booking.list")["filters"] == ["status"]
    tag_fields = next(entity for entity in fixed["entities"] if entity["name"] == "Tag")["fields"]
    assert tag_fields[0] == {"name": "id", "type": "uuid", "primary": True}
    assert {note["path"] for note in notes} >= {"/rules/3/params/scope", "/entities/1/fields"}
    assert fix_backend_defaults(tmp_path, "backend-spec.json") == [], "a second pass changes nothing"


def test_a_scope_written_as_one_string_is_one_error():
    spec = json.loads((EXAMPLES / "specs" / "workshop-bookings.json").read_text())
    spec["rules"].append(
        {"id": "noDoubleBooking", "kind": "noOverlap", "entity": "Booking",
         "params": {"start": "createdAt", "end": "createdAt", "scope": "workshopId"}}
    )  # fmt: skip
    errors = [issue for issue in validate_spec_data(spec).report.errors if issue.path.startswith("/rules/3")]
    assert [(issue.code, issue.path) for issue in errors] == [("RULE_PARAMS_INVALID", "/rules/3/params/scope")]
