"""Tests for Stories 19.3 & 19.4: photos drafted as uploads, regeneration, records & retention."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlmodel import Session

from src.configs import config
from src.engines import EngineRegistry, PromptLibrary
from src.engines.fake_engine import FakeEngine, FakeStep
from src.libs.database import db_session_manager
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.issues import FrontendIssueCode
from src.modules.shared.infrastructure.models import SpecDraftModel, UploadModel
from src.modules.uploads.infrastructure.persistence import UploadRepository
from src.orchestrator.checks.consistency import check_spec_pair
from src.orchestrator.design_direction import (
    PHOTO_STYLES_BY_PRESET,
    apply_direction,
    direction,
)
from src.orchestrator.drafting import DraftRunner, draw_images
from src.orchestrator.scaffold import scaffold_project
from src.orchestrator.store import JobStore

REPO = Path(__file__).parents[2]
EXAMPLES = REPO / "examples"


@pytest.fixture(autouse=True)
def cleanup_draft_test_data():
    yield
    with Session(db_session_manager.engine) as session:
        from sqlmodel import delete

        from src.modules.shared.infrastructure.models import ImageCallModel, SpecDraftModel, UploadModel

        session.exec(delete(ImageCallModel))
        session.exec(delete(SpecDraftModel))
        session.exec(delete(UploadModel))
        session.commit()


def test_v6_prompt_renders_photos_rules_when_enabled():
    prompts = PromptLibrary()
    rendered_on = prompts.render(
        "draft_frontend_spec",
        "v6",
        mode="static",
        requirement_text="A street food website",
        requirement_format="text",
        frontend_schema_path=".bga/frontend-spec.schema.json",
        frontend_schema_digest_path=".bga/frontend-spec.schema.md",
        frontend_example_path=".bga/examples/frontend-spec.json",
        sections_path=".bga/sections.md",
        output_frontend_path="frontend-spec.json",
        notes_path="notes.json",
        design_path=None,
        photos_enabled=True,
        max_photos=8,
    )
    assert 'source: "photo"' in rendered_on.text
    assert "At most 8 photos" in rendered_on.text

    rendered_off = prompts.render(
        "draft_frontend_spec",
        "v6",
        mode="static",
        requirement_text="A street food website",
        requirement_format="text",
        frontend_schema_path=".bga/frontend-spec.schema.json",
        frontend_schema_digest_path=".bga/frontend-spec.schema.md",
        frontend_example_path=".bga/examples/frontend-spec.json",
        sections_path=".bga/sections.md",
        output_frontend_path="frontend-spec.json",
        notes_path="notes.json",
        design_path=None,
        photos_enabled=False,
        max_photos=8,
    )
    assert 'source: "photo"' not in rendered_off.text
    assert "At most 12 drawn images per site." in rendered_off.text


def test_photo_style_derived_from_preset():
    for preset, expected_style in PHOTO_STYLES_BY_PRESET.items():
        assert expected_style, f"Missing style for preset {preset}"

    d = direction(0)
    assert "photoStyle" in d
    assert d["photoStyle"] == PHOTO_STYLES_BY_PRESET.get(d["theme"]["style"])

    # apply_direction adds photoStyle to photo assets without style
    spec = {
        "pages": [{"route": "/", "sections": []}],
        "theme": {"style": "minimal"},
        "assets": [
            {"id": "photo-1", "source": "photo", "prompt": "a bowl of soup"},
            {"id": "photo-2", "source": "photo", "prompt": "a chef", "style": "custom style"},
            {"id": "draw-1", "source": "generate", "prompt": "an icon"},
        ],
    }
    applied = apply_direction(spec, d)
    assets = {a["id"]: a for a in applied["assets"]}
    assert assets["photo-1"]["style"] == d["photoStyle"]
    assert assets["photo-2"]["style"] == "custom style"
    assert "style" not in assets["draw-1"]


def test_draw_images_rule_photos_enabled_and_disabled(tmp_path, monkeypatch):
    images = [{"id": f"img-{i}", "alt": f"Photo {i}"} for i in range(12)]
    (tmp_path / "frontend-spec.json").write_text(json.dumps({"assets": images}))

    # 1. Photos enabled: first 8 become photos, remaining 4 become generate drawings
    monkeypatch.setattr(config, "image_provider", "fake")
    notes = draw_images(tmp_path, None)
    assets = {a["id"]: a for a in json.loads((tmp_path / "frontend-spec.json").read_text())["assets"]}
    photos = [k for k, a in assets.items() if a.get("source") == "photo"]
    drawings = [k for k, a in assets.items() if a.get("source") == "generate"]
    assert len(photos) == 8
    assert len(drawings) == 4
    assert any("Real photos drafted from their alt text" in n["message"] for n in notes)

    # 2. Photos disabled: all become generate drawings up to 12
    (tmp_path / "frontend-spec.json").write_text(json.dumps({"assets": images}))
    monkeypatch.setattr(config, "image_provider", "none")
    draw_images(tmp_path, None)
    assets_off = {a["id"]: a for a in json.loads((tmp_path / "frontend-spec.json").read_text())["assets"]}
    photos_off = [k for k, a in assets_off.items() if a.get("source") == "photo"]
    drawings_off = [k for k, a in assets_off.items() if a.get("source") == "generate"]
    assert len(photos_off) == 0
    assert len(drawings_off) == 12


def test_end_of_draft_photos_become_uploads_and_record_image_calls(client, user_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "image_provider", "fake")
    monkeypatch.setattr(config, "upload_root", str(tmp_path / "uploads"))
    monkeypatch.setattr(config, "artifact_root", str(tmp_path / "artifacts"))

    spec = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
    # Add an explicit photo asset
    spec["assets"].append(
        {
            "id": "dish-sample",
            "kind": "image",
            "source": "photo",
            "prompt": "steaming noodle dish",
            "aspectRatio": "16:9",
            "alt": "Steaming noodles",
        }
    )
    notes = {"assumptions": [], "unresolved": []}
    step_write = {"frontend-spec.json": json.dumps(spec), "notes.json": json.dumps(notes)}
    engine = FakeEngine(
        tmp_path,
        {"draft_frontend_spec": [FakeStep(write=step_write)]},
    )

    runner = DraftRunner(
        EngineRegistry([engine], default="fake"), PromptLibrary(), JobStore(), tmp_path, "w-test", EXAMPLES
    )
    # Create draft
    resp = client.post(
        "/api/v1/spec-drafts",
        json={
            "engine": "fake",
            "mode": "static",
            "requirementText": "A food blog documenting street food recipes from around the world.",
        },
        headers=user_headers,
    )
    assert resp.status_code == 202, resp.text
    draft_id = resp.json()["draftId"]

    asyncio.run(runner.run(draft_id))
    draft = JobStore().draft(uuid.UUID(draft_id)).model_dump(mode="json")
    assert draft["status"] == "SUCCEEDED"

    # Photo assets should now have source: upload:<id>
    assets = {a["id"]: a for a in draft["frontend_spec"]["assets"]}
    dish_asset = assets["dish-sample"]
    assert dish_asset["source"].startswith("upload:")
    assert dish_asset["prompt"] == "steaming noodle dish"

    # image_calls recorded with draft_id
    calls = JobStore().draft_image_calls(uuid.UUID(draft_id))
    assert len(calls) >= 1
    assert any(c.asset_id == "dish-sample" for c in calls)

    # Draft usage contains images breakdown
    assert "images" in draft["usage"]
    assert draft["usage"]["images"]["count"] >= 1


def test_end_of_draft_failed_or_blocked_photo_stays_photo(client, user_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "image_provider", "fake")
    monkeypatch.setattr(config, "upload_root", str(tmp_path / "uploads"))
    monkeypatch.setattr(config, "artifact_root", str(tmp_path / "artifacts"))

    spec = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
    # Prompt with 'blocked' will trigger ImageBlocked in FakeImageGenerator
    spec["assets"].append(
        {
            "id": "blocked-photo",
            "kind": "image",
            "source": "photo",
            "prompt": "blocked picture content",
            "aspectRatio": "16:9",
            "alt": "Blocked photo",
        }
    )
    notes = {"assumptions": [], "unresolved": []}
    step_write = {"frontend-spec.json": json.dumps(spec), "notes.json": json.dumps(notes)}
    engine = FakeEngine(
        tmp_path,
        {"draft_frontend_spec": [FakeStep(write=step_write)]},
    )
    runner = DraftRunner(
        EngineRegistry([engine], default="fake"), PromptLibrary(), JobStore(), tmp_path, "w-test", EXAMPLES
    )
    resp = client.post(
        "/api/v1/spec-drafts",
        json={
            "engine": "fake",
            "mode": "static",
            "requirementText": "A food blog documenting street food recipes from around the world.",
        },
        headers=user_headers,
    )
    assert resp.status_code == 202, resp.text
    draft_id = resp.json()["draftId"]

    asyncio.run(runner.run(draft_id))
    draft = JobStore().draft(uuid.UUID(draft_id)).model_dump(mode="json")
    assert draft["status"] == "SUCCEEDED"

    # Blocked photo keeps source: "photo"
    assets = {a["id"]: a for a in draft["frontend_spec"]["assets"]}
    assert assets["blocked-photo"]["source"] == "photo"

    # An assumption note explains why
    assert any("Photo for 'blocked-photo' could not be generated" in a["message"] for a in draft["assumptions"])


def test_upload_retention_counts_draft_references(login):
    old_time = datetime.now(UTC) - timedelta(days=40)

    with Session(db_session_manager.engine) as session:
        from sqlmodel import select

        from src.modules.shared.infrastructure.models import UserModel

        user = session.exec(select(UserModel)).first()
        owner_id = user.id
        repo = UploadRepository(session)
        # Upload 1: used in a draft
        u1 = repo.create(
            UploadModel(
                id=f"upl_{uuid.uuid4().hex[:20]}",
                owner_id=owner_id,
                filename="draft_photo.webp",
                mime="image/webp",
                bytes=100,
                sha256="sha111111111111111111111111111111111111111111111111111111111111",
                created_at=old_time,
            )
        )
        # Upload 2: not referenced anywhere
        u2 = repo.create(
            UploadModel(
                id=f"upl_{uuid.uuid4().hex[:20]}",
                owner_id=owner_id,
                filename="orphan.webp",
                mime="image/webp",
                bytes=100,
                sha256="sha222222222222222222222222222222222222222222222222222222222222",
                created_at=old_time,
            )
        )

        # Create draft referencing u1
        draft = SpecDraftModel(
            id=uuid.uuid4(),
            owner_id=owner_id,
            engine="fake",
            frontend_spec={"assets": [{"id": "p1", "source": f"upload:{u1.id}"}]},
            created_at=old_time,
            updated_at=old_time,
        )
        session.add(draft)
        session.commit()

        # Check unreferenced
        cutoff = datetime.now(UTC) - timedelta(days=30)
        unref = repo.unreferenced_before(cutoff)
        unref_ids = {u.id for u in unref}
        assert u1.id not in unref_ids, "u1 is referenced by an existing draft and must not be unreferenced"
        assert u2.id in unref_ids, "u2 is orphan and must be unreferenced"

        # Delete draft: u1 now becomes unreferenced
        session.delete(draft)
        session.commit()

        unref2 = repo.unreferenced_before(cutoff)
        unref2_ids = {u.id for u in unref2}
        assert u1.id in unref2_ids


def test_regenerate_asset_endpoint(client, user_headers, login, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "image_provider", "fake")
    monkeypatch.setattr(config, "upload_root", str(tmp_path / "uploads"))
    monkeypatch.setattr(config, "artifact_root", str(tmp_path / "artifacts"))

    # Create draft with an asset
    resp = client.post(
        "/api/v1/spec-drafts",
        json={
            "engine": "fake",
            "mode": "static",
            "requirementText": "A food blog documenting street food recipes from around the world.",
        },
        headers=user_headers,
    )
    assert resp.status_code == 202, resp.text
    draft_id = resp.json()["draftId"]

    # Save a frontend_spec with a photo asset on the draft
    with Session(db_session_manager.engine) as session:
        draft_model = session.get(SpecDraftModel, uuid.UUID(draft_id))
        draft_model.frontend_spec = {
            "assets": [
                {"id": "dish-pho", "kind": "image", "source": "photo", "prompt": "steaming pho", "aspectRatio": "16:9"}
            ]
        }
        session.add(draft_model)
        session.commit()

    # 1. Other user -> 404
    other_headers = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}
    bad_resp = client.post(f"/api/v1/spec-drafts/{draft_id}/assets/dish-pho/regenerate", json={}, headers=other_headers)
    assert bad_resp.status_code == 404

    # 2. Photos disabled -> 400 with PHOTOS_DISABLED
    monkeypatch.setattr(config, "image_provider", "none")
    off_resp = client.post(f"/api/v1/spec-drafts/{draft_id}/assets/dish-pho/regenerate", json={}, headers=user_headers)
    assert off_resp.status_code == 400
    assert off_resp.json()["error"]["code"] == "PHOTOS_DISABLED"

    # 3. Blocked prompt -> 422 with IMAGE_BLOCKED, asset remains unchanged
    monkeypatch.setattr(config, "image_provider", "fake")
    blocked_resp = client.post(
        f"/api/v1/spec-drafts/{draft_id}/assets/dish-pho/regenerate",
        json={"prompt": "blocked content please"},
        headers=user_headers,
    )
    assert blocked_resp.status_code == 422
    assert blocked_resp.json()["error"]["code"] == "IMAGE_BLOCKED"
    draft_after_block = JobStore().draft(uuid.UUID(draft_id)).model_dump(mode="json")
    assert draft_after_block["frontend_spec"]["assets"][0]["source"] == "photo"

    # 4. Success -> 200, asset updated to upload:<id>, new upload created, call recorded
    ok_resp = client.post(
        f"/api/v1/spec-drafts/{draft_id}/assets/dish-pho/regenerate",
        json={"prompt": "fragrant bowl of beef pho with herbs"},
        headers=user_headers,
    )
    assert ok_resp.status_code == 200
    res_asset = ok_resp.json()
    assert res_asset["source"].startswith("upload:")
    assert res_asset["prompt"] == "fragrant bowl of beef pho with herbs"

    draft_after_ok = JobStore().draft(uuid.UUID(draft_id)).model_dump(mode="json")
    assert draft_after_ok["frontend_spec"]["assets"][0]["source"] == res_asset["source"]
    assert draft_after_ok["usage"]["images"]["count"] >= 1


def test_validator_and_consistency_checks_for_record_assets():
    # 1. Frontend validator catches unknown asset in collection records
    pages = [
        {
            "route": "/",
            "title": "Home",
            "sections": [{"id": "s1", "component": "Hero", "content": {"heading": "Welcome"}}],
        }
    ]
    spec_with_bad_record = {
        "specVersion": "1.0",
        "project": {"name": "Test", "mode": "static"},
        "pages": pages,
        "content": [{"collection": "dishes", "records": [{"name": "Pho", "image": "asset:unknown-pho"}]}],
        "assets": [{"id": "other-asset", "kind": "image", "source": "placeholder", "alt": "Other"}],
    }
    report = validate_frontend_spec_data(spec_with_bad_record).report
    assert not report.valid
    errors = [e for e in report.errors if e.code == FrontendIssueCode.FE_UNKNOWN_ASSET]
    assert len(errors) == 1
    assert "unknown-pho" in errors[0].message

    # 2. Consistency pair check catches unknown asset in backend seed
    from src.modules.shared.domain.backend_spec import validate_spec_data

    frontend_spec = {
        "specVersion": "1.0",
        "project": {"name": "Test", "mode": "dynamic"},
        "pages": pages,
        "assets": [{"id": "hero", "kind": "image", "source": "placeholder", "alt": "Hero"}],
    }
    backend_spec = {
        "specVersion": "1.0",
        "project": {"name": "Test"},
        "stack": {
            "framework": "fastapi",
            "database": "postgresql",
            "orm": "sqlalchemy",
            "migration": "alembic",
        },
        "entities": [
            {
                "name": "Dish",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "image", "type": "string"},
                ],
            }
        ],
        "operations": [],
        "seed": [
            {
                "entity": "Dish",
                "records": [{"id": "11111111-1111-1111-1111-111111111111", "image": "asset:missing-seed-photo"}],
            }
        ],
    }
    b_norm = validate_spec_data(backend_spec).normalized
    f_norm = validate_frontend_spec_data(frontend_spec).normalized
    pair_issues = check_spec_pair(f_norm, b_norm)
    assert any(i.code == FrontendIssueCode.FE_UNKNOWN_ASSET and "missing-seed-photo" in i.message for i in pair_issues)


def test_backend_readme_note_when_seed_has_asset_refs(tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    # Scaffold with seed_assets_note
    note = (
        "## Seed data\n\nImage fields of seed records name frontend assets; "
        "the generated frontend serves the file at `/assets/<id>.webp`."
    )
    scaffold_project(
        Path(config.template_dir),
        project_dir,
        "FoodApp",
        generate_dockerfile=False,
        seed_assets_note=note,
    )
    readme = (project_dir / "README.md").read_text()
    assert "## Seed data" in readme
    assert "/assets/<id>.webp" in readme


def test_street_food_static_example_valid():
    spec_path = EXAMPLES / "frontend-specs" / "street-food-static.json"
    assert spec_path.is_file()
    data = json.loads(spec_path.read_text())
    result = validate_frontend_spec_data(data)
    assert result.report.valid
    assert len(result.report.errors) == 0
    assert len(result.report.warnings) == 0
    # Must have dishes collection with 4 records referencing photo assets
    assert any(c["collection"] == "dishes" and len(c["records"]) == 4 for c in data["content"])
    photos = [a for a in data["assets"] if a.get("source") == "photo"]
    assert len(photos) >= 4
