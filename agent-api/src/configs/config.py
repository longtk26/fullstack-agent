from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EXAMPLE_JWT_SECRET = "change-me-to-a-long-random-string"


class Config(BaseSettings):
    app_name: str = "Fullstack Generation Agent"
    port: int = 8000
    log_level: str = "INFO"

    db_url: str
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    auth_cookie_name: str = "bga_token"
    seed_users: str = ""

    cors_origins: str = "http://localhost:3100"
    rate_limit_storage_uri: str = "memory://"
    rate_limit_login: str = "10/minute"

    spec_max_bytes: int = 1_000_000
    frontend_import_max_bytes: int = 5_000_000

    default_engine: str = "claude_code"
    enable_fake_engine: bool = True
    fake_engine_delay_seconds: float = 0.3
    engine_timeout_seconds: int = 900
    engine_max_turns: int = 40
    engine_max_output_bytes: int = 20_000_000
    engine_skills_dir: str = "/opt/bga/skills"
    engine_skills: list[str] = ["fastapi-skills"]

    claude_code_bin: str = "claude"
    claude_code_model: str = "claude-sonnet-5-5"
    anthropic_api_key: str | None = None
    claude_credentials_file: str | None = None

    antigravity_bin: str = "agy"
    antigravity_model: str = "gemini-3.8-flash-medium"  # `agy models` lists the choices
    # agy streams one agent response per tool call, so its "turns" are much smaller than Claude's.
    antigravity_max_turns: int = 150
    antigravity_timeout_seconds: int = 2400
    antigravity_job_timeout_seconds: int = 10800  # a full agy run takes far longer than the 30 min default
    antigravity_auth: Literal["gemini_api_key", "adc", "account"] = "gemini_api_key"
    gemini_api_key: str | None = None
    google_application_credentials: str | None = None

    workspace_root: str = "/tmp/bga/workspaces"
    workspace_max_mb: int = 500
    workspace_retention_hours: int = 72

    template_dir: str = "/opt/bga/fastapi-template"

    sandbox_enabled: bool = True
    sandbox_image: str = "bga-runner:1"
    sandbox_db_image: str = "postgres:18"
    sandbox_cpus: float = 1.0
    sandbox_memory: str = "1g"
    sandbox_pids: int = 256
    sandbox_command_timeout_seconds: int = 300
    sandbox_output_bytes: int = 2_000_000
    sandbox_egress_network: str = "bga-sbx-egress"

    generator_version: str = "0.7.0"
    # Shared by worker (writes) and API (downloads); outlives workspaces.
    artifact_root: str = "/tmp/bga/artifacts"

    # Preview containers (Epic 7): each COMPLETED backend runs as its own container, local-only.
    preview_enabled: bool = True
    preview_port_range: str = "18000-18099"
    preview_bind_host: str = "127.0.0.1"
    preview_public_host: str = "localhost"
    preview_cors_origins: str = "http://localhost:3100"
    preview_max_running: int = 3
    preview_evict: bool = True
    preview_ttl_hours: float = 2
    preview_cpus: float = 1.0
    preview_memory: str = "512m"
    preview_build_timeout_seconds: int = 600
    preview_health_timeout_seconds: int = 60
    preview_reconcile_seconds: int = 300
    preview_command_timeout_seconds: float = 8  # API waiting for the worker (logs); below the Redis socket timeout

    job_timeout_seconds: int = 1800
    worker_lease_ttl_seconds: int = 30
    worker_max_resumes: int = 2
    worker_shutdown_grace_seconds: int = 60
    reaper_interval_seconds: int = 60
    events_cap: int = 5000
    checkpoint_schema: str = "langgraph"
    worker_concurrency: int = 2
    worker_heartbeat_file: str = "/tmp/bga-worker.heartbeat"
    worker_heartbeat_seconds: int = 10
    # Engines this worker runs (comma-separated; empty = all registered). `make up` gives Antigravity's account
    # login to a host worker, because the login lives in the desktop keyring that containers cannot reach.
    worker_engines: str = ""
    # Whether this worker drives preview containers (commands, TTL, reconcile); only one kind of worker should.
    preview_worker: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("claude_code_model", "antigravity_model", mode="before")
    @classmethod
    def _blank_model_means_default(cls, value, info):
        # Compose passes `CLAUDE_CODE_MODEL=` when .env leaves it empty; that means "the default", not "none".
        return cls.model_fields[info.field_name].default if value in (None, "") else value

    @field_validator("jwt_secret")
    @classmethod
    def _reject_weak_jwt_secret(cls, value: str) -> str:
        if not value or value == EXAMPLE_JWT_SECRET or len(value) < 32:
            raise ValueError("JWT_SECRET must be set to a random string of at least 32 characters")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def worker_engine_list(self) -> list[str]:
        return [name.strip() for name in self.worker_engines.split(",") if name.strip()]

    @property
    def preview_ports(self) -> range:
        low, _, high = self.preview_port_range.partition("-")
        return range(int(low), int(high or low) + 1)


config = Config()
