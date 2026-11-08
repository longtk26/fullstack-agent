"""Image generator factory from application settings (Story 19.2)."""

from src.configs import config

from .fake import FakeImageGenerator
from .gemini import GeminiImageGenerator
from .port import IImageGenerator
from .unsplash import UnsplashPhotos


def get_image_generator() -> IImageGenerator | None:
    """None when photos are off: IMAGE_PROVIDER=none, or gemini without GEMINI_IMAGE_API_KEY (paid calls are
    opt-in; GEMINI_API_KEY, the Antigravity key, is never used for photos)."""
    provider = getattr(config, "image_provider", "gemini")
    if provider in ("none", "unsplash"):  # Unsplash finds photos, it does not draw them (`get_stock_photos`)
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


def get_stock_photos() -> UnsplashPhotos | None:
    """Epic 27: Unsplash when IMAGE_PROVIDER=unsplash and UNSPLASH_ACCESS_KEY is set; None otherwise."""
    if getattr(config, "image_provider", "gemini") != "unsplash" or not getattr(config, "unsplash_access_key", None):
        return None
    from .cache import photo_cache_dir

    return UnsplashPhotos(
        access_key=config.unsplash_access_key,
        app_name=config.unsplash_app_name,
        cache_dir=photo_cache_dir().parent / "stock",
        timeout=float(getattr(config, "image_timeout_seconds", 60)),
    )


def photos_enabled() -> bool:
    return get_image_generator() is not None or get_stock_photos() is not None
