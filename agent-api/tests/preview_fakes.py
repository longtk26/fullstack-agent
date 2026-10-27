"""TESTING ONLY (docs/development/test-doubles.md): an in-memory preview runtime, so the preview lifecycle
(Stories 7.3, 7.4) can be tested without Docker. The real runtime is src/preview/docker_preview.py."""

from typing import Any

from src.preview import IPreviewRuntime, PreviewError, PreviewHandle, PreviewRequest, PreviewState


class FakePreviewRuntime(IPreviewRuntime):
    def __init__(self, fail: str | None = None):
        self.fail = fail
        self.containers: dict[str, PreviewState] = {}
        self.images: set[str] = set()
        self.calls: list[tuple[str, str]] = []
        self.requests: dict[str, list[dict[str, Any]]] = {}
        self.seeds: dict[str, bytes | None] = {}
        self.options: dict[str, dict[str, Any]] = {}

    async def deploy(self, request: PreviewRequest) -> PreviewHandle:
        self.calls.append(("deploy", request.generation_id))
        if self.fail:
            raise PreviewError(self.fail, "Step 4/6 : RUN pip install\nERROR: no matching distribution")
        assert request.source_zip.is_file()
        built = request.generation_id not in self.images
        self.images.add(request.generation_id)
        state = self.containers.get(request.generation_id)
        port = state.host_port if state and state.host_port else request.ports[0]
        self.containers[request.generation_id] = PreviewState(app="running", db="running", host_port=port)
        self.seeds[request.generation_id] = request.seed
        self.options[request.generation_id] = dict(request.options)
        return PreviewHandle(
            container_id=f"app-{request.generation_id}",
            db_container_id=f"db-{request.generation_id}",
            host_port=port,
            build_log="Successfully built" if built else None,
        )

    async def stop(self, generation_id: str) -> None:
        self.calls.append(("stop", generation_id))
        if generation_id in self.containers:
            self.containers[generation_id].app = "exited"
            self.containers[generation_id].db = "exited"

    async def remove(self, generation_id: str, keep_image: bool = False) -> None:
        self.calls.append(("remove", generation_id))
        self.containers.pop(generation_id, None)
        if not keep_image:
            self.images.discard(generation_id)

    async def remove_app(self, generation_id: str) -> None:
        self.calls.append(("remove_app", generation_id))
        if generation_id in self.containers:
            self.containers[generation_id].app, self.containers[generation_id].host_port = None, None

    async def drop_database(self, generation_id: str) -> None:
        self.calls.append(("drop_database", generation_id))
        if generation_id in self.containers:
            self.containers[generation_id].db = None

    async def logs(self, generation_id: str, tail: int) -> list[str]:
        return [f"line {i}" for i in range(tail)][:3]

    async def request_log(self, generation_id: str, after: str | None, limit: int) -> list[dict[str, Any]]:
        items = [r for r in self.requests.get(generation_id, []) if not after or r["ts"] > after]
        return items[:limit]

    async def states(self) -> dict[str, PreviewState]:
        return dict(self.containers)
