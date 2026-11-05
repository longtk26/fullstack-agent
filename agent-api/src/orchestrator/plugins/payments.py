"""Payments as a plugin (Story 10.9): one entity is paid for, with the fake provider first.

`POST /payments/<records>/{recordId}/checkout` starts a payment for the amount on the record (never the client's;
409 `ALREADY_PAID` once paid) and answers the provider's checkout URL. The fake provider's page is served by the app
(`/payments/fake/checkout/<session>`): pay, fail or cancel posts a signed event through the incoming webhook path
(10.8: signature, idempotency by event id, a job), so the real flow runs. The job marks the payment, moves the record's
status to `paidStatus` (`failedStatus`) — through the spec's transition rule when there is one (10.4) — and emits
`<entity>.paid`. `GET /payments/{paymentId}` is what success and cancel screens poll. `pay` is in a record's
`allowedActions` until it is paid. The fake page refuses to run when `APP_ENV=production`.
"""

import re
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_snake

from .base import ActionCheck, CaseContext, Code, Plugin, Setting

LIB = "src.libs.payments"
MODULE = "src/modules/payments"
SOURCE = "payments"
EVENTS = ["checkout.completed", "checkout.failed", "checkout.canceled"]


def _payments(spec: dict[str, Any]) -> dict[str, Any]:
    return spec.get("payments") or {}


class PaymentsPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="payments", requires=("webhooks",))

    def applies(self, spec: dict[str, Any]) -> bool:
        return bool(_payments(spec))

    # -- the spec and the plan ------------------------------------------------------------------------------------

    def extend_spec(self, spec: dict[str, Any]) -> None:
        webhooks = spec.setdefault("webhooks", {})
        incoming = webhooks.setdefault("incoming", [])
        if not any(source["source"] == SOURCE for source in incoming):  # the provider's outcomes arrive signed
            incoming.append(
                {"source": SOURCE, "secretEnv": "PAYMENT_WEBHOOK_SECRET", "events": EVENTS, "action": "payment"}
            )

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        payments = _payments(spec)
        model = next(m for m in plan["models"] if m.get("entity") == payments["entity"])
        module = next(m for m in plan["modules"] if m.get("entity") == payments["entity"] and not m.get("plugin"))
        by_api = {column["apiName"]: column for column in model["columns"]}
        amount_field = payments.get("amountField") or next(
            r["params"]["field"]
            for r in spec.get("rules", [])
            if r["kind"] == "sumEquals" and r["entity"] == model["entity"]
        )
        status = by_api[payments["statusField"]]
        pk = next(column for column in model["columns"] if column["primaryKey"])
        transition = next(
            (
                check["constant"]
                for op in module["operations"]
                for check in op.get("ruleChecks") or []
                if check["kind"] == "transition" and check["attr"] == status["attr"]
            ),
            None,
        )
        values = status["enum"]["values"]
        allowed_from = values
        if transition:
            check = next(
                c for op in module["operations"] for c in op.get("ruleChecks") or [] if c["constant"] == transition
            )
            allowed_from = [state for state, nexts in check["allowed"].items() if payments["paidStatus"] in nexts]
        unpaid = next(
            (v for v in allowed_from if v not in (payments["paidStatus"], payments.get("failedStatus"))), None
        )
        status["ruled"] = True
        plan["payments"] = {
            "entity": model["entity"],
            "event": f"{model['entity'][:1].lower()}{model['entity'][1:]}.paid",
            "model": model["class"],
            "statusAttr": status["attr"],
            "statusField": status["apiName"],
            "statusEnum": status["enum"]["class"],
            "paid": payments["paidStatus"],
            "failed": payments.get("failedStatus"),
            "unpaid": unpaid,
            "amountAttr": by_api[amount_field]["attr"],
            "amountField": amount_field,
            "currency": payments.get("currency"),
            "currencyAttr": by_api[payments["currencyField"]]["attr"] if payments.get("currencyField") else None,
            "transition": transition,
            "keyType": pk["type"],
            "path": f"/payments/{module['name']}/{{recordId}}/checkout",
            "module": module["name"],
            "access": "user" if plan.get("auth") else "open",
        }
        module["recordActions"] = [*module.get("recordActions", []), "pay"]
        plan["pluginModels"] = [*plan.get("pluginModels", []), f"{LIB}.models"]
        plan["pluginTables"] = [*plan.get("pluginTables", []), "payments"]
        for source in plan["webhooks"]["incoming"]:
            if source["source"] == SOURCE:
                source["action"] = "payment"  # its handlers are this plugin's
        if unpaid is not None:
            module["tests"] += [
                _test(module, "pay_paid", 200, "the fake page's pay marks the payment and the record paid"),
                _test(module, "pay_failed", 200, "fail marks the payment failed"),
                _test(module, "pay_canceled", 200, "cancel leaves the record as it was"),
                _test(module, "pay_twice", 409, "a paid record cannot be checked out again"),
            ]
        plan["modules"].append(_module(plan["payments"]))
        plan["routers"]["order"].append("payments_router")

    # -- the contract ---------------------------------------------------------------------------------------------

    def contract(self, contract: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> None:
        payments = plan["payments"]
        meta = contract["x-bga"]
        records = meta["fixtures"].get(payments["entity"]) or []
        pk = (meta["entities"].get(payments["entity"]) or {}).get("primaryKey") or "id"
        open_record = next((r for r in records if r.get(payments["statusField"]) == payments["unpaid"]), None)
        paid_record = next((r for r in records if r.get(payments["statusField"]) == payments["paid"]), None)
        meta["payments"] = {
            "entity": payments["entity"],
            "provider": "fake",
            "checkout": "payments.checkout",
            "status": "payments.get",
            "action": "pay",
            "event": payments["event"],
            "statusField": payments["statusField"],
            "paid": payments["paid"],
            **({"payable": open_record[pk]} if open_record else {}),
        }
        info = meta["entities"].get(payments["entity"])
        if info is not None:
            info.setdefault("actionPolicies", {})["pay"] = {"unless": {payments["statusField"]: payments["paid"]}}
        error = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}
        contract["components"]["schemas"]["CheckoutRequest"] = {
            "type": "object",
            "properties": {
                "successUrl": {"type": "string", "format": "uri"},
                "cancelUrl": {"type": "string", "format": "uri"},
            },
        }
        contract["components"]["schemas"]["Payment"] = {
            "type": "object",
            "properties": {
                "paymentId": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": ["pending", "paid", "failed", "canceled"]},
                "amount": {"type": "number"},
                "currency": {"type": "string"},
                "recordId": {"type": "string"},
                "checkoutUrl": {"type": ["string", "null"], "format": "uri"},
            },
            "required": ["paymentId", "status", "amount", "currency", "recordId"],
        }
        payment = {"$ref": "#/components/schemas/Payment"}
        unknown = "00000000-0000-4000-8000-0000000000ff"
        scenarios = [
            {
                "name": "unknown record",
                "params": {"recordId": unknown},
                "body": {},
                "expect": {"status": 404, "code": "NOT_FOUND"},
            }
        ]
        if paid_record:
            scenarios.append(
                {
                    "name": "already paid",
                    "params": {"recordId": paid_record[pk]},
                    "body": {},
                    "expect": {"status": 409, "code": "ALREADY_PAID"},
                }
            )
        checkout: dict[str, Any] = {
            "operationId": "payments.checkout",
            "summary": f"Pay for a {payments['entity']}: the provider's checkout",
            "tags": ["payments"],
            "parameters": [{"name": "recordId", "in": "path", "required": True, "schema": {"type": "string"}}],
            "requestBody": {
                "required": False,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CheckoutRequest"}}},
            },
            "responses": {
                "201": {
                    "description": "The payment and where to pay it",
                    "content": {"application/json": {"schema": payment}},
                },
                "404": {"description": "NOT_FOUND", **error},
                "409": {"description": "ALREADY_PAID", **error},
                "422": {"description": "NOTHING_TO_PAY", **error},
            },
            "x-bga": {
                "entity": payments["entity"],
                "action": "pay",
                "module": "payments",
                "plugin": "payments",
                "mock": "sample",
                "scenarios": scenarios,
                "errors": [
                    {"status": 404, "code": "NOT_FOUND", "message": f"{payments['entity']} not found"},
                    {"status": 409, "code": "ALREADY_PAID", "message": "This is paid already"},
                    {
                        "status": 422,
                        "code": "NOTHING_TO_PAY",
                        "message": "The amount is not above zero",
                        "fields": [payments["amountField"]],
                    },
                ],
            },
        }
        status = {
            "operationId": "payments.get",
            "summary": "A payment's status (what success and cancel screens poll)",
            "tags": ["payments"],
            "parameters": [
                {"name": "paymentId", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
            ],
            "responses": {
                "200": {"description": "The payment", "content": {"application/json": {"schema": payment}}},
                "404": {"description": "NOT_FOUND", **error},
            },
            "x-bga": {
                "entity": None,
                "action": None,
                "module": "payments",
                "plugin": "payments",
                "mock": "sample",
                "scenarios": [
                    {
                        "name": "unknown id",
                        "params": {"paymentId": unknown},
                        "expect": {"status": 404, "code": "NOT_FOUND"},
                    }
                ],
                "errors": [{"status": 404, "code": "NOT_FOUND", "message": "Payment not found"}],
            },
        }
        if payments["access"] == "user":
            for operation in (checkout, status):
                operation["security"] = [{"bearerAuth": []}]
                operation["x-bga"]["auth"] = "jwt"
                operation["responses"]["401"] = {"description": "UNAUTHORIZED", **error}
        contract["paths"][payments["path"]] = {"post": checkout}
        contract["paths"]["/payments/{paymentId}"] = {"get": status}

    # -- the project ----------------------------------------------------------------------------------------------

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        return [
            Setting(
                "payment_provider",
                "str",
                '"fake"',
                comment="fake (a checkout page in this app) or your adapter",
                example="PAYMENT_PROVIDER=fake",
            ),
            Setting(
                "app_env",
                "str",
                '"development"',
                comment="production: the fake checkout page is off",
                example="APP_ENV=development",
            ),
        ]

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        files = super().files(plan)
        payments = (plan or {}).get("payments")
        if not payments:
            return files
        files["src/libs/payments/catalog.py"] = _catalog(payments)
        files[f"{MODULE}/__init__.py"] = ""
        files[f"{MODULE}/presenter/__init__.py"] = (
            'from .router import payments_router\n\n__all__ = ["payments_router"]\n'
        )
        files[f"{MODULE}/presenter/router.py"] = _router(plan, payments)
        jobs = [t["job"] for s in plan["webhooks"]["incoming"] if s["source"] == SOURCE for t in s["types"]]
        files["src/jobs/webhook_in_payments.py"] = (
            '"""The payment provider\'s outcomes (Story 10.9), as jobs of the incoming webhook path (10.8)."""\n\n'
            "from typing import Any\n\nfrom src.libs.jobs import JobContext, job\nfrom src.libs.payments.settle "
            "import settle\n"
            + "".join(
                f'\n\n@job("{name}")\ndef {to_snake(name)}(payload: dict[str, Any], ctx: JobContext) -> None:\n'
                "    settle(ctx.session, payload)\n"
                for name in jobs
            )
        )
        return files

    def action_checks(self, plan, module) -> list[ActionCheck]:
        payments = plan.get("payments")
        if module.get("plugin") or not payments or module["name"] != payments["module"]:
            return []
        return [ActionCheck("pay", f'str(entity.{payments["statusAttr"]}) != "{payments["paid"]}"')]

    def test_case(self, plan, module, op, test, ctx: CaseContext) -> Code | None:
        payments = plan.get("payments")
        case = test["case"]
        if module.get("plugin") or not payments or not case.startswith("pay_") or module["name"] != payments["module"]:
            return None
        from ..backend.codegen import _member

        seed = f"{ctx.seed}({payments['statusAttr']}={payments['statusEnum']}.{_member(payments['unpaid'])})"
        path = payments["path"].replace("{recordId}", "{record.id}")
        lines = [f"def {test['id']}(client):"]
        if plan.get("auth"):
            lines.append('    client.headers["Authorization"] = f"Bearer {sign_in(client)}"')
        lines += [
            f"    record = {seed}",
            f'    checkout = client.post(f"{path}", json={{}})',
            "    assert checkout.status_code == 201, checkout.text",
            '    session_id = checkout.json()["checkoutUrl"].rsplit("/", 1)[1]',
            '    assert client.get(f"/payments/fake/checkout/{session_id}").status_code == 200',
        ]
        outcome = {"pay_paid": "pay", "pay_failed": "fail", "pay_canceled": "cancel", "pay_twice": "pay"}[case]
        lines += [
            f'    assert client.post(f"/payments/fake/checkout/{{session_id}}/{outcome}").status_code == 200',
            '    Worker(create_engine(os.environ["DB_URL"])).run_due()',
            "",
            "    payment = client.get(f\"/payments/{checkout.json()['paymentId']}\").json()",
        ]
        expected = {"pay": "paid", "fail": "failed", "cancel": "canceled"}[outcome]
        lines.append(f'    assert payment["status"] == "{expected}"')
        get = next((o for o in module["operations"] if o.get("action") == "get"), None)
        if case == "pay_paid" and get is not None:  # the record followed, and offers no second payment
            record_path = re.sub(r"\{\w+\}", "{record.id}", get["path"])
            lines += [
                f'    shown = client.get(f"{record_path}").json()',
                f'    assert shown["{payments["statusField"]}"] == "{payments["paid"]}"',
                '    assert "pay" not in shown["allowedActions"]',
            ]
        if case == "pay_twice":
            lines += [
                f'    again = client.post(f"{path}", json={{}})',
                '    assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_PAID"',
            ]
        imports = [("src.libs.jobs", ("Worker",)), ("src.modules.shared.domain.entities", (payments["statusEnum"],))]
        if plan.get("auth"):
            imports.append(("tests.auth", ("sign_in",)))
        return Code(tuple(lines), tuple(imports))

    def engine_note(self, plan: dict[str, Any]) -> str:
        return (
            "Payments (Story 10.9, `src/libs/payments`): the record's status follows its payments; do not set the paid "
            "state yourself. A paid record raises `" + plan["payments"]["event"] + "`."
        )


def _test(module: dict[str, Any], case: str, expect: int, description: str) -> dict[str, Any]:
    create = next((op for op in module["operations"] if op.get("action") == "create"), module["operations"][0])
    return {
        "id": f"test_{module['name']}_{case}",
        "operationId": create["operationId"],
        "case": case,
        "expectStatus": expect,
        "description": description,
    }


def _module(payments: dict[str, Any]) -> dict[str, Any]:
    auth = {"auth": "jwt", "policy": None} if payments["access"] == "user" else None

    def op(op_id, method, path, handler, status, errors):
        entry = {
            "operationId": op_id,
            "type": "plugin",
            "action": None,
            "method": method,
            "path": path,
            "handler": handler,
            "status": status,
            "transactional": method != "GET",
            "errors": [{"status": s, "exception": None, "code": c} for s, c in errors],
        }
        if auth:
            entry["auth"] = auth
        return entry

    return {
        "name": "payments",
        "entity": None,
        "plugin": "payments",
        "port": {"interface": None, "dep": None, "methods": []},
        "usecases": [],
        "dtoFiles": [],
        "router": {
            "variable": "payments_router",
            "file": f"{MODULE}/presenter/router.py",
            "prefix": "",
            "tag": "payments",
        },
        "operations": [
            op(
                "payments.checkout",
                "POST",
                payments["path"],
                "checkout",
                201,
                [(404, "NOT_FOUND"), (409, "ALREADY_PAID"), (422, "NOTHING_TO_PAY")],
            ),
            op("payments.get", "GET", "/payments/{paymentId}", "get_payment", 200, [(404, "NOT_FOUND")]),
        ],
        "recordActions": [],
        "testFile": None,
        "tests": [],
    }


def _catalog(payments: dict[str, Any]) -> str:
    rule = ""
    if payments["transition"]:
        rule = f"from src.libs.rules.catalog import {payments['transition']}\n"
    return (
        '"""What this app takes payments for (Story 10.9), from the plan."""\n\n'
        + rule
        + f"from src.modules.shared.domain.entities import {payments['statusEnum']}\n"
        f"from src.modules.shared.infrastructure.models import {payments['model']}\n\n"
        "from .payable import Payable\n\n"
        "PAYABLE = Payable(\n"
        f'    entity="{payments["entity"]}",\n'
        f"    model={payments['model']},\n"
        f'    status="{payments["statusAttr"]}",\n'
        f"    status_enum={payments['statusEnum']},\n"
        f'    paid="{payments["paid"]}",\n'
        f"    failed={repr(payments['failed']).replace(chr(39), chr(34))},\n"
        f'    amount="{payments["amountAttr"]}",\n'
        f"    currency={repr(payments['currency']).replace(chr(39), chr(34))},\n"
        f"    currency_field={repr(payments['currencyAttr']).replace(chr(39), chr(34))},\n"
        f'    event="{payments["event"]}",\n'
        f"    transition={payments['transition'] or 'None'},\n"
        f'    key_type="{payments["keyType"]}",\n'
        ")\n"
    )


def _router(plan: dict[str, Any], payments: dict[str, Any]) -> str:
    user = payments["access"] == "user"
    param = "_user: CurrentUserDep, " if user else ""
    return (
        '"""Payments (Story 10.9): checkout, a payment\'s status, and the fake provider\'s checkout page."""\n\n'
        "import json\nimport uuid\nfrom decimal import Decimal\nfrom enum import Enum\nfrom html import escape\n"
        "from typing import Annotated\n\n"
        "import httpx\nfrom fastapi import APIRouter, Path, Request\n"
        "from fastapi.responses import HTMLResponse, RedirectResponse\n"
        "from pydantic import BaseModel, ConfigDict, Field\nfrom pydantic.alias_generators import to_camel\n"
        "from sqlmodel import col, select\n\n"
        "from src.configs import config\nfrom src.libs.database.session import SessionDep\n"
        "from src.libs.exceptions import ConflictException, ErrorCode, NotFoundException\n"
        "from src.libs.exceptions.base_exception import BaseException as AppException\n"
        "from src.libs.payments import PaymentModel, get_provider\nfrom src.libs.payments.catalog import PAYABLE\n"
        + ("from src.libs.security import CurrentUserDep\n" if user else "")
        + "from src.libs.webhooks import HEADER, sign\n\n"
        'payments_router = APIRouter(tags=["payments"])\n\n'
        'ERROR = {"description": "Error envelope: {error: {code, message, details}}"}\n'
        'RecordId = Annotated[str, Path(alias="recordId")]\n'
        'PaymentId = Annotated[uuid.UUID, Path(alias="paymentId")]\n'
        'OUTCOMES = {"pay": "checkout.completed", "fail": "checkout.failed", "cancel": "checkout.canceled"}\n\n\n'
        "class Camel(BaseModel):\n    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)\n\n\n"
        "class CheckoutDto(Camel):\n"
        "    success_url: str | None = Field(default=None, max_length=2048)\n"
        "    cancel_url: str | None = Field(default=None, max_length=2048)\n\n\n"
        "class PaymentDto(Camel):\n"
        "    payment_id: uuid.UUID\n    status: str\n    amount: float\n    currency: str\n    record_id: str\n"
        "    checkout_url: str | None = None\n\n\n"
        "def _state(value: object) -> object:\n"
        "    return value.value if isinstance(value, Enum) else value\n\n\n"
        "def _dto(payment: PaymentModel, url: str | None = None) -> PaymentDto:\n"
        "    return PaymentDto(payment_id=payment.id, status=payment.status, amount=float(payment.amount),\n"
        "                      currency=payment.currency, record_id=payment.record_id, checkout_url=url)\n\n\n"
        "@payments_router.post(\n"
        f'    "{payments["path"]}",\n    operation_id="payments.checkout",\n    response_model=PaymentDto,\n'
        "    status_code=201,\n    responses={404: ERROR, 409: ERROR, 422: ERROR},\n)\n"
        f"def checkout(record_id: RecordId, request: Request, {param}session: SessionDep, body: CheckoutDto | "
        f"None = None)"
        " -> PaymentDto:\n"
        '    """A payment for the amount on the record (never the client\'s), and where to pay it."""\n'
        "    try:\n        key = PAYABLE.record_key(record_id)\n    except ValueError:\n        key = None\n"
        "    record = session.get(PAYABLE.model, key) if key is not None else None\n"
        "    if record is None:\n"
        '        raise NotFoundException(f"{PAYABLE.entity} not found", details={"id": record_id})\n'
        "    if _state(getattr(record, PAYABLE.status)) == PAYABLE.paid:\n"
        '        raise ConflictException("This is paid already", ErrorCode.ALREADY_PAID)\n'
        "    amount = getattr(record, PAYABLE.amount)\n"
        "    if amount is None or Decimal(str(amount)) <= 0:\n"
        "        raise AppException(\n"
        '            422, "The amount is not above zero", ErrorCode.NOTHING_TO_PAY, details={"fields": '
        "[PAYABLE.amount]}\n"
        "        )\n"
        '    currency = PAYABLE.currency or str(getattr(record, PAYABLE.currency_field or "", "") or "USD")\n'
        "    payment = PaymentModel(entity=PAYABLE.entity, record_id=str(key), provider=get_provider().name,\n"
        '                           session_id="", amount=Decimal(str(amount)), currency=currency,\n'
        "                           success_url=body.success_url if body else None,\n"
        "                           cancel_url=body.cancel_url if body else None)\n"
        "    checkout_session = get_provider().create_checkout(payment, str(request.base_url))\n"
        "    payment.session_id = checkout_session.session_id\n"
        "    session.add(payment)\n    session.commit()\n    session.refresh(payment)\n"
        "    return _dto(payment, checkout_session.url)\n\n\n"
        '@payments_router.get("/payments/{paymentId}", operation_id="payments.get", response_model=PaymentDto,\n'
        "                     responses={404: ERROR})\n"
        f"def get_payment(payment_id: PaymentId, {param}session: SessionDep) -> PaymentDto:\n"
        "    payment = session.get(PaymentModel, payment_id)\n"
        "    if payment is None:\n"
        '        raise NotFoundException("Payment not found", details={"id": str(payment_id)})\n'
        "    return _dto(payment)\n\n\n"
        "def _pending(session: SessionDep, session_id: str) -> PaymentModel:\n"
        '    if config.app_env == "production" or get_provider().name != "fake":\n'
        '        raise NotFoundException("Not found")  # the fake checkout never runs in production\n'
        "    payment = session.exec(select(PaymentModel).where(col(PaymentModel.session_id) == session_id)).first()\n"
        "    if payment is None:\n"
        '        raise NotFoundException("Checkout not found")\n'
        "    return payment\n\n\n"
        '@payments_router.get("/payments/fake/checkout/{session_id}", include_in_schema=False, '
        "response_class=HTMLResponse)\n"
        "def fake_checkout_page(session_id: str, session: SessionDep) -> HTMLResponse:\n"
        '    """Test double: the fake provider\'s checkout page."""\n'
        "    payment = _pending(session, session_id)\n"
        '    buttons = "".join(\n'
        '        f\'<form method="post" action="/payments/fake/checkout/{escape(session_id)}/{outcome}">\'\n'
        "        f'<button type=\"submit\">{label}</button></form>'\n"
        '        for outcome, label in (("pay", "Pay"), ("fail", "Fail the payment"), ("cancel", "Cancel"))\n'
        "    )\n"
        "    return HTMLResponse(\n"
        '        "<!doctype html><title>Fake checkout</title><body style=\\"font-family: sans-serif\\">"\n'
        '        f"<h1>Fake checkout</h1><p>{escape(PAYABLE.entity)} {escape(payment.record_id)}: "\n'
        '        f"{payment.amount:.2f} {escape(payment.currency)}</p>"\n'
        '        f"<p>Status: {escape(payment.status)}</p>{buttons}</body>"\n'
        "    )\n\n\n"
        '@payments_router.post("/payments/fake/checkout/{session_id}/{outcome}", include_in_schema=False)\n'
        "async def fake_checkout_outcome(session_id: str, outcome: str, request: Request, session: SessionDep):\n"
        '    """Sends the outcome as the provider would: a signed event to this app\'s own webhook route (10.8)."""\n'
        "    payment = _pending(session, session_id)\n"
        "    if outcome not in OUTCOMES:\n"
        '        raise NotFoundException("No such outcome")\n'
        '    event = {"id": f"evt_{uuid.uuid4().hex}", "type": OUTCOMES[outcome], "data": {"sessionId": session_id}}\n'
        '    body = json.dumps(event, separators=(",", ":")).encode()\n'
        '    headers = {HEADER: sign(config.payment_webhook_secret, body), "Content-Type": "application/json"}\n'
        "    transport = httpx.ASGITransport(app=request.app)\n"
        '    async with httpx.AsyncClient(transport=transport, base_url="http://payments.internal") as client:\n'
        '        answer = await client.post("/webhooks/payments", content=body, headers=headers)\n'
        '    target = payment.success_url if outcome == "pay" else payment.cancel_url\n'
        "    if target and answer.status_code == 200:\n"
        "        return RedirectResponse(target, status_code=303)\n"
        "    return HTMLResponse(\n"
        '        f"<!doctype html><title>Fake checkout</title><p>{escape(outcome)}: "\n'
        '        f"the provider answered {answer.status_code}. You can close this tab.</p>",\n'
        "        status_code=200 if answer.status_code == 200 else 502,\n"
        "    )\n"
    )
