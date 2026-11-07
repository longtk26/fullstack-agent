"""The business layer at draft time (Stories 26.1–26.3): discovery, expectations, binding; one provider turn each.

`discover` answers what the business is (values, actors, workflows with branches, scope) and asks once more when a
value has no step that delivers it; `expect` freezes what must be true at every step of the core workflows, before
anything is generated (Epic 26 D2); `bind` translates the business words into the drafted app's terms (roles,
operations, pages, status values), checked by code (`binding.check_binding`). Every call goes through the LLM
provider (Epic 24) and is recorded like a draft's engine calls (`usage_record`).
"""

import json
from pathlib import Path
from typing import Any

from src.engines import PromptLibrary
from src.engines.llm import LlmAnswer, LlmProvider

from .binding import check_binding, compact_operations, compact_pages, demo_roles
from .model import (
    BIND_SCHEMA,
    BUSINESS_SCHEMA,
    EXPECT_SCHEMA,
    MAX_WORKFLOWS,
    core,
    paths,
    undelivered,
)


def usage_record(provider: LlmProvider, prompt_ref, answer: LlmAnswer, purpose: str) -> dict[str, Any]:
    """A provider call in the shape of a draft's engine call record (`drafting/drafts.usage_record`)."""
    priced = [call.cost_usd for call in answer.calls if call.cost_usd is not None]
    sources = {call.cost_source for call in answer.calls if call.cost_source}
    return {
        "purpose": purpose,
        "engine": provider.name,
        "prompt": f"{prompt_ref.id}@{prompt_ref.version}",
        "promptSha256": prompt_ref.sha256,
        "status": "ok",
        "durationMs": answer.duration_ms,
        "turns": len(answer.calls),
        "model": answer.model,
        "inputTokens": sum(call.input_tokens for call in answer.calls),
        "outputTokens": sum(call.output_tokens for call in answer.calls),
        "cacheReadTokens": sum(call.cache_read_tokens for call in answer.calls),
        "cacheWriteTokens": sum(call.cache_write_tokens for call in answer.calls),
        "costUsd": round(sum(priced), 6) if answer.calls and len(priced) == len(answer.calls) else None,
        "costSource": sources.pop() if len(sources) == 1 else None,
        "modelCalls": len(answer.calls),
        **({"structured": answer.structured} if answer.structured is not None else {}),
    }


class BusinessFlow:
    def __init__(self, provider: LlmProvider, prompts: PromptLibrary, state_dir: Path):
        self.provider = provider
        self.prompts = prompts
        self.state_dir = state_dir
        self.calls: list[dict[str, Any]] = []

    async def _ask(self, purpose: str, prompt_id: str, schema: dict[str, Any], **context: Any) -> dict[str, Any]:
        rendered = self.prompts.render(prompt_id, "v1", **context)
        answer = await self.provider.json(purpose, rendered.text, schema, state_dir=self.state_dir)
        self.calls.append(usage_record(self.provider, rendered.ref, answer, purpose))
        return answer.data

    async def discover(self, requirement: str) -> dict[str, Any]:
        """26.1: the business; a second ask when a value has no step that delivers it."""
        context = {"requirement": requirement, "max_workflows": MAX_WORKFLOWS, "missing": [], "previous": ""}
        business = await self._ask("discover_workflows", "discover_workflows", BUSINESS_SCHEMA, **context)
        missing = undelivered(business)
        if missing:
            values = [v for v in business.get("values") or [] if v.get("id") in missing]
            context |= {"missing": json.dumps(values, ensure_ascii=False), "previous": json.dumps(business, indent=1)}
            business = await self._ask("rediscover_workflows", "discover_workflows", BUSINESS_SCHEMA, **context)
        return normalize_business(business)

    async def expect(self, requirement: str, business: dict[str, Any]) -> dict[str, Any]:
        """26.2: what must be true at every step of every core path, in business words (frozen)."""
        walks = [
            {"workflow": w["id"], "name": w.get("name"), "outcome": w.get("outcome"),
             "paths": [{"path": path, "steps": steps} for path, steps in paths(w)]}
            for w in core(business)
        ]  # fmt: skip
        actors = [{"id": a["id"], "name": a.get("name"), "signsIn": a.get("signsIn")} for a in business["actors"]]
        expected = await self._ask(
            "expect_workflows",
            "expect_workflows",
            EXPECT_SCHEMA,
            requirement=requirement,
            actors=json.dumps(actors, indent=1, ensure_ascii=False),
            walks=json.dumps(walks, indent=1, ensure_ascii=False),
        )
        return normalize_expected(business, expected)

    async def bind(
        self,
        business: dict[str, Any],
        expected: dict[str, Any],
        backend_spec: dict[str, Any],
        contract: dict[str, Any],
        frontend_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """26.3: the business words in the app's terms, checked by code (`problems`)."""
        operations = compact_operations(contract)
        pages = compact_pages(frontend_spec)
        roles = demo_roles(backend_spec)
        actors = [
            {"id": a["id"], "name": a.get("name"), "description": a.get("description")} for a in business["actors"]
        ]
        rules = [
            {"workflow": w["id"], "path": path,
             "steps": [{k: s.get(k) for k in ("id", "actor", "action", "statusAfter", "rule")} for s in steps]}
            for w in core(business) for path, steps in paths(w)
        ]  # fmt: skip
        binding = await self._ask(
            "bind_workflows",
            "bind_workflows",
            BIND_SCHEMA,
            roles=json.dumps(roles),
            actors=json.dumps(actors, indent=1, ensure_ascii=False),
            rules=json.dumps(rules, indent=1, ensure_ascii=False),
            expected=json.dumps(expected.get("paths") or [], indent=1, ensure_ascii=False),
            operations=json.dumps(operations, indent=1, ensure_ascii=False),
            pages=json.dumps(pages, indent=1, ensure_ascii=False),
        )
        binding["problems"] = check_binding(binding, operations, pages, roles, business)
        binding["roles"] = roles
        return binding


def normalize_business(business: dict[str, Any]) -> dict[str, Any]:
    """At least one core workflow (the POC demonstrates the most valuable one) and a golden path among them."""
    workflows = business.get("workflows") or []
    if workflows and not core(business):
        workflows[0]["priority"] = "core"
    ids = [w["id"] for w in core(business)]
    scope = business.setdefault("scope", {"goldenPath": "", "included": [], "excluded": []})
    if ids and scope.get("goldenPath") not in ids:
        scope["goldenPath"] = ids[0]
    missing = undelivered(business)
    business["notes"] = [f"no step delivers the value '{value}'" for value in missing]
    return business


def normalize_expected(business: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """26.2: never a `refusedBefore` on the step that creates the record (the record does not exist yet)."""
    notes = []
    for path in expected.get("paths") or []:
        for index, line in enumerate(path.get("steps") or []):
            first = index == 0
            if (line.get("refusedBefore") or []) and first:
                notes.append(f"{path.get('workflow')}/{line.get('step')}: no refusal before the record exists")
                line["refusedBefore"] = []
    expected["notes"] = notes
    return expected
