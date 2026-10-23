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

    workspace_root: str = "/tmp/bga/workspaces"
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
