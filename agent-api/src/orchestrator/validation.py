"""Validation pipeline (Story 6.2). A check reports `passed` only when its command really succeeded.

Order and dependencies (a failed check skips its dependents; independent checks still run):

    1 syntax       static parse of every .py file                    –
    2 lint         ruff check (JSON) + ruff format --check            –
    3 deps         baked venv matches requirements, else install; uv pip check   –
    4 startup      import + serve the app, GET /health                1, 3
    5 migration    autogenerate if models changed; up / check / down / up; schema == plan   3
    6 conventions  fastapi-skills AST checker (static)                1
    7 tests        pytest + planned test ids present                  4, 5
    8 openapi      OpenAPI of the started app == planned operations   4
                   (and conforms to the API contract in dynamic mode, Story 12.3)

Every validation re-runs all checks (they take seconds), so a repair can never hide a regression.
"""

import ast
import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.sandbox import ExecResult, ISandbox

from . import tracing
from .checks.conformance import compare_contract
from .checks.conventions import check_conventions
from .checks.parity import compare_openapi, compare_schema, missing_tests
from .checks.parsers import junit_failures, last_lines, ruff_failures, traceback_frames
from .migrations import ensure_migration, reflect_schema, verify_migration

CHECKS = ("syntax", "lint", "deps", "startup", "migration", "conventions", "tests", "openapi")
DEPENDS_ON = {"startup": ("syntax", "deps"), "migration": ("deps",), "conventions": ("syntax",)}
DEPENDS_ON |= {"tests": ("startup", "migration"), "openapi": ("startup",)}
# Most useful first in the repair digest.
DIGEST_ORDER = ("syntax", "startup", "migration", "conventions", "tests", "openapi", "lint", "deps")
SKIP_DIRS = {".git", ".claude", ".agents", ".venv", "__pycache__", ".bga"}
OPENAPI_MARKER = "BGA_OPENAPI_BEGIN"
FORMAT_FINDING = re.compile(r"^(\S+?):(\d+):\d+: unformatted", re.MULTILINE)
JUNIT_PATH = ".bga/junit.xml"
DIGEST_LIMIT = 30_000


class CheckResult(BaseModel):
    check: str
    status: str  # passed | failed | skipped | not_run
    started_at: datetime | None = None
    duration_ms: int = 0
    summary: str = ""
    details: list[dict] = []
    output: str = ""  # tail of the command output, for the digest


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


@dataclass
class ValidationRequest:
    project: Path
    plan: dict[str, Any]
    run_tests: bool
    sandbox: ISandbox | None = None
    contract: dict[str, Any] | None = None  # the API contract (dynamic mode)
    artifacts: dict[str, Any] = field(default_factory=dict)  # filled by checks (schema, openapi)


@contextmanager
def traced_check(check: str):
    """A `check:<name>` span around one check; the caller hands the result to `slot.append` (Story 8.2)."""
    started = datetime.now(UTC)
    slot: list[CheckResult] = []
    with tracing.span(f"check:{check}", "chain", inputs={"check": check}) as span:
        yield slot
        result = slot[0] if slot else None
        if result is not None:
            result.started_at = started
            span.end(
                outputs={"status": result.status, "summary": result.summary, "durationMs": result.duration_ms},
                error=f"failed: {result.summary}" if result.status == "failed" else None,
            )


class IValidationRunner(ABC):
    @abstractmethod
    async def run(self, request: ValidationRequest) -> ValidationOutcome:
        pass


def syntax_check(project: Path) -> CheckResult:
    started = time.monotonic()
    errors = []
    for path in sorted(project.rglob("*.py")):
        relative = path.relative_to(project)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        try:
            ast.parse(path.read_text(errors="replace"), filename=str(relative))
        except SyntaxError as exc:
            errors.append({"file": relative.as_posix(), "line": exc.lineno, "message": f"SyntaxError: {exc.msg}"})
    return CheckResult(
        check="syntax",
        status="failed" if errors else "passed",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary=f"{len(errors)} syntax error(s)" if errors else "all Python files parse",
        details=errors,
    )


def conventions_check(project: Path, plan: dict[str, Any]) -> CheckResult:
    started = time.monotonic()
    violations = check_conventions(project, plan)
    return CheckResult(
        check="conventions",
        status="failed" if violations else "passed",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary=f"{len(violations)} fastapi-skills violation(s)" if violations else "fastapi-skills checklist met",
        details=violations,
    )


def _format_detail(detail: dict[str, Any]) -> str:
    where = detail.get("file") or detail.get("table") or detail.get("operation") or detail.get("test") or ""
    if detail.get("line"):
        where = f"{where}:{detail['line']}"
    parts = [where, detail.get("code") or detail.get("rule") or "", detail.get("test") or "", detail.get("message")]
    line = " ".join(str(p) for p in parts if p)
    if detail.get("hint"):
        line += f"\n    rule: {detail['hint']}"
    if detail.get("excerpt"):
        line += "\n    " + detail["excerpt"].replace("\n", "\n    ")
    return line


def build_digest(results: list[CheckResult]) -> str:
    return build_digest_for(results, DIGEST_ORDER)


def build_digest_for(results: list[CheckResult], order: tuple[str, ...]) -> str:
    """Failed checks in `order` (most useful first), each with its details and, where useful, its output."""
    by_check = {r.check: r for r in results}
    sections = []
    for check in order:
        result = by_check.get(check)
        if result is None or result.status != "failed":
            continue
        lines = [f"## {check}: {result.summary}"]
        lines += [f"- {_format_detail(detail)}" for detail in result.details[:40]]
        if result.output and (not result.details or check in ("startup", "migration", "deps", "install", "tests")):
            lines += ["```", result.output[-4000:], "```"]
        sections.append("\n".join(lines))
    return "\n\n".join(sections)[:DIGEST_LIMIT]


def implicated(results: list[CheckResult]) -> list[str]:
    files = {
        d["file"]
        for r in results
        if r.status == "failed"
        for d in r.details
        if isinstance(d.get("file"), str) and d["file"] and not d["file"].startswith("/")
    }
    return sorted(files)


def _outcome(results: list[CheckResult]) -> ValidationOutcome:
    return ValidationOutcome(results=results, digest=build_digest(results), implicated_files=implicated(results))


class StaticValidationRunner(IValidationRunner):
    """TESTING ONLY (docs/development/test-doubles.md): used when SANDBOX_ENABLED=false, e.g. in unit tests.
    Runs the checks that need no code execution.
    Everything that runs generated code is reported `not_run`, never `passed`."""

    async def run(self, request: ValidationRequest) -> ValidationOutcome:
        results: list[CheckResult] = []
        for check in CHECKS:
            with traced_check(check) as slot:
                if check == "syntax":
                    result = syntax_check(request.project)
                elif check == "conventions" and request.plan.get("modules") is not None:
                    result = (
                        conventions_check(request.project, request.plan)
                        if results[0].status == "passed"
                        else CheckResult(check=check, status="skipped", summary="skipped: syntax failed")
                    )
                elif check == "tests" and not request.run_tests:
                    result = CheckResult(check=check, status="skipped", summary="runTests=false")
                else:
                    result = CheckResult(check=check, status="not_run", summary="requires the sandbox runner")
                slot.append(result)
            results.append(result)
        return _outcome(results)


class SandboxValidationRunner(IValidationRunner):
    async def run(self, request: ValidationRequest) -> ValidationOutcome:
        if request.sandbox is None:
            return await StaticValidationRunner().run(request)
        await request.sandbox.start()
        results: dict[str, CheckResult] = {}
        steps: dict[str, Callable[[ValidationRequest], Awaitable[CheckResult]]] = {
            "lint": self._lint,
            "deps": self._deps,
            "startup": self._startup,
            "migration": self._migration,
            "tests": self._tests,
            "openapi": self._openapi,
        }
        for check in CHECKS:
            blocked = [d for d in DEPENDS_ON.get(check, ()) if results[d].status != "passed"]
            with traced_check(check) as slot:
                if check == "tests" and not request.run_tests:
                    result = CheckResult(check=check, status="skipped", summary="runTests=false")
                elif blocked:
                    result = CheckResult(
                        check=check, status="skipped", summary=f"skipped: {', '.join(blocked)} did not pass"
                    )
                elif check == "syntax":
                    result = syntax_check(request.project)
                elif check == "conventions":
                    result = conventions_check(request.project, request.plan)
                else:
                    result = await steps[check](request)
                slot.append(result)
            results[check] = result
        return _outcome([results[check] for check in CHECKS])

    @staticmethod
    def _result(check: str, ok: bool, summary: str, run: ExecResult | None, **extra: Any) -> CheckResult:
        return CheckResult(
            check=check,
            status="passed" if ok else "failed",
            duration_ms=run.duration_ms if run else 0,
            summary=summary,
            output=last_lines(run.output, 80) if run and not ok else "",
            **extra,
        )

    async def _lint(self, request: ValidationRequest) -> CheckResult:
        sandbox = request.sandbox
        check = await sandbox.exec("ruff check --output-format json --no-fix .", timeout_s=120)
        fmt = await sandbox.exec("ruff format --check --output-format concise .", timeout_s=120)
        details = ruff_failures(check.stdout)
        details += [
            {"file": match[0], "line": int(match[1]), "code": "format", "message": "not ruff-formatted"}
            for match in FORMAT_FINDING.findall(fmt.stdout)
        ]
        ok = check.ok and fmt.ok
        summary = "ruff check and format clean" if ok else f"{len(details)} ruff finding(s)"
        result = self._result("lint", ok, summary, check if not check.ok else fmt, details=details)
        result.duration_ms = check.duration_ms + fmt.duration_ms
        return result

    async def _deps(self, request: ValidationRequest) -> CheckResult:
        sandbox = request.sandbox
        probe = await sandbox.exec("/opt/bga/bin/ensure_venv.sh", timeout_s=60)
        steps = [probe]
        if probe.exit_code == 3:
            install = await sandbox.exec("/opt/bga/bin/install_venv.sh", timeout_s=600, egress=True)
            steps.append(install)
            if not install.ok:
                return self._result("deps", False, "dependency install failed", install)
        check = await sandbox.exec('uv pip check --python "$(command -v python)"', timeout_s=120)
        steps.append(check)
        ok = check.ok and probe.exit_code in (0, 3)
        venv = "baked runner venv" if probe.exit_code == 0 and "baked" in probe.stdout else "project venv"
        result = self._result("deps", ok, f"dependencies consistent ({venv})" if ok else "uv pip check failed", check)
        result.duration_ms = sum(step.duration_ms for step in steps)
        return result

    async def _startup(self, request: ValidationRequest) -> CheckResult:
        run = await request.sandbox.exec("python /opt/bga/bin/startup_check.py", timeout_s=90)
        ok = run.ok and "STARTUP_OK" in run.stdout
        details = traceback_frames(run.output)[-5:] if not ok else []
        return self._result(
            "startup", ok, "app starts and GET /health → 200" if ok else "app failed to start", run, details=details
        )

    async def _migration(self, request: ValidationRequest) -> CheckResult:
        sandbox, project = request.sandbox, request.project
        generated, regenerated = await ensure_migration(sandbox, project)
        if generated is not None and not generated.ok:
            details = traceback_frames(generated.output)[-5:]
            return self._result("migration", False, "alembic autogenerate failed", generated, details=details)
        verify = await verify_migration(sandbox)
        if not verify.ok:
            details = traceback_frames(verify.output)[-5:]
            return self._result(
                "migration", False, "upgrade / check / downgrade / upgrade failed", verify, details=details
            )
        schema, reflect = await reflect_schema(sandbox)
        if schema is None:
            return self._result("migration", False, "could not reflect the migrated schema", reflect)
        request.artifacts["schema"] = schema
        problems = compare_schema(request.plan, schema)
        summary = (
            f"{len(problems)} schema mismatch(es) with the plan"
            if problems
            else f"{len(schema['tables'])} table(s) match the plan"
            + (" (migration regenerated)" if regenerated else "")
        )
        result = self._result("migration", not problems, summary, None, details=problems)
        result.duration_ms = verify.duration_ms + reflect.duration_ms + (generated.duration_ms if generated else 0)
        return result

    async def _tests(self, request: ValidationRequest) -> CheckResult:
        sandbox, project = request.sandbox, request.project
        missing = missing_tests(request.plan, project)
        await sandbox.reset_database("app_test")
        junit = project / JUNIT_PATH
        junit.unlink(missing_ok=True)
        run = await sandbox.exec(f"pytest -q --maxfail=20 --junitxml=/work/{JUNIT_PATH}", timeout_s=300)
        failures = junit_failures(junit.read_text(errors="replace")) if junit.exists() else []
        if not run.ok and not failures:
            failures = traceback_frames(run.output)[-5:]
        ok = run.ok and not missing
        if ok:
            summary = last_lines(run.stdout, 1) or "tests passed"
        elif not run.ok:
            summary = f"pytest failed ({len(failures)} failing test(s))" + (
                f", {len(missing)} missing" if missing else ""
            )
        else:
            summary = f"{len(missing)} planned test(s) missing"
        return self._result("tests", ok, summary, run if not run.ok else None, details=failures + missing)

    async def _openapi(self, request: ValidationRequest) -> CheckResult:
        run = await request.sandbox.exec("python /opt/bga/bin/export_openapi.py", timeout_s=90)
        if not run.ok or OPENAPI_MARKER not in run.stdout:
            return self._result("openapi", False, "could not export OpenAPI from the started app", run)
        try:
            document = json.loads(run.stdout.split(OPENAPI_MARKER, 1)[1].strip())
        except json.JSONDecodeError:
            return self._result("openapi", False, "OpenAPI output is not JSON", run)
        request.artifacts["openapi"] = document
        problems = compare_openapi(request.plan, document)
        target = "the plan"
        if request.contract is not None:
            problems += compare_contract(request.contract, document)
            target = "the plan and the API contract"
        count = sum(len(item) for item in document.get("paths", {}).values())
        summary = f"{len(problems)} mismatch(es) with {target}" if problems else f"{count} operation(s) match {target}"
        return self._result("openapi", not problems, summary, None, details=problems)


def write_report(path: Path, outcome: ValidationOutcome) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outcome.model_dump(mode="json"), indent=2))
