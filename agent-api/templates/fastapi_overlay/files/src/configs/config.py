from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    app_name: str = "{{PROJECT_NAME}}"
    port: int = 8000
    db_url: str
    cors_origins: str = "*"  # comma-separated
    rate_limit_default: str = "120/minute"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


config = Config()
