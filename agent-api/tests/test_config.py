import pytest
from pydantic import ValidationError

from src.configs.config import EXAMPLE_JWT_SECRET, Config


@pytest.mark.parametrize("secret", ["", EXAMPLE_JWT_SECRET, "too-short"])
def test_rejects_missing_example_or_short_jwt_secret(secret):
    with pytest.raises(ValidationError):
        Config(db_url="postgresql+psycopg://x", jwt_secret=secret)


def test_parses_cors_origins():
    cfg = Config(db_url="postgresql+psycopg://x", jwt_secret="s" * 32, cors_origins="http://a, http://b,")

    assert cfg.cors_origin_list == ["http://a", "http://b"]


def test_blank_engine_models_fall_back_to_the_defaults():
    from src.configs.config import Config

    defaults = Config()
    blank = Config(claude_code_model="", antigravity_model="")

    assert defaults.claude_code_model == blank.claude_code_model == "claude-sonnet-5-5"
    assert defaults.antigravity_model == blank.antigravity_model == "gemini-3.8-flash-medium"
    assert Config(antigravity_model="gemini-4-argon-high").antigravity_model == "gemini-4-argon-high"
