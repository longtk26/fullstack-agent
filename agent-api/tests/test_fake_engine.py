import asyncio

import pytest

from src.engines import EngineRequest, EngineStatus
from src.engines.fake_engine import FakeEngine, FakeStep


@pytest.fixture
def workdir(tmp_path):
    (tmp_path / "job" / "project").mkdir(parents=True)
    return tmp_path


def _request(root, purpose="generate_backend"):
    return EngineRequest(
        purpose=purpose, workdir=root / "job" / "project", state_dir=root / "job" / "state", prompt="go"
    )


def test_replays_steps_per_purpose_and_repeats_the_last(workdir):
    engine = FakeEngine(
        workdir,
        {
            "repair_code": [
                FakeStep(write={"a.py": "broken"}),
                FakeStep(write={"a.py": "fixed"}),
            ]
        },
    )

    first = asyncio.run(engine.run(_request(workdir, "repair_code")))
    second = asyncio.run(engine.run(_request(workdir, "repair_code")))
    third = asyncio.run(engine.run(_request(workdir, "repair_code")))

    assert first.changed_files == ["a.py"]
    assert (workdir / "job" / "project" / "a.py").read_text() == "fixed"
    assert third.status == EngineStatus.OK and second.status == EngineStatus.OK
    assert len(engine.calls) == 3


def test_scripted_failure_is_reported(workdir):
    engine = FakeEngine(workdir, {"*": [FakeStep(status=EngineStatus.CLI_ERROR)]})

    result = asyncio.run(engine.run(_request(workdir)))

    assert result.status == EngineStatus.CLI_ERROR


def test_cancel_interrupts_a_sleeping_step(workdir):
    engine = FakeEngine(workdir, {"*": [FakeStep(sleep_s=30, write={"late.py": "x"})]})
    request = _request(workdir)

    async def scenario():
        task = asyncio.create_task(engine.run(request))
        await asyncio.sleep(0.1)
        await engine.cancel(request.invocation_id)
        return await task

    result = asyncio.run(scenario())

    assert result.status == EngineStatus.CANCELLED
    assert not (workdir / "job" / "project" / "late.py").exists()
