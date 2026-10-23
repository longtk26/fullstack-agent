import json
import shutil
from pathlib import Path
from typing import Literal

from src.libs.redaction import Redactor

from ..cli_engine import CliEngine, Invocation
from ..port import EngineContext, EngineHealth, EngineRequest
from ..process import SubprocessRunner, base_env
from ..workspace import install_skills, remove_path, write_managed_section
from .stream import AntigravityStreamParser

# Headless agy already soft-denies shell commands; the deny rules make it explicit and also cover
# network and MCP. Workspace file reads/writes stay allowed (agy's default).
PERMISSIONS = {
    "allow": ["read_file(*)", "write_file(*)"],
    "deny": ["command(*)", "read_url(*)", "execute_url(*)", "mcp(*)", "write_file(.agents/)"],
}
UNTRUSTED_WORKSPACE_CONFIG = [".agents/hooks.json", ".agents/rules"]


class AntigravityEngine(CliEngine):
    """Antigravity CLI (`agy`) in stream-json stdin mode — the documented way to drive it from a process."""

    name = "antigravity"

    def __init__(
        self,
        *,
        binary: str,
        auth: Literal["gemini_api_key", "adc"],
        gemini_api_key: str | None,
        google_application_credentials: str | None,
        model: str | None,
        allowed_root: Path,
        redactor: Redactor,
        default_timeout_s: float,
        default_max_turns: int,
        max_output_bytes: int,
        runner: SubprocessRunner | None = None,
    ):
        super().__init__(allowed_root, redactor, default_timeout_s, default_max_turns, max_output_bytes, runner)
        self.binary = binary
        self.auth = auth
        self.gemini_api_key = gemini_api_key
        self.google_application_credentials = google_application_credentials
        self.model = model

    async def health(self) -> EngineHealth:
        if shutil.which(self.binary) is None:
            return EngineHealth(name=self.name, available=False, reason=f"'{self.binary}' not found on PATH")
        if self.auth == "gemini_api_key" and not self.gemini_api_key:
            return EngineHealth(name=self.name, available=False, reason="Set GEMINI_API_KEY (or ANTIGRAVITY_AUTH=adc)")
        if self.auth == "adc" and not self.google_application_credentials:
            return EngineHealth(name=self.name, available=False, reason="Set GOOGLE_APPLICATION_CREDENTIALS for ADC")
        return EngineHealth(name=self.name, available=True)

    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        install_skills(context.skill_dirs, workdir / ".agents" / "skills")
        body = context.conventions
        if (workdir / "CLAUDE.md").exists():
            body += "\n\nThe project guide in `CLAUDE.md` (repository root) applies to you as well; read it first."
        write_managed_section(workdir / "AGENTS.md", body)

    def build_invocation(self, request: EngineRequest, home: Path, max_turns: int, timeout_s: float) -> Invocation:
        for relative in UNTRUSTED_WORKSPACE_CONFIG:
            remove_path(request.workdir / relative)
        settings_dir = home / ".gemini" / "antigravity-cli"
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings: dict = {"permissions": PERMISSIONS, "enableTerminalSandbox": True}
        if self.auth == "gemini_api_key":
            settings["modelProvider"] = "gemini"  # GEMINI_API_KEY alone is ignored without this
        (settings_dir / "settings.json").write_text(json.dumps(settings, indent=2))

        argv = [
            self.binary,
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--mode",
            "accept-edits",
            "--print-timeout",
            f"{int(timeout_s)}s",
        ]
        if self.model:
            argv += ["--model", self.model]
        env = base_env(
            HOME=str(home),
            GEMINI_API_KEY=self.gemini_api_key if self.auth == "gemini_api_key" else None,
            AGY_ADC_AUTH="true" if self.auth == "adc" else None,
            GOOGLE_APPLICATION_CREDENTIALS=self.google_application_credentials if self.auth == "adc" else None,
        )
        message = {"event": "user", "message": {"content": request.prompt}}
        stdin = (json.dumps(message) + "\n").encode()  # stdin is closed after this one turn, so agy exits
        return Invocation(argv=argv, env=env, stdin=stdin, parser=AntigravityStreamParser(max_turns))

    def redact_argv(self, argv: list[str]) -> list[str]:
        return list(argv)
