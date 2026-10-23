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
