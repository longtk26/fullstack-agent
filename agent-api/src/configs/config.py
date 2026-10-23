from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EXAMPLE_JWT_SECRET = "change-me-to-a-long-random-string"


class Config(BaseSettings):
    app_name: str = "Backend Generation Agent"
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
    claude_code_model: str | None = None
    anthropic_api_key: str | None = None
    claude_credentials_file: str | None = None

    antigravity_bin: str = "agy"
    antigravity_model: str | None = None
    antigravity_auth: Literal["gemini_api_key", "adc"] = "gemini_api_key"
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("jwt_secret")
    @classmethod
    def _reject_weak_jwt_secret(cls, value: str) -> str:
        if not value or value == EXAMPLE_JWT_SECRET or len(value) < 32:
            raise ValueError("JWT_SECRET must be set to a random string of at least 32 characters")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


config = Config()
