"""Real CLI runs (cost money). Opt in with BGA_LIVE_ENGINE_TESTS=1 plus the engine's credentials
(BGA_LIVE_ANTIGRAVITY_AUTH=account to use the agy login of this machine)."""

import asyncio
import os

import pytest

from src.engines import EngineContext, EngineRequest, EngineStatus, PromptLibrary, build_engine_registry
from src.engines.registry import engine_skills

pytestmark = pytest.mark.skipif(os.environ.get("BGA_LIVE_ENGINE_TESTS") != "1", reason="live engine tests are opt-in")


@pytest.mark.parametrize("engine_name", ["claude_code", "antigravity"])
def test_engine_writes_a_hello_app(engine_name, tmp_path, monkeypatch):
    from src.configs import config

    monkeypatch.setattr(config, "workspace_root", str(tmp_path))
    # conftest pins ANTIGRAVITY_AUTH; e.g. BGA_LIVE_ANTIGRAVITY_AUTH=account uses the host's agy login.
    monkeypatch.setattr(
        config, "antigravity_auth", os.environ.get("BGA_LIVE_ANTIGRAVITY_AUTH", config.antigravity_auth)
    )
    engine = build_engine_registry(config).get(engine_name)
    health = asyncio.run(engine.health())
    if not health.available:
        pytest.skip(health.reason)

    workdir = tmp_path / "job" / "project"
    workdir.mkdir(parents=True)
    context = EngineContext(conventions=PromptLibrary().conventions(), skill_dirs=[s.path for s in engine_skills()])
    asyncio.run(engine.prepare_workspace(workdir, context))
    request = EngineRequest(
        purpose="live_probe",
        workdir=workdir,
        state_dir=tmp_path / "job" / "state",
        prompt="Create hello.py containing a function hello() that returns the string 'hi'. Do nothing else.",
        max_turns=6,
        timeout_s=240,
    )

    result = asyncio.run(engine.run(request))

    assert result.status == EngineStatus.OK, result.error_message
    assert "hello.py" in result.changed_files
    assert "def hello" in (workdir / "hello.py").read_text()
