"""Story 19.10: One-click generate from requirement to running app."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from redis.asyncio import Redis
from sqlmodel import Session, delete, select

from src.configs import config
from src.engines import EngineRegistry, PromptLibrary
from src.engines.fake_engine import FakeEngine, FakeStep, demo_scenario
from src.engines.port import EngineStatus
from src.libs.database import db_session_manager
from src.libs.queue import JobQueue
from src.libs.redaction import Redactor
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.domain.enums import GenerationStatus, SpecDraftStatus
from src.modules.shared.infrastructure.models import (
    BackendSpecModel,
    FrontendSpecModel,
    GenerationEventModel,
    GenerationModel,
    ImageCallModel,
    SpecDraftModel,
    UploadModel,
)
from src.orchestrator.drafting import DraftRunner
from src.orchestrator.store import JobStore
from src.orchestrator.worker_service import WorkerService
from src.orchestrator.workspace import WorkspaceManager
from workflow_helpers import build_runner, generation, redis_client

REPO = Path(__file__).parents[2]
EXAMPLES = REPO / "examples"
REQUIREMENTS = REPO / "examples" / "requirements"

pytestmark = pytest.mark.usefixtures("clean_redis")


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    with Session(db_session_manager.engine) as session:
        session.exec(delete(GenerationEventModel))
        session.exec(delete(ImageCallModel))
        session.exec(delete(SpecDraftModel))
        session.exec(delete(GenerationModel))
        session.exec(delete(BackendSpecModel))
        session.exec(delete(FrontendSpecModel))
        session.exec(delete(UploadModel))
        session.commit()


def _queued_jobs() -> list[str]:
    async def read():
        client = Redis.from_url(config.redis_url, decode_responses=True)
        try:
            jobs = []
            async for key in client.scan_iter(match="bga:jobs:*"):
                jobs += await client.lrange(key, 0, -1)
            return jobs
        finally:
            await client.aclose()

    return asyncio.run(read())


def _queued_drafts() -> list[str]:
    async def read():
        client = Redis.from_url(config.redis_url, decode_responses=True)
        try:
            drafts = []
            async for key in client.scan_iter(match="bga:drafts:*"):
                drafts += await client.lrange(key, 0, -1)
            return drafts
        finally:
            await client.aclose()

    return asyncio.run(read())


# -- API tests ----------------------------------------------------------------------------------------------------


def test_api_create_from_requirement_queues_draft_not_generation(client, user_headers):
    req_text = "A flashcards application with decks and cards for spaced repetition learning."
    res = client.post(
        "/api/v1/generations",
        json={
            "mode": "dynamic",
            "requirement": {"text": req_text, "fileName": "flashcards.md", "format": "markdown"},
            "options": {"engine": "fake"},
        },
        headers=user_headers,
    )
    assert res.status_code == 202
    data = res.json()
    gen_id = data["generationId"]
    assert data["status"] == "DRAFTING"

    # Generation is DRAFTING and not queued in jobs
    assert gen_id not in _queued_jobs()
    gen_row = generation(gen_id)
    assert gen_row.status == GenerationStatus.DRAFTING
    assert gen_row.mode == "dynamic"
    assert gen_row.options.get("autoGenerate") is True
    draft_id = gen_row.options.get("draftId")
    assert draft_id is not None

    # Draft is PENDING, linked to generation, and queued in drafts
    draft_row = JobStore().draft(uuid.UUID(draft_id))
    assert draft_row is not None
    assert draft_row.generation_id == gen_id
    assert draft_row.status == SpecDraftStatus.PENDING
    assert draft_row.requirement_text.startswith("A flashcards application")
    assert draft_id in _queued_drafts()


def test_api_create_from_requirement_static_mode_with_frontend_options(client, user_headers):
    req_text = "A website for a design studio: home with our services and quotes, a work page, about and contact."
    res = client.post(
        "/api/v1/generations",
        json={
            "mode": "static",
            "requirement": {"text": req_text, "fileName": None},
            "options": {
                "engine": "fake",
                "maxRepairAttempts": 3,
                "runTests": True,
                "generateDockerfile": True,
                "deployPreview": True,
                "frontend": {
                    "runTests": True,
                    "generatePreview": True,
                    "mockApi": True,
                    "manageArea": True,
                },
            },
        },
        headers=user_headers,
    )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "DRAFTING"


def test_api_create_invalid_requirement_rejected(client, user_headers):
    # Too short (< 20 chars)
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": "Too short"}},
        headers=user_headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "REQUIREMENT_INVALID"

    # Empty
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": "   "}},
        headers=user_headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "REQUIREMENT_INVALID"

    # Both requirement and specs provided
    res = client.post(
        "/api/v1/generations",
        json={
            "mode": "backend",
            "requirement": {"text": "A valid requirement text that is long enough."},
            "backendSpec": {"project": {"name": "test"}},
        },
        headers=user_headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "MODE_INPUT_MISMATCH"


def test_api_create_from_requirement_idempotency(client, user_headers):
    key = str(uuid.uuid4())
    req_text = "A flashcards application with decks and cards for spaced repetition learning."
    res1 = client.post(
        "/api/v1/generations",
        json={
            "mode": "static",
            "requirement": {"text": req_text},
            "options": {"engine": "fake"},
        },
        headers={**user_headers, "Idempotency-Key": key},
    )
    assert res1.status_code == 202

    res2 = client.post(
        "/api/v1/generations",
        json={
            "mode": "static",
            "requirement": {"text": req_text},
            "options": {"engine": "fake"},
        },
        headers={**user_headers, "Idempotency-Key": key},
    )
    assert res2.status_code == 202
    assert res1.json()["generationId"] == res2.json()["generationId"]


def test_api_cancel_in_drafting(client, user_headers):
    req_text = "A flashcards application with decks and cards for spaced repetition learning."
    create_res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": req_text}, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    gen_id = create_res.json()["generationId"]
    draft_id = generation(gen_id).options["draftId"]

    # Cancel while drafting
    cancel_res = client.post(f"/api/v1/generations/{gen_id}/cancel", headers=user_headers)
    assert cancel_res.status_code == 202
    assert cancel_res.json()["status"] == "CANCELLED"

    # Generation is CANCELLED
    assert generation(gen_id).status == GenerationStatus.CANCELLED

    # Draft is CANCELLED and unqueued
    draft_row = JobStore().draft(uuid.UUID(draft_id))
    assert draft_row.status == SpecDraftStatus.CANCELLED
    assert draft_id not in _queued_drafts()


def test_api_continue_endpoint(client, user_headers, login):
    # Setup generation in NEEDS_REVIEW
    req_text = "A flashcards application with decks and cards for spaced repetition learning."
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": req_text}, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]

    # Wrong status -> 409
    continue_res = client.post(
        f"/api/v1/generations/{gen_id}/continue",
        json={"backendSpec": {"specVersion": "0.1.0", "project": {"name": "Test"}}},
        headers=user_headers,
    )
    assert continue_res.status_code == 409
    assert continue_res.json()["error"]["code"] == "CONFLICT"

    # Set status to NEEDS_REVIEW
    with Session(db_session_manager.engine) as session:
        gen_m = session.get(GenerationModel, gen_id)
        gen_m.status = GenerationStatus.NEEDS_REVIEW
        session.commit()

    # Other user -> 404 (non-owner, non-admin)
    other_headers = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}
    other_res = client.post(
        f"/api/v1/generations/{gen_id}/continue",
        json={"backendSpec": {"specVersion": "0.1.0", "project": {"name": "Test"}}},
        headers=other_headers,
    )
    assert other_res.status_code == 404

    # Owner continue -> 202, PENDING and enqueued
    shop_spec = json.loads((EXAMPLES / "specs" / "shop.json").read_text())
    ok_res = client.post(
        f"/api/v1/generations/{gen_id}/continue",
        json={"backendSpec": shop_spec},
        headers=user_headers,
    )
    assert ok_res.status_code == 202
    assert ok_res.json()["status"] == "PENDING"
    assert gen_id in _queued_jobs()
    gen_row = generation(gen_id)
    assert gen_row.status == GenerationStatus.PENDING
    assert gen_row.spec_id is not None


# -- Worker tests -------------------------------------------------------------------------------------------------


def _draft_service(tmp_path: Path, redis: Redis, engine: FakeEngine):
    registry = EngineRegistry([engine], default=engine.name)
    store = JobStore()
    events = EventPublisher(redis, Redactor())
    queue = JobQueue(redis)
    runner = build_runner(tmp_path, redis, engine=engine)
    return WorkerService(
        runner,
        queue,
        store,
        events,
        redis,
        registry,
        WorkspaceManager(tmp_path, max_mb=200),
        "w-test",
        concurrency=1,
        drafts=DraftRunner(
            registry,
            PromptLibrary(),
            store,
            tmp_path,
            "w-test",
            EXAMPLES,
            queue=queue,
            events=events,
            redis=redis,
        ),
    )


def test_worker_draft_succeeded_chains_to_generation(client, user_headers, tmp_path):
    req_text = (REQUIREMENTS / "corner-shop.md").read_text()
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": req_text}, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]

    async def scenario():
        redis = redis_client()
        stop = asyncio.Event()
        engine = FakeEngine(tmp_path, demo_scenario(delay_s=0))
        svc = _draft_service(tmp_path, redis, engine)
        task = asyncio.create_task(svc.run(stop))
        try:
            # Wait for generation to become COMPLETED
            for _ in range(300):
                gen = JobStore().generation(gen_id)
                if gen.status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED):
                    return gen.status
                await asyncio.sleep(0.1)
            return gen.status
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=15)
            await redis.aclose()

    status = asyncio.run(scenario())
    assert status == GenerationStatus.COMPLETED
    gen_row = generation(gen_id)
    assert gen_row.status == GenerationStatus.COMPLETED
    assert gen_row.spec_id is not None

    # Events stream check: draft.progress events were published
    store = JobStore()
    events = store._with(
        lambda s: [
            (e.type, e.payload)
            for e in s.exec(select(GenerationEventModel).where(GenerationEventModel.generation_id == gen_id)).all()
        ]
    )
    draft_progress_events = [p for (t, p) in events if t == "draft.progress"]
    assert len(draft_progress_events) >= 1
    assert any(p.get("progress") == "drafting" for p in draft_progress_events)


def test_worker_draft_needs_review_stops_generation(client, user_headers, tmp_path):
    req_text = "A flashcards app that will produce an invalid spec from the fake engine."
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": req_text}, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]

    # Configure fake engine to write broken json on draft and repair
    broken_scenario = {
        "draft_spec": [
            FakeStep(
                write={
                    "backend-spec.json": '{"specVersion": "0.1.0"}',
                    "notes.json": '{"assumptions": [], "unresolved": []}',
                }
            )
        ],
        "repair_spec": [
            FakeStep(
                write={
                    "backend-spec.json": '{"specVersion": "0.1.0"}',
                    "notes.json": '{"assumptions": [], "unresolved": []}',
                }
            )
        ],
    }

    async def scenario():
        redis = redis_client()
        stop = asyncio.Event()
        engine = FakeEngine(tmp_path, broken_scenario)
        svc = _draft_service(tmp_path, redis, engine)
        task = asyncio.create_task(svc.run(stop))
        try:
            for _ in range(150):
                gen = JobStore().generation(gen_id)
                if gen.status == GenerationStatus.NEEDS_REVIEW:
                    return gen.status
                await asyncio.sleep(0.1)
            return gen.status
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=15)
            await redis.aclose()

    status = asyncio.run(scenario())
    assert status == GenerationStatus.NEEDS_REVIEW
    # Generation is NOT enqueued in jobs
    assert gen_id not in _queued_jobs()


def test_worker_draft_failed_fails_generation_with_draft_failed(client, user_headers, tmp_path):
    req_text = "A requirement where the engine crashes completely."
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": req_text}, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]

    # Configure fake engine that fails
    empty_scenario = {
        "draft_spec": [FakeStep(status=EngineStatus.CLI_ERROR, message="Engine crash")],
    }

    async def scenario():
        redis = redis_client()
        stop = asyncio.Event()
        engine = FakeEngine(tmp_path, empty_scenario)
        svc = _draft_service(tmp_path, redis, engine)
        task = asyncio.create_task(svc.run(stop))
        try:
            for _ in range(150):
                gen = JobStore().generation(gen_id)
                if gen.status == GenerationStatus.FAILED:
                    return gen.status, gen.error_summary
                await asyncio.sleep(0.1)
            return gen.status, gen.error_summary
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=15)
            await redis.aclose()

    status, error_summary = asyncio.run(scenario())
    assert status == GenerationStatus.FAILED
    assert "DRAFT_FAILED" in (error_summary or "")


def test_worker_reaper_fails_timed_out_draft_and_generation(client, user_headers, tmp_path):
    req_text = "A requirement that gets orphaned before worker starts."
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": req_text}, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]
    draft_id = generation(gen_id).options["draftId"]

    now = datetime.now(UTC)
    with Session(db_session_manager.engine) as session:
        draft_m = session.get(SpecDraftModel, uuid.UUID(draft_id))
        draft_m.updated_at = now - timedelta(seconds=config.draft_pending_timeout_seconds + 60)
        session.commit()

    async def scenario():
        redis = redis_client()
        try:
            svc = _draft_service(tmp_path, redis, FakeEngine(tmp_path))
            svc.reap_drafts(now)
        finally:
            await redis.aclose()

    asyncio.run(scenario())

    draft_row = JobStore().draft(uuid.UUID(draft_id))
    assert draft_row.status == SpecDraftStatus.FAILED
    gen_row = generation(gen_id)
    assert gen_row.status == GenerationStatus.FAILED
    assert "DRAFT_FAILED" in (gen_row.error_summary or "")


# -- review fixes: validation on continue, races, explicit ids, notes, reaper --------------------------------------


def _in_review(client, user_headers, mode: str = "backend", **draft_fields) -> tuple[str, str]:
    """A requirement generation moved to NEEDS_REVIEW (draft NEEDS_REVIEW with `draft_fields`)."""
    res = client.post(
        "/api/v1/generations",
        json={"mode": mode, "requirement": {"text": "A shop that sells coffee beans and brewing gear."}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]
    draft_id = generation(gen_id).options["draftId"]
    with Session(db_session_manager.engine) as session:
        session.get(GenerationModel, gen_id).status = GenerationStatus.NEEDS_REVIEW
        draft_m = session.get(SpecDraftModel, uuid.UUID(draft_id))
        draft_m.status = SpecDraftStatus.NEEDS_REVIEW
        for key, value in draft_fields.items():
            setattr(draft_m, key, value)
        session.commit()
    return gen_id, draft_id


def test_continue_with_a_still_invalid_spec_is_422_and_stays_in_review(client, user_headers):
    gen_id, _ = _in_review(client, user_headers)
    res = client.post(
        f"/api/v1/generations/{gen_id}/continue",
        json={"backendSpec": {"specVersion": "0.1.0", "project": {"name": "Test"}}},
        headers=user_headers,
    )
    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "SPEC_INVALID"
    assert error["details"] and all(issue["spec"] == "backend" for issue in error["details"])
    assert generation(gen_id).status == GenerationStatus.NEEDS_REVIEW
    assert gen_id not in _queued_jobs()


def test_continue_loses_to_a_cancel_committed_meanwhile(client, user_headers, monkeypatch):
    from src.modules.generations.usecases import continue_generation_usecase as module

    gen_id, _ = _in_review(client, user_headers)

    def cancel_then_check(*args):
        with Session(db_session_manager.engine) as session:
            session.get(GenerationModel, gen_id).status = GenerationStatus.CANCELLED
            session.commit()
        return []

    monkeypatch.setattr(module, "input_issues", cancel_then_check)
    shop_spec = json.loads((EXAMPLES / "specs" / "shop.json").read_text())
    res = client.post(f"/api/v1/generations/{gen_id}/continue", json={"backendSpec": shop_spec}, headers=user_headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"
    gen_row = generation(gen_id)
    assert gen_row.status == GenerationStatus.CANCELLED
    assert gen_row.spec_id is None
    assert gen_id not in _queued_jobs()


def test_continue_keeps_reconcile_notes_on_the_draft(client, user_headers):
    backend = json.loads((EXAMPLES / "specs" / "shop.json").read_text())
    frontend = json.loads((EXAMPLES / "frontend-specs" / "shop-dynamic.json").read_text())
    frontend["pages"][0]["sections"][0]["content"]["actions"] = [
        {"id": "gone", "label": "Gone", "kind": "link", "page": "no-such-page"}
    ]
    gen_id, draft_id = _in_review(client, user_headers, mode="dynamic")
    res = client.post(
        f"/api/v1/generations/{gen_id}/continue",
        json={"backendSpec": backend, "frontendSpec": frontend},
        headers=user_headers,
    )
    assert res.status_code == 202, res.json()
    draft_row = JobStore().draft(uuid.UUID(draft_id))
    assert any("no-such-page" in note["message"] for note in draft_row.assumptions)
    stored = JobStore().frontend_spec(generation(gen_id).frontend_spec_id)
    assert json.loads(stored.raw_json)["pages"][0]["sections"][0]["content"]["actions"][0]["page"] == "home"


def test_create_with_draft_id_honours_an_explicit_spec_id(client, user_headers):
    shop_spec = (EXAMPLES / "specs" / "shop.json").read_text()
    spec_id = client.post(
        "/api/v1/specs", content=shop_spec, headers={**user_headers, "content-type": "application/json"}
    ).json()["specId"]
    _, draft_id = _in_review(client, user_headers)  # its draft has no BackendSpec
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "draftId": draft_id, "specId": spec_id, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    assert res.status_code == 202, res.json()
    gen_row = generation(res.json()["generationId"])
    assert str(gen_row.spec_id) == spec_id
    assert gen_row.options["draftId"] == draft_id


def _orphaned_drafting(client, user_headers, draft_status: SpecDraftStatus, **draft_fields) -> str:
    """A DRAFTING generation whose draft finished long ago (its worker died before chaining it)."""
    res = client.post(
        "/api/v1/generations",
        json={"mode": "backend", "requirement": {"text": "A shop that sells coffee beans and brewing gear."}},
        headers=user_headers,
    )
    gen_id = res.json()["generationId"]
    with Session(db_session_manager.engine) as session:
        draft_m = session.get(SpecDraftModel, uuid.UUID(generation(gen_id).options["draftId"]))
        draft_m.status = draft_status
        draft_m.finished_at = datetime.now(UTC) - timedelta(minutes=5)
        for key, value in draft_fields.items():
            setattr(draft_m, key, value)
        session.commit()
    return gen_id


def test_reaper_chains_or_fails_generations_left_drafting(client, user_headers, tmp_path):
    shop_spec = json.loads((EXAMPLES / "specs" / "shop.json").read_text())
    succeeded = _orphaned_drafting(client, user_headers, SpecDraftStatus.SUCCEEDED, backend_spec=shop_spec)
    failed = _orphaned_drafting(client, user_headers, SpecDraftStatus.FAILED, error="engine crashed")
    cancelled = _orphaned_drafting(client, user_headers, SpecDraftStatus.CANCELLED)
    fresh = _orphaned_drafting(client, user_headers, SpecDraftStatus.SUCCEEDED, backend_spec=shop_spec)
    with Session(db_session_manager.engine) as session:
        session.get(SpecDraftModel, uuid.UUID(generation(fresh).options["draftId"])).finished_at = datetime.now(UTC)
        session.commit()

    async def scenario():
        redis = redis_client()
        try:
            await _draft_service(tmp_path, redis, FakeEngine(tmp_path)).reap_drafting(datetime.now(UTC))
        finally:
            await redis.aclose()

    asyncio.run(scenario())
    chained = generation(succeeded)
    assert chained.status == GenerationStatus.PENDING and chained.spec_id is not None
    assert succeeded in _queued_jobs()
    assert generation(failed).status == GenerationStatus.FAILED
    assert "engine crashed" in generation(failed).error_summary
    assert generation(cancelled).status == GenerationStatus.CANCELLED
    assert generation(fresh).status == GenerationStatus.DRAFTING, "its worker may still be chaining it"


def test_chaining_does_not_start_a_generation_cancelled_meanwhile(client, user_headers, tmp_path):
    shop_spec = json.loads((EXAMPLES / "specs" / "shop.json").read_text())
    gen_id = _orphaned_drafting(client, user_headers, SpecDraftStatus.SUCCEEDED, backend_spec=shop_spec)
    with Session(db_session_manager.engine) as session:
        session.get(GenerationModel, gen_id).status = GenerationStatus.CANCELLED
        session.commit()
    draft = JobStore().draft(uuid.UUID(generation(gen_id).options["draftId"]))

    async def scenario():
        redis = redis_client()
        try:
            await _draft_service(tmp_path, redis, FakeEngine(tmp_path)).drafts._chain_generation(draft)
        finally:
            await redis.aclose()

    asyncio.run(scenario())
    gen_row = generation(gen_id)
    assert gen_row.status == GenerationStatus.CANCELLED
    assert gen_row.spec_id is None
    assert gen_id not in _queued_jobs()
