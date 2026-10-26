import re
from collections.abc import Iterable
from typing import Any

MASK = "[REDACTED]"
_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), MASK),
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), MASK),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-~+/=]{8,}"), r"\g<1>" + MASK),
    (re.compile(r"(?i)((?:postgres(?:ql)?|redis|mysql)(?:\+\w+)?://[^:/\s@]+:)[^@\s]+(@)"), r"\g<1>" + MASK + r"\g<2>"),
    (re.compile(r'(?i)("?(?:password|passwd|secret|api[_-]?key|token)"?\s*[:=]\s*"?)[^"\s,}]{4,}'), r"\g<1>" + MASK),
]


class Redactor:
    """Masks known secret values and common credential shapes before text leaves the process."""

    def __init__(self, secrets: Iterable[str | None] = ()):
        self._secrets = sorted({s for s in secrets if s and len(s) >= 8}, key=len, reverse=True)

    def with_secrets(self, *secrets: str | None) -> "Redactor":
        return Redactor([*self._secrets, *secrets])

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, MASK)
        for pattern, replacement in _PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def redact_obj(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, dict):
            return {key: self.redact_obj(item) for key, item in value.items()}
        if isinstance(value, list | tuple):
            return [self.redact_obj(item) for item in value]
        return value


def default_redactor() -> Redactor:
    from src.configs import config

    return Redactor([config.jwt_secret, config.anthropic_api_key, config.gemini_api_key])
