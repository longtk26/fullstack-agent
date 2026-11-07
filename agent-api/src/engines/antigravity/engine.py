import json
import shutil
from pathlib import Path
from typing import Literal

from src.libs.redaction import Redactor

from ..cli_engine import CliEngine, Invocation
from ..port import EngineContext, EngineErrorReason, EngineHealth, EngineRequest, EngineResult, EngineStatus
from ..process import ProcessOutcome, ProcessSpec, SubprocessRunner, base_env
from ..workspace import install_skills, remove_path, write_managed_section
from .stream import AntigravityStreamParser

# Headless agy already soft-denies shell commands; the deny rules make it explicit and also cover
# network and MCP. Workspace file reads/writes are scoped strictly to the request's workdir (Story 18.4).
DENY_PERMISSIONS = ["command(*)", "read_url(*)", "execute_url(*)", "mcp(*)", "write_file(.agents/)"]
UNTRUSTED_WORKSPACE_CONFIG = [".agents/hooks.json", ".agents/rules"]
# Marker files of a container runtime: the agy account login lives in the host's OS keyring.
CONTAINER_MARKERS = (Path("/.dockerenv"), Path("/run/.containerenv"))
# What agy prints on stderr when a turn ends because headless mode auto-denied a permission: its result event still
# says SUCCESS (with an empty response), so the run must not count as done (a module completed with nothing written).
NO_OUTPUT = "no output produced"


def _in_container() -> bool:
    return any(marker.exists() for marker in CONTAINER_MARKERS)


class AntigravityEngine(CliEngine):
    """Antigravity CLI (`agy`) in stream-json stdin mode — the documented way to drive it from a process."""

    name = "antigravity"

    def __init__(
        self,
        *,
        binary: str,
        auth: Literal["gemini_api_key", "adc", "account"],
        gemini_api_key: str | None,
        google_application_credentials: str | None,
        model: str | None,
        allowed_root: Path,
        redactor: Redactor,
        default_timeout_s: float,
        default_max_turns: int,
        max_output_bytes: int,
        purpose_models: dict[str, str] | None = None,
        runner: SubprocessRunner | None = None,
    ):
        super().__init__(allowed_root, redactor, default_timeout_s, default_max_turns, max_output_bytes, runner)
        self.binary = binary
        self.auth = auth
        self.gemini_api_key = gemini_api_key
        self.google_application_credentials = google_application_credentials
        self.model = model
        self.purpose_models = purpose_models or {}
        # workdir → the skills' source folders: agy may find a skill up the tree (a workspace inside the agent's
        # repo) as well as the workspace's copy; both are the same files, readable
        self._skill_sources: dict[str, list[str]] = {}

    async def health(self) -> EngineHealth:
        if shutil.which(self.binary) is None:
            return EngineHealth(name=self.name, available=False, reason=f"'{self.binary}' not found on PATH")
        if self.auth == "gemini_api_key" and not self.gemini_api_key:
            return EngineHealth(name=self.name, available=False, reason="Set GEMINI_API_KEY (or ANTIGRAVITY_AUTH=adc)")
        if self.auth == "adc" and not self.google_application_credentials:
            return EngineHealth(name=self.name, available=False, reason="Set GOOGLE_APPLICATION_CREDENTIALS for ADC")
        if self.auth == "account":
            # `agy` signed in with a Google account keeps its token in the OS keyring (D-Bus secret service), which
            # only exists on the host. Use it for a host dev worker; containers need GEMINI_API_KEY or ADC.
            if _in_container():
                reason = "ANTIGRAVITY_AUTH=account needs the host keyring; use GEMINI_API_KEY or ADC in Docker"
                return EngineHealth(name=self.name, available=False, reason=reason)
            return EngineHealth(name=self.name, available=True, reason="Uses the agy account login on this machine")
        return EngineHealth(name=self.name, available=True)

    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        install_skills(context.skill_dirs, workdir / ".agents" / "skills")
        self._skill_sources[str(workdir.resolve())] = [str(Path(d).resolve()) for d in context.skill_dirs]
        body = context.conventions
        if (workdir / "CLAUDE.md").exists():
            body += "\n\nThe project guide in `CLAUDE.md` (repository root) applies to you as well; read it first."
        write_managed_section(workdir / "AGENTS.md", body)

    def build_invocation(self, request: EngineRequest, home: Path, max_turns: int, timeout_s: float) -> Invocation:
        for relative in UNTRUSTED_WORKSPACE_CONFIG:
            remove_path(request.workdir / relative)
        workdir = str(request.workdir.resolve())
        skills = [f"read_file({source})" for source in self._skill_sources.get(workdir, [])]
        permissions = {
            "allow": [f"read_file({workdir})", f"write_file({workdir})", *skills],
            "deny": list(DENY_PERMISSIONS),
        }
        settings: dict = {"permissions": permissions, "enableTerminalSandbox": True}
        if self.auth == "gemini_api_key":
            settings["modelProvider"] = "gemini"  # GEMINI_API_KEY alone is ignored without this

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
        model = request.model or self.purpose_models.get(request.purpose) or self.model
        if model:
            argv += ["--model", model]
        if self.auth == "account":
            # The account login belongs to the user's real home (on macOS a scratch HOME fails with "authentication
            # required"), so keep HOME and pass the settings for this session only, leaving the user's own alone.
            argv += ["--settings", json.dumps(settings)]
            home = Path.home()
        else:
            settings_dir = home / ".gemini" / "antigravity-cli"
            settings_dir.mkdir(parents=True, exist_ok=True)
            (settings_dir / "settings.json").write_text(json.dumps(settings, indent=2))
        env = base_env(
            HOME=str(home),
            GEMINI_API_KEY=self.gemini_api_key if self.auth == "gemini_api_key" else None,
            AGY_ADC_AUTH="true" if self.auth == "adc" else None,
            GOOGLE_APPLICATION_CREDENTIALS=self.google_application_credentials if self.auth == "adc" else None,
        )
        message = {"event": "user", "message": {"content": request.prompt}}
        stdin = (json.dumps(message) + "\n").encode()  # stdin is closed after this one turn, so agy exits
        return Invocation(argv=argv, env=env, stdin=stdin, parser=AntigravityStreamParser(max_turns, model))

    def redact_argv(self, argv: list[str]) -> list[str]:
        return list(argv)

    def _normalize(self, request: EngineRequest, parsed, outcome: ProcessOutcome, spec: ProcessSpec) -> EngineResult:
        result = super()._normalize(request, parsed, outcome, spec)
        if result.status != EngineStatus.OK:
            return result
        notice = _no_output_notice(spec.stderr_path)
        if notice is None:
            return result
        return result.model_copy(
            update={
                "status": EngineStatus.CLI_ERROR,
                "error_reason": EngineErrorReason.CRASH,
                "error_message": self.redactor.redact(notice),
            }
        )


def _no_output_notice(stderr_path: Path) -> str | None:
    """agy's "no output produced — a tool required the … permission …" line, when the turn ended that way."""
    try:
        text = stderr_path.read_text(errors="replace")[-8000:]
    except OSError:
        return None
    line = next((line for line in reversed(text.splitlines()) if NO_OUTPUT in line.lower()), None)
    return line.strip()[:500] if line else None
