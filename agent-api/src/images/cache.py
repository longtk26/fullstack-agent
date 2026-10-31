"""Photo disk caching (Story 19.2)."""

import hashlib
import json
from pathlib import Path

from src.configs import config

PHOTO_VERSION = "v1"


def photo_cache_key(model: str, prompt_text: str, aspect_ratio: str, size: str = "1K") -> str:
    """Canonical SHA-256 key for a photo."""
    canonical = {
        "version": PHOTO_VERSION,
        "model": model,
        "prompt": " ".join(prompt_text.split()),
        "aspectRatio": aspect_ratio,
        "size": size,
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


def photo_cache_dir() -> Path:
    return Path(config.artifact_root) / "asset-cache" / "photos"


def photo_cache_path(key: str) -> Path:
    return photo_cache_dir() / f"{key}.webp"
