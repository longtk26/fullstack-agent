"""`BACKEND_TESTS` (2026-11-06): run_validation runs a generated backend's own pytest suite only when it is on (the
tests suite sets it, `conftest.py`); off, the `tests` check is the smoke calls alone (every contract scenario against
the running app): only whether the API works."""

import asyncio
from pathlib import Path

from src.configs import config
from src.orchestrator.backend.validation import CheckResult, SandboxValidationRunner, ValidationRequest


class _Sandbox:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def reset_database(self, name: str) -> None:
        self.commands.append(f"reset {name}")

    async def exec(self, command: str, timeout_s: int = 0):  # pragma: no cover - only reached with the tests on
        self.commands.append(command)
        raise AssertionError("pytest must not run")


def _runner_with_smoke(result: CheckResult | None) -> SandboxValidationRunner:
    runner = SandboxValidationRunner.__new__(SandboxValidationRunner)

    async def smoke(request):
        return result

    runner._smoke = smoke  # type: ignore[method-assign]
    return runner


def _request(tmp_path: Path, sandbox: _Sandbox) -> ValidationRequest:
    return ValidationRequest(project=tmp_path, plan={}, run_tests=True, sandbox=sandbox, smoke_contract={"paths": {}})


def test_off_runs_the_smoke_calls_only(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "backend_tests", False)
    sandbox = _Sandbox()
    smoke = CheckResult(check="tests", status="passed", summary="73 scenario(s) answered as the contract says")
    result = asyncio.run(_runner_with_smoke(smoke)._tests(_request(tmp_path, sandbox)))
    assert sandbox.commands == [], "no pytest, no test database"
    assert result.status == "passed"
    assert result.summary == "API: 73 scenario(s) answered as the contract says"


def test_off_with_nothing_to_call_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "backend_tests", False)
    result = asyncio.run(_runner_with_smoke(None)._tests(_request(tmp_path, _Sandbox())))
    assert result.status == "skipped" and "BACKEND_TESTS=false" in result.summary


def test_a_failing_smoke_call_still_fails_the_check(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "backend_tests", False)
    smoke = CheckResult(check="tests", status="failed", summary="2 of 28 smoke call(s) answered wrongly")
    result = asyncio.run(_runner_with_smoke(smoke)._tests(_request(tmp_path, _Sandbox())))
    assert result.status == "failed" and "answered wrongly" in result.summary


def test_the_default_is_off_and_the_suite_turns_it_on():
    from src.configs.config import Config

    assert Config.model_fields["backend_tests"].default is False
    assert config.backend_tests is True  # conftest: the validation and repair tests need the pytest suite
