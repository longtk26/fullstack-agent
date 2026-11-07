"""One LLM provider for every LLM-only step (Epic 24, Stories 24.1 and 24.2).

An LLM-only step needs one answer from a model and nothing else: no files, no tools, no agent loop. Spec drafting and
its repairs, and Epic 26's workflow discovery, expectations, binding, screen judging and summary are such steps.
`LlmProvider.json(step, prompt, schema, images)` asks once and returns the parsed JSON object. Every provider sends
the schema as structured output (Gemini's `responseJsonSchema`, `agy` / `claude` `--json-schema`) and the answer is
checked against it in code as well (Epic 24 D3, `libs/json_schema_check.py`).

Providers: `gemini_api` (`engines/gemini_api/llm.py`), `antigravity` and `claude_code` (one CLI turn,
`engines/json_cli.py`), and the test-only `fake` (`engines/fake_llm.py`). `LLM_PROVIDER` picks one for every step.
"""

import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.libs.json_schema_check import schema_errors

from .port import EngineErrorReason, EngineHealth, EngineStatus, ModelCall

LLM_PROVIDERS = ("antigravity", "claude_code", "gemini_api", "fake")
# The draft engine that runs a provider's one-turn JSON mode (the registry's names).
DRAFT_ENGINE_OF = {
    "antigravity": "antigravity_json",
    "claude_code": "claude_code_json",
    "gemini_api": "gemini_api",
    "fake": "fake",
}
SCHEMA_RETRY = (
    "Your previous answer did not follow the required JSON shape:\n{errors}\n"
    "Answer again with the whole JSON object, fixing exactly these problems."
)
_FENCE = re.compile(r"^```[a-zA-Z0-9]*\s*\n(.*?)\n```\s*$", re.S)


class LlmError(Exception):
    """A step that got no usable answer: the reason and status follow the engines' (`EngineErrorReason`)."""

    def __init__(
        self,
        message: str,
        reason: EngineErrorReason = EngineErrorReason.CRASH,
        status: EngineStatus = EngineStatus.CLI_ERROR,
        calls: list[ModelCall] | None = None,
        text: str = "",
    ):
        super().__init__(message)
        self.reason = reason
        self.status = status
        self.calls = calls or []
        self.text = text


@dataclass
class LlmAnswer:
    data: Any
    text: str
    calls: list[ModelCall] = field(default_factory=list)
    # None: no schema asked; False: the provider refused the schema and the answer came without it
    structured: bool | None = None
    duration_ms: int = 0
    session_id: str | None = None
    notes: list[str] = field(default_factory=list)  # e.g. "the model tried a tool"

    @property
    def model(self) -> str | None:
        return next((call.model for call in reversed(self.calls) if call.model), None)


@dataclass
class Image:
    """An image an LLM step looks at (Epic 26's screen judging): bytes and their media type."""

    data: bytes
    media_type: str = "image/png"
    name: str = "image.png"


class LlmProvider(ABC):
    name: str
    model: str | None = None

    @abstractmethod
    async def health(self) -> EngineHealth:
        pass

    @abstractmethod
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
        """One model turn. Raises LlmError when there is no JSON object to return."""

    async def cancel(self, invocation_id: str) -> bool:
        return False

    async def json(
        self,
        step: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        images: list[Image] | None = None,
        *,
        state_dir: Path,
        invocation_id: str | None = None,
        timeout_s: float | None = None,
        model: str | None = None,
        schema_retry: bool = True,
    ) -> LlmAnswer:
        """Asks once; an answer of the wrong shape is asked again once with its errors (Epic 24 D3)."""
        invocation_id = invocation_id or uuid.uuid4().hex
        kwargs = {"state_dir": state_dir, "timeout_s": timeout_s, "model": model}
        first = await self.answer(step, prompt, schema, images, invocation_id=invocation_id, **kwargs)
        errors = schema_errors(first.data, schema)
        if not errors:
            return first
        if not schema_retry:
            raise LlmError(_errors_message(errors), calls=first.calls, text=first.text)
        retry_prompt = f"{prompt}\n\n{SCHEMA_RETRY.format(errors=_bullets(errors))}"
        second = await self.answer(step, retry_prompt, schema, images, invocation_id=f"{invocation_id}-r", **kwargs)
        second.calls = [*first.calls, *_renumbered(second.calls, len(first.calls))]
        second.duration_ms += first.duration_ms
        second.notes = [*first.notes, f"schema errors asked again: {len(errors)}", *second.notes]
        errors = schema_errors(second.data, schema)
        if errors:
            raise LlmError(_errors_message(errors), calls=second.calls, text=second.text)
        return second


def parse_json_object(text: str) -> dict[str, Any]:
    """The JSON object in a model's text: as is, inside a code fence, or the outermost `{…}`."""
    text = (text or "").strip()
    candidates = [text]
    fenced = _FENCE.match(text)
    if fenced:
        candidates.append(fenced.group(1))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start : end + 1])
    error: Exception | None = None
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except ValueError as exc:
            error = error or exc
            continue
        if isinstance(value, dict):
            return value
        error = ValueError("the answer is not a JSON object")
    raise ValueError(str(error or "no JSON object in the answer"))


def _bullets(errors: list[str]) -> str:
    return "\n".join(f"- {error}" for error in errors)


def _errors_message(errors: list[str]) -> str:
    return "the answer does not follow the schema: " + "; ".join(errors[:5])


def _renumbered(calls: list[ModelCall], offset: int) -> list[ModelCall]:
    return [call.model_copy(update={"seq": call.seq + offset}) for call in calls]
