import json
from typing import Any

from ..cli_engine import StreamParser, classify_error_text
from ..port import EngineErrorReason, EngineEvent, EngineEventKind, EngineUsage

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


class ClaudeStreamParser(StreamParser):
    """Parses `claude -p --output-format stream-json --verbose` (one JSON object per line)."""

    def feed(self, line: str) -> list[EngineEvent]:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not isinstance(message, dict):
            return []
        handler = getattr(self, f"_on_{message.get('type')}", None)
        return handler(message) if handler else []

    def _on_system(self, message: dict) -> list[EngineEvent]:
        if message.get("subtype") != "init":
            return []
        self.run.session_id = message.get("session_id")
        model = message.get("model", "?")
        return [EngineEvent(kind=EngineEventKind.SYSTEM, summary=f"session started ({model})", data={"model": model})]

    def _on_assistant(self, message: dict) -> list[EngineEvent]:
        events = []
        for block in (message.get("message") or {}).get("content") or []:
            if block.get("type") == "text" and block.get("text", "").strip():
                events.append(EngineEvent(kind=EngineEventKind.MESSAGE, summary=_short(block["text"])))
            elif block.get("type") == "tool_use":
                name, target = block.get("name", "?"), tool_target(block.get("input"))
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
        for block in (message.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            content = block.get("content")
            if isinstance(content, list):
                content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
            is_error = bool(block.get("is_error"))
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
        run.usage = EngineUsage(
            input_tokens=input_tokens if usage else None,
            output_tokens=usage.get("output_tokens"),
            cost_usd=message.get("total_cost_usd"),
        )
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
