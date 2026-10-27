"""Usage rollups (Story 8.4): wall time, engine and sandbox time, model calls, tokens and cost per generation,
node, lane and model. Pure functions over execution records, shared by report.json, the trace and usage APIs.

Cost is split by where it comes from: `reported` (Claude Code states it) and `estimated` (tokens × price, e.g.
Antigravity). Calls whose model has no price count as `unpriced` and add nothing.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.modules.shared.domain.entities import (
    CliInvocationEntity,
    GenerationEntity,
    ModelCallEntity,
    NodeRunEntity,
    SandboxExecEntity,
    ValidationRunEntity,
)

TOKEN_KINDS = ("input", "output", "cacheRead", "cacheWrite", "thinking")
DEFAULT_LANE = "backend"


@dataclass
class ExecutionRecords:
    generation: GenerationEntity
    node_runs: list[NodeRunEntity] = field(default_factory=list)
    invocations: list[CliInvocationEntity] = field(default_factory=list)
    model_calls: list[ModelCallEntity] = field(default_factory=list)
    validation_runs: list[ValidationRunEntity] = field(default_factory=list)
    sandbox_execs: list[SandboxExecEntity] = field(default_factory=list)


def ms_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, int((end - start).total_seconds() * 1000))


class Bucket:
    """Accumulates one row of a rollup."""

    def __init__(self):
        self.engine_ms = 0
        self.sandbox_ms = 0
        self.model_calls = 0
        self.engine_calls = 0
        self.tokens = dict.fromkeys(TOKEN_KINDS, 0)
        self.reported = 0.0
        self.estimated = 0.0
        self.unpriced = 0

    def add_cost(self, cost: float | None, source: str | None) -> None:
        if cost is None:
            self.unpriced += 1
        elif source == "estimated":
            self.estimated += cost
        else:
            self.reported += cost

    def add_call(self, call: ModelCallEntity) -> None:
        self.model_calls += 1
        self.tokens["input"] += call.input_tokens
        self.tokens["output"] += call.output_tokens
        self.tokens["cacheRead"] += call.cache_read_tokens
        self.tokens["cacheWrite"] += call.cache_write_tokens
        self.tokens["thinking"] += call.thinking_tokens or 0
        self.add_cost(call.cost_usd, call.cost_source)

    def add_invocation(self, invocation: CliInvocationEntity, calls: list[ModelCallEntity]) -> None:
        """Model calls when the invocation has them; its own totals otherwise (runs recorded before Story 8.4)."""
        self.engine_calls += 1
        self.engine_ms += invocation.duration_ms or 0
        if calls:
            for call in calls:
                self.add_call(call)
            return
        self.tokens["input"] += invocation.input_tokens or 0
        self.tokens["output"] += invocation.output_tokens or 0
        self.tokens["cacheRead"] += invocation.cache_read_tokens or 0
        self.tokens["cacheWrite"] += invocation.cache_write_tokens or 0
        self.tokens["thinking"] += invocation.thinking_tokens or 0
        if invocation.status != "running":
            self.add_cost(invocation.cost_usd, invocation.cost_source or "reported")

    def merge(self, other: "Bucket") -> None:
        self.engine_ms += other.engine_ms
        self.sandbox_ms += other.sandbox_ms
        self.model_calls += other.model_calls
        self.engine_calls += other.engine_calls
        for kind in TOKEN_KINDS:
            self.tokens[kind] += other.tokens[kind]
        self.reported += other.reported
        self.estimated += other.estimated
        self.unpriced += other.unpriced

    def as_dict(self) -> dict[str, Any]:
        return {
            "engineMs": self.engine_ms,
            "sandboxMs": self.sandbox_ms,
            "engineCalls": self.engine_calls,
            "modelCalls": self.model_calls,
            "tokens": dict(self.tokens),
            "cost": {
                "reported": round(self.reported, 6),
                "estimated": round(self.estimated, 6),
                "total": round(self.reported + self.estimated, 6),
                "unpriced": self.unpriced,
            },
        }


def rollup(records: ExecutionRecords, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    generation = records.generation
    calls_by_invocation: dict[Any, list[ModelCallEntity]] = defaultdict(list)
    for call in records.model_calls:
        calls_by_invocation[call.cli_invocation_id].append(call)
    node_of_run = {run.id: run for run in records.node_runs}

    by_node: dict[str, Bucket] = defaultdict(Bucket)
    node_meta: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "durationMs": 0})
    for run in records.node_runs:
        meta = node_meta[run.node]
        meta["attempts"] += 1
        meta["durationMs"] += ms_between(run.started_at, run.finished_at or now) or 0
    total = Bucket()
    by_model: dict[str, Bucket] = defaultdict(Bucket)
    for invocation in records.invocations:
        calls = calls_by_invocation.get(invocation.id, [])
        bucket = Bucket()
        bucket.add_invocation(invocation, calls)
        total.merge(bucket)
        node = node_of_run.get(invocation.node_run_id)
        by_node[node.node if node else "(none)"].merge(bucket)
        if calls:
            for call in calls:
                by_model[call.model or "unknown"].add_call(call)
        else:
            model_bucket = Bucket()
            model_bucket.add_invocation(invocation, [])
            model_bucket.engine_ms = 0
            model_bucket.engine_calls = 0
            by_model[invocation.model or "unknown"].merge(model_bucket)
    for sandbox_run in records.sandbox_execs:
        total.sandbox_ms += sandbox_run.duration_ms
        node = node_of_run.get(sandbox_run.node_run_id)
        by_node[node.node if node else "(none)"].sandbox_ms += sandbox_run.duration_ms

    started = generation.started_at or generation.created_at
    end = generation.finished_at or (now if generation.started_at else None)
    wall_ms = ms_between(started, end) or sum(meta["durationMs"] for meta in node_meta.values())
    nodes = [
        {"node": node, **node_meta[node], **by_node[node].as_dict()}
        for node in dict.fromkeys([run.node for run in records.node_runs] + list(by_node))
        if node in node_meta or by_node[node].engine_calls
    ]
    return {
        "wallMs": wall_ms,
        **total.as_dict(),
        "byNode": nodes,
        "byLane": [{"lane": DEFAULT_LANE, "wallMs": wall_ms, **total.as_dict()}],
        "byModel": [
            {"model": model, **{k: v for k, v in bucket.as_dict().items() if k not in ("engineMs", "sandboxMs")}}
            for model, bucket in sorted(by_model.items())
        ],
    }
