import ast
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

CHECKS = ("syntax", "lint", "deps", "startup", "migration", "conventions", "tests", "openapi")
SKIP_DIRS = {".git", ".claude", ".agents", ".venv", "__pycache__", ".bga"}


class CheckResult(BaseModel):
    check: str
    status: str  # passed | failed | skipped | not_run
    duration_ms: int = 0
    summary: str = ""
    details: list[dict] = []


class ValidationOutcome(BaseModel):
    results: list[CheckResult]
    digest: str
    implicated_files: list[str]

    @property
    def failed_checks(self) -> list[str]:
        return [r.check for r in self.results if r.status == "failed"]

    @property
    def summary(self) -> dict[str, str]:
        return {r.check: r.status for r in self.results}


class IValidationRunner(ABC):
    @abstractmethod
    async def run(self, project: Path, run_tests: bool) -> ValidationOutcome:
        pass


class StaticValidationRunner(IValidationRunner):
    """Checks that need no code execution. Everything that runs generated code (ruff, deps, startup,
    migrations, pytest, OpenAPI export) needs the sandbox from Story 6.1 and is reported `not_run` — never
    `passed` — until then."""

    async def run(self, project: Path, run_tests: bool) -> ValidationOutcome:
        started = time.monotonic()
        errors = []
        for path in sorted(project.rglob("*.py")):
            relative = path.relative_to(project)
            if any(part in SKIP_DIRS for part in relative.parts):
                continue
            try:
                ast.parse(path.read_text(errors="replace"), filename=str(relative))
            except SyntaxError as exc:
                errors.append({"file": relative.as_posix(), "line": exc.lineno, "message": exc.msg})
        syntax = CheckResult(
            check="syntax",
            status="failed" if errors else "passed",
            duration_ms=int((time.monotonic() - started) * 1000),
            summary=f"{len(errors)} syntax error(s)" if errors else "all Python files parse",
            details=errors,
        )
        results = [syntax]
        for check in CHECKS[1:]:
            status = "skipped" if check == "tests" and not run_tests else "not_run"
            results.append(CheckResult(check=check, status=status, summary="requires the sandbox runner (Story 6.1)"))
        digest = "\n".join(f"{e['file']}:{e['line']}: SyntaxError: {e['message']}" for e in errors)
        return ValidationOutcome(results=results, digest=digest, implicated_files=sorted({e["file"] for e in errors}))


def write_report(path: Path, outcome: ValidationOutcome) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outcome.model_dump(), indent=2))
