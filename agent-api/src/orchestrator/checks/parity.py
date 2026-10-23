"""Deterministic plan-vs-result checks: database schema (5.3), OpenAPI operations (5.4), test coverage (5.5)."""

import ast
from pathlib import Path
from typing import Any

from src.orchestrator.planner import planned_operations

IGNORED_PATHS = {"/health"}


def _norm_type(column_type: str) -> str:
    return column_type.upper().replace(" ", "")


def _expected_db_type(column: dict[str, Any]) -> str | None:
    """The reflected type we expect, or None when any spelling is fine."""
    if column["type"] == "enum":
        return f"ENUM({column['enum']['dbName']})".upper()
    simple = {
        "uuid": "UUID",
        "text": "TEXT",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "datetime": "TIMESTAMPWITHTIMEZONE",
    }
    if column["type"] == "string":
        return f"VARCHAR({column['maxLength']})" if column.get("maxLength") else None
    return simple.get(column["type"])


def compare_schema(plan: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    tables = schema.get("tables", {})

    def problem(table: str, message: str) -> None:
        problems.append({"table": table, "message": message})

    for model in plan.get("models", []):
        table = tables.get(model["table"])
        if table is None:
            problem(model["table"], f"table missing (model {model['class']})")
            continue
        columns = {c["name"]: c for c in table["columns"]}
        for column in model["columns"]:
            actual = columns.get(column["attr"])
            if actual is None:
                problem(model["table"], f"column {column['attr']} missing")
                continue
            if column["primaryKey"]:
                continue
            if bool(actual["nullable"]) != bool(column["nullable"]):
                expected = "NULL" if column["nullable"] else "NOT NULL"
                problem(model["table"], f"column {column['attr']} should be {expected}")
            expected_type = _expected_db_type(column)
            if expected_type and _norm_type(actual["type"]) != expected_type:
                problem(model["table"], f"column {column['attr']} has type {actual['type']}, expected {expected_type}")
        pk = model["primaryKey"] if isinstance(model["primaryKey"], list) else [model["primaryKey"]]
        if sorted(table["primaryKey"]) != sorted(pk):
            problem(model["table"], f"primary key is {table['primaryKey']}, expected {pk}")
        actual_fks = {
            (tuple(fk["columns"]), f"{fk['referredTable']}.{fk['referredColumns'][0]}", (fk["onDelete"] or "").upper())
            for fk in table["foreignKeys"]
        }
        for fk in model["foreignKeys"]:
            expected = ((fk["column"],), fk["references"], fk["onDelete"].upper())
            if expected not in actual_fks:
                problem(
                    model["table"],
                    f"foreign key {fk['column']} → {fk['references']} ON DELETE {fk['onDelete']} missing or different",
                )
        unique_sets = {tuple(sorted(u)) for u in table["uniques"]}
        unique_sets |= {tuple(sorted(i["columns"])) for i in table["indexes"] if i["unique"]}
        index_sets = {tuple(sorted(i["columns"])) for i in table["indexes"]}
        for column in model["columns"]:
            if column["unique"] and not column["primaryKey"] and (column["attr"],) not in unique_sets:
                problem(model["table"], f"column {column['attr']} should be unique")
            if column["index"] and (column["attr"],) not in index_sets | unique_sets:
                problem(model["table"], f"column {column['attr']} should be indexed")
        for group in model["uniqueConstraints"]:
            if tuple(sorted(group)) not in unique_sets:
                problem(model["table"], f"unique constraint on {group} missing")
        for index in model["indexes"]:
            if tuple(sorted(index["columns"])) not in (unique_sets if index["unique"] else index_sets | unique_sets):
                problem(model["table"], f"index on {index['columns']} missing")
        for enum in model["enums"]:
            labels = schema.get("enums", {}).get(enum["dbName"])
            if labels is None:
                problem(model["table"], f"enum type {enum['dbName']} missing")
            elif labels != enum["values"]:
                problem(model["table"], f"enum {enum['dbName']} has {labels}, expected {enum['values']}")
    planned_tables = {m["table"] for m in plan.get("models", [])}
    for extra in sorted(set(tables) - planned_tables):
        problem(extra, "table is not in the plan")
    return problems


def compare_openapi(plan: dict[str, Any], document: dict[str, Any]) -> list[dict[str, Any]]:
    actual = set()
    for path, item in document.get("paths", {}).items():
        if path in IGNORED_PATHS:
            continue
        for method, operation in item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                actual.add((method.upper(), path, operation["operationId"]))
    expected = planned_operations(plan)
    problems = [
        {"operation": f"{m} {p}", "message": f"missing (operation_id={o!r})"} for m, p, o in sorted(expected - actual)
    ]
    problems += [
        {"operation": f"{m} {p}", "message": f"not in the plan (operation_id={o!r})"}
        for m, p, o in sorted(actual - expected)
    ]
    return problems


def test_names(project: Path) -> set[str]:
    names = set()
    for path in (project / "tests").rglob("test_*.py"):
        try:
            tree = ast.parse(path.read_text(errors="replace"))
        except SyntaxError:
            continue
        names.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_")
        )
    return names


def missing_tests(plan: dict[str, Any], project: Path) -> list[dict[str, Any]]:
    present = test_names(project)
    return [
        {"file": test["file"], "test": test["id"], "message": f"planned test missing: {test['description']}"}
        for test in plan.get("tests", [])
        if test["id"] not in present
    ]
