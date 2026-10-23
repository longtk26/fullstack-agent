import asyncio
import os
import sys
import time
from pathlib import Path

from src.engines.process import ProcessSpec, SubprocessRunner, base_env


def _spec(tmp_path: Path, code: str, **overrides) -> ProcessSpec:
    values = {
        "argv": [sys.executable, "-c", code],
        "cwd": tmp_path,
        "env": base_env(),
        "stdout_path": tmp_path / "out.log",
        "stderr_path": tmp_path / "err.log",
        "timeout_s": 10,
        "max_output_bytes": 1_000_000,
    }
    values.update(overrides)
    return ProcessSpec(**values)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:  # a zombie still answers signal 0; check its state
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except FileNotFoundError:
        return False


def test_streams_lines_and_passes_stdin(tmp_path):
    lines = []

    async def on_line(line):
        lines.append(line)
        return False

    spec = _spec(tmp_path, "import sys; data = sys.stdin.read(); print('a'); print(data.upper())", stdin=b"hello")
    outcome = asyncio.run(SubprocessRunner().run(spec, on_line))

    assert outcome.exit_code == 0
    assert lines == ["a", "HELLO"]
    assert (tmp_path / "out.log").read_text() == "a\nHELLO\n"


def test_timeout_kills_the_whole_process_group(tmp_path):
    code = (
        "import subprocess, time; p = subprocess.Popen(['sleep', '60']);"
        f"open({str(tmp_path / 'child.pid')!r}, 'w').write(str(p.pid)); time.sleep(60)"
    )
    started = time.monotonic()
    outcome = asyncio.run(SubprocessRunner(kill_grace_s=1).run(_spec(tmp_path, code, timeout_s=1.5)))

    assert outcome.timed_out
    assert time.monotonic() - started < 10
    time.sleep(0.2)
    assert not _alive(int((tmp_path / "child.pid").read_text()))


def test_cancel_event_stops_the_process(tmp_path):
    async def scenario():
        cancel = asyncio.Event()
        asyncio.get_running_loop().call_later(0.5, cancel.set)
        return await SubprocessRunner(kill_grace_s=1).run(_spec(tmp_path, "import time; time.sleep(60)"), None, cancel)

    outcome = asyncio.run(scenario())

    assert outcome.cancelled and not outcome.timed_out


def test_output_cap_stops_runaway_output(tmp_path):
    spec = _spec(tmp_path, "while True: print('x' * 1000)", max_output_bytes=50_000)

    outcome = asyncio.run(SubprocessRunner(kill_grace_s=1).run(spec))

    assert outcome.output_limit_exceeded
    assert (tmp_path / "out.log").stat().st_size <= 50_000


def test_callback_can_stop_the_process(tmp_path):
    async def stop_on_third(line):
        return line == "3"

    spec = _spec(tmp_path, "import time\nfor i in range(100):\n    print(i, flush=True); time.sleep(0.05)")
    outcome = asyncio.run(SubprocessRunner(kill_grace_s=1).run(spec, stop_on_third))

    assert outcome.stopped_by_callback


def test_base_env_drops_worker_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "do-not-leak")
    monkeypatch.setenv("DB_URL", "postgresql://u:p@db/x")

    env = base_env(EXTRA="1", SKIPPED=None)

    assert "JWT_SECRET" not in env and "DB_URL" not in env
    assert env["EXTRA"] == "1" and "SKIPPED" not in env
    assert env["PATH"] == os.environ["PATH"]
