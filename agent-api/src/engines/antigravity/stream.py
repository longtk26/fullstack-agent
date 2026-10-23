import json

from ..cli_engine import StreamParser, classify_error_text
from ..port import EngineErrorReason, EngineEvent, EngineEventKind, EngineUsage

_TARGET_KEYS = ("TargetFile", "AbsolutePath", "FilePath", "File", "Path", "path", "file_path", "Query", "CommandLine")


def _short(text: str, limit: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def tool_target(parameters) -> str:
    if isinstance(parameters, dict):
        for key in _TARGET_KEYS:
            if isinstance(parameters.get(key), str):
                return parameters[key]
    return ""


class AntigravityStreamParser(StreamParser):
    """Parses `agy --output-format stream-json`: `init`, `step_update` and `result` events (agy 1.4.x).

    agy has no max-turns flag, so finished `agent_response` steps are counted here and the run is stopped
    once the limit is passed.
    """

    def __init__(self, max_turns: int | None):
        super().__init__(max_turns)
        self._texts: dict[int, str] = {}
        self._responses = 0

    def feed(self, line: str) -> list[EngineEvent]:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not isinstance(message, dict):
            return []
        kind = message.get("event")
        if kind == "init":
            return self._on_init(message)
        if kind == "step_update":
            return self._on_step(message.get("step_update") or {})
        if kind == "result":
            return self._on_result(message.get("result") or {})
        return []

    def _on_init(self, message: dict) -> list[EngineEvent]:
        payload = message.get("init") or {}
        self.run.session_id = message.get("conversation_id") or payload.get("conversation_id")
        mode = payload.get("permission_mode", "?")
        return [
            EngineEvent(
                kind=EngineEventKind.SYSTEM,
                summary=f"session started (permission mode {mode})",
                data={"tools": payload.get("tools", []), "permissionMode": mode, "model": payload.get("model")},
            )
        ]

    def _on_step(self, step: dict) -> list[EngineEvent]:
        index = step.get("step_index", -1)
        step_type = step.get("step_type")
        if step_type == "agent_response" and step.get("text_delta"):
            self._texts[index] = self._texts.get(index, "") + step["text_delta"]
        if step.get("state") != "DONE":
            return []

        if step_type == "agent_response":
            self._responses += 1
            if self.max_turns is not None and self._responses > self.max_turns:
                self.run.turn_limit_hit = True
            text = self._texts.pop(index, "").strip()
            return [EngineEvent(kind=EngineEventKind.MESSAGE, summary=_short(text))] if text else []

        if step_type == "tool":
            info = step.get("tool_info") or {}
            name = info.get("name") or step.get("tool_name") or "?"
            target = tool_target(info.get("parameters"))
            events = [
                EngineEvent(
                    kind=EngineEventKind.TOOL_USE,
                    summary=f"{name} {target}".strip(),
                    data={"tool": name, "target": target, "stepIndex": index},
                )
            ]
            error = info.get("error")
            if error:
                message = error.get("message") if isinstance(error, dict) else str(error)
                summary = "error: " + _short(str(message), 160)
            else:
                summary = "ok: " + _short(str(info.get("output") or ""), 160)
            events.append(
                EngineEvent(
                    kind=EngineEventKind.TOOL_RESULT,
                    summary=summary,
                    data={"stepIndex": index, "isError": bool(error)},
                )
            )
            return events
        return []

    def _on_result(self, result: dict) -> list[EngineEvent]:
        run = self.run
        run.completed = True
        run.session_id = result.get("conversation_id") or run.session_id
        run.turns = result.get("num_turns")
        run.final_message = result.get("response") or None
        usage = result.get("usage") or {}
        run.usage = EngineUsage(
            input_tokens=(usage.get("input_tokens") or 0) + (usage.get("cache_read_tokens") or 0) if usage else None,
            output_tokens=(usage.get("output_tokens") or 0) + (usage.get("thinking_tokens") or 0) if usage else None,
            cost_usd=None,
        )
        status = result.get("status", "SUCCESS")
        if status != "SUCCESS":
            run.is_error = True
            run.error_message = _short(str(result.get("error") or status), 500)
            run.error_reason = (
                EngineErrorReason.CANCELLED
                if status in ("CANCELED", "INTERRUPTED")
                else classify_error_text(run.error_message)
            )
        summary = f"{run.turns} turns, {run.usage.output_tokens or 0} output tokens"
        return [EngineEvent(kind=EngineEventKind.USAGE, summary=summary, data=run.usage.model_dump())]
