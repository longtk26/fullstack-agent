"""Roles and ownership as a plugin (Story 10.3): the `policies[]` operations name, enforced server-side.

- `role`: the route's current user must have one of the policy's roles (`require_roles`, auth-jwt's security
  library), else 403, before the use case runs.
- `ownership`: the record's `ownerField` is the signed-in user. Create sets it (a client's value is ignored; the
  contract says `x-bga.source: currentUser`); get, update and delete answer another user's record with 404 (the
  policy's `denyStatus` may say 403), checked in the use case; lists show only the caller's records. `bypassRoles`
  reach every record.

`allowedActions` follow both: an action whose operation the caller's role or ownership forbids is not listed. The
owner field becomes a reference to the user entity (a relationship is added when the spec has none), and the demo
users get a second plain account, so "another user's record" can be shown and checked.
"""

import copy
import re
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_snake

from .auth_jwt import DEMO_HASH, _auth, _demo_login
from .base import ActionCheck, CaseContext, Code, Plugin, RepositoryFilter, RouterParam

ENTITIES = "src.modules.shared.domain.entities"
OWN = ("get", "update", "delete")
SIGN_IN = (("tests.auth", ("sign_in",)),)


def _policies(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {policy["name"]: policy for policy in spec.get("policies", [])}


def _owner_only(spec: dict[str, Any], op: dict[str, Any]) -> list[dict[str, Any]]:
    """The `ownerOnly` rules an operation names (Story 10.4: they are ownership, as a policy says it)."""
    rules = {rule["id"]: rule for rule in spec.get("rules", []) if rule.get("kind") == "ownerOnly"}
    return [rules[rule_id] for rule_id in op.get("rules") or [] if rule_id in rules]


def _owned_by(spec: dict[str, Any], op: dict[str, Any]) -> dict[str, Any] | None:
    """`{ownerField, bypassRoles, denyStatus}` of the operation's ownership policy or `ownerOnly` rule."""
    policy = _policies(spec).get(op.get("policy") or "")
    if policy and policy["type"] == "ownership":
        return policy
    rules = _owner_only(spec, op)
    return dict(rules[0]["params"]) if rules else None


def _args(values: list[str]) -> str:
    return ", ".join(f'"{value}"' for value in values)


def _tuple(values: list[str]) -> str:
    return f"({_args(values)}{',' if len(values) == 1 else ''})"


def _quoted(path: str) -> str:
    return f'f"{path}"' if "{" in path else f'"{path}"'


def _sign_in(role: str) -> str:
    return f'client.headers["Authorization"] = f"Bearer {{sign_in(client, role=\'{role}\')}}"'


def _roles(op: dict[str, Any]) -> list[str]:
    return list((op.get("auth") or {}).get("roles") or [])


def _ownership(op: dict[str, Any]) -> dict[str, Any] | None:
    return (op.get("auth") or {}).get("ownership")


def _secured(op: dict[str, Any]) -> bool:
    return (op.get("auth") or {}).get("auth") == "jwt"


def _policed(module: dict[str, Any]) -> bool:
    return any(_roles(op) or _ownership(op) or op.get("ownerSource") for op in module["operations"])


def _record_op(module: dict[str, Any], action: str) -> dict[str, Any] | None:
    """The operation behind a record action (`update`, `delete`, a custom write's operationId; a rule's
    `transition:<STATE>` is an update, 10.4)."""
    action = "update" if action.startswith("transition:") else action
    return next((op for op in module["operations"] if action in (op.get("action"), op["operationId"])), None)


def _own_param(path: str) -> str | None:
    names = re.findall(r"\{(\w+)\}", path)
    return names[-1] if names else None


def scenario_user(
    contract: dict[str, Any], plan: dict[str, Any], op: dict[str, Any], record: dict | None
) -> str | None:
    """The demo user a scenario of `op` on `record` runs as (another plugin's, Story 10.4): one with the role the
    operation needs, the record's owner, or a bypass role; None: the default demo user."""
    auth = plan.get("auth")
    if not auth:
        return None
    demo = auth["demoUsers"]
    if _roles(op) and demo and demo[0]["role"] not in _roles(op):
        return next((u["login"] for u in demo if u["role"] in _roles(op)), None)
    ownership = _ownership(op)
    if not ownership or record is None:
        return None
    user_model = next(m for m in plan["models"] if m.get("entity") == auth["userEntity"])
    user_pk = next(column["apiName"] for column in user_model["columns"] if column["primaryKey"])
    users = contract["x-bga"]["fixtures"].get(auth["userEntity"]) or []
    login_of = {row.get(user_pk): row.get(auth["loginField"]) for row in users}
    owner = login_of.get(record.get(ownership["field"]))
    if owner:
        return owner if owner != demo[0]["login"] else None
    return next((u["login"] for u in demo if u["role"] in ownership["bypassRoles"]), None)


def _test(op: dict[str, Any], case: str, expect: int, description: str) -> dict[str, Any]:
    return {
        "id": f"test_{op['handler']}__{case}",
        "operationId": op["operationId"],
        "case": case,
        "expectStatus": expect,
        "description": description,
    }


class PoliciesPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="policies", requires=("auth-jwt",))

    def applies(self, spec: dict[str, Any]) -> bool:
        return (spec.get("auth") or {}).get("type") == "jwt" and any(
            op.get("policy") or _owner_only(spec, op) for op in spec.get("operations", [])
        )

    # -- the spec and the plan ------------------------------------------------------------------------------------

    def extend_spec(self, spec: dict[str, Any]) -> None:
        auth = _auth(spec)
        owned: dict[str, str] = {}  # entity → owner field
        bypass: set[str] = set()
        for op in spec.get("operations", []):
            policy = _owned_by(spec, op)
            if policy and op.get("entity"):
                owned.setdefault(op["entity"], policy["ownerField"])
                bypass |= set(policy.get("bypassRoles") or [])
        relationships = spec.setdefault("relationships", [])
        names = {rel["name"] for rel in relationships}
        for entity, field in owned.items():
            if any(rel["to"] == entity and rel.get("foreignKey") == field for rel in relationships):
                continue
            name = f"{entity[:1].lower()}{entity[1:]}Owner"
            while name in names:
                name += "2"
            names.add(name)
            relationships.append(
                {
                    "name": name,
                    "type": "one-to-many",
                    "from": auth["userEntity"],
                    "to": entity,
                    "foreignKey": field,
                    "onDelete": "CASCADE",
                }
            )
        if not owned:
            return
        # two demo users without a bypass role: each owns records the other cannot reach
        block = next(seed for seed in spec.get("seed", []) if seed["entity"] == auth["userEntity"])
        demo = [record for record in block["records"] if record.get("passwordHash") == DEMO_HASH]
        plain = [record for record in demo if record["role"] not in bypass]
        if plain and len(plain) < 2:
            other = copy.deepcopy(plain[0])
            other[auth["loginField"]] = _demo_login(auth["loginField"], f"{plain[0]['role']}-2")
            block["records"].append(other)

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        policies = _policies(spec)
        spec_ops = {op["operationId"]: op for op in spec.get("operations", [])}
        models = {model["entity"]: model for model in plan["models"] if model.get("entity")}
        roles = plan["auth"]["roles"]
        for module in plan["modules"]:
            if module.get("plugin"):
                continue
            model = models[module["entity"]]
            by_api = {column["apiName"]: column for column in model["columns"]}
            owner = None
            for op in module["operations"]:
                spec_op = spec_ops.get(op["operationId"], {})
                policy = policies.get((op.get("auth") or {}).get("policy") or "")
                if policy is not None and policy["type"] == "role":
                    op["auth"]["roles"] = list(policy["roles"])
                    op["errors"].append({"status": 403, "exception": "ForbiddenException", "code": "FORBIDDEN"})
                    if op.get("action") and set(roles) - set(policy["roles"]):
                        module["tests"].append(_test(op, "missing_role", 403, "a role the policy does not name"))
                owner_only = _owner_only(spec, spec_op)
                if owner_only:  # Story 10.4: `ownerOnly` rules are this plugin's
                    op["auth"] = {**(op.get("auth") or {"policy": None}), "auth": "jwt"}
                    op["templatedRules"] = [*op.get("templatedRules", []), *(rule["id"] for rule in owner_only)]
                policy = _owned_by(spec, spec_op)
                if policy is None:
                    continue
                owner = by_api[policy["ownerField"]]
                deny = policy.get("denyStatus") or 404
                op["auth"]["ownership"] = {
                    "field": owner["apiName"],
                    "attr": owner["attr"],
                    "bypassRoles": list(policy.get("bypassRoles") or []),
                    "deny": deny,
                }
                if deny == 403 and op.get("action") in OWN:
                    op["errors"].append({"status": 403, "exception": "ForbiddenException", "code": "FORBIDDEN"})
                if op.get("action") in OWN:
                    module["tests"].append(_test(op, "other_owner", deny, "another user's record is out of reach"))
                    if policy.get("bypassRoles") and op["action"] == "get":
                        module["tests"].append(_test(op, "bypass", 200, "a bypass role reaches any record"))
                elif op.get("action") == "list" and "{" not in op["path"]:
                    module["tests"].append(_test(op, "own_records", 200, "the list shows the caller's records"))
            if owner is not None:
                self._owner_from_user(plan, module, model, owner)
        plan["unresolved"] = [entry for entry in plan["unresolved"] if entry["kind"] not in ("auth", "policies")]

    def _owner_from_user(
        self, plan: dict[str, Any], module: dict[str, Any], model: dict[str, Any], owner: dict[str, Any]
    ) -> None:
        """The owner comes from the signed-in user: never sent, so creating needs a sign-in."""
        owner["source"] = "currentUser"
        owner["sourceValue"] = f"current_user.{plan['auth']['primaryKeyAttr']}"
        writable_fks = [c for c in model["columns"] if c.get("foreignKey") and c.get("source") != "currentUser"]
        for op in module["operations"]:
            if op.get("action") != "create":
                continue
            op["ownerSource"] = owner["apiName"]
            op["auth"] = {**(op.get("auth") or {"policy": None}), "auth": "jwt"}
            if writable_fks:
                continue
            op["errors"] = [error for error in op["errors"] if error["code"] != "REFERENCE_NOT_FOUND"]
            module["tests"] = [
                test
                for test in module["tests"]
                if not (test["operationId"] == op["operationId"] and test["case"] == "bad_reference")
            ]

    def contract(self, contract: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> None:
        from ..integration.contract import contract_operations, resolve

        meta = contract["x-bga"]
        demo = plan["auth"]["demoUsers"]
        user_model = next(m for m in plan["models"] if m.get("entity") == plan["auth"]["userEntity"])
        user_pk = next(column["apiName"] for column in user_model["columns"] if column["primaryKey"])
        users = meta["fixtures"].get(plan["auth"]["userEntity"]) or []
        id_of = {row.get(plan["auth"]["loginField"]): row.get(user_pk) for row in users}
        login_of = {value: key for key, value in id_of.items()}
        policies = _policies(spec)
        planned = {op["operationId"]: (module, op) for module in plan["modules"] for op in module["operations"]}
        for op_id, entry in contract_operations(contract).items():
            if op_id not in planned:
                continue
            module, op = planned[op_id]
            operation = entry["operation"]
            xbga = operation.setdefault("x-bga", {})
            name = (op.get("auth") or {}).get("policy")
            ownership = _ownership(op)
            if name in policies:
                xbga["policy"] = {"name": name, "type": policies[name]["type"]} | (
                    {key: ownership[source] for key, source in (("ownerField", "field"), ("bypassRoles", "bypassRoles"),
                                                                ("deny", "deny"))}
                    if policies[name]["type"] == "ownership" and ownership
                    else {"roles": _roles(op)}
                )  # fmt: skip
            for error in xbga.get("errors", []):
                if error["code"] == "FORBIDDEN":
                    error["message"] = (
                        "Your role cannot do this" if _roles(op) else "This record belongs to another user"
                    )
            if op.get("ownerSource"):  # the owner is in the request, read-only: the server sets it
                body = (operation.get("requestBody") or {}).get("content", {}).get("application/json", {})
                schema = resolve(contract, body.get("schema"))
                if isinstance(schema, dict) and "properties" in schema:
                    schema["properties"][op["ownerSource"]] = {
                        "type": "string",
                        "readOnly": True,
                        "x-bga": {"source": "currentUser"},
                    }
            scenarios = xbga.get("scenarios") or []
            writes = entry["method"].lower() in ("post", "patch", "put")
            if _roles(op) and scenarios:
                allowed = next((u for u in demo if u["role"] in _roles(op)), None)
                denied = next((u for u in demo if u["role"] not in _roles(op)), None)
                for scenario in scenarios:  # a demo user with the role runs them, when the default one has not
                    if scenario.get("auth", True) and allowed and demo[0]["role"] not in _roles(op):
                        scenario["user"] = allowed["login"]
                if denied:
                    scenarios.append(
                        {"name": "wrong role", "params": scenarios[-1]["params"], "auth": True,
                         "user": denied["login"], **({"body": {}} if writes else {}),
                         "expect": {"status": 403, "code": "FORBIDDEN"}}
                    )  # fmt: skip
            if ownership and op.get("action") in OWN and scenarios:
                self._ownership_scenarios(meta, module, entry["path"], op, scenarios, demo, id_of, login_of)
        for module in plan["modules"]:  # what the mocks need to narrow `allowedActions` per user (Story 22.7)
            info = meta["entities"].get(module["entity"])
            if module.get("plugin") or info is None:
                continue
            rules = {}
            for action in info.get("allowedActions", []):
                op = _record_op(module, action)
                rule: dict[str, Any] = {"roles": _roles(op)} if op is not None and _roles(op) else {}
                if op is not None and _ownership(op):
                    ownership = _ownership(op) or {}
                    rule |= {"ownerField": ownership["field"], "bypassRoles": ownership["bypassRoles"]}
                if rule:
                    rules[action] = rule
            if rules:
                info["actionPolicies"] = rules
            owner = next((op["ownerSource"] for op in module["operations"] if op.get("ownerSource")), None)
            if owner:
                info["ownerField"] = owner

    @staticmethod
    def _ownership_scenarios(
        meta: dict[str, Any],
        module: dict[str, Any],
        path: str,
        op: dict[str, Any],
        scenarios: list[dict[str, Any]],
        demo: list[dict[str, Any]],
        id_of: dict[Any, Any],
        login_of: dict[Any, Any],
    ) -> None:
        """The owner of the record a scenario reaches runs it; another user's record answers the policy's deny."""
        ownership = _ownership(op) or {}
        records = meta["fixtures"].get(module["entity"]) or []
        pk = (meta["entities"].get(module["entity"]) or {}).get("primaryKey") or "id"
        by_id = {str(row.get(pk)): row for row in records}
        bypassing = next((u for u in demo if u["role"] in ownership["bypassRoles"]), None)
        own = _own_param(path)
        for scenario in scenarios:
            record = by_id.get(str(scenario["params"].get(own)))
            if record is None or scenario.get("auth") is False:
                continue
            owner_login = login_of.get(record.get(ownership["field"]))
            if owner_login and owner_login != demo[0]["login"]:
                scenario["user"] = owner_login
            elif not owner_login and bypassing:
                scenario["user"] = bypassing["login"]
        caller = next((u for u in demo if u["role"] not in ownership["bypassRoles"]), None)
        if caller is None:
            return
        theirs = next((row for row in records if row.get(ownership["field"]) != id_of.get(caller["login"])), None)
        if theirs is None:
            return
        deny = ownership["deny"]
        scenarios.append(
            {"name": "another user's record", "params": {**scenarios[-1]["params"], own: theirs[pk]}, "auth": True,
             "user": caller["login"], **({"body": {}} if op["action"] == "update" else {}),
             "expect": {"status": deny, "code": "NOT_FOUND" if deny == 404 else "FORBIDDEN"}}
        )  # fmt: skip

    # -- the project ----------------------------------------------------------------------------------------------

    def router_params(self, plan, module, op) -> list[RouterParam]:
        """The current user, narrowed to one with a role (role policies), and given to the use case when it checks
        ownership, sets the owner or lists the record's actions for the caller."""
        if module.get("plugin") or not _policed(module):
            return []
        user = plan["auth"]["entityClass"]
        presents = op.get("action") in ("create", "get", "update", "list") and bool(self.action_checks(plan, module))
        if not _secured(op):
            # Story 22.7: a public read of records whose actions depend on the caller: the signed-in user, if any
            if not presents:
                return []
            imports = (("src.libs.security", ("OptionalUserDep",)),)
            return [RouterParam("current_user", "OptionalUserDep", f"{user} | None", imports, ((ENTITIES, (user,)),))]
        needs = bool(_ownership(op) or op.get("ownerSource") or presents)
        usecase, usecase_imports = (user, ((ENTITIES, (user,)),)) if needs else (None, ())
        if _roles(op):
            imports = (
                ("typing", ("Annotated",)),
                ("fastapi", ("Depends",)),
                ("src.libs.security", ("require_roles",)),
                (ENTITIES, (user,)),
            )
            annotation = f"Annotated[{user}, Depends(require_roles({_args(_roles(op))}))]"
            return [RouterParam("current_user", annotation, usecase, imports, usecase_imports)]
        imports = (("src.libs.security", ("CurrentUserDep",)),)
        return [RouterParam("current_user", "CurrentUserDep", usecase, imports, usecase_imports)]

    def prechecks(self, plan, module, op, record) -> list[Code]:
        ownership = _ownership(op)
        if module.get("plugin") or ownership is None:
            return []
        if record is None:  # a list: whose records it shows
            if op.get("action") != "list" or not ownership["bypassRoles"]:
                return []
            pk = plan["auth"]["primaryKeyAttr"]
            line = f"owned_by = None if current_user.role in {_tuple(ownership['bypassRoles'])} else current_user.{pk}"
            return [Code(("# the caller's records; a bypass role sees everyone's (Story 10.3)", line))]
        condition = f"{record}.{ownership['attr']} != current_user.{plan['auth']['primaryKeyAttr']}"
        if ownership["bypassRoles"]:
            condition += f" and current_user.role not in {_tuple(ownership['bypassRoles'])}"
        if ownership["deny"] == 403:
            raise_line = '    raise ForbiddenException("This record belongs to another user")'
            imports = (("src.libs.exceptions", ("ForbiddenException",)),)
        else:
            details = f'details={{"id": str({to_snake(module["entity"])}_id)}}'
            raise_line = f'    raise NotFoundException("{module["entity"]} not found", {details})'
            imports = (("src.libs.exceptions", ("NotFoundException",)),)
        return [Code(("# another user's record (Story 10.3)", f"if {condition}:", raise_line), imports)]

    def repository_filters(self, plan, module) -> list[RepositoryFilter]:
        lists = [op for op in module["operations"] if op.get("action") == "list" and _ownership(op)]
        if module.get("plugin") or not lists:
            return []
        ownership = _ownership(lists[0]) or {}
        model = next(m for m in plan["models"] if m.get("entity") == module["entity"])
        column = next(c for c in model["columns"] if c["attr"] == ownership["attr"])
        value = f"current_user.{plan['auth']['primaryKeyAttr']}"
        if ownership["bypassRoles"]:
            value = "owned_by"  # the list's pre-check: everyone's records for a bypass role
        return [
            RepositoryFilter(
                "owned_by",
                f"{column['pythonType']} | None",
                f"col({{model}}.{ownership['attr']}) == owned_by",
                value,
                (("uuid", ()),) if column["pythonType"] == "uuid.UUID" else (),
                tuple(op["operationId"] for op in lists),
            )
        ]

    def action_checks(self, plan, module) -> list[ActionCheck]:
        if module.get("plugin"):
            return []
        user = plan["auth"]["entityClass"]
        pk = plan["auth"]["primaryKeyAttr"]
        checks = []
        for action in module.get("recordActions") or []:
            op = _record_op(module, action)
            ownership = _ownership(op) if op else None
            parts = []
            if op is not None and _roles(op):
                parts.append(f"user.role in {_tuple(_roles(op))}")
            if ownership:
                owns = f"entity.{ownership['attr']} == user.{pk}"
                if ownership["bypassRoles"]:
                    owns = f"({owns} or user.role in {_tuple(ownership['bypassRoles'])})"
                parts.append(owns)
            if not parts:
                continue
            condition = " and ".join(["user is not None", *parts])
            checks.append(ActionCheck(action, condition, user, imports=((ENTITIES, (user,)),)))
        return checks

    def test_prelude(self, plan, module, op) -> Code | None:
        """Tests of a role operation sign in with a role it allows, when the default account's is not one."""
        roles = _roles(op)
        if module.get("plugin") or not roles or plan["auth"]["roles"][0] in roles:
            return None
        return Code((_sign_in(roles[0]),), SIGN_IN)

    def test_case(self, plan, module, op, test, ctx: CaseContext) -> Code | None:
        case = test["case"]
        if module.get("plugin") or case not in ("missing_role", "other_owner", "bypass", "own_records"):
            return None
        method = op["method"].lower()
        body = ", json={}" if method in ("post", "patch", "put") else ""
        if case == "missing_role":
            role = next(r for r in plan["auth"]["roles"] if r not in _roles(op))
            return Code(
                (
                    f"def {test['id']}(client):",
                    f"    {_sign_in(role)}",
                    "",
                    f"    response = client.{method}({ctx.missing_path or _quoted(op['path'])}{body})",
                    "",
                    "    assert response.status_code == 403",
                    '    assert response.json()["error"]["code"] == "FORBIDDEN"',
                ),
                SIGN_IN,
            )
        ownership = _ownership(op) or {}
        user_seed = ctx.seed_for(plan["auth"]["userEntity"])
        others = f"{ctx.seed}({ownership['attr']}={user_seed}().{plan['auth']['primaryKeyAttr']})"
        plain = next((r for r in plan["auth"]["roles"] if r not in ownership["bypassRoles"]), None)
        lines = [f"def {test['id']}(client):"]
        if case != "bypass" and plan["auth"]["roles"][0] in ownership["bypassRoles"] and plain:
            lines.append(f"    {_sign_in(plain)}")  # the default account reaches every record
        if case == "own_records":
            model = next(m for m in plan["models"] if m.get("entity") == module["entity"])
            pk = next(column for column in model["columns"] if column["primaryKey"])
            return Code(
                (
                    *lines,
                    f"    mine = {ctx.seed}()",
                    f"    {others}",
                    "",
                    f"    body = client.get({_quoted(op['path'])}).json()",
                    "",
                    '    assert body["total"] == 1',
                    f'    assert [item["{pk["apiName"]}"] for item in body["items"]] == [str(mine.{pk["attr"]})]',
                ),
                SIGN_IN,
            )
        lines.append(f"    record = {others}")
        if case == "bypass":
            lines.append(f"    {_sign_in(ownership['bypassRoles'][0])}")
            return Code((*lines, "", f"    assert client.get({ctx.record_path}).status_code == 200"), SIGN_IN)
        deny = ownership["deny"]
        return Code(
            (
                *lines,
                "",
                f"    response = client.{method}({ctx.record_path}{body})",
                "",
                f"    assert response.status_code == {deny}",
                f'    assert response.json()["error"]["code"] == "{"NOT_FOUND" if deny == 404 else "FORBIDDEN"}"',
            ),
            SIGN_IN,
        )

    def engine_note(self, plan: dict[str, Any]) -> str:
        return (
            "Policies (Story 10.3): a role policy's route takes `current_user: Annotated[User, "
            'Depends(require_roles("admin"))]` (`from src.libs.security import require_roles`; 403 without the role). '
            "An ownership policy is checked in the use case, which receives `current_user`: another user's record "
            "answers 404 (`NotFoundException`, or 403 when the policy's `denyStatus` says so), lists show the "
            "caller's records only, and create sets the owner from `current_user`, never from the request."
        )
