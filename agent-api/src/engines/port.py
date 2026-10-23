import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EngineStatus(StrEnum):
    OK = "ok"
    CLI_ERROR = "cli_error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    LIMIT_EXCEEDED = "limit_exceeded"


class EngineErrorReason(StrEnum):
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    MAX_TURNS = "max_turns"
    OUTPUT_LIMIT = "output_limit"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CRASH = "crash"


class EngineEventKind(StrEnum):
    SYSTEM = "system"
    MESSAGE = "message"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    USAGE = "usage"
    ERROR = "error"


class EngineEvent(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    kind: EngineEventKind
    summary: str
    data: dict[str, Any] = {}


class EngineUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class PromptRef(BaseModel):
    id: str
    version: str
    sha256: str


class EngineContext(BaseModel):
    """What gets written into the workspace before a call: skills to install and project conventions."""

    conventions: str
    skill_dirs: list[Path] = []


class EngineRequest(BaseModel):
    invocation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    purpose: str
    workdir: Path
    state_dir: Path
    prompt: str
    prompt_ref: PromptRef | None = None
    max_turns: int | None = None
    timeout_s: float | None = None


class EngineResult(BaseModel):
    invocation_id: str
    engine: str
    purpose: str
    status: EngineStatus
    error_reason: EngineErrorReason | None = None
    error_message: str | None = None
    exit_code: int | None = None
    duration_ms: int
    turns: int | None = None
    usage: EngineUsage | None = None
    session_id: str | None = None
    final_message: str | None = None
    changed_files: list[str] = []
    argv_redacted: list[str] = []
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    prompt_ref: PromptRef | None = None

    @property
    def ok(self) -> bool:
        return self.status == EngineStatus.OK


class EngineHealth(BaseModel):
    name: str
    available: bool
    reason: str | None = None
    version: str | None = None


OnEngineEvent = Callable[[EngineEvent], Awaitable[None]]


class ICodeEngine(ABC):
    name: str

    @abstractmethod
    async def health(self) -> EngineHealth:
        pass

    @abstractmethod
    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        pass

    @abstractmethod
    async def run(self, request: EngineRequest, on_event: OnEngineEvent | None = None) -> EngineResult:
        pass

    @abstractmethod
    async def cancel(self, invocation_id: str) -> bool:
        pass
