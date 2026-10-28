from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PreviewError(Exception):
    def __init__(self, message: str, log: str = ""):
        super().__init__(message)
        self.log = log


@dataclass
class PreviewRequest:
    generation_id: str
    source_zip: Path
    ports: list[int]  # host ports to try, in order
    seed: bytes | None = None
    # backend: corsOrigins; frontend: mode (static | dynamic), mockApi, apiBaseUrl
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreviewHandle:
    container_id: str
    db_container_id: str
    host_port: int
    build_log: str | None = None  # set when the image was (re)built


@dataclass
class PreviewState:
    app: str | None  # Docker state ("running", "exited", …) or None when the container is missing
    db: str | None
    host_port: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class IPreviewRuntime(ABC):
    """Runs generated backends as long-lived containers (app + its own PostgreSQL), local-only."""

    @abstractmethod
    async def deploy(self, request: PreviewRequest) -> PreviewHandle:
        """Builds the image if missing, (re)uses the database, starts the app and waits for /health."""

    @abstractmethod
    async def stop(self, generation_id: str) -> None: ...

    @abstractmethod
    async def remove(self, generation_id: str, keep_image: bool = False) -> None:
        """Containers, network, database volume and (unless keep_image) the image."""

    @abstractmethod
    async def remove_app(self, generation_id: str) -> None:
        """Only the app container (frees its host port; image and data stay)."""

    @abstractmethod
    async def drop_database(self, generation_id: str) -> None:
        """Stops the app and removes the database container and volume (the next deploy starts empty)."""

    @abstractmethod
    async def logs(self, generation_id: str, tail: int) -> list[str]: ...

    @abstractmethod
    async def request_log(self, generation_id: str, after: str | None, limit: int) -> list[dict[str, Any]]:
        """The app's structured access-log lines (`"message": "request"`) newer than `after` (their `ts`)."""

    @abstractmethod
    async def states(self) -> dict[str, PreviewState]:
        """Every preview this deployment owns, by generation id."""

    async def probe(self, generation_id: str, method: str, path: str, body: Any = None) -> tuple[int, Any, bytes]:
        """HTTP request against a running preview container: returns (status_code, json_or_text, raw_bytes)."""
        import httpx

        from src.configs import config

        state = (await self.states()).get(generation_id)
        if state is None or state.app != "running" or not state.host_port:
            return 0, None, b""
        url = f"http://{config.preview_bind_host}:{state.host_port}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(method, url, json=body)
                try:
                    parsed = response.json()
                except Exception:
                    parsed = response.text
                return response.status_code, parsed, response.content
        except httpx.HTTPError:
            return 0, None, b""
