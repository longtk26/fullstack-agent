import json
from pathlib import Path

import pytest

from src.modules.shared.domain.backend_spec import SpecIssueCode, validate_spec_data, validate_spec_text

FIXTURES = Path(__file__).parent / "fixtures" / "specs"
EXAMPLES = Path(__file__).parents[2] / "examples" / "specs"
INVALID = sorted((FIXTURES / "invalid").glob("*.json"))


def _load(path: Path):
    return json.loads(path.read_text())


@pytest.mark.parametrize("path", INVALID, ids=[p.stem for p in INVALID])
def test_invalid_fixture_reports_exactly_its_rule(path):
    fixture = _load(path)
    report = validate_spec_data(fixture["spec"]).report
    issues = report.errors + report.warnings
    got = {(issue.code, issue.path) for issue in issues}

    for expected in fixture["expect"]:
        assert (expected["code"], expected["path"]) in got, fixture["description"]
    assert {issue.code for issue in issues} == {e["code"] for e in fixture["expect"]}, "unrelated issues reported"


def test_every_issue_code_has_a_fixture():
    covered = {e["code"] for path in INVALID for e in _load(path)["expect"]} | {"JSON_MALFORMED"}
    assert covered == {code.value for code in SpecIssueCode}


@pytest.mark.parametrize("path", [FIXTURES / "valid_base.json", *sorted(EXAMPLES.glob("*.json"))], ids=lambda p: p.stem)
def test_valid_specs_have_no_issues(path):
    report = validate_spec_text(path.read_bytes()).report

    assert report.valid, report.errors
    assert report.warnings == []


def test_malformed_json_reports_location():
    report = validate_spec_text(b'{"specVersion": "1.0",').report

    assert not report.valid
    assert report.errors[0].code == SpecIssueCode.JSON_MALFORMED
    assert "line 1" in report.errors[0].message


def test_collects_all_semantic_errors_in_one_pass():
    spec = _load(FIXTURES / "valid_base.json")
    spec["operations"][0]["method"] = "PUT"
    spec["operations"][2]["filters"] = ["colour"]
    spec["entities"][1]["fields"][2]["default"] = "LOST"

    codes = {issue.code for issue in validate_spec_data(spec).report.errors}

    assert codes == {
        SpecIssueCode.METHOD_ACTION_MISMATCH,
        SpecIssueCode.UNKNOWN_FIELD_REF,
        SpecIssueCode.TYPE_DEFAULT_MISMATCH,
    }


def test_warnings_do_not_invalidate():
    spec = _load(FIXTURES / "valid_base.json")
    spec["backgroundJobs"] = [{"name": "nightlyReport", "trigger": "cron:0 2 * * *"}]

    report = validate_spec_data(spec).report

    assert report.valid
    assert [w.code for w in report.warnings] == [SpecIssueCode.UNSUPPORTED_FEATURE]


def test_normalization_fills_defaults():
    result = validate_spec_text((EXAMPLES / "two-entity.json").read_bytes())
    normalized = result.normalized

    assert normalized["project"]["slug"] == "project-tracker"
    assert [e["table"] for e in normalized["entities"]] == ["projects", "tasks"]
    assert normalized["relationships"][0]["foreignKey"] == "projectId"
    task_list = next(op for op in normalized["operations"] if op["operationId"] == "task.list")
    assert task_list["pagination"] == {"defaultLimit": 20, "maxLimit": 100}
    assert task_list["auth"] == "none"
    title = next(f for f in normalized["entities"][1]["fields"] if f["name"] == "title")
    due = next(f for f in normalized["entities"][1]["fields"] if f["name"] == "dueDate")
    assert title["nullable"] is False and due["nullable"] is True
