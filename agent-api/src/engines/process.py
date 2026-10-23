import asyncio
import os
import signal
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

_CHUNK = 65536
_MAX_LINE = 8 * 1024 * 1024
BASE_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "TZ")

# Returning True from the line callback asks the runner to stop the process (e.g. a turn limit).
LineCallback = Callable[[str], Awaitable[bool]]


@dataclass
class ProcessSpec:
    argv: list[str]
    cwd: Path
    env: dict[str, str]
    stdout_path: Path
    stderr_path: Path
    timeout_s: float
    max_output_bytes: int
    stdin: bytes | None = None


@dataclass
class ProcessOutcome:
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False
    cancelled: bool = False
    output_limit_exceeded: bool = False
    stopped_by_callback: bool = False


def base_env(**extra: str | None) -> dict[str, str]:
    """A minimal environment: never the worker's own (DB URLs, JWT secret, other engines' keys)."""
    env = {key: os.environ[key] for key in BASE_ENV_KEYS if key in os.environ}
    env.update({key: value for key, value in extra.items() if value is not None})
    return env


class SubprocessRunner:
    def __init__(self, kill_grace_s: float = 5.0):
        self.kill_grace_s = kill_grace_s

    async def run(
        self,
        spec: ProcessSpec,
        on_stdout_line: LineCallback | None = None,
        cancel: asyncio.Event | None = None,
    ) -> ProcessOutcome:
        spec.stdout_path.parent.mkdir(parents=True, exist_ok=True)
        spec.stderr_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *spec.argv,
            cwd=spec.cwd,
            env=spec.env,
            stdin=asyncio.subprocess.PIPE if spec.stdin is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        outcome = ProcessOutcome(exit_code=None, duration_ms=0)
        stop = asyncio.Event()
        budget = _Budget(spec.max_output_bytes)

        async def feed_stdin() -> None:
            try:
                process.stdin.write(spec.stdin)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.stdin.close()

        async def on_line(line: str) -> None:
            if on_stdout_line is not None and await on_stdout_line(line):
                outcome.stopped_by_callback = True
                stop.set()

        def on_overflow() -> None:
            outcome.output_limit_exceeded = True
            stop.set()

        pumps = [
            asyncio.create_task(_pump(process.stdout, spec.stdout_path, budget, on_overflow, on_line)),
            asyncio.create_task(_pump(process.stderr, spec.stderr_path, budget, on_overflow, None)),
        ]
        if spec.stdin is not None:
            pumps.append(asyncio.create_task(feed_stdin()))

        waiters = {asyncio.create_task(process.wait()): "exit", asyncio.create_task(stop.wait()): "stop"}
        if cancel is not None:
            waiters[asyncio.create_task(cancel.wait())] = "cancel"
        done, pending = await asyncio.wait(waiters, timeout=spec.timeout_s, return_when=asyncio.FIRST_COMPLETED)
        reasons = {waiters[task] for task in done}
        for task in pending:
            task.cancel()

        if "exit" not in reasons:
            outcome.timed_out = not reasons
            outcome.cancelled = "cancel" in reasons
            await self._kill_group(process)
        await asyncio.gather(*pumps, return_exceptions=True)
        outcome.exit_code = process.returncode
        outcome.duration_ms = int((time.monotonic() - started) * 1000)
        return outcome

    async def _kill_group(self, process: asyncio.subprocess.Process) -> None:
        for sig, wait_s in ((signal.SIGTERM, self.kill_grace_s), (signal.SIGKILL, None)):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=wait_s)
                break
            except TimeoutError:
                continue
        try:
            os.killpg(process.pid, signal.SIGKILL)  # reap stragglers that ignored SIGTERM after the leader exited
        except ProcessLookupError:
            pass


class _Budget:
    def __init__(self, limit: int):
        self.remaining = limit

    def take(self, size: int) -> bool:
        self.remaining -= size
        return self.remaining >= 0


async def _pump(stream, path: Path, budget: _Budget, on_overflow, on_line) -> None:
    pending = b""
    with path.open("wb") as sink:
        while chunk := await stream.read(_CHUNK):
            if not budget.take(len(chunk)):
                on_overflow()
                continue
            sink.write(chunk)
            if on_line is None:
                continue
            pending += chunk
            *lines, pending = pending.split(b"\n")
            if len(pending) > _MAX_LINE:
                lines.append(pending[:_MAX_LINE])
                pending = b""
            for line in lines:
                await on_line(line.decode("utf-8", errors="replace").rstrip("\r"))
        if on_line is not None and pending:
            await on_line(pending.decode("utf-8", errors="replace").rstrip("\r"))
