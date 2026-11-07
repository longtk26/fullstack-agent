"""TESTING ONLY (docs/development/test-doubles.md): the fake LLM provider's answers for the business steps (Epic 26).
Registered by importing this module (`tests/test_business_layer.py`); nothing in `src/` imports it.

A generic business (one member, one core workflow: create a record and see it), expectations that say only who may
do each step, and a binding that maps the steps onto the drafted app's first role and first create operation. Enough
for the business layer, the tour and the evaluation to run end to end on the fake engine; no model is called.
"""

import json
from typing import Any

from fake_llm import responder


def _section(prompt: str, title: str, after: str | None = None) -> Any:
    start = prompt.find(title)
    if start < 0:
        return None
    start += len(title)
    end = prompt.find(after, start) if after else -1
    text = prompt[start : end if end > 0 else None].strip()
    try:
        return json.loads(text)
    except ValueError:
        return None


def _business(prompt: str, schema: Any) -> dict[str, Any]:
    step = {"id": "create", "actor": "member", "action": "create a record", "record": "record", "statusAfter": "",
            "rule": "", "delivers": ["track"]}  # fmt: skip
    return {
        "app": {"name": "App", "purpose": "Keep records"},
        "values": [{"id": "track", "value": "Keep track of the records", "measure": "records created"}],
        "actors": [{"id": "member", "name": "Member", "description": "uses the app", "signsIn": True}],
        "workflows": [
            {
                "id": "main",
                "name": "Create a record",
                "priority": "core",
                "values": ["track"],
                "actor": "member",
                "trigger": "A member needs a record",
                "steps": [step],
                "branches": [],
                "outcome": "The member sees the new record",
                "acceptance": {"given": ["a member"], "when": ["they create a record"], "then": ["it is listed"]},
            }
        ],
        "scope": {"goldenPath": "main", "included": ["records"], "excluded": []},
    }


responder("discover_workflows")(_business)
responder("rediscover_workflows")(_business)


@responder("expect_workflows")
def _expect(prompt: str, schema: Any) -> dict[str, Any]:
    walks = _section(prompt, "Workflow paths:", "The requirement") or []
    paths = []
    for walk in walks:
        for path in walk.get("paths") or []:
            steps = [
                {
                    "step": step["id"],
                    "allowed": [step["actor"]],
                    "refused": [],
                    "record": step.get("record", ""),
                    "statusAfter": step.get("statusAfter", ""),
                    "visibleTo": [step["actor"]],
                    "hiddenFrom": [],
                    "effects": [],
                    "refusedBefore": [],
                }  # fmt: skip
                for step in path.get("steps") or []
            ]
            paths.append({"workflow": walk["workflow"], "path": path["path"], "steps": steps, "outcome": []})
    return {"paths": paths}


@responder("bind_workflows")
def _bind(prompt: str, schema: Any) -> dict[str, Any]:
    roles = _section(prompt, "Roles and their demo users:", "\n\nActors:") or {}
    operations = _section(prompt, "API operations:", "\n\nApp pages:") or []
    pages = _section(prompt, "App pages:") or []
    expected = _section(prompt, "Expectations:", "\n\nAPI operations:") or []
    role = next(iter(roles), "")
    create = next(
        (op for op in operations if op.get("method") == "POST" and "{" not in op["path"] and "auth" not in op["path"]),
        None,
    )
    page = next((p["page"] for p in pages if create and any(create["operationId"] in s for s in p["sections"])), "")
    body = {name: "{{run}}" for name, kind in ((create or {}).get("body") or {}).items() if kind.startswith("string")}
    steps = [
        {
            "workflow": path["workflow"],
            "path": path["path"],
            "step": line["step"],
            "operationId": create["operationId"] if create else "",
            "pathParamsJson": "",
            "queryJson": "",
            "bodyJson": json.dumps(body),
            "creates": line.get("record", ""),
            "automatic": False,
            "page": page,
            "pageParamsJson": "",
        }  # fmt: skip
        for path in expected
        for line in path.get("steps") or []
    ]
    return {
        "actors": [{"actor": "member", "role": role}],
        "records": [],
        "setup": [],
        "steps": steps,
        "effects": [],
        "outcomes": [],
        "unbound": [] if create else [{"what": "the create step", "reason": "no create operation"}],
    }
