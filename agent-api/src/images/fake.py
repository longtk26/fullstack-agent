"""Fake image generator for testing and demos (Story 19.2).

Listed in docs/development/test-doubles.md.
"""

import hashlib
import io
import time

from PIL import Image

from .port import GeneratedImage, IImageGenerator, ImageBlocked, ImageFailed


class FakeImageGenerator(IImageGenerator):
    """Deterministic, local test double. Never calls external APIs."""

    def __init__(self, model: str = "fake-image"):
        self.model = model

    async def generate(self, prompt: str, aspect_ratio: str) -> GeneratedImage:
        started = time.monotonic()
        lower = prompt.lower()
        if "blocked" in lower or "refuse" in lower:
            raise ImageBlocked(f"Fake refusal for prompt: {prompt[:60]}")
        if "fail" in lower or "error" in lower:
            raise ImageFailed(f"Fake error for prompt: {prompt[:60]}")

        # Derive a deterministic RGB color from the prompt hash
        h = hashlib.sha256(prompt.encode()).digest()
        color = (h[0], h[1], h[2])

        # Width and height based on aspect ratio
        aspect_dims = {
            "16:9": (320, 180),
            "4:3": (320, 240),
            "1:1": (256, 256),
            "3:4": (240, 320),
            "21:9": (420, 180),
        }
        w, h_dim = aspect_dims.get(aspect_ratio, (320, 180))

        img = Image.new("RGB", (w, h_dim), color=color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        duration_ms = int((time.monotonic() - started) * 1000)

        return GeneratedImage(
            data=buf.getvalue(),
            mime="image/png",
            model=self.model,
            duration_ms=max(1, duration_ms),
            cost_usd=0.0,
        )
