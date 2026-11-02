"""Service functions for generating and post-processing photos (Stories 19.2, 19.3)."""

import asyncio
import hashlib
import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from src.configs import config, get_logger
from src.modules.shared.domain.entities import ImageCallEntity
from src.orchestrator import tracing

from .cache import photo_cache_key, photo_cache_path
from .factory import get_image_generator
from .port import GeneratedImage, IImageGenerator, ImageBlocked, ImageFailed
from .post_process import post_process_photo
from .prompt import build_photo_prompt

logger = get_logger(__name__)


_UNSET = object()


def _write_atomic(path: Path, data: bytes) -> None:
    """Writes through a temp file in the same directory, so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_cached(cache_file: Path) -> tuple[bytes, int, int] | None:
    """A cached photo's bytes and size; None when missing or unreadable (a miss, remade and rewritten)."""
    if not cache_file.is_file():
        return None
    try:
        data = cache_file.read_bytes()
        with Image.open(io.BytesIO(data)) as im:
            im.load()  # decodes it all, so a truncated file fails here
            w, h = im.size
    except Exception as exc:
        logger.warning("Unreadable cached photo, remaking it", extra={"file": str(cache_file), "error": str(exc)})
        return None
    return data, w, h


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
    use_cache: bool = True,
) -> tuple[bool, ImageCallEntity, str | None]:
    """Generates one photo, applying cache, prompt formatting, semaphore, and WebP post-processing.
    Returns (success, image_call_record, fallback_reason); never raises for a bad or unreadable image.
    `use_cache=False` (regenerate) skips the cache read but still writes the new photo to it.
    """
    raw_prompt = custom_prompt or asset.get("prompt") or asset.get("alt") or asset["id"]
    raw_style = custom_style if custom_style is not None else asset.get("style")
    prompt_text = build_photo_prompt(raw_prompt, raw_style, kind=asset.get("kind", "image"))
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

    # 1. Cache hit (an unreadable or partial entry is a miss)
    cached = _read_cached(cache_file) if use_cache else None
    if cached is not None:
        data, w, h = cached
        try:
            _write_atomic(target_path, data)
        except OSError as exc:
            logger.warning("Could not copy a cached photo", extra={"asset_id": asset["id"], "error": str(exc)})
            cached = None
    if cached is not None:
        sha = hashlib.sha256(data).hexdigest()
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
            gen_result: GeneratedImage | None = None
            try:
                gen_result = await generator.generate(prompt_text, aspect_ratio)
                webp_bytes, w, h = post_process_photo(gen_result.data, aspect_ratio)

                _write_atomic(cache_file, webp_bytes)
                _write_atomic(target_path, webp_bytes)

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

            except Exception as exc:
                # An undecodable or truncated image (Pillow), a decompression bomb or a disk error: this asset
                # fails, the others carry on. A call that returned an image was paid for, so its cost is kept.
                error = f"{type(exc).__name__}: {exc}"[:500]
                reason = f"failed: {error}"
                logger.warning("Photo could not be processed", extra={"asset_id": asset["id"], "error": error})
                rec = ImageCallEntity(
                    id=uuid.uuid4(),
                    generation_id=generation_id,
                    draft_id=draft_id,
                    node_run_id=node_run_id,
                    asset_id=asset["id"],
                    model=gen_result.model if gen_result is not None else model,
                    status="failed",
                    error=error,
                    duration_ms=gen_result.duration_ms if gen_result is not None else 0,
                    cost_usd=gen_result.cost_usd if gen_result is not None else 0.0,
                )
                if span and span.enabled:
                    span.end(outputs={"status": "failed", "error": error})
                return False, rec, reason

    if semaphore is not None:
        async with semaphore:
            return await _call()
    return await _call()
