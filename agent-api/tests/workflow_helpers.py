"""Shared builders for orchestrator tests: a runner wired to the test DB, a fresh Redis client and a fake engine."""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from redis.asyncio import Redis
from sqlmodel import Session, select

from src.configs import config
from src.engines import EngineContext, EngineRegistry, PromptLibrary
from src.engines.fake_engine import FakeEngine, demo_scenario
from src.libs.database import db_session_manager
from src.libs.redaction import Redactor
from src.libs.redis import redis_from_url
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.infrastructure.models import (
    CliInvocationModel,
    GenerationEventModel,
    GenerationModel,
    NodeRunModel,
)
from src.orchestrator.runner import JobRunner
from src.orchestrator.store import JobStore
from src.orchestrator.validation import StaticValidationRunner
from src.orchestrator.workspace import WorkspaceManager

TWO_ENTITY = json.loads((Path(__file__).parents[2] / "examples" / "specs" / "two-entity.json").read_text())


def redis_client() -> Redis:
    return redis_from_url(config.redis_url)


def build_runner(
    root: Path,
    redis: Redis,
    engine=None,
    checkpointer=None,
    worker_id: str = "test-worker",
    validator=None,
    sandboxes=None,
    engine_context=None,
    on_completed=None,
    frontend_validator=None,
    previews=None,
    worker_slots=None,
):
    engine = engine or FakeEngine(allowed_root=root)
    store = JobStore()
    return JobRunner(
        registry=EngineRegistry([engine], default=engine.name),
        checkpointer=checkpointer or InMemorySaver(),
        store=store,
        events=EventPublisher(redis, Redactor()),
        workspaces=WorkspaceManager(root, max_mb=200),
        prompts=PromptLibrary(),
        validator=validator or StaticValidationRunner(),
        engine_context=engine_context or EngineContext(conventions="rules"),
        worker_id=worker_id,
        sandboxes=sandboxes,
        on_completed=on_completed,
        frontend_validator=frontend_validator,
        previews=previews,
        worker_slots=worker_slots,
    )


@asynccontextmanager
async def runner_ctx(root: Path, **kwargs):
    redis = redis_client()
    try:
        yield build_runner(root, redis, **kwargs)
    finally:
        await redis.aclose()


def run_job(root: Path, generation_id: str, **kwargs):
    async def go():
        async with runner_ctx(root, **kwargs) as runner:
            return await runner.run(generation_id)

    return asyncio.run(go())


def completed_generation(client, root: Path, **options) -> str:
    """A COMPLETED fake generation (demo scenario without step delays) owned by user@test.local."""
    login = client.post("/api/v1/auth/login", json={"email": "user@test.local", "password": "userpass"})
    headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    generation_id = submit(client, headers, **options)
    assert run_job(root, generation_id, engine=FakeEngine(root, demo_scenario(0))) == "COMPLETED"
    return generation_id


def submit(client, headers, spec=None, **options) -> str:
    # The engine path (crudFromTemplates=false): the fake engine's scripted golden modules, with a planted defect.
    options = {"engine": "fake", "deployPreview": False, "crudFromTemplates": False, **options}
    body = {"backendSpec": spec or TWO_ENTITY, "options": options}
    response = client.post("/api/v1/generations", json=body, headers=headers)
    assert response.status_code == 202, response.text
    return response.json()["generationId"]


def generation(generation_id: str) -> GenerationModel:
    with Session(db_session_manager.engine) as session:
        return session.get(GenerationModel, generation_id)


def events(generation_id: str) -> list[GenerationEventModel]:
    with Session(db_session_manager.engine) as session:
        query = select(GenerationEventModel).where(GenerationEventModel.generation_id == generation_id)
        return list(session.exec(query.order_by(GenerationEventModel.id)))


def statuses(generation_id: str) -> list[str]:
    return [e.status for e in events(generation_id) if e.type == "status.changed"]


def node_runs(generation_id: str) -> list[NodeRunModel]:
    with Session(db_session_manager.engine) as session:
        query = select(NodeRunModel).where(NodeRunModel.generation_id == generation_id)
        return list(session.exec(query.order_by(NodeRunModel.started_at)))


def cli_invocations(generation_id: str) -> list[CliInvocationModel]:
    with Session(db_session_manager.engine) as session:
        return list(session.exec(select(CliInvocationModel).where(CliInvocationModel.generation_id == generation_id)))
