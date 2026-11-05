"""Background jobs and events as a plugin (Story 10.6): the spec's `backgroundJobs[]`.

A job runs on an event (`task.created`, `task.updated`, `task.deleted`, `<entity>.<name>` raised by custom code), after
an operation (its operation id is the event), or on a cron schedule. The queue is a PostgreSQL table
(`src/libs/jobs`): CRUD use cases emit their entity's events in the request's transaction (events hook) only when a job
subscribes, so a rolled-back request leaves no job; `python -m src.worker` takes due jobs with `SKIP LOCKED`, retries
with backoff and marks a job dead after its last attempt.

Handlers are `src/jobs/<name>.py`. `action: log` is built in (it writes the event to the log); a `custom` handler is
the engine's, with the jobs API in its note; a custom job too vague to write is not generated and stays in
`unresolved`.
"""

import re
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_snake

from .base import Code, Plugin, RouterParam

LIB = "src.libs.jobs"
CRUD_EVENTS = {"create": "created", "update": "updated", "delete": "deleted"}
MIN_WORDS = 5


def _event_entity(event: str) -> str:
    return event.partition(".")[0]


def _trigger(job: dict[str, Any]) -> tuple[str, str]:
    trigger = job["trigger"]
    if isinstance(trigger, str):
        kind, _, value = trigger.partition(":")
        return kind, value.strip()
    ((kind, value),) = ((k, v) for k, v in trigger.items() if v)
    return kind, value


def planned_jobs(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return list(plan.get("jobs") or [])


class JobsPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="jobs")

    def applies(self, spec: dict[str, Any]) -> bool:
        return bool(spec.get("backgroundJobs"))

    # -- the plan -------------------------------------------------------------------------------------------------

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        modules = [module for module in plan["modules"] if not module.get("plugin")]
        by_entity = {f"{m['entity'][:1].lower()}{m['entity'][1:]}": m for m in modules}
        by_op = {op["operationId"]: (module, op) for module in modules for op in module["operations"]}
        jobs, unresolved = [], []
        for job in spec.get("backgroundJobs", []):
            kind, value = _trigger(job)
            event = value if kind in ("event", "operation") else None
            entry = {
                "name": job["name"],
                "handler": to_snake(job["name"]),
                "file": f"src/jobs/{to_snake(job['name'])}.py",
                "trigger": {kind: value},
                "event": event,
                "action": job.get("action") or "custom",
                "maxAttempts": job.get("maxAttempts") or 5,
                "description": job.get("description"),
            }
            if entry["action"] == "custom" and len((job.get("description") or "").split()) < MIN_WORDS:
                unresolved.append(
                    {
                        "kind": "backgroundJobs",
                        "ref": job["name"],
                        "message": "Not implemented: its description is too short to say what it does",
                    }
                )
                continue
            module = None
            if kind == "event":
                module = by_entity.get(_event_entity(value))
                action = next((a for a, past in CRUD_EVENTS.items() if value.endswith(f".{past}")), None)
                for op in (module or {}).get("operations", []):
                    if action and op.get("action") == action:
                        op["emits"] = [*op.get("emits", []), value]
            elif kind == "operation" and value in by_op:
                module, op = by_op[value]
                if op.get("type") == "crud":
                    op["emits"] = [*op.get("emits", []), value]
            if module is None:
                module = modules[0] if modules else None
            entry["module"] = module["name"] if module else None
            if entry["action"] == "custom" and module is not None:
                module["customJobs"] = [*module.get("customJobs", []), entry["name"]]
                unresolved.append(
                    {
                        "kind": "backgroundJobs",
                        "ref": job["name"],
                        "message": f"Custom job: the engine writes its handler in {entry['file']}",
                    }
                )
            jobs.append(entry)
        for module in modules:  # each event once per operation
            for op in module["operations"]:
                if op.get("emits"):
                    op["emits"] = list(dict.fromkeys(op["emits"]))
        plan["jobs"] = jobs
        plan["pluginModels"] = [*plan.get("pluginModels", []), f"{LIB}.models"]
        plan["pluginTables"] = [*plan.get("pluginTables", []), "job_queue", "job_schedules"]
        plan["unresolved"] = [entry for entry in plan["unresolved"] if entry["kind"] != "backgroundJobs"] + unresolved

    # -- the contract ---------------------------------------------------------------------------------------------

    def contract(self, contract: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> None:
        from ..integration.contract import contract_operations

        contract["x-bga"]["jobs"] = [
            {
                key: job[key]
                for key in ("name", "trigger", "event", "action", "maxAttempts", "description")
                if job.get(key)
            }
            for job in planned_jobs(plan)
        ]
        emits = {op["operationId"]: op["emits"] for m in plan["modules"] for op in m["operations"] if op.get("emits")}
        for op_id, entry in contract_operations(contract).items():
            if op_id in emits:
                entry["operation"].setdefault("x-bga", {})["emits"] = emits[op_id]

    # -- the project ----------------------------------------------------------------------------------------------

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        files = super().files(plan)
        jobs = planned_jobs(plan or {})
        files["src/worker.py"] = _worker_file(plan)
        names = list(dict.fromkeys(job["handler"] for job in jobs))  # one module may hold several jobs (10.8)
        files["src/jobs/__init__.py"] = (
            '"""The app\'s job handlers (Story 10.6): importing this package registers them."""\n\n'
            + "".join(f"from . import {name}  # noqa: F401\n" for name in names)
        )
        for job in jobs:
            if job["action"] in ("log", "custom"):  # other actions' handlers are their plugin's (email: 10.7)
                files[job["file"]] = _handler_file(job)
        files["tests/modules/jobs/__init__.py"] = ""
        files["tests/modules/jobs/test_jobs.py"] = _test_file(jobs)
        return files

    def router_params(self, plan, module, op) -> list[RouterParam]:
        if module.get("plugin") or not op.get("emits"):
            return []
        return [RouterParam("jobs", "JobQueueDep", "JobQueue", ((LIB, ("JobQueueDep",)),), ((LIB, ("JobQueue",)),))]

    def events(self, plan, module, op, record) -> list[Code]:
        if module.get("plugin") or not op.get("emits"):
            return []
        return [Code(tuple(f'jobs.emit("{event}", {record}.model_dump(mode="json"))' for event in op["emits"]))]

    def engine_note(self, plan: dict[str, Any]) -> str:
        custom = [job for job in planned_jobs(plan) if job["action"] == "custom"]
        lines = [f"- `{job['name']}` in `{job['file']}`: {job.get('description') or ''}" for job in custom]
        note = (
            'Jobs (Story 10.6, `src/libs/jobs`): a use case raises an event with `jobs.emit("<entity>.<name>", '
            "payload)` (`jobs: JobQueueDep` from the route); it is enqueued in the request's transaction. A handler is "
            "`@job(name, events=(...))` / `cron=...` with `(payload, ctx)`; `ctx.session` is its own session, and it "
            "must be idempotent by `ctx.job_id` (a retry runs it again)."
        )
        if lines:
            note += " Write the body of these handlers (replace the `NotImplementedError`):\n" + "\n".join(lines)
        return note


def _worker_file(plan: dict[str, Any] | None) -> str:
    from .app import worker_startup

    extra = worker_startup(plan)
    imports = sorted(
        {
            f"from {module} import {', '.join(names)}" if names else f"import {module}"
            for code in extra
            for module, names in code.imports
        }
    )
    setup = "".join(f"    {line}\n" for code in extra for line in code.lines)
    return (
        '"""The job worker (Story 10.6): `python -m src.worker` runs jobs as they come due; `--once` runs what is due\n'
        'now and exits, non-zero when a job failed."""\n\n'
        "import argparse\nimport signal\nimport sys\n\nfrom sqlmodel import create_engine\n\n"
        "from src.configs import config, get_logger, setup_logging\nfrom src.libs.jobs import Worker\n"
        + "".join(f"{line}\n" for line in imports)
        + "\nlogger = get_logger(__name__)\n\n\n"
        "def main(argv: list[str] | None = None) -> int:\n"
        '    parser = argparse.ArgumentParser(prog="python -m src.worker")\n'
        '    parser.add_argument("--once", action="store_true", help="run what is due, then exit")\n'
        "    args = parser.parse_args(argv)\n"
        "    setup_logging()\n" + setup + "    worker = Worker(create_engine(config.db_url))\n"
        "    if args.once:\n"
        "        summary = worker.run_due()\n"
        '        print(f"jobs: {summary.ran} ran, {summary.failed} failed, {summary.dead} dead")\n'
        "        return 1 if summary.failed else 0\n"
        "    stopping: list[bool] = []\n"
        "    signal.signal(signal.SIGTERM, lambda *_: stopping.append(True))\n"
        '    logger.info("job worker started", extra={"worker": worker.worker_id})\n'
        "    try:\n"
        "        worker.run_forever(stop=lambda: bool(stopping))\n"
        "    except KeyboardInterrupt:\n"
        "        pass\n"
        "    return 0\n\n\n"
        'if __name__ == "__main__":\n    sys.exit(main())\n'
    )


def _handler_file(job: dict[str, Any]) -> str:
    ((kind, value),) = job["trigger"].items()
    when = {"event": f"on {value}", "operation": f"after {value}", "cron": f"on the schedule `{value}`"}[kind]
    register = f'cron="{value}"' if kind == "cron" else f'events=("{job["event"]}",)'
    summary = job.get("description") or f"runs {when}"
    head = f'"""Job `{job["name"]}` (Story 10.6), {when}: {summary.rstrip(".")}."""\n\nfrom typing import Any\n\n'
    signature = f"def {job['handler']}(payload: dict[str, Any], ctx: JobContext) -> None:\n"
    decorator = f'@job("{job["name"]}", {register}, max_attempts={job["maxAttempts"]})\n'
    if job["action"] == "log":
        return (
            head + "from src.configs import get_logger\nfrom src.libs.jobs import JobContext, job\n\n"
            "logger = get_logger(__name__)\n\n\n"
            + decorator
            + signature
            + '    """Built in: writes the event to the log."""\n'
            f'    logger.info("job {job["name"]}", extra={{"job_id": str(ctx.job_id), "attempt": ctx.attempt, '
            '"payload": payload})\n'
        )
    message = re.sub(r'["\\]', "", summary)[:200]
    return (
        head
        + "from src.libs.jobs import JobContext, job\n\n\n"
        + decorator
        + signature
        + '    """Written by the engine; idempotent by `ctx.job_id` (a retry runs it again)."""\n'
        f'    raise NotImplementedError("job {job["name"]}: {message}")\n'
    )


def _test_file(jobs: list[dict[str, Any]]) -> str:
    events = [job for job in jobs if job.get("event")]
    emitted = "".join(
        f"\n\ndef test_{job['handler']}_is_enqueued_on_{to_snake(job['event'].replace('.', '_'))}():\n"
        "    with Session(ENGINE) as session:\n"
        f'        JobQueue(session).emit("{job["event"]}", {{"id": "x"}})\n'
        "        session.commit()\n\n"
        f'    assert [job.kind for job in _jobs("{job["name"]}")] == ["{job["name"]}"]\n'
        for job in events
    )
    return (
        '"""Generated by the Fullstack Generation Agent (Story 10.6, the jobs plugin): the queue and the worker\n'
        'against the test database."""\n\n'
        "import datetime as dt\nimport os\nimport threading\nimport time\nfrom typing import Any\n\n"
        "from sqlalchemy import create_engine\nfrom sqlmodel import Session, col, select\n\n"
        "from src.libs.jobs import JobContext, JobModel, JobQueue, JobScheduleModel, Worker, job\n\n"
        'ENGINE = create_engine(os.environ["DB_URL"])\nRAN: list[str] = []\n\n\n'
        '@job("test.record")\n'
        "def _record(payload: dict[str, Any], ctx: JobContext) -> None:\n"
        "    RAN.append(str(ctx.job_id))\n"
        '    time.sleep(payload.get("sleep", 0))\n\n\n'
        '@job("test.fail", max_attempts=2)\n'
        "def _fail(payload: dict[str, Any], ctx: JobContext) -> None:\n"
        '    raise RuntimeError("always fails")\n\n\n'
        '@job("test.tick", cron="* * * * *")\n'
        "def _tick(payload: dict[str, Any], ctx: JobContext) -> None:\n"
        '    RAN.append(payload["scheduledFor"])\n\n\n'
        "def _jobs(kind: str) -> list[JobModel]:\n"
        "    with Session(ENGINE) as session:\n"
        "        return list(session.exec(select(JobModel).where(col(JobModel.kind) == kind)))\n\n\n"
        "def _enqueue(kind: str, count: int = 1, **payload: Any) -> None:\n"
        "    with Session(ENGINE) as session:\n"
        "        queue = JobQueue(session)\n"
        "        for _ in range(count):\n"
        "            queue.enqueue(kind, payload)\n"
        "        session.commit()\n\n\n"
        "def test_a_job_enqueued_in_a_rolled_back_transaction_never_runs():\n"
        "    RAN.clear()\n"
        "    with Session(ENGINE) as session:\n"
        '        JobQueue(session).enqueue("test.record")\n'
        "        session.rollback()\n"
        '    _enqueue("test.record")\n\n'
        "    summary = Worker(ENGINE).run_due()\n\n"
        "    assert summary.ran == 1 and len(RAN) == 1\n\n\n"
        "def test_a_failing_job_is_retried_then_dead():\n"
        '    _enqueue("test.fail")\n\n'
        "    summary = Worker(ENGINE, retry_after=lambda attempt: dt.timedelta(0)).run_due()\n\n"
        '    [failed] = _jobs("test.fail")\n'
        '    assert summary.ran == 2 and summary.dead == 1 and failed.status == "dead" and failed.attempts == 2\n'
        '    assert "always fails" in (failed.last_error or "")\n\n\n'
        "def test_two_workers_never_take_the_same_job():\n"
        "    RAN.clear()\n"
        '    _enqueue("test.record", 20, sleep=0.01)\n'
        '    workers = [Worker(ENGINE, worker_id=f"w{index}", batch=3) for index in range(2)]\n'
        "    threads = [threading.Thread(target=worker.run_due) for worker in workers]\n"
        "    for thread in threads:\n        thread.start()\n"
        "    for thread in threads:\n        thread.join()\n\n"
        "    assert len(RAN) == 20 and len(set(RAN)) == 20\n"
        '    assert {job.status for job in _jobs("test.record")} == {"done"}\n\n\n'
        "def test_a_cron_tick_enqueues_once():\n"
        "    now = dt.datetime.now(dt.UTC)\n"
        "    with Session(ENGINE) as session:\n"
        "        past = now - dt.timedelta(seconds=5)\n"
        '        due = JobScheduleModel(name="test.tick", cron="* * * * *", next_run_at=past)\n'
        "        session.add(due)\n"
        "        session.commit()\n"
        "    workers = [Worker(ENGINE), Worker(ENGINE)]\n"
        '    threads = [threading.Thread(target=worker.tick_schedules, kwargs={"now": now}) for worker in workers]\n'
        "    for thread in threads:\n        thread.start()\n"
        "    for thread in threads:\n        thread.join()\n"
        "    Worker(ENGINE).tick_schedules(now)\n\n"
        '    assert len(_jobs("test.tick")) == 1\n' + emitted
    )
