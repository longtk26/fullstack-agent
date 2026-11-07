"""The business layer's data (Epic 26): workflows, frozen expectations and the binding, with their answer schemas.

Ported from the business-value lab (`lab/business-value/prompts.py`, 2026-11-07). The schemas use only the keywords
every provider's structured output accepts (type, properties, required, items, enum, minItems, maxItems).
"""

from typing import Any


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or list(properties)}


def _arr(items: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"type": "array", "items": items, **extra}


S = {"type": "string"}
SA = _arr(S)
MAX_WORKFLOWS = 6  # a safety cap on the run's size, not a target

# -- 26.1 discovery ---------------------------------------------------------------------------------------------------

STEP = _obj({"id": S, "actor": S, "action": S, "record": S, "statusAfter": S, "rule": S, "delivers": SA})
BUSINESS_SCHEMA = _obj(
    {
        "app": _obj({"name": S, "purpose": S}),
        "values": _arr(_obj({"id": S, "value": S, "measure": S}), minItems=1),
        "actors": _arr(_obj({"id": S, "name": S, "description": S, "signsIn": {"type": "boolean"}}), minItems=1),
        "workflows": _arr(
            _obj(
                {
                    "id": S,
                    "name": S,
                    "priority": {"type": "string", "enum": ["core", "later"]},
                    "values": SA,
                    "actor": S,
                    "trigger": S,
                    "steps": _arr(STEP, minItems=1),
                    "branches": _arr(_obj({"id": S, "after": S, "condition": S, "steps": _arr(STEP, minItems=1)})),
                    "outcome": S,
                    "acceptance": _obj({"given": SA, "when": SA, "then": SA}),
                }
            ),
            minItems=1,
            maxItems=MAX_WORKFLOWS,
        ),
        "scope": _obj({"goldenPath": S, "included": SA, "excluded": SA}),
    }
)

# -- 26.2 expectations ------------------------------------------------------------------------------------------------

CHANGE = {"type": "string", "enum": ["decrease", "increase", "set", "created"]}
EXPECT_SCHEMA = _obj(
    {
        "paths": _arr(
            _obj(
                {
                    "workflow": S,
                    "path": S,
                    "steps": _arr(
                        _obj(
                            {
                                "step": S,
                                "allowed": SA,
                                "refused": SA,
                                "record": S,
                                "statusAfter": S,
                                "visibleTo": SA,
                                "hiddenFrom": SA,
                                "effects": _arr(_obj({"id": S, "record": S, "what": S, "change": CHANGE})),
                                "refusedBefore": _arr(_obj({"step": S, "as": S, "why": S})),
                            }
                        )
                    ),
                    "outcome": _arr(_obj({"as": S, "sees": S})),
                }
            )
        )
    }
)

# -- 26.3 binding -----------------------------------------------------------------------------------------------------

BOUND_CALL = {"operationId": S, "pathParamsJson": S, "queryJson": S, "bodyJson": S}
BIND_SCHEMA = _obj(
    {
        "actors": _arr(_obj({"actor": S, "role": S})),
        "records": _arr(
            _obj(
                {
                    "record": S,
                    "entity": S,
                    "getOperation": S,
                    "listOperation": S,
                    "statusField": S,
                    "statuses": _arr(_obj({"business": S, "value": S})),
                }
            )  # fmt: skip
        ),
        "setup": _arr(_obj({"var": S, "as": S, **BOUND_CALL, "save": S})),
        "steps": _arr(
            _obj(
                {
                    "workflow": S,
                    "path": S,
                    "step": S,
                    **BOUND_CALL,
                    "creates": S,
                    "automatic": {"type": "boolean"},
                    "page": S,
                    "pageParamsJson": S,
                }
            )  # fmt: skip
        ),
        "effects": _arr(_obj({"workflow": S, "path": S, "step": S, "effect": S, "as": S, **BOUND_CALL, "field": S})),
        "outcomes": _arr(_obj({"workflow": S, "path": S, "as": S, "page": S, "pageParamsJson": S})),
        "unbound": _arr(_obj({"what": S, "reason": S})),
    }
)

# -- 26.5 the second look, judging and the summary

SECOND_LOOK_SCHEMA = _obj({"cause": {"type": "string", "enum": ["app", "binding"]}, "reason": S, **BOUND_CALL})


STEP_JUDGE_SCHEMA = _obj(
    {
        "canDo": {"type": "string", "enum": ["yes", "partly", "no"]},
        "control": S,
        "issue": S,
        "clarity": {"type": "integer"},
    }
)
OUTCOME_JUDGE_SCHEMA = _obj({"shows": {"type": "string", "enum": ["yes", "partly", "no"]}, "note": S})
SUMMARY_SCHEMA = _obj(
    {
        "summary": S,
        "values": _arr(
            _obj({"id": S, "delivered": {"type": "string", "enum": ["yes", "partly", "no"]}, "evidence": S})
        ),
        "gaps": SA,
        "improvements": SA,
    }
)


# -- helpers ----------------------------------------------------------------------------------------------------------


def paths(workflow: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    """A workflow's paths: ("main", its steps) and one (branch id, steps up to the split + the branch's steps)."""
    out = [("main", list(workflow.get("steps") or []))]
    for branch in workflow.get("branches") or []:
        ids = [step["id"] for step in workflow.get("steps") or []]
        cut = ids.index(branch["after"]) + 1 if branch.get("after") in ids else len(ids)
        out.append((branch["id"], list(workflow["steps"][:cut]) + list(branch.get("steps") or [])))
    return out


def all_steps(workflow: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every step once, with the path it belongs to: the main steps, then each branch's own steps."""
    out = [("main", step) for step in workflow.get("steps") or []]
    for branch in workflow.get("branches") or []:
        out += [(branch["id"], step) for step in branch.get("steps") or []]
    return out


def core(business: dict[str, Any]) -> list[dict[str, Any]]:
    return [w for w in business.get("workflows") or [] if w.get("priority", "core") == "core"]


def undelivered(business: dict[str, Any]) -> list[str]:
    """Value ids no step delivers."""
    delivered = {v for w in business.get("workflows") or [] for _, s in all_steps(w) for v in s.get("delivers") or []}
    return [v["id"] for v in business.get("values") or [] if v["id"] not in delivered]


def brief(requirement: str, business: dict[str, Any]) -> str:
    """The requirement the drafting engine receives: the owner's text plus the business workflows, in plain words."""
    actors = {a["id"]: a for a in business.get("actors") or []}

    def name(actor_id: str) -> str:
        return actors.get(actor_id, {}).get("name", actor_id)

    statuses: dict[str, list[str]] = {}

    def step_text(prefix: str, step: dict[str, Any]) -> str:
        text = f"{prefix} {name(step['actor'])}: {step['action']}"
        if step.get("statusAfter"):
            text += f" → the {step['record']} becomes **{step['statusAfter']}**"
            statuses.setdefault(step["record"], [])
            if step["statusAfter"] not in statuses[step["record"]]:
                statuses[step["record"]].append(step["statusAfter"])
        if step.get("rule"):
            text += f" (rule: {step['rule']})"
        return text

    lines = [requirement.strip(), "", "## Business workflows the first version must support end to end", ""]
    roles = [a for a in business.get("actors") or [] if a.get("signsIn")]
    if roles:
        lines.append(
            "Everyone signs in with their own role: "
            + ", ".join(f"**{a['name']}** ({str(a.get('description') or '').rstrip('.')})" for a in roles)
            + ". After signing in, each role lands on the work they must do next (their open records, newest first),"
            " and only sees the actions their role may take."
        )
        lines.append("")
    later = [w for w in business.get("workflows") or [] if w.get("priority", "core") != "core"]
    golden_path = (business.get("scope") or {}).get("goldenPath")
    for workflow in core(business):
        golden = " (the most important one)" if workflow["id"] == golden_path else ""
        lines.append(f"### {workflow['name']}{golden}")
        lines.append(f"Started when: {workflow.get('trigger', '')}")
        numbers = {}
        for number, step in enumerate(workflow.get("steps") or [], 1):
            numbers[step["id"]] = number
            lines.append(step_text(f"{number}.", step))
        for branch in workflow.get("branches") or []:
            where = f" after step {numbers[branch['after']]}" if branch.get("after") in numbers else ""
            lines.append(f"If {str(branch.get('condition') or '').rstrip('.')}{where}:")
            for letter, step in zip("abcdefghij", branch.get("steps") or [], strict=False):
                lines.append(step_text(f"   {letter}.", step))
        lines.append(f"Done when: {workflow.get('outcome', '')}")
        lines.append("")
    if statuses:
        lines.append("Status flows: " + "; ".join(f"{record}: {' → '.join(s)}" for record, s in statuses.items()) + ".")
        lines.append("Each status change is an action on the record, allowed only to the role that performs it.")
        lines.append("")
    if later:
        lines.append("Later, not needed in this first version: " + "; ".join(w["name"] for w in later) + ".")
    excluded = (business.get("scope") or {}).get("excluded") or []
    if excluded:
        lines.append("Not in this first version: " + "; ".join(excluded) + ".")
    return "\n".join(lines).strip() + "\n"


def actor_name(business: dict[str, Any], actor: str) -> str:
    other = actor.startswith("other:")
    base = actor.split(":", 1)[1] if other else actor
    found = next((a["name"] for a in business.get("actors") or [] if a["id"] == base), base)
    return f"another {found}" if other else found


def expectation_texts(business: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    """26.2: one readable sentence per expectation, by code, for the review and the Business tab."""
    workflows = {w["id"]: w for w in business.get("workflows") or []}
    out: list[dict[str, Any]] = []
    for path in expected.get("paths") or []:
        workflow = workflows.get(path.get("workflow")) or {}
        steps = {step["id"]: step for _, step in all_steps(workflow)} if workflow else {}
        for line in path.get("steps") or []:
            step = steps.get(line.get("step")) or {}
            action = step.get("action") or line.get("step")
            texts: list[str] = []
            for actor in line.get("allowed") or []:
                texts.append(f"{actor_name(business, actor)} can {action}")
            for actor in line.get("refused") or []:
                texts.append(f"{actor_name(business, actor)} cannot {action}")
            if line.get("statusAfter"):
                texts.append(f"afterwards the {line.get('record')} is '{line['statusAfter']}'")
            for actor in line.get("visibleTo") or []:
                texts.append(f"{actor_name(business, actor)} sees the {line.get('record')}")
            for actor in line.get("hiddenFrom") or []:
                texts.append(f"{actor_name(business, actor)} does not see the {line.get('record')}")
            for effect in line.get("effects") or []:
                texts.append(f"the {effect.get('record')}'s {effect.get('what')}: {effect.get('change')}")
            for before in line.get("refusedBefore") or []:
                texts.append(
                    f"before this, {actor_name(business, before.get('as', ''))} cannot do step {before.get('step')}"
                )
            out.append(
                {
                    "workflow": path.get("workflow"),
                    "path": path.get("path"),
                    "step": line.get("step"),
                    "texts": texts,
                }
            )
    return out
