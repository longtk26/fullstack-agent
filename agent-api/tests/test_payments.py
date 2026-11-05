"""The payments plugin (Story 10.9): checkout from the record's amount, the fake provider's page through the signed
webhook path, settling by a job (the record's status, `<entity>.paid`), `pay` in allowedActions, and the smoke check."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.smoke import smoke_calls
from src.orchestrator.integration.contract import build_contract, contract_operations
from src.orchestrator.plugins.app import plugin_files
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def payments_spec(tmp_path: Path, auth: bool = False, transition: bool = False) -> dict:
    """two-entity: a task has a price and a payment status (UNPAID → PAID or FAILED) and is paid for in USD."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    task = next(entity for entity in raw["entities"] if entity["name"] == "Task")
    task["fields"] += [
        {"name": "price", "type": "decimal", "required": True, "min": 1},
        {"name": "paymentStatus", "type": "enum", "values": ["UNPAID", "PAID", "FAILED"], "default": "UNPAID"},
    ]
    raw["payments"] = {"provider": "fake", "entity": "Task", "amountField": "price", "currency": "USD",
                       "statusField": "paymentStatus", "paidStatus": "PAID", "failedStatus": "FAILED"}  # fmt: skip
    if transition:
        flow = {"UNPAID": ["PAID", "FAILED"], "FAILED": ["PAID", "UNPAID"]}
        params = {"field": "paymentStatus", "transitions": flow}
        raw["rules"] = [{"id": "paymentFlow", "kind": "transition", "entity": "Task", "params": params}]
        next(op for op in raw["operations"] if op["operationId"] == "task.update")["rules"] = ["paymentFlow"]
    if auth:
        raw["auth"] = {"type": "jwt", "roles": ["member"]}
    (tmp_path / "payments-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "payments-spec.json")


def test_payments_plan_a_checkout_from_the_records_amount_and_a_pay_action(tmp_path):
    plan = build_plan(payments_spec(tmp_path))
    assert [p["name"] for p in plan["plugins"]] == ["rate-limit", "jobs", "webhooks", "payments"]
    payments = plan["payments"]
    assert payments["path"] == "/payments/tasks/{recordId}/checkout" and payments["unpaid"] == "UNPAID"
    assert payments["event"] == "task.paid" and payments["amountAttr"] == "price"
    tasks = next(m for m in plan["modules"] if m["name"] == "tasks")
    assert "pay" in tasks["recordActions"]
    billing = next(s for s in plan["webhooks"]["incoming"] if s["source"] == "payments")
    assert billing["action"] == "payment" and [t["type"] for t in billing["types"]] == [
        "checkout.completed",
        "checkout.failed",
        "checkout.canceled",
    ]
    assert "payments" in plan["pluginTables"]


def test_the_project_has_the_port_the_fake_page_the_settling_jobs_and_tests(tmp_path):
    spec = payments_spec(tmp_path, auth=True, transition=True)
    plan = build_plan(spec)
    files = plugin_files(plan)
    assert "transition=PAYMENT_FLOW," in files["src/libs/payments/catalog.py"]
    router = files["src/modules/payments/presenter/router.py"]
    assert 'raise ConflictException("This is paid already", ErrorCode.ALREADY_PAID)' in router
    assert 'answer = await client.post("/webhooks/payments", content=body, headers=headers)' in router
    assert 'if config.app_env == "production" or get_provider().name != "fake":' in router
    assert "settle(ctx.session, payload)" in files["src/jobs/webhook_in_payments.py"]
    assert "class FakePaymentProvider(IPaymentProvider):" in files["src/libs/payments/provider.py"]
    tasks = next(m for m in plan["modules"] if m["name"] == "tasks")
    tests = module_tests(plan, spec, tasks)["tests/modules/tasks/test_task_api.py"]
    for name in ("test_tasks_pay_paid", "test_tasks_pay_failed", "test_tasks_pay_canceled", "test_tasks_pay_twice"):
        assert f"def {name}(client):" in tests
    assert '"pay" not in shown["allowedActions"]' in tests
    for relative, source in files.items():
        if relative.endswith(".py"):
            compile(source, relative, "exec")


def test_the_contract_and_the_smoke_check_pay_a_seeded_record(tmp_path):
    spec = payments_spec(tmp_path)
    plan = build_plan(spec)
    contract = build_contract(spec, plan)
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    names = [s["name"] for s in ops["payments.checkout"]["x-bga"]["scenarios"]]
    assert names == ["unknown record", "already paid"]
    assert contract["x-bga"]["entities"]["Task"]["actionPolicies"]["pay"] == {"unless": {"paymentStatus": "PAID"}}
    payable = contract["x-bga"]["payments"]["payable"]
    calls, _ = smoke_calls(contract, plan)
    kinds = [(call.get("kind"), call["path"]) for call in calls if call.get("kind")]
    assert kinds == [
        ("payment_pay", f"/payments/tasks/{payable}/checkout"),
        ("worker", "src.worker --once"),
        ("payment_check", "/payments/<id>"),
    ]


def test_payments_are_validated():
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["payments"] = {"entity": "Task", "amountField": "title", "statusField": "status", "paidStatus": "SETTLED"}
    paths = {issue.path for issue in validate_spec_data(raw).report.errors}
    assert paths == {"/payments/amountField", "/payments/currency", "/payments/paidStatus"}
