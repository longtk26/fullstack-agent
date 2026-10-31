"""Service functions for generating and post-processing photos (Stories 19.2, 19.3)."""

import asyncio
import hashlib
import shutil
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from src.configs import config, get_logger
from src.modules.shared.domain.entities import ImageCallEntity
from src.orchestrator import tracing

from .cache import photo_cache_key, photo_cache_path
from .factory import get_image_generator
from .port import IImageGenerator, ImageBlocked, ImageFailed
from .post_process import post_process_photo
from .prompt import build_photo_prompt

logger = get_logger(__name__)


_UNSET = object()


async def generate_single_photo(
    asset: dict[str, Any],
    target_path: Path,
    generator: IImageGenerator | None = _UNSET,  # type: ignore
    *,
    generation_id: str | None = None,
    draft_id: uuid.UUID | None = None,
    node_run_id: uuid.UUID | None = None,
    semaphore: asyncio.Semaphore | None = None,
    custom_prompt: str | None = None,
    custom_style: str | None = None,
) -> tuple[bool, ImageCallEntity, str | None]:
    """Generates one photo, applying cache, prompt formatting, semaphore, and WebP post-processing.
    Returns (success, image_call_record, fallback_reason).
    """
    raw_prompt = custom_prompt or asset.get("prompt") or asset.get("alt") or asset["id"]
    raw_style = custom_style if custom_style is not None else asset.get("style")
    prompt_text = build_photo_prompt(raw_prompt, raw_style)
    aspect_ratio = asset.get("aspectRatio", "16:9")

    if generator is _UNSET:
        generator = get_image_generator()

    if generator is None:
        reason = "photos are off (no GEMINI_IMAGE_API_KEY)"
        record = ImageCallEntity(
            id=uuid.uuid4(),
            generation_id=generation_id,
            draft_id=draft_id,
            node_run_id=node_run_id,
            asset_id=asset["id"],
            model="none",
            status="failed",
            error=reason,
            duration_ms=0,
            cost_usd=0.0,
        )
        return False, record, reason

    model = getattr(generator, "model", "gemini-3.1-flash-lite-image")
    cache_key = photo_cache_key(model, prompt_text, aspect_ratio, getattr(config, "gemini_image_size", "1K"))
    cache_file = photo_cache_path(cache_key)

    # 1. Cache hit
    if cache_file.is_file():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cache_file, target_path)
        with Image.open(target_path) as im:
            w, h = im.size
        sha = hashlib.sha256(target_path.read_bytes()).hexdigest()
        if not draft_id:
            asset["width"] = w
            asset["height"] = h
            asset["sha256"] = sha
            asset["generated"] = True

        record = ImageCallEntity(
            id=uuid.uuid4(),
            generation_id=generation_id,
            draft_id=draft_id,
            node_run_id=node_run_id,
            asset_id=asset["id"],
            model=model,
            status="cached",
            duration_ms=0,
            cost_usd=0.0,
        )
        return True, record, None

    # 2. Cache miss -> generate under semaphore
    async def _call() -> tuple[bool, ImageCallEntity, str | None]:
        with tracing.span(
            f"image:{asset['id']}",
            run_type="tool",
            inputs={"prompt": prompt_text, "aspectRatio": aspect_ratio, "model": model},
        ) as span:
            try:
                gen_result = await generator.generate(prompt_text, aspect_ratio)
                webp_bytes, w, h = post_process_photo(gen_result.data, aspect_ratio)

                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_bytes(webp_bytes)

                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(webp_bytes)

                sha = hashlib.sha256(webp_bytes).hexdigest()
                if not draft_id:
                    asset["width"] = w
                    asset["height"] = h
                    asset["sha256"] = sha
                    asset["generated"] = True

                rec = ImageCallEntity(
                    id=uuid.uuid4(),
                    generation_id=generation_id,
                    draft_id=draft_id,
                    node_run_id=node_run_id,
                    asset_id=asset["id"],
                    model=gen_result.model,
                    status="ok",
                    duration_ms=gen_result.duration_ms,
                    cost_usd=gen_result.cost_usd,
                )
                if span and span.enabled:
                    span.end(
                        outputs={
                            "status": "ok",
                            "costUsd": gen_result.cost_usd,
                            "durationMs": gen_result.duration_ms,
                        }
                    )
                return True, rec, None

            except ImageBlocked as exc:
                reason = f"blocked: {exc.reason}"
                logger.warning("Photo blocked by safety filter", extra={"asset_id": asset["id"], "reason": exc.reason})
                rec = ImageCallEntity(
                    id=uuid.uuid4(),
                    generation_id=generation_id,
                    draft_id=draft_id,
                    node_run_id=node_run_id,
                    asset_id=asset["id"],
                    model=model,
                    status="blocked",
                    error=str(exc.reason),
                    duration_ms=0,
                    cost_usd=0.0,
                )
                if span and span.enabled:
                    span.end(outputs={"status": "blocked", "error": exc.reason})
                return False, rec, reason

            except ImageFailed as exc:
                reason = f"failed: {exc.reason}"
                logger.warning("Photo generation failed", extra={"asset_id": asset["id"], "reason": exc.reason})
                rec = ImageCallEntity(
                    id=uuid.uuid4(),
                    generation_id=generation_id,
                    draft_id=draft_id,
                    node_run_id=node_run_id,
                    asset_id=asset["id"],
                    model=model,
                    status="failed",
                    error=str(exc.reason),
                    duration_ms=0,
                    cost_usd=0.0,
                )
                if span and span.enabled:
                    span.end(outputs={"status": "failed", "error": exc.reason})
                return False, rec, reason

    if semaphore is not None:
        async with semaphore:
            return await _call()
    return await _call()
