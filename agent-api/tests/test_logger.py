import json
import logging

from src.configs.logger import JsonFormatter


def test_json_formatter_includes_extra_context():
    record = logging.LogRecord("bga", logging.INFO, __file__, 1, "job %s", ("started",), None)
    record.generation_id = "gen_123"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["msg"] == "job started"
    assert payload["level"] == "INFO"
    assert payload["generation_id"] == "gen_123"
