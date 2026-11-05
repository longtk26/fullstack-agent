"""Email as a plugin (Story 10.7): the spec's `emails[]`, each sent by a job (10.6) when its trigger fires, so a
failure retries. `to` and the `{{placeholders}}` are paths from the trigger's record (`task.project.ownerEmail`);
the job loads the records the paths reach and renders Jinja templates (`src/templates/emails/<name>.*.j2`, values
HTML-escaped in the HTML part). With JWT auth, `auth.passwordReset` and `auth.emailVerification` add the plugin's
`account` module: signed, expiring links sent the same way.

`EMAIL_BACKEND=console` (the default) writes emails to the log; `smtp` sends them. Locally every sandbox and preview
sends to one shared Mailpit (`src/sandbox/mail_service.py`), tagged with its generation id.
"""

import html
import re
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_pascal, to_snake

from .base import Plugin, Setting

LIB = "src.libs.email"
TEMPLATES = "src/templates/emails"
MODULE = "src/modules/account"
PLACEHOLDER = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
ACCOUNT_KINDS = {"passwordReset": "email.passwordReset", "emailVerification": "email.emailVerification"}


def _auth_options(spec: dict[str, Any]) -> dict[str, bool]:
    auth = spec.get("auth") or {}
    if auth.get("type") != "jwt":
        return {}
    return {key: True for key in ("passwordReset", "emailVerification") if auth.get(key)}


def _trigger(email: dict[str, Any]) -> tuple[str, str]:
    trigger = email["trigger"]
    if isinstance(trigger, str):
        kind, _, value = trigger.partition(":")
        return kind, value.strip()
    ((kind, value),) = ((k, v) for k, v in trigger.items() if v)
    return kind, value


class EmailPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="email", requires=("jobs",))

    def applies(self, spec: dict[str, Any]) -> bool:
        return bool(spec.get("emails") or _auth_options(spec))

    # -- the spec and the plan ------------------------------------------------------------------------------------

    def extend_spec(self, spec: dict[str, Any]) -> None:
        jobs = spec.setdefault("backgroundJobs", [])
        for email in spec.get("emails", []):  # each email is a job of its trigger
            jobs.append(
                {
                    "name": f"email{to_pascal(email['name'])}",
                    "trigger": email["trigger"],
                    "action": "email",
                    "email": email["name"],
                    "maxAttempts": 5,
                }
            )
        if _auth_options(spec).get("emailVerification"):
            name = (spec.get("auth") or {}).get("userEntity") or "User"
            entity = next(entity for entity in spec["entities"] if entity["name"] == name)
            if not any(field["name"] == "emailVerifiedAt" for field in entity["fields"]):
                entity["fields"].append(
                    {"name": "emailVerifiedAt", "type": "datetime", "required": False, "nullable": True}
                )

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        models = {model["entity"]: model for model in plan["models"] if model.get("entity")}
        ops = {op["operationId"]: op for module in plan["modules"] for op in module["operations"]}
        emails = []
        for email in spec.get("emails", []):
            kind, value = _trigger(email)
            root = None
            if kind == "event":
                root = next((e for e in models if f"{e[:1].lower()}{e[1:]}" == value.partition(".")[0]), None)
            elif kind == "operation" and value in ops:
                root = next((m["entity"] for m in plan["modules"] if ops[value] in m["operations"]), None)
            loads: dict[str, dict[str, Any]] = {}
            resolve = _resolver(models, root, loads)
            to = email["to"]
            recipient = {"literal": to} if "@" in to else {"path": resolve(to)}
            subject = PLACEHOLDER.sub(lambda m, resolve=resolve: "{{ " + resolve(m.group(1)) + " }}", email["subject"])
            text = PLACEHOLDER.sub(lambda m, resolve=resolve: "{{ " + resolve(m.group(1)) + " }}", email["body"])
            html_body = _html(email["body"], resolve)
            emails.append(
                {
                    "name": email["name"],
                    "job": f"email{to_pascal(email['name'])}",
                    "handler": to_snake(f"email{to_pascal(email['name'])}"),
                    "template": to_snake(email["name"]),
                    "trigger": {kind: value},
                    "root": (f"{root[:1].lower()}{root[1:]}" if root else None),
                    "loads": list(loads.values()),
                    "to": recipient,
                    "subject": subject,
                    "text": text,
                    "html": html_body,
                }
            )
        plan["emails"] = emails
        account = _auth_options(spec)
        if account and plan.get("auth"):
            plan["account"] = account
            plan["modules"].append(_account_module(account, bool(plan.get("auth"))))
            plan["routers"]["order"].append("account_router")
            plan["jobs"] = [
                *plan.get("jobs", []),
                {
                    "name": "accountEmails",
                    "handler": "account_emails",
                    "file": "src/jobs/account_emails.py",
                    "trigger": {"enqueued": "account"},
                    "event": None,
                    "action": "email",
                    "maxAttempts": 5,
                    "description": "The account module's emails (password reset, email verification)",
                },
            ]

    # -- the contract ---------------------------------------------------------------------------------------------

    def contract(self, contract: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> None:
        contract["x-bga"]["emails"] = [
            {
                "name": e["name"],
                "trigger": e["trigger"],
                "to": next(
                    iter(spec_email["to"] for spec_email in spec.get("emails", []) if spec_email["name"] == e["name"])
                ),
            }
            for e in plan.get("emails", [])
        ]
        account = plan.get("account")
        if account:
            _account_contract(contract, account)

    # -- the project ----------------------------------------------------------------------------------------------

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        return [
            Setting(
                "email_backend",
                "str",
                '"console"',
                comment="console (the log) or smtp",
                example="EMAIL_BACKEND=console",
            ),
            Setting("smtp_host", "str", '"localhost"', example="SMTP_HOST="),
            Setting("smtp_port", "int", "587", example="SMTP_PORT=587"),
            Setting("smtp_user", "str", '""', example="SMTP_USER="),
            Setting("smtp_password", "str", '""', example="SMTP_PASSWORD="),
            Setting("smtp_from", "str", '"no-reply@example.com"', example="SMTP_FROM="),
            Setting("smtp_tls", "bool", "True", example="SMTP_TLS=true"),
            Setting("email_tag", "str", '""', comment="tags every message (local previews: the generation id)"),
            Setting(
                "app_base_url",
                "str",
                '"http://localhost:3000"',
                comment="links in account emails",
                example="APP_BASE_URL=",
            ),
        ]

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        files = super().files(plan)
        plan = plan or {}
        for email in plan.get("emails", []):
            files[f"{TEMPLATES}/{email['template']}.subject.j2"] = email["subject"] + "\n"
            files[f"{TEMPLATES}/{email['template']}.txt.j2"] = email["text"].rstrip("\n") + "\n"
            files[f"{TEMPLATES}/{email['template']}.html.j2"] = _layout(email["html"])
            files[f"src/jobs/{email['handler']}.py"] = _handler(email, plan)
        account = plan.get("account")
        if account:
            files |= _account_files(plan, account)
        files["tests/modules/email/__init__.py"] = ""
        files["tests/modules/email/test_emails.py"] = _test_file(plan)
        return files

    def engine_note(self, plan: dict[str, Any]) -> str:
        return (
            "Email (Story 10.7, `src/libs/email`): send from a job, never from a request: "
            "`send_template(name, to, context, message_id=str(ctx.job_id))` with templates in `src/templates/emails/` "
            "(`<name>.subject.j2`, `.txt.j2`, `.html.j2`)."
        )


# -- paths and templates ------------------------------------------------------------------------------------------


def _resolver(models: dict[str, dict[str, Any]], root: str | None, loads: dict[str, dict[str, Any]]):
    """`task.project.ownerEmail` → `task_project.owner_email`, recording the record each reference loads."""

    def resolve(path: str) -> str:
        parts = path.strip().split(".")
        entity, alias = root, parts[0]
        for part in parts[1:-1]:
            model = models[entity]
            column = next(c for c in model["columns"] if c["apiName"] == f"{part}Id")
            table = column["foreignKey"]["references"].partition(".")[0]
            parent = next(m for m in models.values() if m["table"] == table)
            child_alias, alias = alias, f"{alias}_{to_snake(part)}"
            pk = next(c for c in parent["columns"] if c["primaryKey"])
            loads.setdefault(
                alias,
                {
                    "alias": alias,
                    "from": child_alias,
                    "attr": column["attr"],
                    "model": parent["class"],
                    "pkType": pk["type"],
                },
            )
            entity = parent["entity"]
        last = next(c for c in models[entity]["columns"] if c["apiName"] == parts[-1])
        return f"{alias}.{last['attr']}"

    return resolve


def _html(body: str, resolve) -> str:
    """The body as HTML: its text escaped, placeholders left to Jinja (which escapes their values)."""
    out, position = [], 0
    for match in PLACEHOLDER.finditer(body):
        out.append(html.escape(body[position : match.start()]))
        out.append("{{ " + resolve(match.group(1)) + " }}")
        position = match.end()
    out.append(html.escape(body[position:]))
    paragraphs = "".join(out).strip().split("\n\n")
    return "\n".join(f"<p>{paragraph.replace(chr(10), '<br>')}</p>" for paragraph in paragraphs)


def _layout(content: str) -> str:
    return (
        '<!doctype html>\n<html>\n  <body style="font-family: sans-serif; line-height: 1.5; color: #1f2933">\n'
        + "".join(f"    {line}\n" for line in content.splitlines())
        + "  </body>\n</html>\n"
    )


def _handler(email: dict[str, Any], plan: dict[str, Any]) -> str:
    ((kind, value),) = email["trigger"].items()
    register = f'cron="{value}"' if kind == "cron" else f'events=("{value}",)'
    root = email["root"]
    lines = []
    imports = {
        "from typing import Any",
        "from src.libs.email import send_template",
        "from src.libs.jobs import JobContext, job",
    }
    context = []
    if root:
        lines.append(f"    {root} = payload")
        context.append(f'"{root}": {root}')
    for load in email["loads"]:
        imports.add(f"from src.modules.shared.infrastructure.models import {load['model']}")
        key = f'{load["from"]}.get("{load["attr"]}")'
        parse = f"uuid.UUID(str({key}))" if load["pkType"] == "uuid" else key
        if load["pkType"] == "uuid":
            imports.add("import uuid")
        lines += [
            f"    found = ctx.session.get({load['model']}, {parse}) if {key} else None",
            f'    {load["alias"]} = found.model_dump(mode="json") if found else {{}}',
        ]
        context.append(f'"{load["alias"]}": {load["alias"]}')
    if "literal" in email["to"]:
        lines.append(f'    to = "{email["to"]["literal"]}"')
    else:
        alias, attr = email["to"]["path"].split(".")
        lines += [f'    to = {alias}.get("{attr}")', "    if not to:", "        return  # nobody to send it to"]
    lines.append(f'    send_template("{email["template"]}", to, {{{", ".join(context)}}}, message_id=str(ctx.job_id))')
    stdlib = sorted([i for i in imports if not i.startswith("from src.")], key=lambda i: (i.startswith("from"), i))
    ours = sorted(i for i in imports if i.startswith("from src."))
    return (
        f'"""Email `{email["name"]}` (Story 10.7), on {value}: sent by this job, so a failure retries."""\n\n'
        + "\n".join(stdlib)
        + "\n\n"
        + "\n".join(ours)
        + f'\n\n\n@job("{email["job"]}", {register}, max_attempts=5)\n'
        f"def {email['handler']}(payload: dict[str, Any], ctx: JobContext) -> None:\n" + "\n".join(lines) + "\n"
    )


def _sample(column: dict[str, Any]) -> Any:
    kind = column["type"]
    if kind in ("integer",):
        return 1
    if kind in ("float", "decimal"):
        return 1.5
    if kind == "boolean":
        return True
    if "email" in column["apiName"].lower():
        return "someone@example.com"
    return "<b>Sample</b>"


def _test_file(plan: dict[str, Any]) -> str:
    models = {model["entity"]: model for model in plan["models"] if model.get("entity")}
    by_class = {model["class"]: model for model in models.values()}
    cases = []
    for email in plan.get("emails", []):
        context: dict[str, dict[str, Any]] = {}
        if email["root"]:
            model = next(m for e, m in models.items() if f"{e[:1].lower()}{e[1:]}" == email["root"])
            context[email["root"]] = {c["attr"]: _sample(c) for c in model["columns"]}
        for load in email["loads"]:
            context[load["alias"]] = {c["attr"]: _sample(c) for c in by_class[load["model"]]["columns"]}
        cases.append(
            f"\n\ndef test_{email['template']}_renders_with_its_values_escaped_in_html():\n"
            f'    subject, text, html = render("{email["template"]}", {context!r})\n\n'
            "    assert subject\n"
            '    assert "<b>" not in html  # values are escaped in the HTML part\n'
            '    assert "{{" not in text and "{{" not in html\n'
        )
    account = plan.get("account") or {}
    imports = "from src.libs.email import render\n"
    if account:
        imports = (
            "import os\n\nfrom sqlalchemy import create_engine\nfrom sqlmodel import Session, col, select\n\n"
            "from src.libs.email import render\nfrom src.libs.jobs import JobModel, Worker\n"
            "from tests.auth import account, sign_in\n"
        )
        cases.append(_account_tests(plan, account))
    return (
        '"""Generated by the Fullstack Generation Agent (Story 10.7, the email plugin): every template renders."""\n\n'
        + imports
        + ("".join(cases) if cases else "\n\ndef test_no_emails():\n    pass\n")
    )


# -- the account module: password reset and email verification ------------------------------------------------------


def _account_module(account: dict[str, bool], secured: bool) -> dict[str, Any]:
    ops = []

    def op(op_id, method, path, handler, status, errors, auth=False):
        entry = {
            "operationId": op_id,
            "type": "plugin",
            "action": None,
            "method": method,
            "path": path,
            "handler": handler,
            "status": status,
            "transactional": True,
            "errors": [{"status": s, "exception": None, "code": c} for s, c in errors],
        }
        if auth:
            entry["auth"] = {"auth": "jwt", "policy": None}
        ops.append(entry)

    if account.get("passwordReset"):
        op(
            "account.requestPasswordReset",
            "POST",
            "/auth/password-reset",
            "request_password_reset",
            202,
            [(422, "VALIDATION_ERROR")],
        )
        op(
            "account.resetPassword",
            "POST",
            "/auth/password-reset/confirm",
            "reset_password",
            204,
            [(400, "INVALID_TOKEN"), (422, "VALIDATION_ERROR")],
        )
    if account.get("emailVerification"):
        op(
            "account.requestEmailVerification",
            "POST",
            "/auth/email-verification",
            "request_email_verification",
            202,
            [(401, "UNAUTHORIZED")],
            auth=True,
        )
        op(
            "account.verifyEmail",
            "POST",
            "/auth/email-verification/confirm",
            "verify_email",
            204,
            [(400, "INVALID_TOKEN"), (422, "VALIDATION_ERROR")],
        )
    return {
        "name": "account",
        "entity": None,
        "plugin": "email",
        "port": {"interface": None, "dep": None, "methods": []},
        "usecases": [],
        "dtoFiles": [],
        "router": {
            "variable": "account_router",
            "file": f"{MODULE}/presenter/router.py",
            "prefix": "",
            "tag": "account",
        },
        "operations": ops,
        "recordActions": [],
        "testFile": "tests/modules/email/test_emails.py",
        "tests": [],
    }


def _account_contract(contract: dict[str, Any], account: dict[str, bool]) -> None:
    schemas = contract["components"]["schemas"]
    error = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}
    demo = (contract["x-bga"].get("auth") or {}).get("login", {}).get("body", {})
    field = (contract["x-bga"].get("auth") or {}).get("login", {}).get("field", "email")

    def operation(op_id, summary, schema, status, scenarios, errors, auth=False):
        body = {
            "required": True,
            "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}},
        }
        out = {
            "operationId": op_id,
            "summary": summary,
            "tags": ["account"],
            "responses": {
                str(status): {"description": summary},
                **{str(e["status"]): {"description": e["code"], **error} for e in errors},
            },
            "x-bga": {
                "entity": None,
                "action": None,
                "module": "account",
                "plugin": "email",
                "mock": "sample",
                "errors": errors,
                "scenarios": scenarios,
            },
        }
        if schema:
            out["requestBody"] = body
        if auth:
            out["security"] = [{"bearerAuth": []}]
            out["x-bga"]["auth"] = "jwt"
        return {"post": out}

    if account.get("passwordReset"):
        schemas["PasswordResetRequest"] = {
            "type": "object",
            "properties": {field: {"type": "string"}},
            "required": [field],
        }
        schemas["PasswordResetConfirm"] = {
            "type": "object",
            "properties": {"token": {"type": "string"}, "password": {"type": "string", "minLength": 8}},
            "required": ["token", "password"],
        }
        contract["paths"]["/auth/password-reset"] = operation(
            "account.requestPasswordReset",
            "Email a password reset link (answered the same for unknown addresses)",
            "PasswordResetRequest",
            202,
            [
                {
                    "name": "known address",
                    "params": {},
                    "auth": False,
                    "body": {field: demo.get(field)},
                    "expect": {"status": 202},
                },
                {
                    "name": "unknown address",
                    "params": {},
                    "auth": False,
                    "body": {field: "nobody@example.com"},
                    "expect": {"status": 202},
                },
            ],
            [],
        )
        contract["paths"]["/auth/password-reset/confirm"] = operation(
            "account.resetPassword",
            "Set a new password with the emailed token",
            "PasswordResetConfirm",
            204,
            [
                {
                    "name": "invalid token",
                    "params": {},
                    "auth": False,
                    "body": {"token": "not-a-token", "password": "new-password-1"},
                    "expect": {"status": 400, "code": "INVALID_TOKEN"},
                }
            ],
            [
                {
                    "status": 400,
                    "code": "INVALID_TOKEN",
                    "message": "The link is invalid or has expired",
                    "fields": ["token"],
                }
            ],
        )
    if account.get("emailVerification"):
        schemas["EmailVerificationConfirm"] = {
            "type": "object",
            "properties": {"token": {"type": "string"}},
            "required": ["token"],
        }
        contract["paths"]["/auth/email-verification"] = operation(
            "account.requestEmailVerification",
            "Email a link that verifies the signed-in user's address",
            None,
            202,
            [{"name": "signed in", "params": {}, "auth": True, "expect": {"status": 202}}],
            [{"status": 401, "code": "UNAUTHORIZED", "message": "Sign in to continue"}],
            auth=True,
        )
        contract["paths"]["/auth/email-verification/confirm"] = operation(
            "account.verifyEmail",
            "Verify an address with the emailed token",
            "EmailVerificationConfirm",
            204,
            [
                {
                    "name": "invalid token",
                    "params": {},
                    "auth": False,
                    "body": {"token": "not-a-token"},
                    "expect": {"status": 400, "code": "INVALID_TOKEN"},
                }
            ],
            [
                {
                    "status": 400,
                    "code": "INVALID_TOKEN",
                    "message": "The link is invalid or has expired",
                    "fields": ["token"],
                }
            ],
        )


def _account_files(plan: dict[str, Any], account: dict[str, bool]) -> dict[str, str]:
    auth = plan["auth"]
    model, login, attr = auth["model"], auth["loginField"], auth["loginAttr"]
    user = next(m for m in plan["models"] if m.get("entity") == auth["userEntity"])
    pk = next(c for c in user["columns"] if c["primaryKey"])
    parse = "uuid.UUID(subject)" if pk["type"] == "uuid" else ("int(subject)" if pk["type"] == "integer" else "subject")
    files: dict[str, str] = {
        f"{TEMPLATES}/password_reset.subject.j2": "Reset your password\n",
        f"{TEMPLATES}/password_reset.txt.j2": "Someone asked to reset the password of this account.\n\n"
        "Open this link within 30 minutes to choose a new one:\n{{ link }}\n\nIf it was not you, ignore this email.\n",
        f"{TEMPLATES}/password_reset.html.j2": _layout(
            "<p>Someone asked to reset the password of this account.</p>\n"
            '<p><a href="{{ link }}">Choose a new password</a> (the link works for 30 minutes).</p>\n'
            "<p>If it was not you, ignore this email.</p>"
        ),
        f"{TEMPLATES}/email_verification.subject.j2": "Verify your email address\n",
        f"{TEMPLATES}/email_verification.txt.j2": "Open this link to verify your address:\n{{ link }}\n",
        f"{TEMPLATES}/email_verification.html.j2": _layout('<p><a href="{{ link }}">Verify your email address</a></p>'),
        "src/jobs/account_emails.py": (
            '"""The account module\'s emails (Story 10.7): password reset and email verification links, sent by\n'
            'jobs."""\n\n'
            "from typing import Any\n\nfrom src.libs.email import send_template\n"
            "from src.libs.jobs import JobContext, job\n\n\n"
            '@job("email.passwordReset")\n'
            "def password_reset(payload: dict[str, Any], ctx: JobContext) -> None:\n"
            '    context = {"link": payload["link"]}\n'
            '    send_template("password_reset", payload["to"], context, message_id=str(ctx.job_id))\n\n\n'
            '@job("email.emailVerification")\n'
            "def email_verification(payload: dict[str, Any], ctx: JobContext) -> None:\n"
            '    context = {"link": payload["link"]}\n'
            '    send_template("email_verification", payload["to"], context, message_id=str(ctx.job_id))\n'
        ),
        f"{MODULE}/__init__.py": "",
        f"{MODULE}/tokens.py": (
            '"""Signed, expiring account links (Story 10.7). A reset token also carries a fingerprint of the current\n'
            'password hash, so it works once: a new password changes the hash."""\n\n'
            "import datetime as dt\nimport hashlib\n\nimport jwt\n\nfrom src.configs import config\n\n"
            "RESET_MINUTES = 30\nVERIFY_HOURS = 48\n\n\n"
            "def fingerprint(password_hash: str) -> str:\n"
            "    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]\n\n\n"
            "def issue(purpose: str, subject: object, lifetime: dt.timedelta, **claims: str) -> str:\n"
            "    now = dt.datetime.now(dt.UTC)\n"
            '    payload = {"sub": str(subject), "purpose": purpose, "iat": now, "exp": now + lifetime, **claims}\n'
            '    return jwt.encode(payload, config.jwt_secret, algorithm="HS256")\n\n\n'
            "def read(token: str, purpose: str) -> dict | None:\n"
            "    try:\n"
            '        claims = jwt.decode(token, config.jwt_secret, algorithms=["HS256"])\n'
            "    except jwt.PyJWTError:\n"
            "        return None\n"
            '    return claims if claims.get("purpose") == purpose else None\n'
        ),
    }
    routes = [
        "import datetime as dt\nimport uuid\n\nfrom fastapi import APIRouter, Response\n"
        "from pydantic import BaseModel, Field\n"
        "from sqlmodel import col, select\n\n"
        "from src.configs import config\nfrom src.libs.database.session import SessionDep\n"
        "from src.libs.exceptions import BadRequestException, ErrorCode\nfrom src.libs.jobs import JobQueueDep\n"
        "from src.libs.security import CurrentUserDep, hash_password\n"
        f"from src.modules.shared.infrastructure.models import {model}\n\n"
        "from ..tokens import RESET_MINUTES, VERIFY_HOURS, fingerprint, issue, read\n\n"
        'account_router = APIRouter(tags=["account"])\n\n'
        'ERROR = {"description": "Error envelope: {error: {code, message, details}}"}\n\n\n'
        "def _invalid() -> BadRequestException:\n"
        "    return BadRequestException(\n"
        '        "The link is invalid or has expired", ErrorCode.INVALID_TOKEN, details={"fields": ["token"]}\n'
        "    )\n\n\n"
        "def _subject(subject: str) -> object:\n"
        f"    return {parse}\n"
    ]
    if account.get("passwordReset"):
        routes.append(
            "\n\nclass PasswordResetRequestDto(BaseModel):\n"
            f'    {attr}: str = Field(alias="{login}", min_length=1, max_length=255)\n\n\n'
            "class PasswordResetConfirmDto(BaseModel):\n"
            "    token: str = Field(min_length=1)\n    password: str = Field(min_length=8, max_length=128)\n\n\n"
            '@account_router.post(\n    "/auth/password-reset",\n    operation_id="account.requestPasswordReset",\n'
            "    status_code=202,\n"
            "                     responses={422: ERROR})\n"
            "def request_password_reset(\n"
            "    body: PasswordResetRequestDto, session: SessionDep, jobs: JobQueueDep\n) -> dict:\n"
            '    """The same answer for unknown addresses, so it tells nobody which accounts exist."""\n'
            f"    account = session.exec(select({model}).where(col({model}.{attr}) == body.{attr})).first()\n"
            "    if account is not None:\n"
            f'        token = issue("reset", account.{pk["attr"]}, dt.timedelta(minutes=RESET_MINUTES),\n'
            "                      hash=fingerprint(account.password_hash))\n"
            '        link = f"{config.app_base_url}/reset-password?token={token}"\n'
            f'        jobs.enqueue("email.passwordReset", {{"to": account.{attr}, "link": link}})\n'
            "        session.commit()\n"
            '    return {"status": "sent"}\n\n\n'
            '@account_router.post(\n    "/auth/password-reset/confirm",\n    operation_id="account.resetPassword",\n'
            "    status_code=204,\n"
            "                     responses={400: ERROR, 422: ERROR})\n"
            "def reset_password(body: PasswordResetConfirmDto, session: SessionDep) -> Response:\n"
            '    claims = read(body.token, "reset")\n'
            f'    account = session.get({model}, _subject(claims["sub"])) if claims else None\n'
            '    if account is None or claims.get("hash") != fingerprint(account.password_hash):\n'
            "        raise _invalid()\n"
            "    account.password_hash = hash_password(body.password)\n"
            "    session.add(account)\n    session.commit()\n"
            "    return Response(status_code=204)\n"
        )
    if account.get("emailVerification"):
        routes.append(
            "\n\nclass EmailVerificationConfirmDto(BaseModel):\n    token: str = Field(min_length=1)\n\n\n"
            '@account_router.post("/auth/email-verification", operation_id="account.requestEmailVerification",\n'
            "                     status_code=202, responses={401: ERROR})\n"
            "def request_email_verification(\n"
            "    current_user: CurrentUserDep, session: SessionDep, jobs: JobQueueDep\n"
            ") -> dict:\n"
            f'    token = issue("verify", current_user.{pk["attr"]}, dt.timedelta(hours=VERIFY_HOURS))\n'
            '    link = f"{config.app_base_url}/verify-email?token={token}"\n'
            f'    jobs.enqueue("email.emailVerification", {{"to": current_user.{attr}, "link": link}})\n'
            "    session.commit()\n"
            '    return {"status": "sent"}\n\n\n'
            '@account_router.post(\n    "/auth/email-verification/confirm",\n    operation_id="account.verifyEmail",\n'
            "    status_code=204,\n"
            "                     responses={400: ERROR, 422: ERROR})\n"
            "def verify_email(body: EmailVerificationConfirmDto, session: SessionDep) -> Response:\n"
            '    claims = read(body.token, "verify")\n'
            f'    account = session.get({model}, _subject(claims["sub"])) if claims else None\n'
            "    if account is None:\n        raise _invalid()\n"
            "    account.email_verified_at = account.email_verified_at or dt.datetime.now(dt.UTC)\n"
            "    session.add(account)\n    session.commit()\n"
            "    return Response(status_code=204)\n"
        )
    files[f"{MODULE}/presenter/__init__.py"] = 'from .router import account_router\n\n__all__ = ["account_router"]\n'
    files[f"{MODULE}/presenter/router.py"] = "".join(routes)
    return files


def _account_tests(plan: dict[str, Any], account: dict[str, bool]) -> str:
    login = plan["auth"]["loginField"]
    out = (
        '\nENGINE = create_engine(os.environ["DB_URL"])\n\n\n'
        "def _link(kind: str) -> str:\n"
        "    with Session(ENGINE) as session:\n"
        "        job = session.exec(select(JobModel).where(col(JobModel.kind) == kind)).one()\n"
        '    return job.payload["link"]\n'
    )
    if account.get("passwordReset"):
        out += (
            "\n\ndef test_a_password_reset_link_sets_a_new_password_once(client):\n"
            "    body = account()\n"
            '    assert client.post("/auth/register", json=body).status_code == 201\n'
            f'    assert client.post("/auth/password-reset", json={{"{login}": body["{login}"]}}).status_code == 202\n'
            '    token = _link("email.passwordReset").split("token=")[1]\n'
            '    new = {"token": token, "password": "a-new-password-9"}\n\n'
            '    assert client.post("/auth/password-reset/confirm", json=new).status_code == 204\n'
            f'    again = {{"{login}": body["{login}"], "password": "a-new-password-9"}}\n'
            '    assert client.post("/auth/login", json=again).status_code == 200\n'
            '    assert client.post("/auth/password-reset/confirm", json=new).status_code == 400  # used once\n'
            "    assert Worker(ENGINE).run_due().failed == 0  # the email job renders and sends\n\n\n"
            "def test_an_unknown_address_gets_the_same_answer_and_no_email(client):\n"
            f'    unknown = {{"{login}": "nobody@example.com"}}\n'
            '    assert client.post("/auth/password-reset", json=unknown).status_code == 202\n'
            "    with Session(ENGINE) as session:\n"
            "        assert session.exec(select(JobModel)).first() is None\n"
        )
    if account.get("emailVerification"):
        out += (
            "\n\ndef test_an_email_verification_link_verifies_the_address(client):\n"
            '    headers = {"Authorization": f"Bearer {sign_in(client)}"}\n'
            '    assert client.post("/auth/email-verification", headers=headers).status_code == 202\n'
            '    token = _link("email.emailVerification").split("token=")[1]\n\n'
            '    assert client.post("/auth/email-verification/confirm", json={"token": token}).status_code == 204\n'
            '    assert client.get("/auth/me", headers=headers).json()["emailVerifiedAt"] is not None\n'
            '    assert client.post("/auth/email-verification/confirm", json={"token": "x"}).status_code == 400\n'
        )
    return out
