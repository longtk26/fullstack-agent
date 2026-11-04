"""Gemini API engine (Story 18.10): one `generateContent` request per step, no agent loop, no files, no tools.

Drafting a spec needs no workspace: the prompt carries every input (the engine says so with `inline_inputs`, and
`drafting.py` renders the inline prompt versions) and the model answers with one JSON **envelope**:

    {"files": {"frontend-spec.json": {...}, "notes.json": {...}},   # written whole (objects are dumped as JSON)
     "patches": {"backend-spec.json": [{"op": "replace", "path": "/…", "value": …}, …]},   # RFC 6902, applied
     "message": "what was done"}

Files land in the request's workdir, patches apply to the JSON files already there (a patch that does not apply is
reported in the message and skipped). The engine cannot write a project (`drafts_only`): a code purpose is refused.
Each attempt is one `ModelCall` priced with `pricing.py`; 429 and 5xx answers retry with backoff, an answer that is
not JSON is asked again once with the parse error, a truncated answer is `output_limit`, a safety block is `crash`.
"""

import asyncio
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from src.configs import get_logger
from src.libs.jsonpatch import PatchError, apply_patch
from src.libs.redaction import Redactor

from ..port import (
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
from ..pricing import Price, estimate
from ..workspace import ensure_inside

logger = get_logger(__name__)

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DRAFT_PURPOSES = frozenset({"draft_spec", "draft_frontend_spec", "repair_spec", "repair_direction", "draft_tree"})
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
HEALTH_CACHE_S = 600
NOT_JSON = (
    "Your previous answer was not valid JSON ({error}). Answer again with one JSON object only, no prose and no "
    'code fences: {{"files": {{...}}, "patches": {{...}}, "message": "..."}}.'
)


class GeminiApiEngine(ICodeEngine):
    name = "gemini_api"
    drafts_only = True
    inline_inputs = True

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        allowed_root: Path,
        redactor: Redactor,
        default_timeout_s: float = 600,
        max_output_tokens: int = 65536,
        thinking_budget: int | None = None,
        prices: Mapping[str, Price] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_backoff_s: float = 2.0,
        base_url: str = API_BASE,
    ):
        self.api_key = api_key
        self.model = model
        self.allowed_root = allowed_root
        self.redactor = redactor.with_secrets(api_key)
        self.default_timeout_s = default_timeout_s
        self.max_output_tokens = max_output_tokens
        self.thinking_budget = thinking_budget
        self.prices = prices
        # TESTING ONLY (docs/development/test-doubles.md): tests pass an httpx.MockTransport so no request leaves
        # the process; None = the network.
        self.transport = transport
        self.retry_backoff_s = retry_backoff_s
        self.base_url = base_url.rstrip("/")
        self._cancels: dict[str, asyncio.Event] = {}
        self._requests: dict[str, asyncio.Task[httpx.Response]] = {}
        self._health: tuple[float, EngineHealth] | None = None

    # -- health and workspace -------------------------------------------------------------------------------------

    async def health(self) -> EngineHealth:
        if not self.api_key:
            return EngineHealth(name=self.name, available=False, reason="Set GEMINI_API_KEY", drafts_only=True)
        if self._health is not None and time.monotonic() - self._health[0] < HEALTH_CACHE_S:
            return self._health[1]
        try:
            async with httpx.AsyncClient(timeout=15, transport=self.transport) as client:
                response = await client.get(f"{self.base_url}/models/{self.model}", headers=self._headers())
            if response.status_code == 200:
                health = EngineHealth(name=self.name, available=True, reason="Drafts only", drafts_only=True)
            else:
                reason = f"Gemini API answered {response.status_code} for model {self.model}"
                health = EngineHealth(name=self.name, available=False, reason=reason, drafts_only=True)
        except httpx.HTTPError as exc:
            reason = f"Gemini API unreachable: {self.redactor.redact(str(exc))[:200]}"
            health = EngineHealth(name=self.name, available=False, reason=reason, drafts_only=True)
        self._health = (time.monotonic(), health)
        return health

    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        return None  # nothing reads the workspace: inputs travel in the prompt

    async def cancel(self, invocation_id: str) -> bool:
        self._cancels.setdefault(invocation_id, asyncio.Event()).set()
        request = self._requests.get(invocation_id)
        if request is not None:
            request.cancel()
        return True

    # -- one step --------------------------------------------------------------------------------------------------

    async def run(self, request: EngineRequest, on_event: OnEngineEvent | None = None) -> EngineResult:
        workdir = ensure_inside(request.workdir, self.allowed_root)
        ensure_inside(request.state_dir, self.allowed_root)
        started = time.monotonic()
        calls: list[ModelCall] = []
        log = request.state_dir / "logs" / f"{request.invocation_id}.gemini_api.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)

        async def emit(kind: EngineEventKind, summary: str, **data: Any) -> None:
            if on_event is not None:
                await on_event(EngineEvent(kind=kind, summary=summary, data=data))

        def finish(
            status: EngineStatus,
            reason: EngineErrorReason | None = None,
            message: str | None = None,
            changed: list[str] | None = None,
            final: str | None = None,
        ) -> EngineResult:
            self._cancels.pop(request.invocation_id, None)
            self._requests.pop(request.invocation_id, None)
            return EngineResult(
                invocation_id=request.invocation_id,
                engine=self.name,
                purpose=request.purpose,
                status=status,
                error_reason=reason,
                error_message=self.redactor.redact(message) if message else None,
                duration_ms=int((time.monotonic() - started) * 1000),
                turns=len(calls),
                usage=self._usage(calls),
                final_message=final,
                changed_files=changed or [],
                stdout_ref=str(log),
                model_calls=calls,
            )

        if request.purpose not in DRAFT_PURPOSES:
            message = f"{self.name} drafts specs only; '{request.purpose}' needs a code engine"
            return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, message)
        if not self.api_key:
            return finish(EngineStatus.CLI_ERROR, EngineErrorReason.AUTH, "GEMINI_API_KEY is not set")

        cancel = self._cancels.setdefault(request.invocation_id, asyncio.Event())
        model = request.model or self.model
        timeout = request.timeout_s or self.default_timeout_s
        prompt = request.prompt
        await emit(EngineEventKind.SYSTEM, f"request to {model}", model=model)
        attempt, json_retries = 0, 0
        while True:
            attempt += 1
            if cancel.is_set():
                return finish(EngineStatus.CANCELLED, EngineErrorReason.CANCELLED, "cancelled")
            call_started = datetime.now(UTC)
            try:
                response = await self._post(request.invocation_id, model, prompt, timeout)
            except asyncio.CancelledError:
                if cancel.is_set():
                    return finish(EngineStatus.CANCELLED, EngineErrorReason.CANCELLED, "cancelled")
                raise
            except httpx.TimeoutException:
                self._log(log, {"attempt": attempt, "error": "timeout", "timeout_s": timeout})
                return finish(EngineStatus.TIMEOUT, EngineErrorReason.TIMEOUT, f"no answer within {timeout:.0f} s")
            except httpx.HTTPError as exc:
                self._log(log, {"attempt": attempt, "error": self.redactor.redact(str(exc))})
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(self.retry_backoff_s * attempt)
                    continue
                return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, f"request failed: {exc}")

            self._log(log, {"attempt": attempt, "status": response.status_code, "body": self._redacted(response)})
            if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                await emit(EngineEventKind.ERROR, f"HTTP {response.status_code}, retrying", attempt=attempt)
                await asyncio.sleep(self.retry_backoff_s * attempt)
                continue
            if response.status_code == 429:
                return finish(EngineStatus.CLI_ERROR, EngineErrorReason.RATE_LIMIT, "rate limited")
            if response.status_code in (401, 403):
                return finish(EngineStatus.CLI_ERROR, EngineErrorReason.AUTH, f"HTTP {response.status_code}")
            if response.status_code != 200:
                return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, f"HTTP {response.status_code}")

            data = response.json()
            call = self._model_call(len(calls) + 1, model, data, call_started)
            calls.append(call)
            await emit(EngineEventKind.USAGE, "usage", input=call.input_tokens, output=call.output_tokens)
            blocked = (data.get("promptFeedback") or {}).get("blockReason")
            candidate = (data.get("candidates") or [{}])[0]
            finish_reason = candidate.get("finishReason")
            if blocked or finish_reason in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"):
                return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, f"blocked: {blocked or finish_reason}")
            if finish_reason == "MAX_TOKENS":
                return finish(EngineStatus.LIMIT_EXCEEDED, EngineErrorReason.OUTPUT_LIMIT, "answer truncated")
            text = self._text(candidate)
            try:
                envelope = json.loads(text)
                if not isinstance(envelope, dict):
                    raise ValueError("the answer is not a JSON object")
            except ValueError as exc:
                if json_retries == 0 and attempt < MAX_ATTEMPTS + 1:
                    json_retries += 1
                    await emit(EngineEventKind.ERROR, "answer was not JSON, asking again", error=str(exc)[:200])
                    prompt = f"{request.prompt}\n\n{NOT_JSON.format(error=str(exc)[:200])}"
                    continue
                return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, f"answer was not JSON: {exc}")
            break

        changed, problems = self._apply(workdir, envelope)
        for relative in changed:
            await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
            calls[-1].tools.append(ToolCall(name="Write", target=relative, started_at=datetime.now(UTC)))
        message = str(envelope.get("message") or "")
        if problems:
            message = (message + "\n" if message else "") + "Not applied: " + "; ".join(problems)
        await emit(EngineEventKind.MESSAGE, message or "done")
        if not changed and problems:
            return finish(EngineStatus.CLI_ERROR, EngineErrorReason.CRASH, message, final=message)
        return finish(EngineStatus.OK, changed=changed, final=message)

    # -- helpers ---------------------------------------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key or "", "Content-Type": "application/json"}

    def _body(self, prompt: str) -> dict[str, Any]:
        generation: dict[str, Any] = {"responseMimeType": "application/json", "maxOutputTokens": self.max_output_tokens}
        if self.thinking_budget is not None:
            generation["thinkingConfig"] = {"thinkingBudget": self.thinking_budget}
        return {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": generation}

    async def _post(self, invocation_id: str, model: str, prompt: str, timeout: float) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(timeout=timeout, transport=self.transport) as client:
                url = f"{self.base_url}/models/{model}:generateContent"
                return await client.post(url, headers=self._headers(), json=self._body(prompt))

        task = asyncio.create_task(send())
        self._requests[invocation_id] = task
        try:
            return await task
        finally:
            self._requests.pop(invocation_id, None)

    @staticmethod
    def _text(candidate: dict[str, Any]) -> str:
        parts = (candidate.get("content") or {}).get("parts") or []
        return "".join(part.get("text", "") for part in parts if isinstance(part, dict) and not part.get("thought"))

    def _model_call(self, seq: int, model: str, data: dict[str, Any], started_at: datetime) -> ModelCall:
        usage = data.get("usageMetadata") or {}
        thinking = int(usage.get("thoughtsTokenCount") or 0)
        call = ModelCall(
            seq=seq,
            model=data.get("modelVersion") or model,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0) + thinking,
            cache_read_tokens=int(usage.get("cachedContentTokenCount") or 0),
            thinking_tokens=thinking,
            started_at=started_at,
            ended_at=datetime.now(UTC),
            latency_source="measured",
        )
        estimate([call], self.prices if self.prices is not None else _configured_prices())
        return call

    def _usage(self, calls: list[ModelCall]) -> EngineUsage | None:
        if not calls:
            return None
        priced = [call.cost_usd for call in calls if call.cost_usd is not None]
        return EngineUsage(
            input_tokens=sum(call.input_tokens for call in calls),
            output_tokens=sum(call.output_tokens for call in calls),
            cache_read_tokens=sum(call.cache_read_tokens for call in calls),
            cache_write_tokens=0,
            thinking_tokens=sum(call.thinking_tokens or 0 for call in calls),
            cost_usd=round(sum(priced), 6) if len(priced) == len(calls) else None,
            cost_source="estimated" if len(priced) == len(calls) else None,
            model=calls[-1].model,
        )

    def _apply(self, workdir: Path, envelope: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Writes the envelope's files and applies its patches; returns (changed files, problems)."""
        changed: list[str] = []
        problems: list[str] = []
        files = envelope.get("files") or {}
        if not isinstance(files, dict):
            problems.append("'files' is not an object")
            files = {}
        for relative, content in files.items():
            try:
                target = ensure_inside(workdir / str(relative), workdir)
            except Exception as exc:  # outside the workdir, or an odd name
                problems.append(f"{relative}: {exc}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            text = content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False) + "\n"
            target.write_text(text)
            changed.append(str(relative))
        patches = envelope.get("patches") or {}
        if not isinstance(patches, dict):
            problems.append("'patches' is not an object")
            patches = {}
        for relative, patch in patches.items():
            try:
                target = ensure_inside(workdir / str(relative), workdir)
                document = json.loads(target.read_text())
            except Exception as exc:
                problems.append(f"{relative}: cannot patch ({exc})")
                continue
            if not isinstance(patch, list):
                problems.append(f"{relative}: 'patches' entry is not a list")
                continue
            try:
                patched = apply_patch(document, patch)
            except PatchError as exc:
                # Apply the operations before the failing one, so one bad pointer does not undo the round.
                problems.append(f"{relative}: {exc}")
                if exc.index == 0:
                    continue
                patched = apply_patch(document, patch[: exc.index])
            target.write_text(json.dumps(patched, indent=2, ensure_ascii=False) + "\n")
            if str(relative) not in changed:
                changed.append(str(relative))
        return changed, problems

    def _redacted(self, response: httpx.Response) -> Any:
        try:
            return self.redactor.redact_obj(response.json())
        except ValueError:
            return self.redactor.redact(response.text[:4000])

    @staticmethod
    def _log(path: Path, record: dict[str, Any]) -> None:
        with path.open("a") as handle:
            handle.write(json.dumps({"ts": datetime.now(UTC).isoformat(), **record}, ensure_ascii=False) + "\n")


def _configured_prices() -> Mapping[str, Price]:
    from ..pricing import configured_prices

    return configured_prices()
