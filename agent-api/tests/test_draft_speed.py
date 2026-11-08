"""A draft's speed (2026-11-08): `fast` runs every model call of the draft on the provider's fast model
(FAST_DRAFT_MODELS; a pet adoption draft took 85 s instead of 15.6 min on agy), `thorough` on its own model. The
request's `draftSpeed` wins over DRAFT_SPEED."""

import asyncio
import uuid

from src.configs import config
from src.engines.prompts import PromptLibrary
from src.modules.shared.domain.entities import SpecDraftEntity
from src.modules.shared.domain.enums import GenerationMode, SpecDraftStatus, SpecSource
from src.orchestrator.business.flow import BusinessFlow
from src.orchestrator.drafting.business import draft_model
from tests.fake_llm import FakeLlmProvider


def _draft(**inputs) -> SpecDraftEntity:
    return SpecDraftEntity(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        source=SpecSource.REQUIREMENT,
        mode=GenerationMode.DYNAMIC,
        requirement_text="A shelter's adoption applications.",
        engine="antigravity_json",
        status=SpecDraftStatus.PENDING,
        inputs=inputs,
    )


def test_a_fast_draft_uses_the_providers_fast_model(monkeypatch):
    monkeypatch.setattr(config, "draft_speed", "thorough")
    monkeypatch.setattr(config, "fast_draft_models", {"antigravity": "gemini-3.8-flash-low"})
    assert draft_model(_draft(draftSpeed="fast"), "antigravity_json") == "gemini-3.8-flash-low"
    assert draft_model(_draft(), "antigravity_json") is None, "thorough: the provider's own model"
    assert draft_model(_draft(draftSpeed="fast"), "claude_code_json") is None, "no fast model named for claude"
    assert draft_model(_draft(draftSpeed="fast", llmProvider="antigravity"), "gemini_api") == "gemini-3.8-flash-low"


def test_the_request_wins_over_the_servers_default(monkeypatch):
    monkeypatch.setattr(config, "draft_speed", "fast")
    monkeypatch.setattr(config, "fast_draft_models", {"antigravity": "gemini-3.8-flash-low"})
    assert draft_model(_draft(), "antigravity_json") == "gemini-3.8-flash-low"
    assert draft_model(_draft(draftSpeed="thorough"), "antigravity_json") is None


def test_the_workflow_calls_ask_for_the_fast_model(tmp_path):
    asked: list[str | None] = []

    class Recording(FakeLlmProvider):
        async def answer(self, step, prompt, schema, images, *, model, **kwargs):
            asked.append(model)
            return await super().answer(step, prompt, schema, images, model=model, **kwargs)

    flow = BusinessFlow(Recording(), PromptLibrary(), tmp_path, model="gemini-3.8-flash-low")
    asyncio.run(flow.discover("A shelter lists animals; people apply to adopt one; staff review applications."))
    assert asked and set(asked) == {"gemini-3.8-flash-low"}
