"""Static nextjs-skills checker for generated frontends (Story 13.4, `conventions` check).

Runs on the files the engine writes (pages, shell, sections, features); generator-owned files are only compared
with their recorded hashes. Each violation is `{file, line, rule, message, hint}`, like the backend checker.
"""

import re
from pathlib import Path
from typing import Any

from src.orchestrator.frontend_scaffold import OWNED_INFO, changed_owned

SKIP_DIRS = {"node_modules", ".next", "out", ".git", ".bga", ".claude", ".agents", "test-results", "playwright-report"}
OWNED_PREFIXES = ("src/components/ui/", "src/lib/", "src/mocks/", "src/content/", "tests/")
WILDCARD_REACT = re.compile(r'^\s*import\s+\*\s+as\s+React\s+from\s+["\']react["\']', re.MULTILINE)
COLOR_CLASS = re.compile(r"\b[a-z-]+-\[(#|rgb|rgba|hsl|hsla|oklch|oklab|lab|lch)\b")
STYLE_COLOR = re.compile(r"\b(color|background|backgroundColor|borderColor|fill|stroke)\s*:\s*[\"'`](#|rgb|hsl|oklch)")
HEX_IN_CLASS = re.compile(r"className=[\"'{][^\"'}]*#[0-9a-fA-F]{3,8}\b")
TOKEN_STORAGE = re.compile(
    r"(localStorage|sessionStorage)\s*\.\s*setItem\s*\(\s*[\"'`][^\"'`]*(token|jwt|auth|bearer|session)", re.I
)
NETWORK = re.compile(r"\b(fetch\s*\(|axios\b|new\s+XMLHttpRequest|new\s+WebSocket|new\s+EventSource)")
LOW_LEVEL_API = re.compile(r"from\s+[\"']@/lib/api/(client|operations)[\"']")
TYPE_DECL = re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^=]*>)?\s*=", re.MULTILINE)
INTERFACE_DECL = re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
COMPONENT = re.compile(r"^export (?:default )?function ([A-Z][A-Za-z0-9]*)\s*\(", re.MULTILINE)
HOOK_IMPORT = re.compile(r"from\s+[\"'][^\"']*/use-[a-z0-9-]+[\"']")
MAX_LOGIC_LINES = 30


def _violation(file: str, line: int | None, rule: str, message: str, hint: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"file": file, "line": line, "rule": rule, "message": message}
    if hint:
        item["hint"] = hint
    return item


def _line(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _engine_files(project: Path) -> list[Path]:
    """TypeScript files the engine may write: everything under src/ except generator-owned paths."""
    owned: set[str] = set()
    if (project / OWNED_INFO).exists():
        import json

        owned = set(json.loads((project / OWNED_INFO).read_text()))
    files = []
    for path in sorted((project / "src").rglob("*")):
        relative = path.relative_to(project).as_posix()
        if not path.is_file() or path.suffix not in (".ts", ".tsx") or SKIP_DIRS & set(path.parts):
            continue
        if relative in owned or relative.startswith(OWNED_PREFIXES):
            continue
        files.append(path)
    return files


def _logic_lines(text: str, start: int) -> int:
    """Non-blank, non-comment lines between a component's signature and its top-level `return (`."""
    body = text[start:]
    end = re.search(r"^  return[ (]", body, re.MULTILINE)
    if end is None:
        return 0
    lines = body[: end.start()].splitlines()[1:]
    return sum(1 for line in lines if line.strip() and not line.strip().startswith(("//", "/*", "*")))


def check_frontend_conventions(project: Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for path in _engine_files(project):
        relative = path.relative_to(project).as_posix()
        text = path.read_text(errors="replace")
        for match in WILDCARD_REACT.finditer(text):
            violations.append(
                _violation(
                    relative,
                    _line(text, match.start()),
                    "react-imports",
                    "wildcard React import",
                    'Use named imports: import { useState } from "react"',
                )  # fmt: skip
            )
        for pattern in (COLOR_CLASS, STYLE_COLOR, HEX_IN_CLASS):
            for match in pattern.finditer(text):
                violations.append(
                    _violation(
                        relative,
                        _line(text, match.start()),
                        "design-tokens",
                        "hard-coded colour",
                        "Use design tokens from globals.css (bg-primary, text-muted-foreground, …)",
                    )  # fmt: skip
                )
        for match in TOKEN_STORAGE.finditer(text):
            violations.append(
                _violation(
                    relative,
                    _line(text, match.start()),
                    "token-storage",
                    "credentials stored in browser storage",
                    "Use cookies via Server Actions",
                )  # fmt: skip
            )
        for match in NETWORK.finditer(text):
            violations.append(
                _violation(
                    relative,
                    _line(text, match.start()),
                    "network",
                    "network call outside the generated client",
                    "Use the React Query hooks from @/lib/api/queries",
                )  # fmt: skip
            )
        for match in LOW_LEVEL_API.finditer(text):
            violations.append(
                _violation(
                    relative,
                    _line(text, match.start()),
                    "network",
                    "components must not import the low-level API client",
                    "Use the React Query hooks from @/lib/api/queries",
                )  # fmt: skip
            )
        for match in INTERFACE_DECL.finditer(text):
            violations.append(
                _violation(
                    relative,
                    _line(text, match.start()),
                    "types",
                    f"interface {match.group(1)}",
                    "Use `type` instead of `interface`",
                )  # fmt: skip
            )
        for match in TYPE_DECL.finditer(text):
            name = match.group(1)
            line = _line(text, match.start())
            if name.endswith("Props"):
                if re.match(r"^T[A-Z]", name):
                    violations.append(_violation(relative, line, "types", f"{name}: prop types have no T prefix"))
            elif not re.match(r"^T[A-Z]", name):
                violations.append(
                    _violation(relative, line, "types", f"{name}: standalone types need the T prefix", f"T{name}")
                )
        if path.suffix == ".tsx" and not HOOK_IMPORT.search(text):
            for match in COMPONENT.finditer(text):
                lines = _logic_lines(text, match.start())
                if lines > MAX_LOGIC_LINES:
                    violations.append(
                        _violation(
                            relative,
                            _line(text, match.start()),
                            "custom-hooks",
                            f"{match.group(1)} has {lines} lines of logic",
                            "Move the logic to a companion use-*.ts hook",
                        )  # fmt: skip
                    )
        if path.name == "page.tsx" and "metadata" not in text:
            violations.append(
                _violation(
                    relative,
                    None,
                    "pages",
                    "page has no metadata",
                    "export const metadata = { title: … } (the page's SEO title from the plan)",
                )  # fmt: skip
            )
    for relative in changed_owned(project):
        violations.append(
            _violation(
                relative,
                None,
                "owned-files",
                "generator-owned file was changed",
                "Revert it; change your own components instead",
            )  # fmt: skip
        )
    planned = [plan["shell"]["file"], *(c["file"] for c in plan["components"]), *(r["file"] for r in plan["routes"])]
    for relative in planned:
        if not (project / relative).is_file():
            violations.append(_violation(relative, None, "plan", "planned file is missing"))
    return violations
