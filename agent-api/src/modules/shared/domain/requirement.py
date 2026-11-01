"""Requirement input for drafting (Stories 2.4, 12.4): plain text or Markdown, typed or from a `.md` / `.txt` file.

Pure checks shared by the API and the draft runner, so a file the browser accepted is checked again on the server.
"""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

RequirementFormat = Literal["text", "markdown"]

TEXT_EXTENSIONS: dict[str, RequirementFormat] = {".md": "markdown", ".markdown": "markdown", ".txt": "text"}
MIN_CHARS = 20
# Control characters other than tab, newline and carriage return mean the "text" is really binary content.
_ALLOWED_CONTROL = {"\t", "\n", "\r"}


class RequirementError(ValueError):
    pass


@dataclass(frozen=True)
class Requirement:
    text: str
    format: RequirementFormat
    file_name: str | None = None

    @property
    def artifact_name(self) -> str:
        return "requirement.md" if self.format == "markdown" else "requirement.txt"


def check_requirement(
    text: str | None,
    max_bytes: int,
    file_name: str | None = None,
    requested_format: RequirementFormat | None = None,
) -> Requirement:
    """Raises RequirementError with a message for the user; returns the text with normalised line endings."""
    name = None
    if file_name:
        name = PurePosixPath(file_name.replace("\\", "/")).name[:255]
        extension = PurePosixPath(name).suffix.lower()
        if extension not in TEXT_EXTENSIONS:
            allowed = ", ".join(TEXT_EXTENSIONS)
            raise RequirementError(f"'{name}' is not a text requirement; use a {allowed} file")
    if text is None or not text.strip():
        raise RequirementError("The requirement is empty")
    if len(text.encode("utf-8", errors="surrogatepass")) > max_bytes:
        raise RequirementError(f"The requirement is larger than {max_bytes // 1024} KB")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RequirementError("The requirement is not valid UTF-8 text") from exc
    if any(ord(ch) < 32 and ch not in _ALLOWED_CONTROL or ch == "\x7f" for ch in text):
        raise RequirementError("The requirement contains binary content; upload a plain text or Markdown file")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").removeprefix("﻿").strip() + "\n"
    if len(normalized.strip()) < MIN_CHARS:
        raise RequirementError(f"Describe what to build in at least {MIN_CHARS} characters")
    fmt: RequirementFormat = requested_format or (
        TEXT_EXTENSIONS[PurePosixPath(name).suffix.lower()] if name else "text"
    )
    return Requirement(text=normalized, format=fmt, file_name=name)


def validate_requirement(
    text: str | None,
    file_name: str | None = None,
    requested_format: RequirementFormat | None = None,
    max_bytes: int | None = None,
) -> Requirement:
    """Convenience helper that converts RequirementError to UnprocessableEntityException."""
    from src.configs import config
    from src.libs.exceptions import ErrorCode, UnprocessableEntityException

    try:
        return check_requirement(
            text,
            max_bytes if max_bytes is not None else config.requirement_max_bytes,
            file_name,
            requested_format,
        )
    except RequirementError as exc:
        raise UnprocessableEntityException(str(exc), code=ErrorCode.REQUIREMENT_INVALID) from exc
