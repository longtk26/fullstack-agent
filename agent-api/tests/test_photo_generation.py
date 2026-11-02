"""Tests for Story 19.2: photo generation with Gemini image API / Fake generator."""

import asyncio
import io
import uuid

import httpx
import pytest
from PIL import Image

from src.configs import config
from src.images import (
    FakeImageGenerator,
    GeminiImageGenerator,
    GeneratedImage,
    ImageBlocked,
    ImageFailed,
    build_photo_prompt,
    generate_single_photo,
    get_image_generator,
    photo_cache_key,
    photo_cache_path,
    photos_enabled,
    post_process_photo,
)
from src.orchestrator.frontend_assets import _run_photos, generate_assets


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
    sentinel_key = "MY_SUPER_SECRET_KEY_12345"
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(400, text=f'{{"error": "API key {sentinel_key} rejected for this request"}}')

    async def _run():
        gen = GeminiImageGenerator(api_key=sentinel_key, transport=httpx.MockTransport(handler))
        with pytest.raises(ImageFailed) as exc_info:
            await gen.generate("Test prompt", "16:9")
        return str(exc_info.value)

    error_msg = asyncio.run(_run())
    assert len(seen) == 1 and seen[0].url.host == "generativelanguage.googleapis.com"
    assert sentinel_key not in error_msg
    assert "[REDACTED]" in error_msg and "(400)" in error_msg


def test_gemini_photos_are_off_without_their_own_key(monkeypatch):
    monkeypatch.setattr(config, "image_provider", "gemini")
    monkeypatch.setattr(config, "gemini_api_key", "antigravity-key")
    monkeypatch.setattr(config, "gemini_image_api_key", None)
    assert get_image_generator() is None and not photos_enabled()

    monkeypatch.setattr(config, "gemini_image_api_key", "image-key")
    generator = get_image_generator()
    assert isinstance(generator, GeminiImageGenerator) and generator.api_key == "image-key"


class _BytesGenerator:
    """Returns fixed bytes as a paid image (what a corrupt or truncated API answer looks like)."""

    model = "bytes-image"

    def __init__(self, data: bytes):
        self.data = data
        self.calls = 0

    async def generate(self, prompt: str, aspect_ratio: str) -> GeneratedImage:
        self.calls += 1
        return GeneratedImage(data=self.data, mime="image/jpeg", model=self.model, duration_ms=5, cost_usd=0.03)


def _jpeg(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (320, 180), color=color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.parametrize("data", [b"not an image at all", _jpeg()[:200]], ids=["undecodable", "truncated"])
def test_an_image_pillow_cannot_read_is_a_failed_record_not_a_crash(tmp_path, monkeypatch, data):
    monkeypatch.setattr(config, "artifact_root", str(tmp_path))
    asset = {"id": "bad", "aspectRatio": "16:9", "prompt": "broken bytes"}
    target = tmp_path / "out/bad.webp"

    ok, rec, fallback = asyncio.run(generate_single_photo(asset, target, generator=_BytesGenerator(data)))

    assert ok is False and rec.status == "failed" and fallback.startswith("failed:")
    assert rec.cost_usd == 0.03  # the API call was paid for
    assert not target.exists()
    assert not photo_cache_path(photo_cache_key("bytes-image", build_photo_prompt("broken bytes"), "16:9")).exists()


def test_an_unreadable_cache_entry_is_a_miss_and_is_rewritten(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "artifact_root", str(tmp_path))
    gen = _BytesGenerator(_jpeg())
    asset = {"id": "pho", "aspectRatio": "16:9", "prompt": "steaming pho"}
    cache_file = photo_cache_path(photo_cache_key(gen.model, build_photo_prompt("steaming pho"), "16:9"))
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"RIFF\x00\x00partial")

    ok, rec, _ = asyncio.run(generate_single_photo(asset, tmp_path / "out/pho.webp", generator=gen))

    assert ok is True and rec.status == "ok" and gen.calls == 1
    assert cache_file.read_bytes()[8:12] == b"WEBP"
    assert not list(cache_file.parent.glob("*.tmp"))  # written atomically, nothing left behind


def test_regenerate_skips_the_cache_read_but_refreshes_it(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "artifact_root", str(tmp_path))
    gen = _BytesGenerator(_jpeg())
    asset = {"id": "pho", "aspectRatio": "16:9", "prompt": "steaming pho"}
    target = tmp_path / "out/pho.webp"

    asyncio.run(generate_single_photo(asset, target, generator=gen))
    _, cached, _ = asyncio.run(generate_single_photo(asset, target, generator=gen))
    assert cached.status == "cached" and gen.calls == 1

    first = target.read_bytes()
    gen.data = _jpeg((200, 100, 0))
    ok, fresh, _ = asyncio.run(generate_single_photo(asset, target, generator=gen, use_cache=False))
    assert ok is True and fresh.status == "ok" and gen.calls == 2
    assert target.read_bytes() != first
    cache_file = photo_cache_path(photo_cache_key(gen.model, build_photo_prompt("steaming pho"), "16:9"))
    assert cache_file.read_bytes() == target.read_bytes()


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


def test_run_photos_never_makes_more_than_the_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "artifact_root", str(tmp_path))
    monkeypatch.setattr(config, "image_provider", "fake")
    monkeypatch.setattr(config, "frontend_max_photos", 2)
    wanted = [
        {"id": f"p{i}", "render": "photo", "file": f"public/assets/p{i}.webp", "prompt": f"dish {i}"} for i in range(4)
    ]
    emitted, recorded = [], []

    class Ctx:
        generation_id = "gen_cap"
        store = type("Store", (), {"add_image_calls": staticmethod(recorded.extend)})

        @staticmethod
        async def emit(event, **kwargs):
            emitted.append((event, kwargs))

    fallbacks, ready, _ = asyncio.run(_run_photos(Ctx, tmp_path, wanted))

    assert ready == 2 and len(recorded) == 2
    assert [f["id"] for f in fallbacks] == ["p2", "p3"] and "photo cap" in fallbacks[0]["reason"]
    assert not (tmp_path / "public/assets/p2.webp").exists()
    assert wanted[3]["generated"] is False and "photo cap" in wanted[3]["fallback"]
