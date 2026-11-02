"""Image generator factory from application settings (Story 19.2)."""

from src.configs import config

from .fake import FakeImageGenerator
from .gemini import GeminiImageGenerator
from .port import IImageGenerator


def get_image_generator() -> IImageGenerator | None:
    """None when photos are off: IMAGE_PROVIDER=none, or gemini without GEMINI_IMAGE_API_KEY (paid calls are
    opt-in; GEMINI_API_KEY, the Antigravity key, is never used for photos)."""
    provider = getattr(config, "image_provider", "gemini")
    if provider == "none":
        return None
    if provider == "fake":
        return FakeImageGenerator()
    if provider == "gemini":
        key = getattr(config, "gemini_image_api_key", None)
        if not key:
            return None
        return GeminiImageGenerator(
            api_key=key,
            model=getattr(config, "gemini_image_model", "gemini-3.1-flash-lite-image"),
            size=getattr(config, "gemini_image_size", "1K"),
            price_usd=getattr(config, "gemini_image_price_usd", 0.0336),
            timeout=float(getattr(config, "image_timeout_seconds", 60)),
        )
    return None


def photos_enabled() -> bool:
    return get_image_generator() is not None
