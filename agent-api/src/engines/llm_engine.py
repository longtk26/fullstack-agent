"""A draft engine on top of an LLM provider (Stories 24.1, 24.2): one-turn JSON drafting on `agy` or `claude`.

Drafting talks to engines (`ICodeEngine.run`); this adapter makes any `LlmProvider` one: the inline prompt (every input
in the prompt, `inline_inputs`), the request's answer schema as structured output, the schema checked in code with one
round of its errors (`LlmProvider.json`), then the same envelope handling as the Gemini API engine
(`engines/envelope.py`). It drafts only (`drafts_only`): a code purpose is refused, code stays on the CLI engines.
"""

import time
from datetime import UTC, datetime
from pathlib import Path

from .envelope import apply_envelope
from .gemini_api.engine import DRAFT_PURPOSES
from .llm import LlmError, LlmProvider
from .port import (
    EngineContext,
    EngineErrorReason,
    EngineEvent,
    EngineEventKind,
    EngineHealth,
    EngineRequest,
    EngineResult,
    EngineStatus,
    EngineUsage,
    ICodeEngine,
    ModelCall,
    OnEngineEvent,
    ToolCall,
)
from .workspace import ensure_inside


class LlmDraftEngine(ICodeEngine):
    drafts_only = True
    inline_inputs = True
    drafts = True

    def __init__(self, name: str, provider: LlmProvider, allowed_root: Path):
        self.name = name
        self.provider = provider
        self.allowed_root = allowed_root

    async def health(self) -> EngineHealth:
        health = await self.provider.health()
        return health.model_copy(update={"name": self.name, "drafts_only": True, "drafts": True})

    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        return None  # inputs travel in the prompt

    async def cancel(self, invocation_id: str) -> bool:
        return await self.provider.cancel(invocation_id)

    async def run(self, request: EngineRequest, on_event: OnEngineEvent | None = None) -> EngineResult:
        workdir = ensure_inside(request.workdir, self.allowed_root)
        state_dir = ensure_inside(request.state_dir, self.allowed_root)
        started = time.monotonic()

        async def emit(kind: EngineEventKind, summary: str, **data) -> None:
            if on_event is not None:
                await on_event(EngineEvent(kind=kind, summary=summary, data=data))

        def finish(status, reason=None, message=None, calls=None, changed=None, final=None, structured=None):
            calls = calls or []
            return EngineResult(
                invocation_id=request.invocation_id,
                engine=self.name,
                purpose=request.purpose,
                status=status,
                error_reason=reason,
                error_message=message,
                duration_ms=int((time.monotonic() - started) * 1000),
                turns=len(calls),
                usage=_usage(calls),
                final_message=final,
                changed_files=changed or [],
                prompt_ref=request.prompt_ref,
                model_calls=calls,
                structured=structured,
            )

        if request.purpose not in DRAFT_PURPOSES:
            message = f"{self.name} drafts specs only; '{request.purpose}' needs a code engine"
            return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, message)
        await emit(
            EngineEventKind.SYSTEM, f"one {self.provider.name} turn", structured=request.response_schema is not None
        )
        try:
            answer = await self.provider.json(
                request.purpose,
                request.prompt,
                request.response_schema,
                state_dir=state_dir,
                invocation_id=request.invocation_id,
                timeout_s=request.timeout_s,
                model=request.model,
            )
        except LlmError as exc:
            return finish(exc.status, exc.reason, str(exc), exc.calls)
        for note in answer.notes:
            await emit(EngineEventKind.ERROR, note)
        changed, problems = apply_envelope(workdir, answer.data)
        if answer.calls:
            for relative in changed:
                answer.calls[-1].tools.append(ToolCall(name="Write", target=relative, started_at=datetime.now(UTC)))
        for relative in changed:
            await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
        message = str(answer.data.get("message") or "")
        if problems:
            message = (message + "\n" if message else "") + "Not applied: " + "; ".join(problems)
        await emit(EngineEventKind.MESSAGE, message or "done")
        if not changed and problems:
            return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, message, answer.calls, final=message)
        return finish(EngineStatus.OK, calls=answer.calls, changed=changed, final=message, structured=answer.structured)


def _usage(calls: list[ModelCall]) -> EngineUsage | None:
    if not calls:
        return None
    priced = [call.cost_usd for call in calls if call.cost_usd is not None]
    sources = {call.cost_source for call in calls if call.cost_source}
    return EngineUsage(
        input_tokens=sum(call.input_tokens for call in calls),
        output_tokens=sum(call.output_tokens for call in calls),
        cache_read_tokens=sum(call.cache_read_tokens for call in calls),
        cache_write_tokens=sum(call.cache_write_tokens for call in calls),
        thinking_tokens=sum(call.thinking_tokens or 0 for call in calls),
        cost_usd=round(sum(priced), 6) if len(priced) == len(calls) else None,
        cost_source=(sources.pop() if len(sources) == 1 else "estimated") if len(priced) == len(calls) else None,
        model=calls[-1].model,
    )
