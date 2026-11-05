"""Webhooks as a plugin (Story 10.8): outgoing and incoming, on the jobs plugin (10.6).

Outgoing: `webhooks.outgoing.events` may be subscribed to (`POST /webhooks/subscriptions`, an admin with roles). Each
event fans out (a job of that event) to a delivery per active subscription; each delivery is a job with backoff that
POSTs the event signed with the subscription's secret (`X-Webhook-Signature: t=<unix>,v1=<hex>` over `<t>.<body>`,
plus `X-Webhook-Id` and `X-Webhook-Event`), never following redirects, and refuses private targets unless
`WEBHOOK_ALLOW_PRIVATE=true` (set in local previews and sandboxes only).

Incoming: `webhooks.incoming[]` sources post signed events to `POST /webhooks/<source>`; the route checks the
signature and its timestamp window, stores the event id (a repeat is answered 200 and ignored) and enqueues the job of
its type (`log`, built in, or `custom`, the engine's).
"""

import re
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_pascal, to_snake

from .base import Plugin, Setting

LIB = "src.libs.webhooks"
MODULE = "src/modules/webhooks"
RESERVED = {"subscriptions", "deliveries"}
RECEIVER_PORT = 8767  # the smoke check's receiver, inside the sandbox


def _name(*parts: str) -> str:
    return "".join(to_pascal(re.sub(r"[^A-Za-z0-9]+", "_", part)) for part in parts)


def _spec_webhooks(spec: dict[str, Any]) -> dict[str, Any]:
    return spec.get("webhooks") or {}


def outgoing_events(spec: dict[str, Any]) -> list[str]:
    return list((_spec_webhooks(spec).get("outgoing") or {}).get("events") or [])


class WebhooksPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="webhooks", requires=("jobs",))

    def applies(self, spec: dict[str, Any]) -> bool:
        webhooks = _spec_webhooks(spec)
        return bool(outgoing_events(spec) or webhooks.get("incoming"))

    # -- the spec and the plan ------------------------------------------------------------------------------------

    def extend_spec(self, spec: dict[str, Any]) -> None:
        jobs = spec.setdefault("backgroundJobs", [])
        for event in outgoing_events(spec):  # an event fans out to its subscriptions' deliveries
            jobs.append(
                {
                    "name": f"webhookOut{_name(event)}",
                    "trigger": {"event": event},
                    "action": "webhook",
                    "maxAttempts": 5,
                }
            )

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        roles = (plan.get("auth") or {}).get("roles") or []
        access = "role" if "admin" in roles else ("user" if plan.get("auth") else "open")
        incoming = []
        first_module = next((m for m in plan["modules"] if not m.get("plugin")), None)
        for source in _spec_webhooks(spec).get("incoming") or []:
            types = []
            for event_type in source["events"]:
                job = f"webhookIn{_name(source['source'], event_type)}"
                types.append({"type": event_type, "job": job})
                plan["jobs"].append(
                    {
                        "name": job,
                        "handler": f"webhook_in_{to_snake(source['source'])}",
                        "file": f"src/jobs/webhook_in_{to_snake(source['source'])}.py",
                        "trigger": {"webhook": f"{source['source']}:{event_type}"},
                        "event": None,
                        "action": "webhook",
                        "maxAttempts": 5,
                        "description": source.get("description"),
                    }
                )
            incoming.append(
                {
                    "source": source["source"],
                    "secretEnv": source["secretEnv"],
                    "setting": source["secretEnv"].lower(),
                    "action": source.get("action") or "log",
                    "description": source.get("description"),
                    "types": types,
                    "path": f"/webhooks/{source['source']}",
                }
            )
            if (source.get("action") or "log") == "custom" and first_module is not None:
                first_module["customJobs"] = [
                    *first_module.get("customJobs", []),
                    f"webhookIn{_name(source['source'])}",
                ]
        plan["jobs"].append(
            {
                "name": "webhooks.deliver",
                "handler": "webhooks_deliver",
                "file": "src/jobs/webhooks_deliver.py",
                "trigger": {"webhook": "delivery"},
                "event": None,
                "action": "webhook",
                "maxAttempts": 6,
                "description": "Sends one signed delivery",
            }
        )
        plan["webhooks"] = {"outgoing": outgoing_events(spec), "incoming": incoming, "access": access}
        plan["pluginModels"] = [*plan.get("pluginModels", []), f"{LIB}.models"]
        plan["pluginTables"] = [
            *plan.get("pluginTables", []),
            "webhook_subscriptions",
            "webhook_deliveries",
            "webhook_events_received",
        ]
        plan["modules"].append(_module(plan["webhooks"]))
        plan["routers"]["order"].append("webhooks_router")

    # -- the contract ---------------------------------------------------------------------------------------------

    def contract(self, contract: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> None:
        webhooks = plan["webhooks"]
        contract["x-bga"]["webhooks"] = {
            "outgoing": {"events": webhooks["outgoing"], "signature": "X-Webhook-Signature: t=<unix>,v1=<hex>"},
            "incoming": [
                {"source": s["source"], "path": s["path"], "events": [t["type"] for t in s["types"]]}
                for s in webhooks["incoming"]
            ],
        }
        _contract_paths(contract, plan)

    # -- the project ----------------------------------------------------------------------------------------------

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        settings = [
            Setting(
                "webhook_allow_private",
                "bool",
                "False",
                comment="local previews and sandboxes only",
                example="WEBHOOK_ALLOW_PRIVATE=false",
                test_value="true",
            ),
            Setting("webhook_timeout_seconds", "float", "10.0", example="WEBHOOK_TIMEOUT_SECONDS=10"),
            Setting("webhook_tolerance_seconds", "int", "300", comment="an incoming signature's age, at most"),
        ]
        for source in ((plan or {}).get("webhooks") or {}).get("incoming", []):
            settings.append(
                Setting(
                    source["setting"],
                    "str",
                    '""',
                    comment=f"signs {source['source']}'s webhooks",
                    example=f"{source['secretEnv']}=",
                    test_value=f"test-{source['source']}-secret",
                )
            )
        return settings

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        files = super().files(plan)
        plan = plan or {}
        webhooks = plan.get("webhooks")
        if not webhooks:
            return files
        files |= _router_files(plan)
        files["src/jobs/webhooks_deliver.py"] = (
            '"""Sends one webhook delivery (Story 10.8); a failure retries with the jobs\' backoff."""\n\n'
            "import uuid\nfrom typing import Any\n\n"
            "from src.libs.jobs import JobContext, job\nfrom src.libs.webhooks import DELIVER, MAX_ATTEMPTS, "
            "deliver\n\n\n"
            "@job(DELIVER, max_attempts=MAX_ATTEMPTS)\n"
            "def webhooks_deliver(payload: dict[str, Any], ctx: JobContext) -> None:\n"
            '    deliver(ctx.session, uuid.UUID(payload["deliveryId"]), ctx.attempt)\n'
        )
        for job in plan.get("jobs", []):
            if job["action"] == "webhook" and job.get("event") and job["name"].startswith("webhookOut"):
                files[job["file"]] = (
                    f'"""Fans {job["event"]} out to the webhook subscriptions that want it (Story 10.8)."""\n\n'
                    "from typing import Any\n\nfrom src.libs.jobs import JobContext, job\nfrom "
                    "src.libs.webhooks import fan_out\n\n\n"
                    f'@job("{job["name"]}", events=("{job["event"]}",), max_attempts={job["maxAttempts"]})\n'
                    f"def {job['handler']}(payload: dict[str, Any], ctx: JobContext) -> None:\n"
                    '    data = {key: value for key, value in payload.items() if key != "event"}\n'
                    f'    fan_out(ctx.session, "{job["event"]}", data)\n'
                )
        for source in webhooks["incoming"]:
            if source["action"] in ("log", "custom"):  # a `payment` source's handlers are the payments plugin's
                files[f"src/jobs/webhook_in_{to_snake(source['source'])}.py"] = _incoming_handlers(source)
        files["tests/modules/webhooks/__init__.py"] = ""
        files["tests/modules/webhooks/test_webhooks.py"] = _test_file(plan)
        return files

    def engine_note(self, plan: dict[str, Any]) -> str:
        custom = [s for s in plan["webhooks"]["incoming"] if s["action"] == "custom"]
        note = (
            "Webhooks (Story 10.8, `src/libs/webhooks`): outgoing events fan out by themselves once emitted "
            "(`jobs.emit`); incoming events arrive as jobs `webhookIn<Source><Type>` with `{id, type, data}`."
        )
        for source in custom:
            note += (
                f" Write the handlers in `src/jobs/webhook_in_{to_snake(source['source'])}.py` (replace the "
                f"`NotImplementedError`): {source.get('description') or ''}"
            )
        return note


def _module(webhooks: dict[str, Any]) -> dict[str, Any]:
    def op(op_id, method, path, handler, status, errors, auth=True):
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
        if auth and webhooks["access"] != "open":
            entry["auth"] = {"auth": "jwt", "policy": None}
        return entry

    forbidden = [(403, "FORBIDDEN")] if webhooks["access"] == "role" else []
    ops = []
    if webhooks["outgoing"]:
        ops += [
            op("webhooks.listSubscriptions", "GET", "/webhooks/subscriptions", "list_subscriptions", 200, forbidden),
            op(
                "webhooks.subscribe",
                "POST",
                "/webhooks/subscriptions",
                "subscribe",
                201,
                [*forbidden, (422, "VALIDATION_ERROR"), (422, "UNSAFE_TARGET")],
            ),
            op(
                "webhooks.unsubscribe",
                "DELETE",
                "/webhooks/subscriptions/{subscriptionId}",
                "unsubscribe",
                204,
                [*forbidden, (404, "NOT_FOUND")],
            ),
            op(
                "webhooks.ping",
                "POST",
                "/webhooks/subscriptions/{subscriptionId}/ping",
                "ping",
                202,
                [*forbidden, (404, "NOT_FOUND")],
            ),
            op("webhooks.listDeliveries", "GET", "/webhooks/deliveries", "list_deliveries", 200, forbidden),
        ]
    for source in webhooks["incoming"]:
        ops.append(
            op(
                f"webhooks.receive{_name(source['source'])}",
                "POST",
                source["path"],
                f"receive_{to_snake(source['source'])}",
                200,
                [(400, "INVALID_SIGNATURE")],
                auth=False,
            )
        )
    return {
        "name": "webhooks",
        "entity": None,
        "plugin": "webhooks",
        "port": {"interface": None, "dep": None, "methods": []},
        "usecases": [],
        "dtoFiles": [],
        "router": {
            "variable": "webhooks_router",
            "file": f"{MODULE}/presenter/router.py",
            "prefix": "",
            "tag": "webhooks",
        },
        "operations": ops,
        "recordActions": [],
        "testFile": "tests/modules/webhooks/test_webhooks.py",
        "tests": [],
    }


def _access(plan: dict[str, Any]) -> tuple[str, str, str]:
    """(imports, the dependency alias line, the route parameter) of who may manage subscriptions."""
    access = plan["webhooks"]["access"]
    if access == "role":
        user = plan["auth"]["entityClass"]
        return (
            "from typing import Annotated\n\nfrom fastapi import Depends\n",
            f'AdminDep = Annotated[{user}, Depends(require_roles("admin"))]\n\n\n',
            "_admin: AdminDep, ",
        )
    if access == "user":
        return "", "", "_user: CurrentUserDep, "
    return "", "", ""


def _router_files(plan: dict[str, Any]) -> dict[str, str]:
    webhooks = plan["webhooks"]
    access = webhooks["access"]
    head_imports, alias, param = _access(plan)
    security = ""
    if access == "role":
        security = "from src.libs.security import require_roles\n"
        security += f"from src.modules.shared.domain.entities import {plan['auth']['entityClass']}\n"
    elif access == "user":
        security = "from src.libs.security import CurrentUserDep\n"
    events = ", ".join(f'"{e}"' for e in webhooks["outgoing"])
    events = f"({events},)" if len(webhooks["outgoing"]) == 1 else f"({events})"
    receivers = {s["source"]: {t["type"]: t["job"] for t in s["types"]} for s in webhooks["incoming"]}
    text = (
        '"""Webhooks (Story 10.8): subscriptions and deliveries (outgoing), and the signed receivers (incoming)."""\n\n'
        "import datetime as dt\nimport json\nimport secrets\nimport uuid\n"
        + "from typing import Annotated\n"
        + "\nfrom fastapi import APIRouter"
        + (", Depends" if head_imports else "")
        + ", Path, Query, Request, Response\n"
        "from pydantic import BaseModel, ConfigDict, Field\nfrom pydantic.alias_generators import to_camel\n"
        "from sqlalchemy.dialects.postgresql import insert\nfrom sqlmodel import col, select\n\n"
        "from src.configs import config\nfrom src.libs.database.session import SessionDep\n"
        "from src.libs.exceptions import BadRequestException, ErrorCode, NotFoundException\n"
        "from src.libs.exceptions.base_exception import BaseException as AppException\n"
        "from src.libs.jobs import JobQueue\n"
        + security
        + "from src.libs.webhooks import (\n    HEADER,\n    UnsafeTarget,\n    WebhookDeliveryModel,\n"
        "    WebhookEventReceivedModel,\n    WebhookSubscriptionModel,\n    check_target,\n    fan_out,\n    "
        "verify,\n)\n\n"
        'webhooks_router = APIRouter(tags=["webhooks"])\n\n'
        'ERROR = {"description": "Error envelope: {error: {code, message, details}}"}\n'
        f"EVENTS: tuple[str, ...] = {events if webhooks['outgoing'] else '()'}  # what may be subscribed to\n"
        f"RECEIVERS: dict[str, dict[str, str]] = {receivers!r}  # source → event type → job\n"
        'SubscriptionId = Annotated[uuid.UUID, Path(alias="subscriptionId")]  # the API\'s camelCase name\n\n\n'
        + alias
        + "class Camel(BaseModel):\n    model_config = ConfigDict(alias_generator=to_camel, "
        "populate_by_name=True)\n\n\n"
        "class SubscribeDto(Camel):\n"
        "    url: str = Field(min_length=8, max_length=2048)\n    events: list[str] = Field(min_length=1)\n\n\n"
        "class SubscriptionDto(Camel):\n"
        "    id: uuid.UUID\n    url: str\n    events: list[str]\n    active: bool\n    created_at: dt.datetime\n\n\n"
        "class SubscribedDto(SubscriptionDto):\n"
        "    secret: str  # shown once: the receiver checks signatures with it\n\n\n"
        "class DeliveryDto(Camel):\n"
        "    id: uuid.UUID\n    subscription_id: uuid.UUID\n    event: str\n    status: str\n    attempts: int\n"
        "    response_code: int | None\n    last_error: str | None\n    created_at: dt.datetime\n"
        "    delivered_at: dt.datetime | None\n"
    )
    if webhooks["outgoing"]:
        text += (
            "\n\n@webhooks_router.get(\n"
            '    "/webhooks/subscriptions", operation_id="webhooks.listSubscriptions", '
            "response_model=list[SubscriptionDto]\n)\n"
            f"def list_subscriptions({param}session: SessionDep) -> list[SubscriptionDto]:\n"
            "    rows = "
            "session.exec(select(WebhookSubscriptionModel).order_by(col(WebhookSubscriptionModel.created_at)))\n"
            "    return [SubscriptionDto.model_validate(row.model_dump()) for row in rows]\n\n\n"
            "@webhooks_router.post(\n"
            '    "/webhooks/subscriptions",\n    operation_id="webhooks.subscribe",\n    '
            "response_model=SubscribedDto,\n"
            "    status_code=201,\n    responses={422: ERROR},\n)\n"
            f"def subscribe(body: SubscribeDto, {param}session: SessionDep) -> SubscribedDto:\n"
            "    unknown = sorted(set(body.events) - set(EVENTS))\n"
            "    if unknown:\n"
            "        raise AppException(\n"
            "            422, f\"Not an event: {', '.join(unknown)}\", ErrorCode.VALIDATION_ERROR, "
            'details={"fields": ["events"]}\n'
            "        )\n"
            "    try:\n"
            "        check_target(body.url, config.webhook_allow_private)\n"
            "    except UnsafeTarget as exc:\n"
            '        raise AppException(422, str(exc), ErrorCode.UNSAFE_TARGET, details={"fields": ["url"]}) from exc\n'
            "    row = WebhookSubscriptionModel(url=body.url, events=body.events, secret=secrets.token_hex(24))\n"
            "    session.add(row)\n    session.commit()\n    session.refresh(row)\n"
            "    return SubscribedDto.model_validate(row.model_dump())\n\n\n"
            "@webhooks_router.delete(\n"
            '    "/webhooks/subscriptions/{subscriptionId}",\n    operation_id="webhooks.unsubscribe",\n'
            "    status_code=204,\n    responses={404: ERROR},\n)\n"
            f"def unsubscribe(subscription_id: SubscriptionId, {param}session: SessionDep) -> Response:\n"
            "    row = session.get(WebhookSubscriptionModel, subscription_id)\n"
            "    if row is None:\n"
            '        raise NotFoundException("Subscription not found", details={"id": str(subscription_id)})\n'
            "    session.delete(row)\n    session.commit()\n    return Response(status_code=204)\n\n\n"
            "@webhooks_router.post(\n"
            '    "/webhooks/subscriptions/{subscriptionId}/ping",\n    operation_id="webhooks.ping",\n'
            "    status_code=202,\n    responses={404: ERROR},\n)\n"
            f"def ping(subscription_id: SubscriptionId, {param}session: SessionDep) -> dict:\n"
            '    """A signed `ping` delivery to this subscription only, so its receiver can be checked."""\n'
            "    row = session.get(WebhookSubscriptionModel, subscription_id)\n"
            "    if row is None:\n"
            '        raise NotFoundException("Subscription not found", details={"id": str(subscription_id)})\n'
            '    delivery = WebhookDeliveryModel(subscription_id=row.id, event="ping", payload={"ping": True})\n'
            "    session.add(delivery)\n    session.flush()\n"
            '    JobQueue(session).enqueue("webhooks.deliver", {"deliveryId": str(delivery.id)})\n'
            "    session.commit()\n"
            '    return {"deliveryId": str(delivery.id)}\n\n\n'
            "@webhooks_router.get(\n"
            '    "/webhooks/deliveries", operation_id="webhooks.listDeliveries", response_model=list[DeliveryDto]\n)\n'
            f"def list_deliveries({param}session: SessionDep, limit: int = Query(default=50, ge=1, le=200)) -> "
            f"list[DeliveryDto]:\n"
            "    query = "
            "select(WebhookDeliveryModel).order_by(col(WebhookDeliveryModel.created_at).desc()).limit(limit)\n"
            "    return [DeliveryDto.model_validate(row.model_dump()) for row in session.exec(query)]\n"
        )
    for source in webhooks["incoming"]:
        text += (
            "\n\n@webhooks_router.post(\n"
            f'    "{source["path"]}",\n    operation_id="webhooks.receive{_name(source["source"])}",\n'
            "    responses={400: ERROR},\n)\n"
            f"async def receive_{to_snake(source['source'])}(request: Request, session: SessionDep) -> dict:\n"
            f'    """{source["source"]}\'s signed events: one job per new event id, of its type."""\n'
            "    body = await request.body()\n"
            f"    if not verify(config.{source['setting']}, request.headers.get(HEADER), body, "
            "config.webhook_tolerance_seconds):\n"
            '        raise BadRequestException("The signature is missing, wrong or too old", '
            "ErrorCode.INVALID_SIGNATURE)\n"
            "    event = json.loads(body)\n"
            f'    job = RECEIVERS["{source["source"]}"].get(str(event.get("type")))\n'
            "    if job is None:\n"
            '        return {"status": "ignored"}\n'
            f'    row = {{"id": uuid.uuid4(), "source": "{source["source"]}", "event_id": str(event.get("id")), '
            '"event_type": str(event.get("type"))}\n'
            "    stored = session.connection().execute(\n"
            "        "
            "insert(WebhookEventReceivedModel).values(**row).on_conflict_do_nothing().returning(WebhookEventReceivedModel.id)\n"
            "    ).first()\n"
            "    if stored is None:\n"
            '        return {"status": "duplicate"}  # seen before: answered, not handled again\n'
            '    JobQueue(session).enqueue(job, {"id": event.get("id"), "type": event.get("type"), "data": '
            'event.get("data")})\n'
            "    session.commit()\n"
            '    return {"status": "accepted"}\n'
        )
    if "fan_out" not in text.split("webhooks_router = APIRouter", 1)[1]:
        text = text.replace("    fan_out,\n", "")
    if not webhooks["outgoing"]:
        for name in ("UnsafeTarget", "WebhookDeliveryModel", "WebhookSubscriptionModel", "check_target"):
            text = text.replace(f"    {name},\n", "")
        text = text.replace("import secrets\n", "").replace(", NotFoundException", "")
        text = text.replace(", Path, Query", "").replace(", Response", "")
        text = text.replace(
            'SubscriptionId = Annotated[uuid.UUID, Path(alias="subscriptionId")]  # the API\'s camelCase name\n', ""
        )
    if not webhooks["incoming"]:
        text = (
            text.replace("    HEADER,\n", "")
            .replace("    WebhookEventReceivedModel,\n", "")
            .replace("    verify,\n", "")
        )
        text = text.replace("import json\n", "").replace(", Request", "")
        text = text.replace("from sqlalchemy.dialects.postgresql import insert\n", "")
        text = text.replace(
            "from src.libs.exceptions import BadRequestException, ErrorCode",
            "from src.libs.exceptions import ErrorCode",
        )
    return {
        f"{MODULE}/__init__.py": "",
        f"{MODULE}/presenter/__init__.py": 'from .router import webhooks_router\n\n__all__ = ["webhooks_router"]\n',
        f"{MODULE}/presenter/router.py": text,
    }


def _incoming_handlers(source: dict[str, Any]) -> str:
    lines = [
        f'"""{source["source"]}\'s incoming webhook events (Story 10.8), one job per event type."""\n',
        "from typing import Any\n",
    ]
    if source["action"] == "log":
        lines.append(
            "from src.configs import get_logger\nfrom src.libs.jobs import JobContext, job\n\nlogger = "
            "get_logger(__name__)\n"
        )
    else:
        lines.append("from src.libs.jobs import JobContext, job\n")
    for entry in source["types"]:
        handler = to_snake(entry["job"])
        body = (
            f'    logger.info("webhook {source["source"]} {entry["type"]}", extra={{"job_id": str(ctx.job_id), '
            '"event": payload})\n'
            if source["action"] == "log"
            else f'    raise NotImplementedError("{source["source"]} {entry["type"]}: written by the engine")\n'
        )
        lines.append(
            f'\n@job("{entry["job"]}")\n'
            f"def {handler}(payload: dict[str, Any], ctx: JobContext) -> None:\n"
            '    """`payload`: the event, `{id, type, data}`; idempotent by `payload["id"]`."""\n' + body
        )
    return "\n".join(lines)


def _test_file(plan: dict[str, Any]) -> str:
    webhooks = plan["webhooks"]
    access = webhooks["access"]
    sign_in = {"role": 'sign_in(client, role="admin")', "user": "sign_in(client)"}.get(access)
    out = [
        '"""Generated by the Fullstack Generation Agent (Story 10.8, the webhooks plugin)."""\n',
        "import json\nimport os\nimport threading\nimport time\nfrom http.server import BaseHTTPRequestHandler, "
        "HTTPServer\n",
        "import pytest\nfrom sqlalchemy import create_engine\nfrom sqlmodel import Session, col, select\n\n"
        "from src.configs import config\n",
        "from src.libs.jobs import JobModel, Worker\nfrom src.libs.webhooks import HEADER, UnsafeTarget, "
        "check_target, sign, verify\n" + ("from tests.auth import sign_in\n" if sign_in else ""),
        'ENGINE = create_engine(os.environ["DB_URL"])\n',
        "\ndef test_a_signature_round_trips_and_a_tampered_body_or_an_old_one_fails():\n"
        '    header = sign("secret", b\'{"a":1}\')\n'
        '    assert verify("secret", header, b\'{"a":1}\')\n'
        '    assert not verify("secret", header, b\'{"a":2}\')\n'
        '    assert not verify("other", header, b\'{"a":1}\')\n'
        '    old = sign("secret", b"{}", int(time.time()) - 3600)\n'
        '    assert not verify("secret", old, b"{}", tolerance=300)\n',
        "\ndef test_a_private_target_is_refused():\n"
        '    for url in ("http://127.0.0.1/hook", "http://10.1.2.3/hook", "http://169.254.169.254/latest", '
        '"ftp://x.org/"):\n'
        "        with pytest.raises(UnsafeTarget):\n"
        "            check_target(url, allow_private=False)\n",
    ]
    if sign_in:
        out.append(
            "\n@pytest.fixture(autouse=True)\ndef _signed_in(client):\n"
            f'    client.headers["Authorization"] = f"Bearer {{{sign_in}}}"\n'
            "    yield\n"
            '    client.headers.pop("Authorization", None)\n'
        )
    if webhooks["outgoing"]:
        event = webhooks["outgoing"][0]
        out.append(
            "\nclass _Receiver(BaseHTTPRequestHandler):\n"
            "    got: list[tuple[str, bytes]] = []\n\n"
            "    def do_POST(self) -> None:  # noqa: N802 - http.server's name\n"
            '        body = self.rfile.read(int(self.headers["Content-Length"]))\n'
            "        _Receiver.got.append((self.headers[HEADER], body))\n"
            "        self.send_response(204)\n"
            "        self.end_headers()\n\n"
            "    def log_message(self, *args: object) -> None:\n"
            "        pass\n\n\n"
            "def test_a_subscription_gets_a_signed_ping_and_its_delivery_is_recorded(client):\n"
            '    server = HTTPServer(("127.0.0.1", 0), _Receiver)\n'
            "    threading.Thread(target=server.serve_forever, daemon=True).start()\n"
            '    url = f"http://127.0.0.1:{server.server_address[1]}/hook"\n'
            f'    created = client.post("/webhooks/subscriptions", json={{"url": url, "events": ["{event}"]}})\n'
            "    assert created.status_code == 201, created.text\n"
            "    subscription = created.json()\n\n"
            "    assert client.post(f\"/webhooks/subscriptions/{subscription['id']}/ping\").status_code == 202\n"
            "    Worker(ENGINE).run_due()\n"
            "    server.shutdown()\n\n"
            "    [(header, body)] = _Receiver.got\n"
            '    assert verify(subscription["secret"], header, body) and json.loads(body)["type"] == "ping"\n'
            '    [delivery] = client.get("/webhooks/deliveries").json()\n'
            '    assert delivery["status"] == "delivered" and delivery["responseCode"] == 204\n\n\n'
            "def test_an_unknown_event_or_a_private_target_cannot_be_subscribed(client, monkeypatch):\n"
            "    from src.configs import config\n\n"
            '    body = {"url": "https://example.com/hook", "events": ["nothing.happened"]}\n'
            '    assert client.post("/webhooks/subscriptions", json=body).status_code == 422\n'
            '    monkeypatch.setattr(config, "webhook_allow_private", False)\n'
            f'    private = {{"url": "http://127.0.0.1:9/hook", "events": ["{event}"]}}\n'
            '    response = client.post("/webhooks/subscriptions", json=private)\n'
            '    assert response.status_code == 422 and response.json()["error"]["code"] == "UNSAFE_TARGET"\n'
        )
    for source in webhooks["incoming"]:
        event_type = source["types"][0]["type"]
        job = source["types"][0]["job"]
        out.append(
            f"\ndef test_{to_snake(source['source'])}_events_are_handled_once_and_must_be_signed(client):\n"
            f'    body = json.dumps({{"id": "evt_1", "type": "{event_type}", "data": {{}}}}).encode()\n'
            f'    headers = {{HEADER: sign(config.{source["setting"]}, body), "Content-Type": '
            f'"application/json"}}\n\n'
            f'    first = client.post("{source["path"]}", content=body, headers=headers)\n'
            f'    again = client.post("{source["path"]}", content=body, headers=headers)\n\n'
            '    assert first.json() == {"status": "accepted"} and again.json() == {"status": "duplicate"}\n'
            "    with Session(ENGINE) as session:\n"
            f'        assert len(list(session.exec(select(JobModel).where(col(JobModel.kind) == "{job}")))) == 1\n'
            f'    forged = {{HEADER: sign("not-the-secret", body)}}\n'
            f'    assert client.post("{source["path"]}", content=body, headers=forged).status_code == 400\n'
        )
    return "\n".join(out)


def _contract_paths(contract: dict[str, Any], plan: dict[str, Any]) -> None:
    webhooks = plan["webhooks"]
    error = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}
    schemas = contract["components"]["schemas"]
    secured = webhooks["access"] != "open"
    admin = next((u["login"] for u in (plan.get("auth") or {}).get("demoUsers", []) if u["role"] == "admin"), None)

    def operation(op_id, summary, status, scenarios, errors, body=None, response=None, auth=True, params=None):
        out: dict[str, Any] = {
            "operationId": op_id,
            "summary": summary,
            "tags": ["webhooks"],
            "responses": {
                str(status): {
                    "description": summary,
                    **({"content": {"application/json": {"schema": response}}} if response else {}),
                },
                **{str(e["status"]): {"description": e["code"], **error} for e in errors},
            },
            "x-bga": {
                "entity": None,
                "action": None,
                "module": "webhooks",
                "plugin": "webhooks",
                "mock": "sample",
                "errors": errors,
                "scenarios": scenarios,
            },
        }
        if body:
            out["requestBody"] = {"required": True, "content": {"application/json": {"schema": body}}}
        if params:
            out["parameters"] = params
        if auth and secured:
            out["security"] = [{"bearerAuth": []}]
            out["x-bga"]["auth"] = "jwt"
            for scenario in scenarios:
                if admin and webhooks["access"] == "role":
                    scenario["user"] = admin
        return out

    if webhooks["outgoing"]:
        schemas["WebhookSubscribe"] = {
            "type": "object",
            "required": ["url", "events"],
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "events": {"type": "array", "items": {"type": "string", "enum": webhooks["outgoing"]}},
            },
        }
        schemas["WebhookSubscription"] = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "url": {"type": "string"},
                "events": {"type": "array", "items": {"type": "string"}},
                "active": {"type": "boolean"},
                "createdAt": {"type": "string", "format": "date-time"},
            },
            "required": ["id", "url", "events", "active", "createdAt"],
        }
        listing = {"type": "array", "items": {"$ref": "#/components/schemas/WebhookSubscription"}}
        sub_id = [
            {"name": "subscriptionId", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
        ]
        unknown = "00000000-0000-4000-8000-0000000000ff"
        contract["paths"]["/webhooks/subscriptions"] = {
            "get": operation(
                "webhooks.listSubscriptions",
                "Webhook subscriptions",
                200,
                [{"name": "success", "params": {}, "expect": {"status": 200}}],
                [],
                response=listing,
            ),
            "post": operation(
                "webhooks.subscribe",
                "Subscribe a URL to events (answers its signing secret once)",
                201,
                [
                    {
                        "name": "unknown event",
                        "params": {},
                        "body": {"url": "https://example.com/hook", "events": ["nothing.happened"]},
                        "expect": {"status": 422, "code": "VALIDATION_ERROR"},
                    }
                ],
                [
                    {
                        "status": 422,
                        "code": "UNSAFE_TARGET",
                        "message": "The URL points inside a private network",
                        "fields": ["url"],
                    },
                    {"status": 422, "code": "VALIDATION_ERROR", "message": "Not an event", "fields": ["events"]},
                ],
                body={"$ref": "#/components/schemas/WebhookSubscribe"},
            ),
        }
        contract["paths"]["/webhooks/subscriptions/{subscriptionId}"] = {
            "delete": operation(
                "webhooks.unsubscribe",
                "Remove a subscription",
                204,
                [
                    {
                        "name": "unknown id",
                        "params": {"subscriptionId": unknown},
                        "expect": {"status": 404, "code": "NOT_FOUND"},
                    }
                ],
                [{"status": 404, "code": "NOT_FOUND", "message": "Subscription not found"}],
                params=sub_id,
            )
        }
        contract["paths"]["/webhooks/subscriptions/{subscriptionId}/ping"] = {
            "post": operation(
                "webhooks.ping",
                "Send a signed ping to the subscription",
                202,
                [
                    {
                        "name": "unknown id",
                        "params": {"subscriptionId": unknown},
                        "expect": {"status": 404, "code": "NOT_FOUND"},
                    }
                ],
                [{"status": 404, "code": "NOT_FOUND", "message": "Subscription not found"}],
                params=sub_id,
            )
        }
        contract["paths"]["/webhooks/deliveries"] = {
            "get": operation(
                "webhooks.listDeliveries",
                "Recent deliveries, newest first",
                200,
                [{"name": "success", "params": {}, "expect": {"status": 200}}],
                [],
            )
        }
    for source in webhooks["incoming"]:
        contract["paths"][source["path"]] = {
            "post": operation(
                f"webhooks.receive{_name(source['source'])}",
                f"{source['source']}'s signed events",
                200,
                [
                    {
                        "name": "unsigned",
                        "params": {},
                        "auth": False,
                        "body": {"id": "evt_x", "type": source["types"][0]["type"], "data": {}},
                        "expect": {"status": 400, "code": "INVALID_SIGNATURE"},
                    }
                ],
                [{"status": 400, "code": "INVALID_SIGNATURE", "message": "The signature is missing, wrong or too old"}],
                body={
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "type": {"type": "string"}, "data": {}},
                },
                auth=False,
            )
        }
