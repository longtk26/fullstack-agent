"""The Gemini API as an LLM provider (Story 24.2): one `generateContent` request per step, the engine's request code."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ..llm import Image, LlmAnswer, LlmError, LlmProvider, parse_json_object
from ..port import EngineErrorReason, EngineHealth, EngineStatus, ModelCall
from .engine import MAX_ATTEMPTS, RETRY_STATUSES, GeminiApiEngine


class GeminiLlmProvider(LlmProvider):
    name = "gemini_api"

    def __init__(self, engine: GeminiApiEngine):
        self.engine = engine
        self.model = engine.model

    async def health(self) -> EngineHealth:
        return await self.engine.health()

    async def cancel(self, invocation_id: str) -> bool:
        return await self.engine.cancel(invocation_id)

    async def answer(
        self,
        step: str,
        prompt: str,
        schema: dict[str, Any] | None,
        images: list[Image] | None,
        *,
        state_dir: Path,
        invocation_id: str,
        timeout_s: float | None,
        model: str | None,
    ) -> LlmAnswer:
        engine = self.engine
        if not engine.api_key:
            raise LlmError("GEMINI_API_KEY is not set", EngineErrorReason.AUTH)
        model = model or engine.model
        timeout = timeout_s or engine.default_timeout_s
        started = datetime.now(UTC)
        calls: list[ModelCall] = []
        asked_schema = schema
        attempt = 0
        while True:
            attempt += 1
            call_started = datetime.now(UTC)
            try:
                response = await engine._post(invocation_id, model, prompt, timeout, schema, images)
            except httpx.TimeoutException as exc:
                raise LlmError(
                    f"no answer within {timeout:.0f} s", EngineErrorReason.TIMEOUT, EngineStatus.TIMEOUT
                ) from exc
            except httpx.HTTPError as exc:
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(engine.retry_backoff_s * attempt)
                    continue
                raise LlmError(f"request failed: {engine.redactor.redact(str(exc))}") from exc
            if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                await asyncio.sleep(engine.retry_backoff_s * attempt)
                continue
            if response.status_code == 429:
                raise LlmError("rate limited", EngineErrorReason.RATE_LIMIT)
            if response.status_code in (401, 403):
                raise LlmError(f"HTTP {response.status_code}", EngineErrorReason.AUTH)
            if response.status_code == 400 and schema is not None:
                schema = None  # the schema is past what structured output compiles: ask without it
                continue
            if response.status_code != 200:
                raise LlmError(f"HTTP {response.status_code}")
            data = response.json()
            calls.append(engine._model_call(len(calls) + 1, model, data, call_started))
            candidate = (data.get("candidates") or [{}])[0]
            finish = candidate.get("finishReason")
            blocked = (data.get("promptFeedback") or {}).get("blockReason")
            if blocked or finish in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"):
                raise LlmError(f"blocked: {blocked or finish}", calls=calls)
            if finish == "MAX_TOKENS":
                raise LlmError("answer truncated", EngineErrorReason.OUTPUT_LIMIT, EngineStatus.LIMIT_EXCEEDED, calls)
            text = engine._text(candidate)
            try:
                parsed = parse_json_object(text)
            except ValueError as exc:
                raise LlmError(f"answer was not JSON: {exc}", calls=calls, text=text[:500]) from exc
            return LlmAnswer(
                data=parsed,
                text=text,
                calls=calls,
                structured=None if asked_schema is None else schema is not None,
                duration_ms=int((datetime.now(UTC) - started).total_seconds() * 1000),
            )
