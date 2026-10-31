"""Tests for Story 19.2: photo generation with Gemini image API / Fake generator."""

import asyncio
import io
import uuid

import pytest
from PIL import Image

from src.configs import config
from src.images import (
    FakeImageGenerator,
    GeminiImageGenerator,
    ImageBlocked,
    ImageFailed,
    build_photo_prompt,
    generate_single_photo,
    photo_cache_key,
    photo_cache_path,
    post_process_photo,
)
from src.orchestrator.frontend_assets import generate_assets


def test_build_photo_prompt():
    prompt = build_photo_prompt("A delicious bowl of pho", "warm natural light")
    assert "A delicious bowl of pho. warm natural light. Photorealistic photograph." in prompt
    assert "No text, letters, logos or watermarks in the image." in prompt
    assert len(prompt) <= 1000

    # Without style
    prompt_no_style = build_photo_prompt("A mountain landscape")
    assert "A mountain landscape. Photorealistic photograph." in prompt_no_style

    # Truncate very long prompt
    long_p = "x" * 2000
    assert len(build_photo_prompt(long_p)) <= 1000


def test_post_process_photo():
    # Create a 2000x1000 test image (2:1 aspect ratio)
    img = Image.new("RGB", (2000, 1000), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    # Target 16:9 aspect ratio
    webp_bytes, w, h = post_process_photo(raw_bytes, "16:9")
    assert webp_bytes[:4] == b"RIFF" and webp_bytes[8:12] == b"WEBP"
    assert max(w, h) <= 1600
    assert abs(w / h - 16 / 9) < 0.02


def test_fake_image_generator():
    async def _run():
        gen = FakeImageGenerator(model="test-fake")
        res = await gen.generate("Delicious pho", "16:9")
        assert res.mime == "image/png"
        assert len(res.data) > 0
        assert res.cost_usd == 0.0

        # Triggers for blocked and failed
        with pytest.raises(ImageBlocked):
            await gen.generate("blocked picture", "16:9")

        with pytest.raises(ImageFailed):
            await gen.generate("fail please", "16:9")

    asyncio.run(_run())


def test_generate_single_photo_cache_hit_and_miss(tmp_path, monkeypatch):
    async def _run():
        monkeypatch.setattr(config, "artifact_root", str(tmp_path))

        gen = FakeImageGenerator()
        asset = {"id": "pho-1", "aspectRatio": "16:9", "prompt": "steaming pho"}
        target = tmp_path / "out/pho-1.webp"

        # First call: cache miss
        ok1, rec1, fallback1 = await generate_single_photo(asset, target, generator=gen)
        assert ok1 is True
        assert rec1.status == "ok"
        assert fallback1 is None
        assert target.is_file()

        # Verify cache file exists
        ck = photo_cache_key(gen.model, build_photo_prompt("steaming pho"), "16:9")
        assert photo_cache_path(ck).is_file()

        # Second call: cache hit
        target2 = tmp_path / "out/pho-1-copy.webp"
        ok2, rec2, fallback2 = await generate_single_photo(asset, target2, generator=gen)
        assert ok2 is True
        assert rec2.status == "cached"
        assert target2.is_file()

    asyncio.run(_run())


def test_generate_single_photo_no_generator(tmp_path):
    async def _run():
        asset = {"id": "pho-2", "aspectRatio": "16:9", "prompt": "cold pho"}
        target = tmp_path / "out/pho-2.webp"

        ok, rec, fallback = await generate_single_photo(asset, target, generator=None)
        assert ok is False
        assert rec.status == "failed"
        assert "photos are off" in fallback

    asyncio.run(_run())


def test_generate_single_photo_blocked(tmp_path):
    async def _run():
        gen = FakeImageGenerator()
        asset = {"id": "blocked-photo", "aspectRatio": "16:9", "prompt": "blocked content"}
        target = tmp_path / "out/blocked.webp"

        ok, rec, fallback = await generate_single_photo(asset, target, generator=gen)
        assert ok is False
        assert rec.status == "blocked"
        assert "blocked:" in fallback

    asyncio.run(_run())


def test_gemini_generator_redacts_api_key():
    async def _run():
        sentinel_key = "MY_SUPER_SECRET_KEY_12345"
        gen = GeminiImageGenerator(api_key=sentinel_key, timeout=0.01)

        # Force a timeout / connection error
        with pytest.raises(ImageFailed) as exc_info:
            await gen.generate("Test prompt", "16:9")

        error_msg = str(exc_info.value)
        assert sentinel_key not in error_msg
        assert "[REDACTED]" in error_msg or "timed out" in error_msg or "failed" in error_msg

    asyncio.run(_run())


def test_generate_assets_with_photos_and_remade_uploads(tmp_path, monkeypatch):
    from unittest.mock import MagicMock

    from src.orchestrator.frontend_scaffold import record_owned

    async def _run():
        monkeypatch.setattr(config, "artifact_root", str(tmp_path))
        monkeypatch.setattr(config, "image_provider", "fake")

        frontend = tmp_path / "frontend"
        frontend.mkdir(parents=True, exist_ok=True)
        (frontend / ".bga").mkdir(parents=True, exist_ok=True)
        record_owned(frontend, [])

        plan = {
            "assets": [
                {
                    "id": "hero-photo",
                    "render": "photo",
                    "file": "public/assets/hero-photo.webp",
                    "src": "/assets/hero-photo.webp",
                    "prompt": "sunny beach",
                    "aspectRatio": "16:9",
                    "decorative": False,
                },
                # Regenerable photo: public-file with prompt, missing src
                {
                    "id": "deleted-upload",
                    "render": "public-file",
                    "file": "public/assets/deleted-upload",
                    "prompt": "coffee cup",
                    "aspectRatio": "1:1",
                    "upload": "upl_gone123",
                    "decorative": True,
                },
                # Plain upload without prompt, missing src -> stays placeholder
                {
                    "id": "plain-upload",
                    "render": "public-file",
                    "file": "public/assets/plain-upload",
                    "aspectRatio": "1:1",
                    "upload": "upl_plain456",
                    "decorative": True,
                },
            ]
        }
        plan_file = frontend / ".bga/frontend-plan.json"
        import json

        plan_file.write_text(json.dumps(plan))

        emitted = []

        class FakeCtx:
            generation_id = "gen_test123"
            current_node_run_id = uuid.uuid4()
            engine = MagicMock(name="fake")

            class workspace:
                frontend = tmp_path / "frontend"
                root = tmp_path

            class store:
                recorded_calls = []

                @classmethod
                def add_image_calls(cls, calls):
                    cls.recorded_calls.extend(calls)

            frontend_plan_lock = asyncio.Lock()

            @staticmethod
            def frontend_path(ref):
                return frontend / ref

            @staticmethod
            async def emit(event, **kwargs):
                emitted.append((event, kwargs))

        state = {"frontend_plan_ref": ".bga/frontend-plan.json"}
        update, summary = await generate_assets(state, FakeCtx)

        # hero-photo generated
        assert (frontend / "public/assets/hero-photo.webp").is_file()
        # deleted-upload remade as photo and generated
        assert (frontend / "public/assets/deleted-upload.webp").is_file()
        assert any(e[0] == "frontend.photo.remade" for e in emitted)
        assert summary["photosReady"] == 2

        # plain upload stayed placeholder
        assert not (frontend / "public/assets/plain-upload").is_file()

        # Image calls were recorded
        assert len(FakeCtx.store.recorded_calls) == 2

    asyncio.run(_run())
