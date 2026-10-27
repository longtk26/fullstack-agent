import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from src.configs.config import config

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}
# Fields every log line of the current task carries, e.g. generation_id and trace_id while a job runs (NFR 8.5).
log_context: ContextVar[dict[str, Any] | None] = ContextVar("bga_log_context", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(log_context.get() or {})
        payload.update({key: value for key, value in record.__dict__.items() if key not in _RESERVED})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(config.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
