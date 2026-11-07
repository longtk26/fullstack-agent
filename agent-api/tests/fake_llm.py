"""TESTING ONLY (docs/development/test-doubles.md): an LLM provider that answers without a model (Epic 24). Tests
pass it where the product takes an `LlmProvider` (e.g. `DraftRunner(llm_provider=...)`); nothing in `src/` imports it.

Each step has a responder `(prompt, schema) -> dict`; steps without one get the smallest object the schema allows
(`skeleton`). Epic 26's fake answers (discovery, expectations, binding) register here (`tests/business_fakes.py`).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.engines.llm import Image, LlmAnswer, LlmProvider
from src.engines.port import EngineHealth, ModelCall

Responder = Callable[[str, dict[str, Any] | None], Any]
RESPONDERS: dict[str, Responder] = {}


def responder(step: str) -> Callable[[Responder], Responder]:
    def register(function: Responder) -> Responder:
        RESPONDERS[step] = function
        return function

    return register


def skeleton(schema: dict[str, Any] | None, root: dict[str, Any] | None = None) -> Any:
    """The smallest value that satisfies the schema's types, required properties, enums and minItems."""
    if not schema:
        return {}
    root = root or schema
    if "$ref" in schema:
        target: Any = root
        for part in str(schema["$ref"])[2:].split("/"):
            target = target.get(part, {}) if isinstance(target, dict) else {}
        return skeleton(target, root)
    if schema.get("anyOf"):
        return skeleton(schema["anyOf"][0], root)
    if schema.get("enum"):
        return schema["enum"][0]
    kind = schema.get("type")
    kind = kind[0] if isinstance(kind, list) else kind
    if kind == "object" or (kind is None and "properties" in schema):
        properties = schema.get("properties") or {}
        return {name: skeleton(properties.get(name, {}), root) for name in schema.get("required") or []}
    if kind == "array":
        return [skeleton(schema.get("items") or {}, root) for _ in range(int(schema.get("minItems") or 0))]
    return {"string": "", "integer": 0, "number": 0, "boolean": False, "null": None}.get(kind or "", None)


class FakeLlmProvider(LlmProvider):
    name = "fake"
    model = "fake"

    def __init__(self, responders: dict[str, Responder] | None = None):
        self.responders = responders
        self.calls: list[dict[str, Any]] = []  # what each step was asked (tests read it)

    async def health(self) -> EngineHealth:
        return EngineHealth(name="fake", available=True, reason="Test double", drafts=True)

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
        self.calls.append({"step": step, "prompt": prompt, "schema": schema, "images": len(images or [])})
        table = self.responders if self.responders is not None else RESPONDERS
        function = table.get(step)
        data = function(prompt, schema) if function is not None else skeleton(schema)
        now = datetime.now(UTC)
        call = ModelCall(
            seq=1,
            model="fake",
            input_tokens=len(prompt) // 4,
            output_tokens=10,
            started_at=now,
            ended_at=now,
            cost_usd=0.0,
            cost_source="reported",
        )
        return LlmAnswer(data=data, text="", calls=[call], structured=None if schema is None else True)
