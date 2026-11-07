"""Story 26.5: checks the frozen expectations against the live app, through the binding (from the business-value lab).

Every expectation becomes one line with a result and its evidence:

    does        the allowed actor performs the step                         2xx
    refused     a refused actor tries the same call                         4xx
    premature   a later step is tried before this one (refusedBefore)       4xx
    status      the record's status after the step                          the bound status value
    visible     an actor who must see the record reads it                   200
    hidden      an actor who must not see it reads it                       4xx
    effect      a watched number changes (decrease, increase, set, created) before vs after

Results: pass, fail, blocked (an earlier step failed), unbound (the app has nothing to check it with). A branch path
first replays the main steps it shares (`prefix`, not scored again).
"""

import json
import re
import secrets
from typing import Any

from ..business.model import all_steps
from .api import Api, EvaluationError, get_path, render, var_name

ok2 = lambda status: isinstance(status, int) and 200 <= status < 300  # noqa: E731
refused = lambda status: isinstance(status, int) and 400 <= status < 500  # noqa: E731


def judged(result: dict[str, Any], want) -> str:
    """No answer (the call could not be made) → unbound; else pass / fail on the status code."""
    if result.get("status") is None:
        return "unbound"
    return "pass" if want(result["status"]) else "fail"


def _clip(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text[:limit]


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Checker:
    def __init__(self, *, api: Api, second_look, log, business, expected, binding, walker, frontend, routes, auth):
        # second_look(step, bound, result, operations) -> {"cause", "reason", **call} (a provider call, or None)
        self.api, self.second_look, self.log = api, second_look, log
        self.business, self.expected, self.binding = business, expected, binding
        self.walker, self.frontend, self.routes, self.auth = walker, frontend, routes, auth
        self.roles = {a["actor"]: a["role"] for a in binding.get("actors", [])}
        self.records = {var_name(r["record"]): r for r in binding.get("records", [])}
        self.steps_info = {(w["id"], s["id"]): s for w in business["workflows"] for _, s in all_steps(w)}
        self.actor_names = {a["id"]: a["name"] for a in business["actors"]}
        self.signed_in: dict[str, Any] = {}
        self.shot_no = 0

    # -- lookups -----------------------------------------------------------------------------------------------------

    def role(self, actor: str) -> str | None:
        """An actor id (or `other:<actor>`) → the api's `as` key, None when no role plays it."""
        if actor.startswith("other:"):
            base = self.roles.get(actor.split(":", 1)[1])
            return f"other:{base}" if base else None
        return self.roles.get(actor) or None

    def name(self, actor: str) -> str:
        if actor.startswith("other:"):
            return "another " + self.actor_names.get(actor.split(":", 1)[1], actor).lower()
        return self.actor_names.get(actor, actor)

    def bound_step(self, workflow: str, path: str, step: str) -> dict[str, Any] | None:
        candidates = [b for b in self.binding.get("steps", []) if b["workflow"] == workflow and b["step"] == step]
        return next((b for b in candidates if b["path"] == path), None) or next(
            (b for b in candidates if b["path"] == "main"), candidates[0] if candidates else None
        )

    def bound_effect(self, workflow: str, path: str, step: str, effect: str) -> dict[str, Any] | None:
        candidates = [
            e
            for e in self.binding.get("effects", [])
            if e["workflow"] == workflow and e["step"] == step and e["effect"] == effect
        ]
        return next((e for e in candidates if e["path"] == path), candidates[0] if candidates else None)

    def read_record(
        self, record: str, variables: dict[str, Any], as_key: str, lister: str | None = None
    ) -> dict[str, Any]:
        bound = self.records.get(var_name(record))
        if not bound or not bound.get("getOperation"):
            return {"ok": None, "error": f"no read operation bound for {record!r}"}
        op = self.api.operations.get(bound["getOperation"])
        if op is None:
            return {"ok": None, "error": f"unknown operation {bound['getOperation']!r}"}
        if var_name(record) not in variables and bound.get("listOperation") in self.api.operations:
            listed = self.api.call(
                {"operationId": bound["listOperation"], "queryJson": '{"limit": 1}'}, variables, lister or as_key
            )
            first = get_path(listed.get("data"), "items.0.id") if ok2(listed.get("status")) else None
            if first is not None:  # the path made none: an existing one (the seed's), listed by the step's own actor
                variables[var_name(record)] = first
                variables.setdefault("__borrowed__", set()).add(var_name(record))
        result = self._read(op, record, variables, as_key)
        if result.get("status") in (403, 404):
            # a role may read the record through its own operation (an assigned worker's `GET /jobs/{id}`, as its
            # screens do): another single-record read of the same fields counts, and the evidence names it
            for other in self._other_reads(op):
                again = self._read(other, record, variables, as_key)
                if ok2(again.get("status")):
                    return again
        return result

    def _read(self, op: dict[str, Any], record: str, variables: dict[str, Any], as_key: str) -> dict[str, Any]:
        params = {name: f"{{{{{var_name(record)}}}}}" for name in re.findall(r"\{([^}]+)\}", op["path"])}
        return self.api.call(
            {"operationId": op["operationId"], "pathParamsJson": json.dumps(params)}, variables, as_key
        )

    def _other_reads(self, op: dict[str, Any]) -> list[dict[str, Any]]:
        """The other `GET /…/{id}` operations of the same record: the same response fields, or an untyped response
        under the same resource (`GET /repair-requests/jobs/{id}` drafted without a response type)."""
        fields = set((op.get("response") or {}).keys())
        resource = (op.get("path") or "").strip("/").split("/")[0]

        def same_record(other: dict[str, Any]) -> bool:
            theirs = set((other.get("response") or {}).keys())
            if theirs:
                return bool(fields) and theirs == fields
            return bool(resource) and (other.get("path") or "").strip("/").split("/")[0] == resource

        return [
            other
            for other in self.api.operations.values()
            if other["operationId"] != op["operationId"]
            and other.get("method") == "GET"
            and len(re.findall(r"\{[^}]+\}", other.get("path") or "")) == 1
            and same_record(other)
        ]

    # -- the browser -------------------------------------------------------------------------------------------------

    def screenshot(self, as_key: str | None, page: str, params_json: str, variables: dict[str, Any], label: str):
        if self.walker is None or not page:
            return None
        route = self.routes.get(page)
        if not route:
            return {"page": page, "ok": False, "error": f"no page {page!r}"}
        try:
            params = json.loads(render(params_json or "", variables) or "{}")
        except (EvaluationError, json.JSONDecodeError) as exc:
            return {"page": page, "ok": False, "error": f"params: {exc}"}
        url_path = re.sub(r"\[([A-Za-z0-9_]+)\]", lambda m: str(params.get(m.group(1), m.group(0))), route)
        user = None
        if self.auth and as_key:
            login = self.api.login_of(as_key)
            if login not in self.signed_in:
                self.shot_no += 1
                file = f"{self.shot_no:02d}-signin-{as_key.replace(':', '-')}.png"
                self.signed_in[login] = self.walker.send(
                    {
                        "cmd": "login",
                        "user": login,
                        "url": self.frontend + (self.auth.get("signIn") or "/login"),
                        "field": self.auth["field"],
                        "login": login,
                        "password": self.auth["password"],
                        "file": f"/out/{file}",
                    }
                ) | {"file": f"shots/{file}", "as": as_key}
                self.log(f"    UI sign-in as {login}: {'ok' if self.signed_in[login].get('ok') else 'FAILED'}")
            user = login
        self.shot_no += 1
        file = f"{self.shot_no:02d}-{''.join(c if c.isalnum() else '-' for c in label.lower())[:60]}.png"
        answer = self.walker.send(
            {"cmd": "shot", "user": user, "url": self.frontend + url_path, "file": f"/out/{file}"}
        )
        return {"page": page, "route": url_path, "as": as_key, "file": f"shots/{file}", **answer}

    # -- running -----------------------------------------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        users = self.api.user_variables()
        lines: list[dict[str, Any]] = []
        paths_out = []
        for expected_path in self.expected["paths"]:
            out = self.run_path(expected_path, users, lines)
            paths_out.append(out)
        return {"lines": lines, "paths": paths_out, "signIn": self.signed_in, "users": sorted(users)}

    def run_path(self, expected_path: dict[str, Any], users: dict[str, Any], lines: list[dict[str, Any]]):
        workflow, path = expected_path["workflow"], expected_path["path"]
        self.log(f"  {workflow} / {path}")
        variables: dict[str, Any] = {"run": secrets.token_hex(3), **users}
        main_ids = (
            {s["id"] for w in self.business["workflows"] if w["id"] == workflow for s in w["steps"]}
            if path != "main"
            else set()
        )
        notes: list[str] = []
        for setup in self.binding.get("setup", []):
            as_key = self.role(setup["as"]) or setup["as"]
            result = self.api.call(setup, variables, as_key)
            value = get_path(result.get("data"), setup.get("save", "")) if ok2(result.get("status")) else None
            if value is None and ok2(result.get("status")) and setup.get("queryJson"):
                # nothing matches the filter (e.g. no flat belongs to the demo tenant): a finding about the demo data;
                # take an unfiltered one so the rest of the path can still be checked
                retry = self.api.call({**setup, "queryJson": ""}, variables, as_key)
                value = get_path(retry.get("data"), setup.get("save", "")) if ok2(retry.get("status")) else None
                notes.append(
                    f"Finding: no {setup['var']} matches {setup['queryJson']} for the demo {setup['as']}"
                    + (" (used another one to go on)" if value is not None else "")
                )
            elif value is None:
                notes.append(
                    f"setup {setup['var']}: {result.get('status', result.get('error'))}, nothing at {setup.get('save')}"
                )
            if value is not None:
                variables[var_name(setup["var"])] = value
        shots: list[dict[str, Any]] = []
        repairs: list[dict[str, Any]] = []
        blocked: str | None = None

        def line(step, kind, actor, expect, result, evidence=None, scored=True):
            lines.append(
                {
                    "workflow": workflow,
                    "path": path,
                    "step": step,
                    "kind": kind,
                    "actor": actor,
                    "expect": expect,
                    "result": result,
                    "evidence": evidence or {},
                    "scored": scored,
                }
            )
            mark = {"pass": "ok", "fail": "FAIL", "blocked": "blocked", "unbound": "unbound"}.get(result, result)
            if scored and result != "blocked":
                self.log(f"    {step:<22} {kind:<9} {mark:<7} {expect}")

        def evidence(result: dict[str, Any], detail: str = "") -> dict[str, Any]:
            out = {"call": result.get("call"), "as": result.get("as"), "status": result.get("status")}
            if result.get("error"):
                out["error"] = result["error"]
            if detail:
                out["detail"] = detail
            if result.get("status") is not None and not ok2(result.get("status")):
                out["response"] = _clip(result.get("data"))
            return out

        for exp in expected_path["steps"]:
            step = exp["step"]
            info = self.steps_info.get((workflow, step), {})
            action = info.get("action", step)
            record = exp.get("record") or info.get("record", "")
            prefix = step in main_ids
            scored = not prefix
            allowed = (exp.get("allowed") or [info.get("actor", "")])[0]
            expectations = self.expectation_texts(exp, action, record)

            if blocked:
                for kind, actor, text in expectations:
                    if scored:
                        line(step, kind, actor, text, "blocked", {"detail": f"blocked by {blocked}"})
                continue
            bound = self.bound_step(workflow, path, step)
            as_key = self.role(allowed)
            if bound is not None and bound.get("automatic"):
                # the app does this step itself, inside the previous one: check what it must lead to, nothing to call
                line(
                    step,
                    "does",
                    allowed,
                    f"{action} (done by the app itself)",
                    "pass",
                    {"detail": "the app performs this step automatically as part of the previous step"},
                    scored,
                )
                for kind, actor, text in expectations:
                    if kind in ("refused", "premature"):
                        line(step, kind, actor, text, "n/a", {"detail": "no separate action to refuse"}, scored=False)
                if scored:
                    self.after_step(step, exp, record, allowed, as_key, variables, line, evidence, {})
                continue
            if bound is None or as_key is None:
                reason = "no operation performs this step" if bound is None else f"no app role for {allowed}"
                for kind, actor, text in expectations:
                    line(step, kind, actor, text, "unbound", {"detail": reason}, scored)
                blocked = f"{step} ({reason})"
                continue

            baselines: dict[str, Any] = {}
            changed_by: list[str] = []  # wrong actors whose attempt went through (and may have changed the record)
            if scored:
                for attempt in exp.get("refusedBefore") or []:
                    later = self.steps_info.get((workflow, attempt["step"]), {}).get("action", attempt["step"])
                    text = f"{self.name(attempt['as'])} cannot {later} yet ({attempt.get('why', '')})"
                    other = self.bound_step(workflow, path, attempt["step"])
                    key = self.role(attempt["as"])
                    if other is None or key is None:
                        line(step, "premature", attempt["as"], text, "unbound", {"detail": "no operation or role"})
                        continue
                    result = self.api.call(other, variables, key)
                    if result.get("status") is None and "unresolved" in str(result.get("error")):
                        # the record it acts on does not exist yet: nothing to try, not a finding about the app
                        line(step, "premature", attempt["as"], text, "n/a", evidence(result), scored=False)
                        continue
                    line(step, "premature", attempt["as"], text, judged(result, refused), evidence(result))
                    if ok2(result.get("status")) and (result.get("call") or "").split(" ")[0] != "GET":
                        changed_by.append(f"{self.name(attempt['as'])} ({attempt['step']})")
                for actor in exp.get("refused") or []:
                    text = f"{self.name(actor)} is refused: {action}"
                    key = self.role(actor)
                    if key is None:
                        line(step, "refused", actor, text, "unbound", {"detail": f"no app role for {actor}"})
                        continue
                    result = self.api.call(bound, variables, key)
                    line(step, "refused", actor, text, judged(result, refused), evidence(result))
                    if ok2(result.get("status")) and (result.get("call") or "").split(" ")[0] != "GET":
                        changed_by.append(self.name(actor))
                for effect in exp.get("effects") or []:
                    reader = self.bound_effect(workflow, path, step, effect["id"])
                    if reader is not None:
                        before = self.api.call(
                            reader, variables, self.role(reader.get("as", "")) or reader.get("as", "")
                        )
                        baselines[effect["id"]] = (reader, before)
                shot = self.screenshot(
                    as_key,
                    bound.get("page", ""),
                    bound.get("pageParamsJson", ""),
                    variables,
                    f"{workflow}-{path}-{step}",
                )
                if shot:
                    shots.append({"step": step, **shot})

            result = self.api.call(bound, variables, as_key)
            if not ok2(result.get("status")) and not repairs and self.second_look is not None:
                verdict = self.second_look(
                    {"step": step, "action": action, "expected": exp},
                    bound,
                    {k: result.get(k) for k in ("call", "as", "status", "data", "body", "error")},
                    list(self.api.operations.values()),
                )
                if verdict is None:
                    verdict = {"cause": "app", "reason": "no second look (the provider did not answer)"}
                repairs.append({"step": step, "cause": verdict["cause"], "reason": verdict["reason"]})
                self.log(f"    second look at {step}: {verdict['cause']} ({verdict['reason'][:160]})")
                if verdict["cause"] == "binding":
                    bound = {
                        **bound,
                        **{k: verdict[k] for k in ("operationId", "pathParamsJson", "queryJson", "bodyJson")},
                    }
                    result = self.api.call(bound, variables, as_key)
            does_text = f"{self.name(allowed)} can {action}"
            if not ok2(result.get("status")):
                if changed_by and result.get("status") is not None:
                    # not a finding of its own: a wrong actor already changed the record (that line failed)
                    line(
                        step,
                        "does",
                        allowed,
                        does_text,
                        "blocked",
                        evidence(result, f"the record was already changed by {', '.join(changed_by)}"),
                        scored,
                    )
                else:
                    line(step, "does", allowed, does_text, judged(result, ok2), evidence(result), scored)
                blocked = f"{step} ({result.get('status') or result.get('error')})"
                for kind, actor, text in expectations:
                    if kind != "does" and scored and kind not in ("refused", "premature"):
                        line(step, kind, actor, text, "blocked", {"detail": f"blocked by {blocked}"})
                continue
            line(step, "does", allowed, does_text, "pass", evidence(result), scored)
            if bound.get("creates"):
                created = get_path(result.get("data"), "id")
                if created is not None:
                    variables[var_name(bound["creates"])] = created
            if not scored:
                continue

            self.after_step(step, exp, record, allowed, as_key, variables, line, evidence, baselines)

        outcome_shots = []
        for outcome in [o for o in self.binding.get("outcomes", []) if o["workflow"] == workflow and o["path"] == path]:
            expect = next((x["sees"] for x in expected_path.get("outcome") or [] if x["as"] == outcome["as"]), "")
            shot = self.screenshot(
                self.role(outcome["as"]),
                outcome.get("page", ""),
                outcome.get("pageParamsJson", ""),
                variables,
                f"{workflow}-{path}-outcome-{outcome['as']}",
            )
            if shot:
                outcome_shots.append({"as": outcome["as"], "expect": expect, **shot})
        completed = blocked is None
        return {
            "workflow": workflow,
            "path": path,
            "completed": completed,
            "stopped": blocked,
            "repairs": repairs,
            "notes": notes,
            "shots": shots,
            "outcomes": outcome_shots,
        }

    def after_step(self, step, exp, record, allowed, as_key, variables, line, evidence, baselines) -> None:
        """What must be true once the step happened: the status, who can and cannot see the record, the effects."""
        status_word = exp.get("statusAfter")
        visible = exp.get("visibleTo") or []
        if status_word:
            text = f"the {record} becomes {status_word}"
            bound_record = self.records.get(var_name(record)) or {}
            value = next((s["value"] for s in bound_record.get("statuses", []) if s["business"] == status_word), None)
            reader_actor = next((a for a in visible if self.role(a)), allowed)
            if not bound_record.get("statusField") or value is None:
                line(step, "status", reader_actor, text, "unbound", {"detail": f"no status bound for {status_word!r}"})
            else:
                read = self.read_record(record, variables, self.role(reader_actor) or as_key, lister=as_key)
                got = get_path(read.get("data"), bound_record["statusField"]) if ok2(read.get("status")) else None
                verdict = (
                    ("pass" if str(got).lower() == str(value).lower() else "fail")
                    if read.get("status") is not None
                    else "unbound"
                )
                line(
                    step,
                    "status",
                    reader_actor,
                    text,
                    verdict,
                    evidence(read, f"{bound_record['statusField']} = {got!r}, expected {value!r}"),
                )
        for actor in visible:
            text = f"{self.name(actor)} can see the {record}"
            key = self.role(actor)
            if key is None:
                line(step, "visible", actor, text, "unbound", {"detail": f"no app role for {actor}"})
                continue
            read = self.read_record(record, variables, key, lister=as_key)
            line(step, "visible", actor, text, judged(read, ok2), evidence(read))
        for actor in exp.get("hiddenFrom") or []:
            text = f"{self.name(actor)} cannot see the {record}"
            key = self.role(actor)
            if key is None:
                line(step, "hidden", actor, text, "unbound", {"detail": f"no app role for {actor}"})
                continue
            if var_name(record) in variables.get("__borrowed__", set()) or var_name(record) not in variables:
                # an existing record whose owner this path does not know: no fair way to say who must not see it
                line(step, "hidden", actor, text, "n/a", {"detail": "the path made no record of its own"}, scored=False)
                continue
            read = self.read_record(record, variables, key, lister=as_key)
            line(step, "hidden", actor, text, judged(read, refused), evidence(read))
        for effect in exp.get("effects") or []:
            text = f"{effect['what']} of the {effect['record']}: {effect['change']}"
            if effect["id"] not in baselines:
                line(step, "effect", "", text, "unbound", {"detail": "nothing in the app reads it"})
                continue
            reader, before = baselines[effect["id"]]
            after = self.api.call(reader, variables, self.role(reader.get("as", "")) or reader.get("as", ""))
            b = _number(get_path(before.get("data"), reader["field"]))
            a = _number(get_path(after.get("data"), reader["field"]))
            change = effect["change"]
            if a is None or b is None:
                passed = change == "set" and get_path(after.get("data"), reader["field"]) is not None
            elif change == "decrease":
                passed = a < b
            elif change in ("increase", "created"):
                passed = a > b
            else:
                passed = a != b
            line(
                step, "effect", "", text, "pass" if passed else "fail", evidence(after, f"{reader['field']}: {b} → {a}")
            )

    def expectation_texts(self, exp: dict[str, Any], action: str, record: str) -> list[tuple[str, str, str]]:
        """The step's expectations as (kind, actor, text), for blocked and unbound lines."""
        out = [("does", (exp.get("allowed") or [""])[0], f"{self.name((exp.get('allowed') or [''])[0])} can {action}")]
        out += [("refused", a, f"{self.name(a)} is refused: {action}") for a in exp.get("refused") or []]
        out += [
            ("premature", r["as"], f"{self.name(r['as'])} cannot {r['step']} yet")
            for r in exp.get("refusedBefore") or []
        ]
        if exp.get("statusAfter"):
            out.append(("status", "", f"the {record} becomes {exp['statusAfter']}"))
        out += [("visible", a, f"{self.name(a)} can see the {record}") for a in exp.get("visibleTo") or []]
        out += [("hidden", a, f"{self.name(a)} cannot see the {record}") for a in exp.get("hiddenFrom") or []]
        out += [("effect", "", f"{e['what']} of the {e['record']}: {e['change']}") for e in exp.get("effects") or []]
        return out


def score(lines: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [line for line in lines if line["scored"]]
    counts = {r: sum(1 for line in scored if line["result"] == r) for r in ("pass", "fail", "blocked", "unbound")}
    by_kind: dict[str, dict[str, int]] = {}
    for line in scored:
        bucket = by_kind.setdefault(line["kind"], {"pass": 0, "total": 0})
        bucket["total"] += 1
        bucket["pass"] += line["result"] == "pass"
    total = len(scored)
    decided = counts["pass"] + counts["fail"]  # blocked and unbound lines are unknown, not failures
    return {
        "met": counts["pass"],
        "total": total,
        "percent": round(100 * counts["pass"] / total) if total else 0,
        "decided": decided,
        "decidedPercent": round(100 * counts["pass"] / decided) if decided else 0,
        "counts": counts,
        "byKind": by_kind,
    }
