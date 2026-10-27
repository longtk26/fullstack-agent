"""LangSmith tracing for a generation (Stories 8.1, 8.2, 8.4).

One generation is one trace: a root run `backend-generation` with node spans under it, and engine, model-call,
tool, check and sandbox spans under those. Spans are built with the LangSmith RunTree API rather than LangGraph's
callback tracer, so names and nesting follow the trace shape in Epic 8 and a resumed job keeps adding to the
same trace (the root's dotted order is stored on the generation). LangGraph's own auto-tracing is switched off
for the graph run, so a run is never traced twice.

Without `LANGSMITH_TRACING=true` and an API key every span is a no-op; the trace id still exists and still
correlates logs and events. Tracing must never fail a job: every LangSmith call is guarded.
"""

import asyncio
import uuid
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from src.configs import config, get_logger
from src.libs.redaction import Redactor, default_redactor

logger = get_logger(__name__)

ROOT_NAME = "backend-generation"
MAX_TRACED_TEXT = 4096  # graph state and outputs carry refs; anything bigger is cut (Story 8.1)
_current: ContextVar["Span | None"] = ContextVar("bga_trace_span", default=None)


def tracing_enabled() -> bool:
    return bool(config.langsmith_tracing and config.langsmith_api_key)


def destination() -> dict[str, Any]:
    """An agent address when LANGSMITH_AGENT_ID is set (beta, per workspace), otherwise the project.

    Naming it in code outranks the environment, where the SDK refuses to trace when both are set."""
    if config.langsmith_agent_id:
        from langsmith import agent_address

        return {"address": agent_address(config.langsmith_agent_id, config.langsmith_agent_environment)}
    return {"project_name": config.langsmith_project}


def _trim(value: Any, redactor: Redactor) -> Any:
    if isinstance(value, str):
        value = redactor.redact(value)
        return value if len(value) <= MAX_TRACED_TEXT else value[:MAX_TRACED_TEXT] + f"… [{len(value)} chars]"
    if isinstance(value, dict):
        return {key: _trim(item, redactor) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_trim(item, redactor) for item in value]
    return value


def redact_for_trace(data: dict) -> dict:
    """The client's hide_inputs / hide_outputs / hide_metadata hook: secrets masked, long text cut (Story 8.1)."""
    return _trim(data, default_redactor().with_secrets(config.langsmith_api_key))


_client = None


def langsmith_client():
    """One client per process; everything it sends passes `redact_for_trace` first."""
    global _client
    if _client is None and tracing_enabled():
        from langsmith import Client

        with warnings.catch_warnings():
            # The SDK warns when the env names both a project and an agent; we name the destination in code.
            warnings.simplefilter("ignore")
            _client = Client(
                api_url=config.langsmith_endpoint,
                api_key=config.langsmith_api_key,
                hide_inputs=redact_for_trace,
                hide_outputs=redact_for_trace,
                hide_metadata=redact_for_trace,
            )
    return _client


class Span:
    """A handle on one LangSmith run, or a no-op. Ending a span twice is harmless."""

    def __init__(self, run=None, posted: bool = False):
        self.run = run
        self._posted = posted
        self.ended = run is None

    @property
    def enabled(self) -> bool:
        return self.run is not None

    def child(
        self,
        name: str,
        run_type: str = "chain",
        *,
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> "Span":
        if self.run is None:
            return Span()
        try:
            run = self.run.create_child(
                name,
                run_type,
                inputs=inputs or {},
                tags=tags,
                extra={"metadata": metadata or {}},
                start_time=start_time,
                end_time=end_time,
            )
            span = Span(run)
            if end_time is None:
                run.post()  # open spans show up while the job runs
                span._posted = True
            return span
        except Exception:
            logger.warning("trace span failed", extra={"span": name}, exc_info=True)
            return Span()

    def end(
        self,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
        end_time: datetime | None = None,
        usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.ended or self.run is None:
            return
        self.ended = True
        try:
            if usage is not None:
                self.run.set(usage_metadata=usage)
            self.run.end(outputs=outputs, error=error, end_time=end_time or datetime.now(UTC), metadata=metadata)
            self.run.patch() if self._posted else self.run.post()
        except Exception:
            logger.warning("trace span end failed", extra={"span": self.run.name}, exc_info=True)


def current() -> Span:
    return _current.get() or Span()


@contextmanager
def span(name: str, run_type: str = "chain", **kwargs: Any) -> Iterator[Span]:
    """A child of the current span that becomes the current span for the block."""
    child = current().child(name, run_type, **kwargs)
    token = _current.set(child)
    try:
        yield child
    except BaseException as exc:
        child.end(error=f"{type(exc).__name__}: {exc}"[:500])
        raise
    finally:
        _current.reset(token)
        child.end()


@contextmanager
def under(parent: Span) -> Iterator[None]:
    token = _current.set(parent)
    try:
        yield
    finally:
        _current.reset(token)


def _start_of(dotted_order: str) -> datetime | None:
    try:
        return datetime.strptime(dotted_order[:22], "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC)
    except ValueError:
        return None


class GenerationTrace:
    """The root of one generation's trace: opened on the first run, reattached on resume, closed at the end."""

    def __init__(self, trace_id: str, root: Span, parent: str | None):
        self.trace_id = trace_id
        self.root = root
        self.parent = parent  # dotted order of the root run, stored on the generation

    @classmethod
    def open(
        cls,
        generation_id: str,
        *,
        trace_id: str | None,
        parent: str | None,
        inputs: dict[str, Any],
        metadata: dict[str, Any],
        tags: list[str],
    ) -> "GenerationTrace":
        client = langsmith_client()
        if client is None:
            return cls(trace_id or str(uuid.uuid4()), Span(), parent)
        try:
            from langsmith.run_trees import RunTree

            common = {"ls_client": client, "tags": tags, "extra": {"metadata": metadata}, **destination()}
            if parent:
                run = RunTree.from_dotted_order(
                    parent, name=ROOT_NAME, run_type="chain", start_time=_start_of(parent), inputs=inputs, **common
                )
                return cls(str(run.trace_id), Span(run, posted=True), parent)
            run_id = uuid.UUID(trace_id) if trace_id else uuid.uuid4()
            run = RunTree(id=run_id, name=ROOT_NAME, run_type="chain", inputs=inputs, **common)
            run.post()
            return cls(str(run.trace_id), Span(run, posted=True), run.dotted_order)
        except Exception:
            logger.warning("could not open the trace", extra={"generation_id": generation_id}, exc_info=True)
            return cls(trace_id or str(uuid.uuid4()), Span(), parent)

    async def url(self) -> str | None:
        if not self.root.enabled:
            return None
        try:
            return await asyncio.to_thread(self.root.run.get_url)
        except Exception:
            logger.warning("could not resolve the trace URL", exc_info=True)
            return None

    def close(self, outputs: dict[str, Any], error: str | None = None) -> None:
        self.root.end(outputs=outputs, error=error)

    @staticmethod
    async def flush() -> None:
        client = langsmith_client()
        if client is not None:
            try:
                await asyncio.to_thread(client.flush)
            except Exception:
                logger.warning("trace flush failed", exc_info=True)
