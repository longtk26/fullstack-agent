import json
import logging
import sys
from datetime import UTC, datetime

from src.configs.config import config

_RESERVED = set(vars(logging.makeLogRecord({})))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update({key: value for key, value in vars(record).items() if key not in _RESERVED})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(config.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    """Structured logger: pass context as `extra={...}`, e.g. logger.info("task created", extra={"task_id": id})."""
    return logging.getLogger(name)
