from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Any

from fastapi import Depends

from src.libs.exceptions import BadRequestException, ForbiddenException
from src.modules.generations.ports.output import (
    IComponentCacheRepoDep,
    IExecutionRecordRepoDep,
    IGenerationRepoDep,
)
from src.modules.generations.usecases.project_names import project_names
from src.modules.shared.domain.entities import ComponentCacheEntity, GenerationEntity, UserEntity
from src.modules.shared.domain.enums import GenerationStatus
from src.modules.shared.domain.telemetry import ExecutionRecords, rollup
from src.modules.specs.ports.output import IBackendSpecRepoDep, IFrontendSpecRepoDep

MAX_GENERATIONS = 1000
MAX_DAYS = 366


def _add_cost(target: dict[str, Any], cost: dict[str, Any]) -> None:
    for key in ("reported", "estimated", "total"):
        target[key] = round(target.get(key, 0.0) + cost[key], 6)
    target["unpriced"] = target.get("unpriced", 0) + cost["unpriced"]


def _add_tokens(target: dict[str, int], tokens: dict[str, int]) -> None:
    for key, value in tokens.items():
        target[key] = target.get(key, 0) + value


SUCCEEDED = (GenerationStatus.COMPLETED, GenerationStatus.COMPLETED_WITH_WARNINGS)


class GetUsageUsecase:
    """Usage & traces page (Story 9.10): the 8.4 rollups of every generation in a period, aggregated by day,
    engine, model, node and lane. No LangSmith dependency."""

    def __init__(
        self,
        generations: IGenerationRepoDep,
        records: IExecutionRecordRepoDep,
        specs: IBackendSpecRepoDep,
        frontend_specs: IFrontendSpecRepoDep,
        component_cache: IComponentCacheRepoDep,
    ):
        self.generations = generations
        self.records = records
        self.specs = specs
        self.frontend_specs = frontend_specs
        self.component_cache = component_cache

    async def execute(
        self, user: UserEntity, start: date | None, end: date | None, all_owners: bool = False
    ) -> dict[str, Any]:
        if all_owners and not user.is_admin:
            raise ForbiddenException("scope=all requires the admin role")
        end = end or datetime.now(UTC).date()
        start = start or end - timedelta(days=6)
        if start > end or (end - start).days > MAX_DAYS:
            raise BadRequestException(f"'from' must be on or before 'to', at most {MAX_DAYS} days apart")
        rows = self.generations.list_created_between(
            None if all_owners else user.id,
            datetime.combine(start, time.min, UTC),
            datetime.combine(end + timedelta(days=1), time.min, UTC),
            MAX_GENERATIONS,
        )
        loaded = self.records.records_for([row.id for row in rows])
        names = project_names(rows, self.specs, self.frontend_specs)
        items = [(row, rollup(ExecutionRecords(generation=row, **loaded[row.id]))) for row in rows]
        return {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "truncated": len(rows) >= MAX_GENERATIONS,
            "totals": _totals(items),
            "byDay": _by_day(items, start, end),
            "byEngine": _by_key(items, lambda row: row.engine, "engine"),
            "byMode": _by_key(items, lambda row: str(row.mode), "mode"),
            "byModel": _by_model(items),
            "byNode": _by_node(items),
            "byLane": _by_lane(items),
            # Admins: the most reused custom components, candidates for the section library (Story 17.3)
            "catalogueCandidates": [_candidate(entry) for entry in self.component_cache.most_reused()]
            if all_owners
            else [],
            "generations": [_row(row, usage, names) for row, usage in items],
        }


def _totals(items) -> dict[str, Any]:
    completed = [usage for row, usage in items if row.status in SUCCEEDED]
    finished = [row for row, _ in items if row.status in (*SUCCEEDED, GenerationStatus.FAILED)]
    cost: dict[str, Any] = {}
    tokens: dict[str, int] = {}
    for _, usage in items:
        _add_cost(cost, usage["cost"])
        _add_tokens(tokens, usage["tokens"])
    return {
        "generations": len(items),
        "completed": len(completed),
        "failed": sum(1 for row, _ in items if row.status == GenerationStatus.FAILED),
        "successRate": round(len(completed) / len(finished), 4) if finished else None,
        "wallMs": sum(usage["wallMs"] or 0 for _, usage in items),
        "engineMs": sum(usage["engineMs"] for _, usage in items),
        "sandboxMs": sum(usage["sandboxMs"] for _, usage in items),
        "modelCalls": sum(usage["modelCalls"] for _, usage in items),
        "cacheHits": sum(usage["cacheHits"] for _, usage in items),
        "savedEngineMs": sum(usage["savedEngineMs"] for _, usage in items),
        "tokens": tokens,
        "cost": cost or {"reported": 0.0, "estimated": 0.0, "total": 0.0, "unpriced": 0},
        "avgCostPerCompleted": round(sum(u["cost"]["total"] for u in completed) / len(completed), 6)
        if completed
        else None,
        "avgWallMsPerCompleted": int(sum(u["wallMs"] or 0 for u in completed) / len(completed)) if completed else None,
    }


def _candidate(entry: ComponentCacheEntity) -> dict[str, Any]:
    return {
        "name": entry.name,
        "key": entry.key,
        "hits": entry.hits,
        "savedEngineMs": int(entry.hits * entry.saved_seconds * 1000),
        "engine": entry.engine,
        "model": entry.model,
        "lastUsedAt": entry.last_used_at.isoformat() if entry.last_used_at else None,
    }


def _by_day(items, start: date, end: date) -> list[dict[str, Any]]:
    days = {
        (start + timedelta(days=offset)).isoformat(): {"generations": 0, "wallMs": 0, "modelCalls": 0, "cost": {}}
        for offset in range((end - start).days + 1)
    }
    for row, usage in items:
        day = days.get(row.created_at.astimezone(UTC).date().isoformat())
        if day is None:
            continue
        day["generations"] += 1
        day["wallMs"] += usage["wallMs"] or 0
        day["modelCalls"] += usage["modelCalls"]
        _add_cost(day["cost"], usage["cost"])
    for day in days.values():
        day["cost"] = day["cost"] or {"reported": 0.0, "estimated": 0.0, "total": 0.0, "unpriced": 0}
    return [{"date": key, **value} for key, value in days.items()]


def _by_key(items, key, label: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row, usage in items:
        group = groups.setdefault(
            key(row), {label: key(row), "generations": 0, "completed": 0, "wallMs": 0, "modelCalls": 0, "cost": {}}
        )
        group["generations"] += 1
        group["completed"] += row.status in SUCCEEDED
        group["wallMs"] += usage["wallMs"] or 0
        group["modelCalls"] += usage["modelCalls"]
        _add_cost(group["cost"], usage["cost"])
    for group in groups.values():
        group["avgWallMs"] = int(group["wallMs"] / group["generations"])
        group["avgCost"] = round(group["cost"]["total"] / group["generations"], 6)
    return sorted(groups.values(), key=lambda g: -g["cost"]["total"])


def _by_model(items) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for _, usage in items:
        for entry in usage["byModel"]:
            group = groups.setdefault(
                entry["model"], {"model": entry["model"], "modelCalls": 0, "tokens": {}, "cost": {}}
            )
            group["modelCalls"] += entry["modelCalls"]
            _add_tokens(group["tokens"], entry["tokens"])
            _add_cost(group["cost"], entry["cost"])
    return sorted(groups.values(), key=lambda g: -g["cost"]["total"])


def _by_node(items) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "runs": 0,
            "generations": 0,
            "durationMs": 0,
            "engineMs": 0,
            "sandboxMs": 0,
            "modelCalls": 0,
            "cost": {},
        }
    )
    for _, usage in items:
        for entry in usage["byNode"]:
            group = groups[entry["node"]]
            group["runs"] += entry["attempts"]
            group["generations"] += 1
            group["durationMs"] += entry["durationMs"]
            group["engineMs"] += entry["engineMs"]
            group["sandboxMs"] += entry["sandboxMs"]
            group["modelCalls"] += entry["modelCalls"]
            _add_cost(group["cost"], entry["cost"])
    return [
        {
            "node": node,
            **group,
            "avgDurationMs": int(group["durationMs"] / group["generations"]),
            "avgCost": round(group["cost"]["total"] / group["generations"], 6),
        }
        for node, group in groups.items()
    ]


def _by_lane(items) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for _, usage in items:
        for entry in usage["byLane"]:
            group = groups.setdefault(entry["lane"], {"lane": entry["lane"], "wallMs": 0, "modelCalls": 0, "cost": {}})
            group["wallMs"] += entry["wallMs"] or 0
            group["modelCalls"] += entry["modelCalls"]
            _add_cost(group["cost"], entry["cost"])
    return list(groups.values())


def _row(row: GenerationEntity, usage: dict[str, Any], names: dict[str, str | None]) -> dict[str, Any]:
    return {
        "generationId": row.id,
        "projectName": names.get(row.id),
        "mode": str(row.mode),
        "engine": row.engine,
        "status": row.status,
        "repairAttempts": row.repair_attempts,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "wallMs": usage["wallMs"],
        "modelCalls": usage["modelCalls"],
        "tokens": usage["tokens"],
        "cost": usage["cost"],
        "langsmithUrl": row.langsmith_run_url,
    }


GetUsageUsecaseDep = Annotated[GetUsageUsecase, Depends(GetUsageUsecase)]
