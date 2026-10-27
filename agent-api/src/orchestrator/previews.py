"""Preview lifecycle on the worker (Stories 7.3, 7.4, 13.5): the only place that touches preview containers.

A generation has up to two previews, one per kind: `backend` (the API with its database) and `frontend` (the
static export or the Next.js server). Commands arrive over Redis (PreviewCommandBus) from the API, or from the
runner when a generation completes; `args.kind` picks the preview (default `backend`). Each generation's
commands run one at a time; the previews rows and `preview.status` events report the outcome.
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
from src.modules.shared.domain.enums import LaneStatus, PreviewStatus
from src.modules.shared.domain.generation_modes import backend_ready
from src.preview import IPreviewRuntime, PreviewError, PreviewRequest

from .packaging import ArtifactWriter
from .store import JobStore

logger = get_logger(__name__)
ACTIVE = (PreviewStatus.STARTING, PreviewStatus.RUNNING)
MUTATING = {"start", "restart", "stop", "delete", "reset-db"}
KINDS = ("backend", "frontend")
SOURCES = {"backend": "backend.zip", "frontend": "frontend.zip"}


def _now() -> datetime:
    return datetime.now(UTC)


class PreviewService:
    def __init__(
        self,
        runtime: IPreviewRuntime,
        store: JobStore,
        events: EventPublisher,
        bus: PreviewCommandBus,
        frontend_runtime: IPreviewRuntime | None = None,
    ):
        self.runtimes: dict[str, IPreviewRuntime] = {"backend": runtime}
        if frontend_runtime is not None:
            self.runtimes["frontend"] = frontend_runtime
        self.runtime = runtime
        self.store = store
        self.events = events
        self.bus = bus
        self.locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # -- entry points -------------------------------------------------------------------------------------------

    def startable(self, generation_id: str) -> list[str]:
        """The previews a finished generation gets: the frontend first (the backend's CORS needs its origin)."""
        generation = self.store.generation(generation_id)
        if generation is None:
            return []
        kinds = []
        frontend = generation.options.get("frontend") or {}
        if (
            "frontend" in self.runtimes
            and generation.lanes.get("frontend") == LaneStatus.COMPLETED.value
            and frontend.get("generatePreview", True)
        ):
            kinds.append("frontend")
        if generation.options.get("deployPreview", True) and backend_ready(generation.status, generation.lanes):
            if generation.lanes.get("backend", LaneStatus.COMPLETED.value) == LaneStatus.COMPLETED.value:
                kinds.append("backend")
        return kinds

    async def request_start(self, generation_id: str) -> None:
        """Called by the runner when a generation finishes (Q6: previews start automatically)."""
        for kind in self.startable(generation_id):
            self.store.upsert_preview(generation_id, kind, status=PreviewStatus.STARTING, started_at=_now(), error=None)
            await self._event(generation_id, kind, PreviewStatus.STARTING)
            await self.bus.send("start", generation_id, kind=kind)

    async def handle(self, command: dict[str, Any]) -> None:
        op, generation_id, args = command["op"], command["generationId"], command.get("args") or {}
        kind = args.get("kind", "backend")
        try:
            if kind not in self.runtimes:
                result: Any = {"error": f"no {kind} previews on this worker"}
            elif op in MUTATING:
                async with self.locks[generation_id]:
                    result = await getattr(self, op.replace("-", "_"))(generation_id, kind)
            elif op == "logs":
                result = {"lines": await self.runtimes[kind].logs(generation_id, int(args.get("tail", 200)))}
            elif op == "requests":
                items = await self.runtimes[kind].request_log(
                    generation_id, args.get("after"), int(args.get("limit", 200))
                )
                result = {"items": items, "cursor": items[-1]["ts"] if items else args.get("after")}
            else:
                result = {"error": f"unknown preview command {op!r}"}
        except Exception as exc:
            logger.exception("preview command failed", extra={"generation_id": generation_id, "op": op})
            result = {"error": str(exc)[:500]}
        if command.get("reply"):
            await self.bus.reply(command["reply"], result)

    # -- commands -----------------------------------------------------------------------------------------------

    async def start(self, generation_id: str, kind: str = "backend") -> None:
        generation = self.store.generation(generation_id)
        source = self.store.artifact_by_name(generation_id, SOURCES[kind])
        if generation is None or source is None or not self._ready(generation, kind):
            what = "frontend" if kind == "frontend" else "backend"
            await self._fail(
                generation_id, kind, f"only generations with a completed, packaged {what} can be previewed"
            )
            return
        current = self.store.upsert_preview(
            generation_id, kind, status=PreviewStatus.STARTING, started_at=_now(), error=None
        )
        await self._event(generation_id, kind, PreviewStatus.STARTING)
        if not await self._make_room(generation_id, kind):
            return
        seed = self.store.artifact_by_name(generation_id, "seed.json") if kind == "backend" else None
        request = PreviewRequest(
            generation_id=generation_id,
            source_zip=self._file(source),
            ports=await self._ports(generation_id, kind, current),
            seed=self._file(seed).read_bytes() if seed else None,
            options=self._options(generation, kind),
        )
        try:
            handle = await self.runtimes[kind].deploy(request)
        except PreviewError as exc:
            if exc.log:
                prefix = "frontend-preview" if kind == "frontend" else "preview"
                name = f"{prefix}-build.log" if "build" in str(exc) else f"{prefix}.log"
                self._save_log(generation_id, name, exc.log)
            await self._fail(generation_id, kind, str(exc))
            return
        if handle.build_log:
            self._save_log(generation_id, "frontend-preview-build.log" if kind == "frontend" else "preview-build.log",
                           handle.build_log)  # fmt: skip
        now, url = _now(), f"http://{config.preview_public_host}:{handle.host_port}"
        self.store.upsert_preview(
            generation_id,
            kind,
            status=PreviewStatus.RUNNING,
            container_id=handle.container_id,
            db_container_id=handle.db_container_id or None,
            host_port=handle.host_port,
            url=url,
            started_at=now,
            last_accessed_at=now,
            expires_at=now + timedelta(hours=config.preview_ttl_hours),
            error=None,
            mock_api=request.options.get("mockApi") if kind == "frontend" else None,
        )
        await self._event(generation_id, kind, PreviewStatus.RUNNING, url=url)

    def _ready(self, generation, kind: str) -> bool:
        if kind == "frontend":
            return generation.lanes.get("frontend") == LaneStatus.COMPLETED.value
        return backend_ready(generation.status, generation.lanes)

    def _options(self, generation, kind: str) -> dict[str, Any]:
        if kind == "frontend":
            frontend = generation.options.get("frontend") or {}
            if generation.mode != "dynamic":
                return {"mode": generation.mode}  # a static export has no API, so no mock switch
            return {"mode": generation.mode, "mockApi": frontend.get("mockApi", True), "apiBaseUrl": ""}
        origins = [origin for origin in config.preview_cors_origins.split(",") if origin]
        frontend = self.store.preview(generation.id, "frontend")
        if frontend is not None and frontend.host_port:
            # The frontend preview calls this backend once it leaves the mock API (Story 14.2).
            origins += [
                f"http://{config.preview_public_host}:{frontend.host_port}",
                f"http://127.0.0.1:{frontend.host_port}",
            ]
        return {"corsOrigins": ",".join(dict.fromkeys(origins))}

    async def restart(self, generation_id: str, kind: str = "backend") -> None:
        await self.runtimes[kind].stop(generation_id)
        await self.start(generation_id, kind)

    async def stop(self, generation_id: str, kind: str = "backend", reason: str | None = None) -> None:
        await self.runtimes[kind].stop(generation_id)
        if self.store.preview(generation_id, kind) is not None:
            self.store.upsert_preview(generation_id, kind, status=PreviewStatus.STOPPED, error=reason)
            await self._event(generation_id, kind, PreviewStatus.STOPPED, reason=reason)

    async def delete(self, generation_id: str, kind: str = "backend") -> None:
        await self.runtimes[kind].remove(generation_id)
        self.store.delete_preview(generation_id, kind)
        await self.events.publish(generation_id, "preview.status", status="DELETED", payload={"kind": kind})

    async def reset_db(self, generation_id: str, kind: str = "backend") -> None:
        await self.runtimes[kind].drop_database(generation_id)
        await self.start(generation_id, kind)

    # -- housekeeping (worker periodic task) --------------------------------------------------------------------

    async def expire(self) -> int:
        """Stops RUNNING previews idle past their TTL (PREVIEW_TTL_HOURS, refreshed by /touch)."""
        expired = [p for p in self.store.previews((PreviewStatus.RUNNING,)) if p.expires_at and p.expires_at < _now()]
        for preview in expired:
            if preview.kind not in self.runtimes:
                continue
            async with self.locks[preview.generation_id]:
                await self.stop(preview.generation_id, preview.kind, reason="idle TTL reached")
        return len(expired)

    async def reconcile(self) -> dict[str, int]:
        """Syncs rows with the containers that really exist: missing/stopped containers → STOPPED, interrupted
        starts → FAILED, containers without a row → removed."""
        changed = removed = 0
        stale_start = _now() - timedelta(
            seconds=config.preview_build_timeout_seconds + config.preview_health_timeout_seconds + 120
        )
        rows_by_kind: dict[str, dict[str, PreviewEntity]] = defaultdict(dict)
        for preview in self.store.previews():
            rows_by_kind[preview.kind][preview.generation_id] = preview
        for kind, runtime in self.runtimes.items():
            states = await runtime.states()
            rows = rows_by_kind.get(kind, {})
            for generation_id, preview in rows.items():
                if self.locks[generation_id].locked():
                    continue
                state = states.get(generation_id)
                if preview.status == PreviewStatus.RUNNING and (state is None or state.app != "running"):
                    found = state.app if state and state.app else "missing"
                    self.store.upsert_preview(
                        generation_id, kind, status=PreviewStatus.STOPPED, error=f"container not running ({found})"
                    )
                    await self._event(generation_id, kind, PreviewStatus.STOPPED, reason=f"container {found}")
                    changed += 1
                elif (
                    preview.status == PreviewStatus.STARTING and preview.started_at and preview.started_at < stale_start
                ):
                    await self._fail(generation_id, kind, "start was interrupted (worker restarted?)")
                    changed += 1
            for generation_id in set(states) - set(rows):
                await runtime.remove(generation_id)
                removed += 1
        if changed or removed:
            logger.info("previews reconciled", extra={"changed": changed, "removed_orphans": removed})
        return {"changed": changed, "removed": removed}

    # -- helpers ------------------------------------------------------------------------------------------------

    async def _make_room(self, generation_id: str, kind: str) -> bool:
        """PREVIEW_MAX_RUNNING counts other generations' previews (a generation's own two never evict each other)."""
        running = [p for p in self.store.previews(ACTIVE) if p.generation_id != generation_id]
        excess = len({p.generation_id for p in running}) - config.preview_max_running + 1
        if excess <= 0:
            return True
        if not config.preview_evict:
            await self._fail(
                generation_id,
                kind,
                f"{len(running)} previews running (PREVIEW_MAX_RUNNING={config.preview_max_running})",
            )
            return False
        oldest = sorted(running, key=lambda p: p.last_accessed_at or p.started_at or _now())
        victims: list[str] = []
        for preview in oldest:
            if preview.generation_id not in victims:
                victims.append(preview.generation_id)
        for victim in victims[:excess]:
            for preview in running:
                if preview.generation_id == victim and preview.status == PreviewStatus.RUNNING:
                    await self.stop(victim, preview.kind, reason=f"evicted to start {generation_id}")
        return True

    async def _ports(self, generation_id: str, kind: str, current: PreviewEntity) -> list[int]:
        """The preview's previous port first; then free ports; when the range is full, take the port of the least
        recently used stopped preview (its app container is recreated on its next start)."""
        rows = [p for p in self.store.previews() if (p.generation_id, p.kind) != (generation_id, kind)]
        used = {p.host_port for p in rows if p.host_port}
        ports = [current.host_port] if current.host_port else []
        ports += [port for port in config.preview_ports if port not in used and port not in ports]
        if len(ports) < 3:
            stopped = sorted(
                (p for p in rows if p.status in (PreviewStatus.STOPPED, PreviewStatus.FAILED) and p.host_port),
                key=lambda p: p.last_accessed_at or p.started_at or _now(),
            )
            for preview in stopped[:3]:
                if preview.kind in self.runtimes:
                    await self.runtimes[preview.kind].remove_app(preview.generation_id)
                self.store.upsert_preview(preview.generation_id, preview.kind, host_port=None, url=None)
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

    async def _fail(self, generation_id: str, kind: str, message: str) -> None:
        self.store.upsert_preview(generation_id, kind, status=PreviewStatus.FAILED, error=message[:2000])
        await self._event(generation_id, kind, PreviewStatus.FAILED, error=message[:500])

    async def _event(self, generation_id: str, kind: str, status: PreviewStatus, **payload: Any) -> None:
        await self.events.publish(generation_id, "preview.status", status=status, payload={"kind": kind, **payload})
