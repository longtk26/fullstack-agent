from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

SandboxKind = Literal["backend", "frontend"]


class ExecResult(BaseModel):
    exit_code: int
    duration_ms: int
    stdout: str
    stderr: str
    truncated: bool = False
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        return (self.stdout + ("\n" + self.stderr if self.stderr else "")).strip()


class SandboxError(Exception):
    pass


class ISandbox(ABC):
    """One job's sandbox: a throwaway PostgreSQL plus short-lived runner containers over /work (the project)."""

    db_url: str
    test_db_url: str

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def exec(
        self, command: str, timeout_s: int | None = None, env: dict[str, str] | None = None, egress: bool = False
    ) -> ExecResult:
        """Runs `sh -c command` in a fresh locked-down runner container with /work mounted."""

    @abstractmethod
    async def reset_database(self, name: str) -> None:
        """Drops and recreates database `name` on the sidecar."""

    @abstractmethod
    async def stop(self) -> None: ...


class ISandboxProvider(ABC):
    @abstractmethod
    def for_job(self, generation_id: str, project: Path, kind: SandboxKind = "backend") -> ISandbox:
        """backend: the Python runner plus a PostgreSQL sidecar; frontend: the Node runner, no database."""

    @abstractmethod
    async def job_ids(self) -> set[str]:
        """Generation ids that currently own sandbox containers or networks."""

    @abstractmethod
    async def remove(self, generation_ids: set[str]) -> int:
        """Removes those generations' sandbox containers and networks; returns how many objects were removed."""
