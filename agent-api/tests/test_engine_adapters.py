import asyncio
import json
from pathlib import Path

import pytest

from src.engines import EngineContext, EngineErrorReason, EngineEventKind, EngineRequest, EngineStatus
from src.engines.antigravity import AntigravityEngine
from src.engines.claude_code import ClaudeCodeEngine
from src.engines.claude_code.stream import ClaudeStreamParser
from src.engines.workspace import WorkspaceViolation
from src.libs.redaction import Redactor

BIN = Path(__file__).parent / "fixtures" / "engines" / "bin"
FIXTURES = Path(__file__).parent / "fixtures" / "engines"
SECRET = "sk-ant-api03-SECRETSECRETSECRET"


@pytest.fixture
def root(tmp_path):
    (tmp_path / "job" / "project").mkdir(parents=True)
    return tmp_path


def _limits(root):
    return {
        "allowed_root": root,
        "redactor": Redactor([SECRET]),
        "default_timeout_s": 10,
        "default_max_turns": 5,
        "max_output_bytes": 2_000_000,
    }


def _claude(root, **overrides):
    values = {"binary": str(BIN / "fake_claude"), "api_key": "test-key-123456", "credentials_file": None, "model": None}
    values.update(overrides)
    return ClaudeCodeEngine(**values, **_limits(root))


def _agy(root):
    return AntigravityEngine(
        binary=str(BIN / "fake_agy"),
        auth="gemini_api_key",
        gemini_api_key="gemini-test-key-123",
        google_application_credentials=None,
        model=None,
        **_limits(root),
    )


def _request(root, prompt="write hello", **overrides):
    values = {"purpose": "probe", "workdir": root / "job" / "project", "state_dir": root / "job" / "state"}
    values.update(overrides)
    return EngineRequest(prompt=prompt, **values)


def _run(engine, request):
    events = []

    async def on_event(event):
        events.append(event)

    return asyncio.run(engine.run(request, on_event)), events


def _record(root, engine_name):
    return json.loads((root / "job" / "state" / "engine-home" / engine_name / "record.json").read_text())


def test_claude_success_is_normalized(root):
    result, events = _run(_claude(root), _request(root))

    assert result.status == EngineStatus.OK
    assert result.turns == 2
    assert result.usage.input_tokens == 150 and result.usage.output_tokens == 20 and result.usage.cost_usd == 0.0123
    assert result.changed_files == ["hello.py"]
    assert result.session_id == "s-1"
    kinds = [event.kind for event in events]
    assert kinds == [
        EngineEventKind.SYSTEM,
        EngineEventKind.TOOL_USE,
        EngineEventKind.TOOL_RESULT,
        EngineEventKind.MESSAGE,
        EngineEventKind.USAGE,
    ]
    assert events[1].summary == "Write hello.py", "paths are workspace-relative"


def test_claude_invocation_is_isolated_and_restricted(root, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "worker-secret-should-not-leak")
    _run(_claude(root), _request(root, prompt="write hello"))
    record = _record(root, "claude_code")
    argv, env = record["argv"], record["env"]

    assert record["prompt"] == "write hello", "prompt goes over stdin"
    assert argv[argv.index("--tools") + 1] == "Read,Write,Edit,Glob,Grep,Skill"
    assert "Bash" in argv[argv.index("--disallowedTools") + 1]
    assert argv[argv.index("--permission-mode") + 1] == "acceptEdits"
    assert "--strict-mcp-config" in argv
    assert env["CLAUDE_CONFIG_DIR"].endswith("engine-home/claude_code/.claude")
    assert env["ANTHROPIC_API_KEY"] == "test-key-123456"
    assert "JWT_SECRET" not in env and "DB_URL" not in env


def test_claude_removes_planted_workspace_settings(root):
    project = root / "job" / "project"
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text('{"hooks": {"Stop": []}}')
    (project / ".mcp.json").write_text("{}")

    _run(_claude(root), _request(root))

    assert not (project / ".claude" / "settings.json").exists()
    assert not (project / ".mcp.json").exists()


def test_claude_copies_credentials_only_without_api_key(root, tmp_path):
    credentials = tmp_path / "creds.json"
    credentials.write_text('{"token": "x"}')

    _run(_claude(root, api_key=None, credentials_file=str(credentials)), _request(root))

    copied = root / "job" / "state" / "engine-home" / "claude_code" / ".claude" / ".credentials.json"
    assert copied.read_text() == '{"token": "x"}'
    assert oct(copied.stat().st_mode & 0o777) == "0o600"


@pytest.mark.parametrize(
    ("mode", "status", "reason"),
    [
        ("auth", EngineStatus.CLI_ERROR, EngineErrorReason.AUTH),
        ("max_turns", EngineStatus.LIMIT_EXCEEDED, EngineErrorReason.MAX_TURNS),
        ("crash", EngineStatus.CLI_ERROR, EngineErrorReason.CRASH),
    ],
)
def test_claude_failures_are_classified(root, mode, status, reason):
    result, _ = _run(_claude(root), _request(root, prompt=f"MODE={mode}"))

    assert (result.status, result.error_reason) == (status, reason)


def test_claude_output_flood_hits_the_limit(root):
    engine = _claude(root)
    engine.max_output_bytes = 200_000

    result, _ = _run(engine, _request(root, prompt="MODE=flood"))

    assert result.status == EngineStatus.LIMIT_EXCEEDED
    assert result.error_reason == EngineErrorReason.OUTPUT_LIMIT


def test_claude_cancel_terminates_the_run(root):
    engine = _claude(root)
    request = _request(root, prompt="MODE=sleep", timeout_s=30)

    async def scenario():
        task = asyncio.create_task(engine.run(request))
        await asyncio.sleep(1.0)
        assert await engine.cancel(request.invocation_id)
        return await task

    result = asyncio.run(scenario())

    assert result.status == EngineStatus.CANCELLED


def test_secrets_are_redacted_from_events_and_result(root):
    result, events = _run(_claude(root), _request(root, prompt="MODE=secret"))

    assert SECRET not in result.final_message
    assert all(SECRET not in event.summary for event in events)


def test_workdir_outside_the_root_is_rejected(root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")

    with pytest.raises(WorkspaceViolation):
        asyncio.run(_claude(root).run(_request(root, workdir=outside)))


def test_recorded_real_claude_stream_parses():
    parser = ClaudeStreamParser(max_turns=4)
    events = [e for line in (FIXTURES / "claude_stream_ok.jsonl").read_text().splitlines() for e in parser.feed(line)]

    assert parser.run.completed and not parser.run.is_error
    assert parser.run.turns == 2
    assert parser.run.usage.cost_usd > 0
    assert any(e.kind == EngineEventKind.TOOL_USE and e.data["tool"] == "Write" for e in events)


def test_antigravity_success_is_normalized(root):
    result, events = _run(_agy(root), _request(root))

    assert result.status == EngineStatus.OK
    assert result.session_id == "c-1"
    assert result.usage.input_tokens == 140 and result.usage.output_tokens == 25
    assert result.usage.cost_usd is None, "agy reports tokens only"
    assert result.changed_files == ["hello.py"]
    assert [e.summary for e in events if e.kind == EngineEventKind.MESSAGE] == ["Created hello.py."]
    assert any(e.summary == "write_file hello.py" for e in events)


def test_antigravity_invocation_uses_stream_stdin_and_api_key_settings(root):
    _run(_agy(root), _request(root, prompt="write hello"))
    record = _record(root, "antigravity")
    argv = record["argv"]

    assert record["prompt"] == "write hello"
    assert argv[argv.index("--input-format") + 1] == "stream-json"
    assert argv[argv.index("--mode") + 1] == "accept-edits"
    assert argv[argv.index("--print-timeout") + 1] == "10s"
    assert record["settings"]["modelProvider"] == "gemini"
    assert "command(*)" in record["settings"]["permissions"]["deny"]
    assert record["env"]["GEMINI_API_KEY"] == "gemini-test-key-123"


def test_antigravity_auth_failure_is_classified(root):
    result, _ = _run(_agy(root), _request(root, prompt="MODE=auth"))

    assert (result.status, result.error_reason) == (EngineStatus.CLI_ERROR, EngineErrorReason.AUTH)


def test_antigravity_turn_limit_stops_the_run(root):
    result, _ = _run(_agy(root), _request(root, prompt="MODE=many_turns", max_turns=2))

    assert (result.status, result.error_reason) == (EngineStatus.LIMIT_EXCEEDED, EngineErrorReason.MAX_TURNS)
    assert result.duration_ms < 1500


@pytest.mark.parametrize(
    ("factory", "skills_dir", "context_file"),
    [(_claude, ".claude/skills", "CLAUDE.md"), (_agy, ".agents/skills", "AGENTS.md")],
)
def test_prepare_workspace_installs_skill_and_conventions(root, tmp_path, factory, skills_dir, context_file):
    skill = tmp_path / "skills" / "fastapi-skills"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: fastapi-skills\n---\n")
    workdir = root / "job" / "project"

    asyncio.run(factory(root).prepare_workspace(workdir, EngineContext(conventions="RULES", skill_dirs=[skill])))

    assert (workdir / skills_dir / "fastapi-skills" / "SKILL.md").exists()
    assert "RULES" in (workdir / context_file).read_text()
