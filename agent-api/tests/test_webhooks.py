"""The webhooks plugin (Story 10.8): subscriptions and signed deliveries out, signed and idempotent events in, the SSRF
guard, admin-only management with roles, and the smoke check's receiver."""

import json
from pathlib import Path

from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.smoke import smoke_calls
from src.orchestrator.integration.contract import build_contract, contract_operations
from src.orchestrator.plugins.app import plugin_files
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def webhooks_spec(tmp_path: Path, auth: bool = True) -> dict:
    """two-entity: new tasks can be subscribed to; a billing system posts `invoice.paid` events."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["webhooks"] = {
        "outgoing": {"events": ["task.created"]},
        "incoming": [{"source": "billing", "secretEnv": "BILLING_WEBHOOK_SECRET", "events": ["invoice.paid"]}],
    }
    if auth:
        raw["auth"] = {"type": "jwt", "roles": ["member", "admin"]}
    (tmp_path / "webhooks-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "webhooks-spec.json")


def test_outgoing_events_fan_out_through_jobs_and_management_is_for_admins(tmp_path):
    plan = build_plan(webhooks_spec(tmp_path))
    assert [p["name"] for p in plan["plugins"]] == ["rate-limit", "auth-jwt", "jobs", "webhooks"]
    assert plan["webhooks"]["access"] == "role"
    jobs = {job["name"]: job for job in plan["jobs"]}
    assert jobs["webhookOutTaskCreated"]["trigger"] == {"event": "task.created"}
    assert {"webhookInBillingInvoicePaid", "webhooks.deliver"} <= set(jobs)
    task_create = next(op for m in plan["modules"] for op in m["operations"] if op["operationId"] == "task.create")
    assert task_create["emits"] == ["task.created"]
    assert {"webhook_subscriptions", "webhook_deliveries", "webhook_events_received"} <= set(plan["pluginTables"])
    files = plugin_files(plan)
    router = files["src/modules/webhooks/presenter/router.py"]
    assert 'AdminDep = Annotated[UserEntity, Depends(require_roles("admin"))]' in router
    assert 'SubscriptionId = Annotated[uuid.UUID, Path(alias="subscriptionId")]' in router
    assert "if not verify(config.billing_webhook_secret, request.headers.get(HEADER), body," in router
    assert "on_conflict_do_nothing()" in router and '"duplicate"' in router
    assert 'fan_out(ctx.session, "task.created", data)' in files["src/jobs/webhook_out_task_created.py"]
    assert (
        'deliver(ctx.session, uuid.UUID(payload["deliveryId"]), ctx.attempt)' in files["src/jobs/webhooks_deliver.py"]
    )
    tests = files["tests/modules/webhooks/test_webhooks.py"]
    for name in (
        "test_a_signature_round_trips_and_a_tampered_body_or_an_old_one_fails",
        "test_a_private_target_is_refused",
        "test_a_subscription_gets_a_signed_ping_and_its_delivery_is_recorded",
        "test_billing_events_are_handled_once_and_must_be_signed",
    ):
        assert f"def {name}(" in tests
    for relative, source in files.items():
        if relative.endswith(".py"):
            compile(source, relative, "exec")


def test_without_auth_the_routes_are_open_and_the_contract_lists_them(tmp_path):
    spec = webhooks_spec(tmp_path, auth=False)
    plan = build_plan(spec)
    assert plan["webhooks"]["access"] == "open"
    contract = build_contract(spec, plan)
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    assert {"webhooks.subscribe", "webhooks.ping", "webhooks.listDeliveries", "webhooks.receiveBilling"} <= set(ops)
    assert "security" not in ops["webhooks.subscribe"]
    unsigned = ops["webhooks.receiveBilling"]["x-bga"]["scenarios"][0]
    assert unsigned["expect"] == {"status": 400, "code": "INVALID_SIGNATURE"}
    assert contract["x-bga"]["webhooks"]["incoming"] == [
        {"source": "billing", "path": "/webhooks/billing", "events": ["invoice.paid"]}
    ]


def test_the_smoke_check_subscribes_a_receiver_before_the_worker_and_checks_it_after(tmp_path):
    spec = webhooks_spec(tmp_path)
    plan = build_plan(spec)
    calls, _ = smoke_calls(build_contract(spec, plan), plan)
    kinds = [call.get("kind") for call in calls if call.get("kind")]
    assert kinds == ["webhook_subscribe", "worker", "webhook_check"]
    subscribe = next(call for call in calls if call.get("kind") == "webhook_subscribe")
    assert subscribe["user"] == "demo-admin@example.com" and subscribe["event"] == "task.created"


def test_webhooks_are_validated():
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["webhooks"] = {
        "outgoing": {"events": ["invoice.created"]},
        "incoming": [
            {"source": "subscriptions", "secretEnv": "A_SECRET", "events": ["x"]},
            {"source": "crm", "secretEnv": "CRM_SECRET", "events": ["bad event"], "action": "custom"},
        ],
    }
    paths = {issue.path for issue in validate_spec_data(raw).report.errors}
    assert {"/webhooks/incoming/0/source", "/webhooks/incoming/1/events/0", "/webhooks/incoming/1/description"} <= paths
    assert any(path.startswith("/webhooks/outgoing/events/0") for path in paths)
