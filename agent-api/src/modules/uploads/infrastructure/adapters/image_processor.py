"""Uploaded images (Story 15.4): the type comes from the content, never the file name.

PNG, JPEG and WebP are decoded and re-encoded with Pillow, which drops their metadata (EXIF, GPS, comments) after
applying the camera orientation, and shrinks them to `MAX_SIDE` pixels on the longest side. SVGs must pass the same
safety rules as drawn assets (orchestrator/svg_assets.py) except the theme-colour rule, and are kept as uploaded.
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from src.orchestrator.svg_assets import SvgIssue, check_svg, parse_svg

MAX_SIDE = 2_560
MAX_PIXELS = 50_000_000  # Pillow's decompression-bomb guard, below its own default
RASTER_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}


class UploadRejected(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason  # type | unsafe


@dataclass
class ProcessedImage:
    content: bytes
    mime: str
    width: int | None
    height: int | None


def sniff(data: bytes) -> str | None:
    """The image type from the first bytes (or the XML root), or None."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    try:
        text = data.decode("utf-8-sig").lstrip()
    except UnicodeDecodeError:
        return None
    if not text.startswith("<"):
        return None
    root = parse_svg(text)
    if isinstance(root, SvgIssue):
        return "image/svg+xml" if root.rule == "safe" and "<svg" in text[:2000] else None
    return "image/svg+xml" if root.tag.rsplit("}", 1)[-1] == "svg" else None


def _svg_size(text: str) -> tuple[int | None, int | None]:
    root = parse_svg(text)
    view_box = None if isinstance(root, SvgIssue) else root.get("viewBox")
    try:
        _, _, width, height = (float(part) for part in (view_box or "").replace(",", " ").split())
        return round(width), round(height)
    except ValueError:
        return None, None


def process(data: bytes) -> ProcessedImage:
    mime = sniff(data)
    if mime is None:
        raise UploadRejected("type", "Not a PNG, JPEG, WebP or SVG image")
    if mime == "image/svg+xml":
        text = data.decode("utf-8-sig")
        issues = [issue for issue in check_svg(text, None, theme=False)]
        if issues:
            raise UploadRejected("unsafe", "; ".join(f"{issue.rule}: {issue.message}" for issue in issues[:5]))
        width, height = _svg_size(text)
        return ProcessedImage(content=data, mime=mime, width=width, height=height)
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            if mime == "image/jpeg" and image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            out = io.BytesIO()
            # A fresh encode carries no EXIF / GPS / XMP / comments: nothing is passed on from the original.
            image.save(out, format=RASTER_FORMATS[mime], **({"quality": 88} if mime != "image/png" else {}))
            return ProcessedImage(content=out.getvalue(), mime=mime, width=image.width, height=image.height)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise UploadRejected("type", f"The image cannot be read: {exc}") from exc
