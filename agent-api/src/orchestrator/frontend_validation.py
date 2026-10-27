"""Frontend validation pipeline (Story 13.4), reported like the backend pipeline (6.2).

    1 install      pnpm install from the pre-warmed store (offline); egress only when new packages are needed
    2 typecheck    tsc --noEmit                                                     1
    3 lint         ESLint (eslint-config-next)                                      1
    4 conventions  static nextjs-skills checker, owned files unchanged, planned files present   –
    5 build        next build                                                       1, 2
    6 routes       every planned route is in the build output                       5
    7 tests        Vitest (unit) + Playwright smoke on the mock API / the export    5

A failed check skips its dependents; every validation re-runs all checks.
"""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.sandbox import ExecResult, ISandbox

from .checks.frontend_conventions import check_frontend_conventions
from .checks.parsers import junit_failures, last_lines
from .validation import CheckResult, ValidationOutcome, build_digest_for, implicated, traced_check

CHECKS = ("install", "typecheck", "lint", "conventions", "build", "routes", "tests")
DEPENDS_ON = {"typecheck": ("install",), "lint": ("install",), "build": ("install", "typecheck")}
DEPENDS_ON |= {"routes": ("build",), "tests": ("build",)}
DIGEST_ORDER = ("install", "typecheck", "build", "conventions", "lint", "routes", "tests")
TS_ERROR = re.compile(r"^(?:\./)?(src/[^\s(:]+)\((\d+),\d+\): error (TS\d+): (.+)$", re.MULTILINE)
BUILD_LOCATION = re.compile(r"^\./(src/[^\s:]+):(\d+):\d+", re.MULTILINE)
NO_OFFLINE = ("ERR_PNPM_NO_OFFLINE", "ERR_PNPM_OFFLINE", "not found in the store", "ERR_PNPM_FETCH")


@dataclass
class FrontendValidationRequest:
    project: Path
    plan: dict[str, Any]
    run_tests: bool
    sandbox: ISandbox | None = None


def _result(check: str, ok: bool, summary: str, run: ExecResult | None, **extra: Any) -> CheckResult:
    return CheckResult(
        check=check,
        status="passed" if ok else "failed",
        duration_ms=run.duration_ms if run else 0,
        summary=summary,
        output=last_lines(run.output, 80) if run and not ok else "",
        **extra,
    )


def typescript_errors(output: str) -> list[dict[str, Any]]:
    return [
        {"file": match[0], "line": int(match[1]), "code": match[2], "message": match[3].strip()}
        for match in TS_ERROR.findall(output)
    ][:60]


def eslint_failures(output: str) -> list[dict[str, Any]]:
    start = output.find("[")
    try:
        reports = json.loads(output[start:]) if start >= 0 else []
    except json.JSONDecodeError:
        return []
    failures = []
    for report in reports:
        file = str(report.get("filePath", "")).removeprefix("/work/")
        for message in report.get("messages", []):
            if message.get("severity", 0) < 2:
                continue
            failures.append(
                {
                    "file": file,
                    "line": message.get("line"),
                    "code": message.get("ruleId"),
                    "message": message.get("message"),
                }
            )
    return failures[:60]


def built_routes(project: Path, mode: str) -> set[str] | None:
    """Routes in the build output: the app path manifest (dynamic) or the exported HTML files (static)."""
    if mode == "static":
        out = project / "out"
        if not out.is_dir():
            return None
        return {
            "/" + path.parent.relative_to(out).as_posix().strip(".").strip("/") if path.name == "index.html" else ""
            for path in out.rglob("index.html")
        } - {""}
    manifest = project / ".next" / "app-path-routes-manifest.json"
    if not manifest.is_file():
        return None
    return {route for route in json.loads(manifest.read_text()).values()}


def _route_present(route: dict[str, Any], built: set[str], mode: str, example: str | None) -> bool:
    if mode == "static" and route["params"]:
        prefix = route["route"].split("/[")[0]
        target = (example or "").rstrip("/")
        return (target in built) if target else any(path.startswith(prefix + "/") for path in built)
    return route["route"] in built or (route["route"].rstrip("/") or "/") in built


def routes_check(project: Path, plan: dict[str, Any]) -> CheckResult:
    started = time.monotonic()
    mode = plan["project"]["mode"]
    built = built_routes(project, mode)
    if built is None:
        return CheckResult(check="routes", status="failed", summary="no build output found")
    examples = {test["pageId"]: test.get("path") for test in plan["tests"] if test["kind"] == "route"}
    missing = [
        {"file": route["file"], "message": f"route {route['route']} is not in the build output"}
        for route in plan["routes"]
        if not _route_present(route, built, mode, examples.get(route["pageId"]))
    ]
    return CheckResult(
        check="routes",
        status="failed" if missing else "passed",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary=f"{len(missing)} planned route(s) missing" if missing else f"{len(plan['routes'])} route(s) built",
        details=missing,
    )


def conventions_check(project: Path, plan: dict[str, Any]) -> CheckResult:
    started = time.monotonic()
    violations = check_frontend_conventions(project, plan)
    return CheckResult(
        check="conventions",
        status="failed" if violations else "passed",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary=f"{len(violations)} nextjs-skills violation(s)" if violations else "nextjs-skills checklist met",
        details=violations,
    )


def _outcome(results: list[CheckResult]) -> ValidationOutcome:
    return ValidationOutcome(
        results=results, digest=build_digest_for(results, DIGEST_ORDER), implicated_files=implicated(results)
    )


class StaticFrontendValidationRunner:
    """TESTING ONLY (docs/development/test-doubles.md): used without the sandbox. Runs the conventions check;
    everything that needs Node is reported `not_run`, never `passed`."""

    async def run(self, request: FrontendValidationRequest) -> ValidationOutcome:
        results = []
        for check in CHECKS:
            with traced_check(check) as slot:
                if check == "conventions":
                    result = conventions_check(request.project, request.plan)
                elif check == "tests" and not request.run_tests:
                    result = CheckResult(check=check, status="skipped", summary="runTests=false")
                else:
                    result = CheckResult(check=check, status="not_run", summary="requires the Node sandbox")
                slot.append(result)
            results.append(result)
        return _outcome(results)


class SandboxFrontendValidationRunner:
    async def run(self, request: FrontendValidationRequest) -> ValidationOutcome:
        if request.sandbox is None:
            return await StaticFrontendValidationRunner().run(request)
        await request.sandbox.start()
        results: dict[str, CheckResult] = {}
        for check in CHECKS:
            blocked = [d for d in DEPENDS_ON.get(check, ()) if results[d].status != "passed"]
            with traced_check(check) as slot:
                if check == "tests" and not request.run_tests:
                    result = CheckResult(check=check, status="skipped", summary="runTests=false")
                elif blocked:
                    result = CheckResult(
                        check=check, status="skipped", summary=f"skipped: {', '.join(blocked)} did not pass"
                    )
                elif check == "conventions":
                    result = conventions_check(request.project, request.plan)
                elif check == "routes":
                    result = routes_check(request.project, request.plan)
                else:
                    result = await getattr(self, f"_{check}")(request)
                slot.append(result)
            results[check] = result
        return _outcome([results[check] for check in CHECKS])

    async def _install(self, request: FrontendValidationRequest) -> CheckResult:
        sandbox = request.sandbox
        run = await sandbox.exec("pnpm install --frozen-lockfile --offline", timeout_s=600)
        steps = [run]
        if not run.ok and any(marker in run.output for marker in NO_OFFLINE):
            run = await sandbox.exec("pnpm install --frozen-lockfile --prefer-offline", timeout_s=900, egress=True)
            steps.append(run)
        source = "pre-warmed store" if len(steps) == 1 else "registry (new packages)"
        result = _result(
            "install", run.ok, f"dependencies installed ({source})" if run.ok else "pnpm install failed", run
        )
        result.duration_ms = sum(step.duration_ms for step in steps)
        return result

    async def _typecheck(self, request: FrontendValidationRequest) -> CheckResult:
        run = await request.sandbox.exec("pnpm exec tsc --noEmit --pretty false", timeout_s=300)
        errors = typescript_errors(run.output)
        summary = "no type errors" if run.ok else f"{len(errors) or 'some'} type error(s)"
        return _result("typecheck", run.ok, summary, run, details=errors)

    async def _lint(self, request: FrontendValidationRequest) -> CheckResult:
        run = await request.sandbox.exec("pnpm exec eslint --format json .", timeout_s=300)
        failures = eslint_failures(run.stdout)
        ok = run.ok and not failures
        result = _result("lint", ok, "ESLint clean" if ok else f"{len(failures) or 'some'} ESLint error(s)", run)
        result.details = failures
        result.output = "" if failures else result.output
        return result

    async def _build(self, request: FrontendValidationRequest) -> CheckResult:
        run = await request.sandbox.exec("pnpm exec next build", timeout_s=600)
        details = typescript_errors(run.output) or [
            {"file": match[0], "line": int(match[1]), "message": "build error"}
            for match in BUILD_LOCATION.findall(run.output)
        ]
        return _result(
            "build", run.ok, "next build succeeded" if run.ok else "next build failed", run, details=details[:20]
        )

    async def _tests(self, request: FrontendValidationRequest) -> CheckResult:
        sandbox, project = request.sandbox, request.project
        reports = project / "test-results"
        for name in ("unit-junit.xml", "e2e-junit.xml"):
            (reports / name).unlink(missing_ok=True)
        unit = await sandbox.exec(
            "pnpm exec vitest run --reporter=default --reporter=junit --outputFile.junit=test-results/unit-junit.xml",
            timeout_s=300,
        )
        e2e = await sandbox.exec("pnpm exec playwright test", timeout_s=600, env={"E2E_PORT": "3100"})
        failures = []
        for name in ("unit-junit.xml", "e2e-junit.xml"):
            if (reports / name).is_file():
                failures += junit_failures((reports / name).read_text(errors="replace"))
        ok = unit.ok and e2e.ok
        if ok:
            summary = "unit and smoke tests passed"
        else:
            parts = [label for label, run in (("unit", unit), ("smoke", e2e)) if not run.ok]
            summary = f"{' and '.join(parts)} tests failed ({len(failures)} failing test(s))"
        failing_run = e2e if not e2e.ok else unit
        result = _result("tests", ok, summary, failing_run if not ok else None, details=failures)
        result.duration_ms = unit.duration_ms + e2e.duration_ms
        return result
