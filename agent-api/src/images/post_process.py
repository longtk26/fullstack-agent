"""Post-processing for generated photos (Story 19.2)."""

import io

from PIL import Image, ImageOps

MAX_SIDE = 1600
MAX_PIXELS = 50_000_000
PHOTO_QUALITY = 80

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "16:9": (16, 9),
    "4:3": (4, 3),
    "1:1": (1, 1),
    "3:4": (3, 4),
    "21:9": (21, 9),
}


def post_process_photo(raw_bytes: bytes, target_aspect: str = "16:9") -> tuple[bytes, int, int]:
    """Decodes image with Pillow, strips metadata, crops to exact aspect ratio if needed,
    scales to at most 1600 px on the long side, and encodes as WebP (quality 80).
    Returns (webp_bytes, width, height).
    """
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    with Image.open(io.BytesIO(raw_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        w, h = img.size

        # Crop to target aspect ratio if needed
        if target_aspect in ASPECT_RATIOS:
            ratio_w, ratio_h = ASPECT_RATIOS[target_aspect]
            target_ratio = ratio_w / ratio_h
            current_ratio = w / h
            if abs(current_ratio - target_ratio) > 0.01:
                if current_ratio > target_ratio:
                    # Too wide: crop horizontal borders
                    new_w = max(1, int(round(h * target_ratio)))
                    left = (w - new_w) // 2
                    img = img.crop((left, 0, left + new_w, h))
                else:
                    # Too tall: crop vertical borders
                    new_h = max(1, int(round(w / target_ratio)))
                    top = (h - new_h) // 2
                    img = img.crop((0, top, w, top + new_h))
                w, h = img.size

        # Scale down if longest side > MAX_SIDE
        max_dim = max(w, h)
        if max_dim > MAX_SIDE:
            scale = MAX_SIDE / max_dim
            new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            w, h = img.size

        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=PHOTO_QUALITY, method=6)
        return buf.getvalue(), w, h
