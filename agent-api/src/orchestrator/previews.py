"""Preview lifecycle on the worker (Stories 7.3, 7.4): the only place that touches preview containers.

Commands arrive over Redis (PreviewCommandBus) from the API, or from the runner when a generation completes.
Each generation's commands run one at a time; the previews row and `preview.status` events report the outcome.
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.configs import config, get_logger
from src.libs.queue import PreviewCommandBus
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.domain.entities import ArtifactEntity, PreviewEntity
from src.modules.shared.domain.enums import GenerationStatus, PreviewStatus
from src.preview import IPreviewRuntime, PreviewError, PreviewRequest

from .packaging import ArtifactWriter
from .store import JobStore

logger = get_logger(__name__)
ACTIVE = (PreviewStatus.STARTING, PreviewStatus.RUNNING)
MUTATING = {"start", "restart", "stop", "delete", "reset-db"}


def _now() -> datetime:
    return datetime.now(UTC)


class PreviewService:
    def __init__(self, runtime: IPreviewRuntime, store: JobStore, events: EventPublisher, bus: PreviewCommandBus):
        self.runtime = runtime
        self.store = store
        self.events = events
        self.bus = bus
        self.locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # -- entry points -------------------------------------------------------------------------------------------

    async def request_start(self, generation_id: str) -> None:
        """Called by the runner on COMPLETED (Q6: previews start automatically)."""
        self.store.upsert_preview(generation_id, status=PreviewStatus.STARTING, started_at=_now(), error=None)
        await self._event(generation_id, PreviewStatus.STARTING)
        await self.bus.send("start", generation_id)

    async def handle(self, command: dict[str, Any]) -> None:
        op, generation_id, args = command["op"], command["generationId"], command.get("args") or {}
        try:
            if op in MUTATING:
                async with self.locks[generation_id]:
                    result: Any = await getattr(self, op.replace("-", "_"))(generation_id)
            elif op == "logs":
                result = {"lines": await self.runtime.logs(generation_id, int(args.get("tail", 200)))}
            elif op == "requests":
                items = await self.runtime.request_log(generation_id, args.get("after"), int(args.get("limit", 200)))
                result = {"items": items, "cursor": items[-1]["ts"] if items else args.get("after")}
            else:
                result = {"error": f"unknown preview command {op!r}"}
        except Exception as exc:
            logger.exception("preview command failed", extra={"generation_id": generation_id, "op": op})
            result = {"error": str(exc)[:500]}
        if command.get("reply"):
            await self.bus.reply(command["reply"], result)

    # -- commands -----------------------------------------------------------------------------------------------

    async def start(self, generation_id: str) -> None:
        generation = self.store.generation(generation_id)
        source = self.store.artifact_by_name(generation_id, "backend.zip")
        if generation is None or generation.status != GenerationStatus.COMPLETED or source is None:
            await self._fail(generation_id, "only COMPLETED generations with a packaged source can be previewed")
            return
        current = self.store.upsert_preview(generation_id, status=PreviewStatus.STARTING, started_at=_now(), error=None)
        await self._event(generation_id, PreviewStatus.STARTING)
        if not await self._make_room(generation_id):
            return
        seed = self.store.artifact_by_name(generation_id, "seed.json")
        request = PreviewRequest(
            generation_id=generation_id,
            source_zip=self._file(source),
            ports=await self._ports(generation_id, current),
            seed=self._file(seed).read_bytes() if seed else None,
        )
        try:
            handle = await self.runtime.deploy(request)
        except PreviewError as exc:
            if exc.log:
                self._save_log(generation_id, "preview-build.log" if "build" in str(exc) else "preview.log", exc.log)
            await self._fail(generation_id, str(exc))
            return
        if handle.build_log:
            self._save_log(generation_id, "preview-build.log", handle.build_log)
        now, url = _now(), f"http://{config.preview_public_host}:{handle.host_port}"
        self.store.upsert_preview(
            generation_id,
            status=PreviewStatus.RUNNING,
            container_id=handle.container_id,
            db_container_id=handle.db_container_id,
            host_port=handle.host_port,
            url=url,
            started_at=now,
            last_accessed_at=now,
            expires_at=now + timedelta(hours=config.preview_ttl_hours),
            error=None,
        )
        await self._event(generation_id, PreviewStatus.RUNNING, url=url)

    async def restart(self, generation_id: str) -> None:
        await self.runtime.stop(generation_id)
        await self.start(generation_id)

    async def stop(self, generation_id: str, reason: str | None = None) -> None:
        await self.runtime.stop(generation_id)
        if self.store.preview(generation_id) is not None:
            self.store.upsert_preview(generation_id, status=PreviewStatus.STOPPED, error=reason)
            await self._event(generation_id, PreviewStatus.STOPPED, reason=reason)

    async def delete(self, generation_id: str) -> None:
        await self.runtime.remove(generation_id)
        self.store.delete_preview(generation_id)
        await self.events.publish(generation_id, "preview.status", status="DELETED")

    async def reset_db(self, generation_id: str) -> None:
        await self.runtime.drop_database(generation_id)
        await self.start(generation_id)

    # -- housekeeping (worker periodic task) --------------------------------------------------------------------

    async def expire(self) -> int:
        """Stops RUNNING previews idle past their TTL (PREVIEW_TTL_HOURS, refreshed by /touch)."""
        expired = [p for p in self.store.previews((PreviewStatus.RUNNING,)) if p.expires_at and p.expires_at < _now()]
        for preview in expired:
            async with self.locks[preview.generation_id]:
                await self.stop(preview.generation_id, reason="idle TTL reached")
        return len(expired)

    async def reconcile(self) -> dict[str, int]:
        """Syncs rows with the containers that really exist: missing/stopped containers → STOPPED, interrupted
        starts → FAILED, containers without a row → removed."""
        states = await self.runtime.states()
        rows = {p.generation_id: p for p in self.store.previews()}
        changed = removed = 0
        stale_start = _now() - timedelta(
            seconds=config.preview_build_timeout_seconds + config.preview_health_timeout_seconds + 120
        )
        for generation_id, preview in rows.items():
            if self.locks[generation_id].locked():
                continue
            state = states.get(generation_id)
            if preview.status == PreviewStatus.RUNNING and (state is None or state.app != "running"):
                found = state.app if state and state.app else "missing"
                self.store.upsert_preview(
                    generation_id, status=PreviewStatus.STOPPED, error=f"container not running ({found})"
                )
                await self._event(generation_id, PreviewStatus.STOPPED, reason=f"container {found}")
                changed += 1
            elif preview.status == PreviewStatus.STARTING and preview.started_at and preview.started_at < stale_start:
                await self._fail(generation_id, "start was interrupted (worker restarted?)")
                changed += 1
        for generation_id in set(states) - set(rows):
            await self.runtime.remove(generation_id)
            removed += 1
        if changed or removed:
            logger.info("previews reconciled", extra={"changed": changed, "removed_orphans": removed})
        return {"changed": changed, "removed": removed}

    # -- helpers ------------------------------------------------------------------------------------------------

    async def _make_room(self, generation_id: str) -> bool:
        running = [p for p in self.store.previews(ACTIVE) if p.generation_id != generation_id]
        excess = len(running) - config.preview_max_running + 1
        if excess <= 0:
            return True
        if not config.preview_evict:
            await self._fail(
                generation_id, f"{len(running)} previews running (PREVIEW_MAX_RUNNING={config.preview_max_running})"
            )
            return False
        oldest = sorted(running, key=lambda p: p.last_accessed_at or p.started_at or _now())[:excess]
        for preview in oldest:
            if preview.status == PreviewStatus.RUNNING:
                await self.stop(preview.generation_id, reason=f"evicted to start {generation_id}")
        return True

    async def _ports(self, generation_id: str, current: PreviewEntity) -> list[int]:
        """The preview's previous port first; then free ports; when the range is full, take the port of the least
        recently used stopped preview (its app container is recreated on its next start)."""
        rows = [p for p in self.store.previews() if p.generation_id != generation_id]
        used = {p.host_port for p in rows if p.host_port}
        ports = [current.host_port] if current.host_port else []
        ports += [port for port in config.preview_ports if port not in used and port not in ports]
        if len(ports) < 3:
            stopped = sorted(
                (p for p in rows if p.status in (PreviewStatus.STOPPED, PreviewStatus.FAILED) and p.host_port),
                key=lambda p: p.last_accessed_at or p.started_at or _now(),
            )
            for preview in stopped[:3]:
                await self.runtime.remove_app(preview.generation_id)
                self.store.upsert_preview(preview.generation_id, host_port=None, url=None)
                ports.append(preview.host_port)
        return ports

    def _file(self, artifact: ArtifactEntity) -> Path:
        return Path(config.artifact_root) / artifact.path

    def _save_log(self, generation_id: str, name: str, text: str) -> None:
        writer = ArtifactWriter(Path(config.artifact_root), generation_id)
        existing = self.store.artifact_by_name(generation_id, name)
        if existing:
            writer.ids[name] = existing.id
        writer.write(name, "log", text.encode(), "text/plain")
        self.store.replace_artifacts(generation_id, writer.written)

    async def _fail(self, generation_id: str, message: str) -> None:
        self.store.upsert_preview(generation_id, status=PreviewStatus.FAILED, error=message[:2000])
        await self._event(generation_id, PreviewStatus.FAILED, error=message[:500])

    async def _event(self, generation_id: str, status: PreviewStatus, **payload: Any) -> None:
        await self.events.publish(generation_id, "preview.status", status=status, payload=payload)
