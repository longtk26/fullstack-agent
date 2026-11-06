from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from src.configs import config as default_config
from src.libs.redaction import default_redactor

from .antigravity import AntigravityEngine
from .claude_code import ClaudeCodeEngine
from .fake_engine import FakeEngine, demo_scenario
from .gemini_api import GeminiApiEngine
from .port import EngineContext, EngineHealth, ICodeEngine
from .prompts import PromptLibrary
from .workspace import directory_sha256


class UnknownEngineError(LookupError):
    pass


class EngineRegistry:
    def __init__(self, engines: list[ICodeEngine], default: str, draft_default: str | None = None):
        self.engines = {engine.name: engine for engine in engines}
        self.default = default
        # Story 18.10: the engine that drafts specs when a request names none; Story 22.8: always one that drafts
        # (an API engine, or the fake), never a CLI engine. None: no engine can draft (set GEMINI_API_KEY).
        drafters = self.draft_engine_names()
        if draft_default in drafters:
            self.draft_default: str | None = draft_default
        elif default in drafters:
            self.draft_default = default
        else:
            self.draft_default = next((name for name in drafters if name != "fake"), drafters[0] if drafters else None)

    def names(self) -> list[str]:
        return list(self.engines)

    def draft_engine_names(self) -> list[str]:
        """Engines that may draft specs (Story 22.8: the API engines and the fake; CLI engines only write code)."""
        return [name for name, engine in self.engines.items() if engine.drafts]

    def check_draft_engine(self, name: str | None) -> str:
        """The engine a draft runs on, or a 422 that says why it cannot (Story 22.8)."""
        from src.libs.exceptions import ErrorCode, UnprocessableEntityException

        if name is None:
            raise UnprocessableEntityException(
                "No engine can draft specs: drafting runs on the Gemini API engine (set GEMINI_API_KEY)",
                code=ErrorCode.ENGINE_UNKNOWN,
            )
        if name not in self.engines:
            raise UnprocessableEntityException(f"Engine '{name}' is not enabled", code=ErrorCode.ENGINE_UNKNOWN)
        if name not in self.draft_engine_names():
            allowed = ", ".join(self.draft_engine_names()) or "none: set GEMINI_API_KEY"
            raise UnprocessableEntityException(
                f"Engine '{name}' writes code only; drafts run on an API engine ({allowed})",
                code=ErrorCode.ENGINE_UNKNOWN,
            )
        return name

    def code_engine_names(self) -> list[str]:
        """Engines that can write a project (an API engine only drafts, Story 18.10)."""
        return [name for name, engine in self.engines.items() if not engine.drafts_only]

    def get(self, name: str | None = None) -> ICodeEngine:
        key = name or self.default
        if key not in self.engines:
            raise UnknownEngineError(f"Unknown engine '{key}'. Available: {', '.join(self.engines)}")
        return self.engines[key]

    async def health(self) -> list[EngineHealth]:
        return [await engine.health() for engine in self.engines.values()]


class SkillInfo(BaseModel):
    name: str
    path: Path
    sha256: str


def engine_skills(cfg=default_config, names: list[str] | None = None) -> list[SkillInfo]:
    root = Path(cfg.engine_skills_dir)
    return [
        SkillInfo(name=name, path=root / name, sha256=directory_sha256(root / name))
        for name in (cfg.engine_skills if names is None else names)
        if (root / name / "SKILL.md").is_file()
    ]


def build_engine_context(prompts: PromptLibrary, cfg=default_config) -> EngineContext:
    return EngineContext(conventions=prompts.conventions(), skill_dirs=[skill.path for skill in engine_skills(cfg)])


def build_frontend_engine_context(prompts: PromptLibrary, cfg=default_config) -> EngineContext:
    """The frontend lane's engine context: nextjs-skills and the frontend project rules (Story 13.2)."""
    skills = engine_skills(cfg, cfg.frontend_engine_skills)
    return EngineContext(conventions=prompts.frontend_conventions(), skill_dirs=[skill.path for skill in skills])


def build_engine_registry(cfg=default_config) -> EngineRegistry:
    root = Path(cfg.workspace_root)
    redactor = default_redactor()
    limits = {
        "allowed_root": root,
        "redactor": redactor,
        "default_timeout_s": cfg.engine_timeout_seconds,
        "default_max_turns": cfg.engine_max_turns,
        "max_output_bytes": cfg.engine_max_output_bytes,
    }
    engines: list[ICodeEngine] = [
        ClaudeCodeEngine(
            binary=cfg.claude_code_bin,
            api_key=cfg.anthropic_api_key,
            credentials_file=cfg.claude_credentials_file,
            model=cfg.claude_code_model,
            purpose_models=cfg.claude_code_purpose_models,
            **limits,
        ),
        AntigravityEngine(
            binary=cfg.antigravity_bin,
            auth=cfg.antigravity_auth,
            gemini_api_key=cfg.gemini_api_key,
            google_application_credentials=cfg.google_application_credentials,
            model=cfg.antigravity_model,
            purpose_models=cfg.antigravity_purpose_models,
            **{
                **limits,
                "default_timeout_s": cfg.antigravity_timeout_seconds,
                "default_max_turns": cfg.antigravity_max_turns,
            },
        ),
    ]
    engines.append(
        GeminiApiEngine(
            api_key=cfg.gemini_api_key,
            model=cfg.gemini_api_model,
            allowed_root=root,
            redactor=redactor,
            default_timeout_s=cfg.gemini_api_timeout_seconds,
            max_output_tokens=cfg.gemini_api_max_output_tokens,
            thinking_budget=cfg.gemini_api_thinking_budget,
        )
    )
    if cfg.enable_fake_engine:
        engines.append(FakeEngine(allowed_root=root, scenario=demo_scenario(cfg.fake_engine_delay_seconds)))
    return EngineRegistry(engines, default=cfg.default_engine, draft_default=cfg.draft_engine_name)


@lru_cache
def get_engine_registry() -> EngineRegistry:
    return build_engine_registry()
