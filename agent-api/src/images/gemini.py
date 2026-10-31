"""Gemini image generation adapter using generativelanguage interactions API (Story 19.2)."""

import asyncio
import base64
import time
from typing import Any

import httpx

from src.configs import get_logger

from .port import GeneratedImage, IImageGenerator, ImageBlocked, ImageFailed

logger = get_logger(__name__)

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


class GeminiImageGenerator(IImageGenerator):
    """Generates photos via Google Generative Language interactions endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.1-flash-lite-image",
        size: str = "1K",
        price_usd: float = 0.0336,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.model = model
        self.size = size
        self.price_usd = price_usd
        self.timeout = timeout

    def _redact(self, text: str) -> str:
        if self.api_key and self.api_key in text:
            return text.replace(self.api_key, "[REDACTED]")
        return text

    async def generate(self, prompt: str, aspect_ratio: str) -> GeneratedImage:
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "response_format": {
                "type": "image",
                "mime_type": "image/jpeg",
                "aspect_ratio": aspect_ratio,
                "image_size": self.size,
            },
        }

        started = time.monotonic()
        max_attempts = 2

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(INTERACTIONS_URL, headers=headers, json=body)

                if resp.status_code == 200:
                    data = resp.json()
                    duration_ms = int((time.monotonic() - started) * 1000)
                    return self._parse_success(data, duration_ms)

                # Refusal or safety block on 400
                if resp.status_code == 400:
                    err_text = self._redact(resp.text)
                    if any(term in err_text.lower() for term in ("safety", "policy", "block", "filter")):
                        raise ImageBlocked(f"Image blocked by policy: {err_text[:300]}")
                    raise ImageFailed(f"Gemini image API bad request (400): {err_text[:300]}")

                # Retry on 429 or 5xx once
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                    await asyncio.sleep(1.0)
                    continue

                err_text = self._redact(resp.text)
                raise ImageFailed(f"Gemini image API error ({resp.status_code}): {err_text[:300]}")

            except httpx.TimeoutException as exc:
                if attempt < max_attempts:
                    await asyncio.sleep(1.0)
                    continue
                raise ImageFailed(
                    f"Gemini image API timed out after {self.timeout}s: {self._redact(str(exc))}"
                ) from exc
            except (ImageBlocked, ImageFailed):
                raise
            except Exception as exc:
                if attempt < max_attempts:
                    await asyncio.sleep(1.0)
                    continue
                raise ImageFailed(f"Gemini image API request failed: {self._redact(str(exc))}") from exc

        raise ImageFailed("Gemini image generation failed after retries")

    def _parse_success(self, data: dict[str, Any], duration_ms: int) -> GeneratedImage:
        steps = data.get("steps", [])
        image_bytes: bytes | None = None
        refusal_reason: str | None = None

        for step in steps:
            if step.get("type") == "model_output":
                for item in step.get("content", []):
                    item_type = item.get("type")
                    if item_type == "image" and item.get("data"):
                        try:
                            image_bytes = base64.b64decode(item["data"])
                        except Exception as e:
                            raise ImageFailed(f"Failed to decode base64 image data: {e}") from e
                    elif item_type == "text" and item.get("text"):
                        refusal_reason = item["text"]

        if image_bytes is not None:
            return GeneratedImage(
                data=image_bytes,
                mime="image/jpeg",
                model=self.model,
                duration_ms=max(1, duration_ms),
                cost_usd=self.price_usd,
            )

        if refusal_reason:
            raise ImageBlocked(f"Image generation refused: {refusal_reason}")

        raise ImageFailed("No image data or refusal message returned by Gemini API")
