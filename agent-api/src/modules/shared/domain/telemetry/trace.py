"""The local trace (Story 8.3): the span tree of a generation, built from its execution records, so the UI has a
waterfall whether or not LangSmith is configured. Same shape as the LangSmith trace (Epic 8 diagram)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from .usage import DEFAULT_LANE, ExecutionRecords, ms_between

RUNNING = {"running", "pending"}
ERROR_STATUSES = {"failed", "cli_error", "timeout", "limit_exceeded", "error"}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _span(
    span_id: str,
    parent_id: str | None,
    kind: str,
    name: str,
    status: str,
    started: datetime | None,
    ended: datetime | None,
    attrs: dict[str, Any] | None = None,
    refs: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "spanId": span_id,
        "parentId": parent_id,
        "kind": kind,
        "name": name,
        "lane": DEFAULT_LANE,
        "status": status,
        "error": status in ERROR_STATUSES,
        "startedAt": _iso(started),
        "endedAt": _iso(ended),
        "durationMs": ms_between(started, ended),
        "attrs": {k: v for k, v in (attrs or {}).items() if v is not None},
        "refs": refs or {},
    }


def build_spans(records: ExecutionRecords, patches: dict[int, str] | None = None) -> list[dict[str, Any]]:
    """`patches` maps a repair attempt to its patch artifact id (the patch viewer of repair spans)."""
    generation = records.generation
    patches = patches or {}
    spans = [
        _span(
            "root",
            None,
            "generation",
            "backend-generation",
            generation.status.lower(),
            generation.started_at or generation.created_at,
            generation.finished_at,
            {"engine": generation.engine, "repairAttempts": generation.repair_attempts},
        )
    ]
    node_spans: dict[Any, dict[str, Any]] = {}
    for run in records.node_runs:
        name = f"{run.node}#{run.attempt}" if run.node in ("run_validation", "repair_code") else run.node
        refs = {"patch": patches[run.attempt]} if run.node == "repair_code" and run.attempt in patches else {}
        span = _span(
            f"node:{run.id}",
            "root",
            "node",
            name,
            run.status,
            run.started_at,
            run.finished_at,
            {"node": run.node, "attempt": run.attempt, **run.summary},
            refs,
        )
        node_spans[run.id] = span
        spans.append(span)

    calls_by_invocation: dict[Any, list] = {}
    for call in records.model_calls:
        calls_by_invocation.setdefault(call.cli_invocation_id, []).append(call)
    for invocation in records.invocations:
        started = invocation.created_at
        ended = invocation.finished_at
        if ended is None and invocation.status not in RUNNING and started and invocation.duration_ms is not None:
            ended = started + timedelta(milliseconds=invocation.duration_ms)
        parent = f"node:{invocation.node_run_id}" if invocation.node_run_id in node_spans else "root"
        engine_id = f"engine:{invocation.id}"
        calls = calls_by_invocation.get(invocation.id, [])
        spans.append(
            _span(
                engine_id,
                parent,
                "engine",
                f"engine:{invocation.engine}",
                invocation.status,
                started,
                ended,
                {
                    "purpose": invocation.purpose,
                    "prompt": invocation.prompt_ref,
                    "model": invocation.model,
                    "exitCode": invocation.exit_code,
                    "turns": invocation.turns,
                    "errorReason": invocation.error_reason,
                    "inputTokens": invocation.input_tokens,
                    "outputTokens": invocation.output_tokens,
                    "cacheReadTokens": invocation.cache_read_tokens,
                    "cacheWriteTokens": invocation.cache_write_tokens,
                    "costUsd": invocation.cost_usd,
                    "costSource": invocation.cost_source,
                    "modelCalls": len(calls),
                    "changedFiles": invocation.changed_files[:50] or None,
                },
                {"stdout": "stdout", "stderr": "stderr"} if invocation.stdout_ref else {},
            )
        )
        for call in calls:
            llm_id = f"llm:{call.id}"
            spans.append(
                _span(
                    llm_id,
                    engine_id,
                    "llm",
                    f"llm:{call.model or 'unknown'} #{call.seq}",
                    "ok",
                    call.started_at,
                    call.ended_at,
                    {
                        "model": call.model,
                        "seq": call.seq,
                        "inputTokens": call.input_tokens,
                        "outputTokens": call.output_tokens,
                        "cacheReadTokens": call.cache_read_tokens,
                        "cacheWriteTokens": call.cache_write_tokens,
                        "thinkingTokens": call.thinking_tokens,
                        "costUsd": call.cost_usd,
                        "costSource": call.cost_source,
                        "latencySource": call.latency_source,
                    },
                )
            )
            for index, tool in enumerate(call.tools):
                tool_start = _parse(tool.get("started_at"))
                spans.append(
                    _span(
                        f"tool:{call.id}:{index}",
                        llm_id,
                        "tool",
                        f"tool:{tool.get('name')} {tool.get('target') or ''}".strip(),
                        "failed" if tool.get("is_error") else "ok",
                        tool_start,
                        _parse(tool.get("ended_at")) or tool_start,
                        {"tool": tool.get("name"), "target": tool.get("target")},
                    )
                )

    check_spans: list[tuple[dict[str, Any], datetime, datetime]] = []
    validation_nodes = {run.attempt: run for run in records.node_runs if run.node == "run_validation"}
    for check in records.validation_runs:
        node = validation_nodes.get(check.attempt)
        started = check.started_at or (node.started_at if node else check.created_at)
        ended = started + timedelta(milliseconds=check.duration_ms or 0) if started else None
        span = _span(
            f"check:{check.id}",
            f"node:{node.id}" if node else "root",
            "check",
            f"check:{check.check}",
            check.status,
            started,
            ended,
            {"check": check.check, "attempt": check.attempt, "summary": check.details.get("summary")},
            {"output": "output"} if check.details.get("output") else {},
        )
        spans.append(span)
        if started and ended:
            check_spans.append((span, started, ended))

    for run in records.sandbox_execs:
        ended = run.started_at + timedelta(milliseconds=run.duration_ms)
        parent = f"node:{run.node_run_id}" if run.node_run_id in node_spans else "root"
        for span, started, check_end in check_spans:
            if span["parentId"] == parent and started - timedelta(seconds=1) <= run.started_at <= check_end:
                parent = span["spanId"]
                break
        spans.append(
            _span(
                f"sandbox:{run.id}",
                parent,
                "sandbox",
                f"sandbox:{run.name}",
                run.status,
                run.started_at,
                ended,
                {"command": run.command, "exitCode": run.exit_code},
            )
        )
    return spans


def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None
