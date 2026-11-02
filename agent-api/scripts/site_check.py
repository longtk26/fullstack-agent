"""Builds a FrontendSpec with the section renderer in the Node sandbox and runs `scripts/design-check.mjs` on it
(Stories 17.7, 20.1). Shared by the design diversity report and the section-library design check. Dev tools only.

Needs Docker and the `bga-runner-node` image (`make runner-node`). Projects are built under `.data/` (Docker Desktop
only shares configured host paths); generated drawings and photos are shown as placeholders, since they need an
engine or the image API.
"""

import copy
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DESIGN_CHECK = REPO / "scripts" / "design-check.mjs"
BUILD_ROOT = REPO / ".data" / "test-sandbox"


def offline_assets(spec: dict[str, Any]) -> dict[str, Any]:
    """Generated drawings and photos need an engine or the image API; the checks show them as placeholders."""
    out = copy.deepcopy(spec)
    for asset in out.get("assets") or []:
        if isinstance(asset, dict) and asset.get("source") in ("generate", "photo"):
            asset["source"] = "placeholder"
    return out


async def check_site(
    spec: dict[str, Any],
    shots: Path,
    routes: list[str] | None = None,
    widths: str | None = None,
    schemes: str | None = None,
) -> dict[str, Any] | None:
    """Builds `spec` and runs the design check on `routes` (default: every page without route parameters). The
    screenshots and `report.json` land in `shots`; returns the report, or None when the spec or the build failed
    (the reason is printed)."""
    from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
    from src.orchestrator.frontend_planner import plan_frontend
    from src.orchestrator.frontend_scaffold import scaffold_frontend
    from src.orchestrator.frontend_validation import FrontendValidationRequest, SandboxFrontendValidationRunner
    from src.sandbox import DockerSandboxProvider

    result = validate_frontend_spec_data(offline_assets(spec))
    if not result.report.valid:
        print(f"  {shots.name}: spec invalid: {[issue.message for issue in result.report.errors][:3]}")
        return None
    plan = plan_frontend(result.normalized)
    routes = routes or [route["route"] for route in plan["routes"] if not route["params"]]
    target = BUILD_ROOT / f"check-{uuid.uuid4().hex[:10]}"
    project = target / "frontend"
    scaffold_frontend(project, plan, result.normalized)
    sandbox = DockerSandboxProvider().for_job(f"gen_CHK{uuid.uuid4().hex[:10].upper()}", project, "frontend")
    try:
        outcome = await SandboxFrontendValidationRunner().run(
            FrontendValidationRequest(project=project, plan=plan, run_tests=False, sandbox=sandbox)
        )
        if outcome.summary.get("build") != "passed":
            print(f"  {shots.name}: build {outcome.summary}\n{outcome.digest[-3000:]}")
            return None
        shutil.copy(DESIGN_CHECK, project / "design-check.mjs")
        env = {
            key: value for key, value in (("DESIGN_CHECK_WIDTHS", widths), ("DESIGN_CHECK_SCHEMES", schemes)) if value
        }
        run = await sandbox.exec(f"node design-check.mjs shots {' '.join(routes)}", timeout_s=900, env=env)
        report = project / "shots" / "report.json"
        if not run.ok or not report.is_file():
            print(f"  {shots.name}: design check failed\n{run.output[-3000:]}")
            return None
        shutil.rmtree(shots, ignore_errors=True)
        shutil.copytree(project / "shots", shots)
        return json.loads((shots / "report.json").read_text())
    finally:
        await sandbox.stop()
        shutil.rmtree(target, ignore_errors=True)
