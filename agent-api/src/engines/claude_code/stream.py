import json
from datetime import UTC, datetime
from typing import Any

from ..cli_engine import StreamParser, classify_error_text
from ..port import EngineErrorReason, EngineEvent, EngineEventKind, EngineUsage, ModelCall, ToolCall
from ..pricing import apportion

_TARGET_KEYS = ("file_path", "path", "notebook_path", "pattern", "skill", "command", "url")


def tool_target(tool_input: Any) -> str:
    if isinstance(tool_input, dict):
        for key in _TARGET_KEYS:
            if isinstance(tool_input.get(key), str):
                return tool_input[key]
    return ""


def _short(text: str, limit: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _timestamp(message: dict) -> datetime:
    """The CLI stamps assistant and user messages; anything else is timed on arrival."""
    value = message.get("timestamp")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(UTC)


class ClaudeStreamParser(StreamParser):
    """Parses `claude -p --output-format stream-json --verbose` (one JSON object per line).

    Model calls (Story 8.4): the CLI repeats an assistant message once per content block, so calls are keyed by
    `message.id`. A call starts when the previous turn ended (session start or the last tool result) and ends
    with its last block, so its latency is approximate."""

    def __init__(self, max_turns, model=None, prices=None):
        super().__init__(max_turns, model, prices)
        self._calls: dict[str, ModelCall] = {}
        self._pending_tools: dict[str, ToolCall] = {}
        self._turn_started = datetime.now(UTC)

    def feed(self, line: str) -> list[EngineEvent]:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not isinstance(message, dict):
            return []
        handler = getattr(self, f"_on_{message.get('type')}", None)
        return handler(message) if handler else []

    def _record_call(self, message: dict) -> ModelCall | None:
        body = message.get("message") or {}
        message_id = body.get("id")
        if not message_id:
            return None
        at = _timestamp(message)
        usage = body.get("usage") or {}
        call = self._calls.get(message_id)
        if call is None:
            call = ModelCall(
                seq=len(self._calls) + 1,
                model=body.get("model") or self.model,
                started_at=min(self._turn_started, at),
                ended_at=at,
            )
            self._calls[message_id] = call
            self.run.model_calls.append(call)
        cache_read = usage.get("cache_read_input_tokens") or 0
        cache_write = usage.get("cache_creation_input_tokens") or 0
        call.cache_read_tokens = max(call.cache_read_tokens, cache_read)
        call.cache_write_tokens = max(call.cache_write_tokens, cache_write)
        call.input_tokens = max(call.input_tokens, (usage.get("input_tokens") or 0) + cache_read + cache_write)
        call.output_tokens = max(call.output_tokens, usage.get("output_tokens") or 0)
        call.ended_at = max(call.ended_at, at)
        return call

    def _on_system(self, message: dict) -> list[EngineEvent]:
        if message.get("subtype") != "init":
            return []
        self.run.session_id = message.get("session_id")
        self._turn_started = datetime.now(UTC)
        model = message.get("model", "?")
        self.model = message.get("model") or self.model
        return [EngineEvent(kind=EngineEventKind.SYSTEM, summary=f"session started ({model})", data={"model": model})]

    def _on_assistant(self, message: dict) -> list[EngineEvent]:
        events = []
        call = self._record_call(message)
        for block in (message.get("message") or {}).get("content") or []:
            if block.get("type") == "text" and block.get("text", "").strip():
                events.append(EngineEvent(kind=EngineEventKind.MESSAGE, summary=_short(block["text"])))
            elif block.get("type") == "tool_use":
                name, target = block.get("name", "?"), tool_target(block.get("input"))
                if call is not None:
                    tool = self.add_tool(call, ToolCall(name=name, target=target, started_at=call.ended_at))
                    if tool is not None and block.get("id"):
                        self._pending_tools[block["id"]] = tool
                events.append(
                    EngineEvent(
                        kind=EngineEventKind.TOOL_USE,
                        summary=f"{name} {target}".strip(),
                        data={"tool": name, "target": target, "toolUseId": block.get("id")},
                    )
                )
        return events

    def _on_user(self, message: dict) -> list[EngineEvent]:
        events = []
        at = _timestamp(message)
        self._turn_started = at
        for block in (message.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            content = block.get("content")
            if isinstance(content, list):
                content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
            is_error = bool(block.get("is_error"))
            tool = self._pending_tools.pop(block.get("tool_use_id") or "", None)
            if tool is not None:
                tool.ended_at, tool.is_error = max(at, tool.started_at), is_error
            summary = ("error: " if is_error else "ok: ") + _short(str(content or ""), 160)
            events.append(
                EngineEvent(
                    kind=EngineEventKind.TOOL_RESULT,
                    summary=summary,
                    data={"toolUseId": block.get("tool_use_id"), "isError": is_error},
                )
            )
        return events

    def _on_result(self, message: dict) -> list[EngineEvent]:
        run = self.run
        run.completed = True
        run.session_id = message.get("session_id") or run.session_id
        run.turns = message.get("num_turns")
        run.final_message = message.get("result")
        usage = message.get("usage") or {}
        input_tokens = sum(
            usage.get(key) or 0 for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
        model_usage = message.get("modelUsage") or {}
        cost = message.get("total_cost_usd")
        run.usage = EngineUsage(
            input_tokens=input_tokens if usage else None,
            output_tokens=usage.get("output_tokens"),
            cache_read_tokens=usage.get("cache_read_input_tokens"),
            cache_write_tokens=usage.get("cache_creation_input_tokens"),
            thinking_tokens=(usage.get("output_tokens_details") or {}).get("thinking_tokens"),
            cost_usd=cost,
            cost_source="reported" if cost is not None else None,
            model=next(iter(model_usage), None) if len(model_usage) == 1 else self.model,
        )
        reported = {
            model: {"cost": totals.get("costUSD") or 0.0, "outputTokens": totals.get("outputTokens") or 0}
            for model, totals in model_usage.items()
        }
        if not reported and cost is not None and run.model_calls:
            # Older CLIs report only the session total: one bucket per (single) model.
            reported = {run.model_calls[0].model or "": {"cost": cost, "outputTokens": usage.get("output_tokens")}}
        apportion(run.model_calls, reported, self.price_table())
        subtype = message.get("subtype", "")
        if subtype == "error_max_turns":
            run.is_error, run.error_reason = True, EngineErrorReason.MAX_TURNS
            run.error_message = f"stopped after {run.turns} turns"
        elif message.get("is_error") or subtype.startswith("error"):
            run.is_error = True
            run.error_message = _short(str(message.get("result") or subtype), 500)
            run.error_reason = classify_error_text(run.error_message)
        summary = f"{run.turns} turns, {run.usage.output_tokens or 0} output tokens"
        if run.usage.cost_usd is not None:
            summary += f", ${run.usage.cost_usd:.4f}"
        return [EngineEvent(kind=EngineEventKind.USAGE, summary=summary, data=run.usage.model_dump())]
