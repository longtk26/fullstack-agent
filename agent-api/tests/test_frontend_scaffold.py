"""Frontend base + overlay + generated code (Story 13.2), the conventions checker and the static checks (13.4)."""

import json
import shutil
from pathlib import Path

import pytest
from generation_helpers import EXAMPLES, app_pair

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_text
from src.orchestrator.checks.frontend_conventions import check_frontend_conventions
from src.orchestrator.frontend.codegen import generated_files, type_name
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.frontend.scaffold import (
    BASE_DIR,
    OVERLAY_DIR,
    FrontendTemplateDrift,
    check_base,
    load_manifest,
    scaffold_frontend,
)
from src.orchestrator.frontend.validation import (
    eslint_failures,
    routes_check,
    typescript_errors,
)
from src.orchestrator.integration.contract import build_contract

# Dynamic FrontendSpecs are apps (Story 22.8): the app flow's spec for an example BackendSpec (`app_pair`).
TRACKER = "two-entity"
LANDING = "static-landing"
SHOP = "shop"
APPS = {TRACKER, SHOP, "flashcards", "workshop-bookings"}


def inputs(name: str) -> tuple[dict, dict | None, dict]:
    """A static example (`examples/frontend-specs/<name>.json`) or the app of an example BackendSpec."""
    if name in APPS:
        raw, backend = app_pair(name)
        contract = build_contract(validate_spec_data(backend).normalized)
    else:  # a static example, or the static shop of custom components (`tests/fixtures/frontend-specs/`)
        source = EXAMPLES / "frontend-specs" / f"{name}.json"
        if not source.is_file():
            source = Path(__file__).parent / "fixtures" / "frontend-specs" / f"{name}.json"
        raw, contract = json.loads(source.read_text()), None
    spec = validate_frontend_spec_text(json.dumps(raw)).normalized
    return spec, contract, plan_frontend(spec, contract)


def scaffolded(tmp_path: Path, name: str) -> tuple[Path, dict]:
    spec, contract, plan = inputs(name)
    project = tmp_path / name
    scaffold_frontend(project, plan, spec, contract)
    return project, plan


def test_the_pinned_base_matches_the_overlay_manifest():
    assert check_base() == []
    assert (BASE_DIR / "pnpm-lock.yaml").is_file() and not (BASE_DIR / "node_modules").exists()


def test_drift_in_the_base_is_refused(tmp_path):
    base = tmp_path / "base"
    shutil.copytree(BASE_DIR, base)
    (base / "next.config.ts").write_text("// changed\n")
    spec, contract, plan = inputs(LANDING)
    with pytest.raises(FrontendTemplateDrift, match="next.config.ts: changed"):
        scaffold_frontend(tmp_path / "project", plan, spec, contract, base=base)
    assert not (tmp_path / "project").exists()


def test_static_scaffold_has_content_and_no_api(tmp_path):
    project, plan = scaffolded(tmp_path, LANDING)
    assert (project / "src/content/services.json").is_file()
    assert not (project / "src/lib/api").exists() and not (project / "src/mocks").exists()
    assert 'output: "export"' in (project / "next.config.ts").read_text()
    # Story 17.2: the home route renders the spec; the base's demo page is gone.
    assert '<PageRenderer pageId="home" />' in (project / "src/app/page.tsx").read_text()
    ui = sorted(path.stem for path in (project / "src/components/ui").glob("*.tsx"))
    assert ui == plan["shadcn"]
    package = json.loads((project / "package.json").read_text())
    assert package["name"] == "northwind-studio" and package["scripts"]["test:e2e"] == "playwright test"
    assert "# Northwind Studio" in (project / "README.md").read_text()


def test_dynamic_scaffold_has_the_typed_client_and_the_mock_layer(tmp_path):
    project, _ = scaffolded(tmp_path, TRACKER)
    types = (project / "src/lib/api/types.ts").read_text()
    assert "export type TProject = {" in types and "export type TListTasksParams = {" in types
    assert '  status?: "TODO" | "IN_PROGRESS" | "DONE";' in types
    operations = (project / "src/lib/api/operations.ts").read_text()
    assert "export function getProject(params: TGetProjectParams): Promise<TProject> {" in operations
    assert 'return request<TProject>("GET", `/projects/${encodeURIComponent(String(params.id))}`);' in operations
    queries = (project / "src/lib/api/queries.ts").read_text()
    assert "export function useListTasks(params: TListTasksParams = {}, options: TQueryOptions = {}) {" in queries
    assert "onSuccess: () => queryClient.invalidateQueries({ queryKey: taskKeys.all })," in queries
    mocks = json.loads((project / "src/mocks/operations.json").read_text())
    task_list = next(op for op in mocks if op["operationId"] == "task.list")
    assert task_list["filters"] == ["projectId", "status"] and task_list["sort"] == ["dueDate", "priority"]
    assert len(json.loads((project / "src/mocks/fixtures.json").read_text())["Task"]) == 3
    forms = (project / "src/lib/forms.ts").read_text()
    assert 'status: z.preprocess(blank, z.enum(["TODO", "IN_PROGRESS", "DONE"]).optional()),' in forms
    assert "priority: z.preprocess(blank, z.number().int().min(1).max(5).optional())," in forms
    assert (project / ".bga/contract.json").is_file() and 'output: "standalone"' in (
        project / "next.config.ts"
    ).read_text()


def test_generated_files_are_deterministic():
    spec, contract, plan = inputs(TRACKER)
    assert generated_files(plan, spec, contract) == generated_files(plan, spec, contract)
    assert type_name("ProductResponse") == "TProduct" and type_name("ListProductsResponse") == "TListProductsResponse"


@pytest.mark.parametrize("name", [LANDING, TRACKER, SHOP])
def test_a_generated_frontend_meets_the_conventions_without_engine_files(tmp_path, name):
    project, plan = scaffolded(tmp_path, name)
    assert plan["rendering"] == ("renderer" if name == LANDING else "app")
    assert check_frontend_conventions(project, plan) == []


VIOLATIONS = [
    ("react-imports", 'import * as React from "react";\n'),
    ("design-tokens", 'export const box = <div className="bg-[#ff0000]" />;\n'),
    ("token-storage", 'localStorage.setItem("authToken", "x");\n'),
    ("network", 'fetch("/api/projects");\n'),
    ("network", 'import { request } from "@/lib/api/client";\n'),
    ("types", "export type Project = { id: string };\n"),
    ("types", "export type TCardProps = { id: string };\n"),
    ("types", "export interface TProject { id: string }\n"),
]


@pytest.mark.parametrize(("rule", "code"), VIOLATIONS, ids=[f"{rule}:{i}" for i, (rule, _) in enumerate(VIOLATIONS)])
def test_conventions_report_each_rule(tmp_path, rule, code):
    project, plan = scaffolded(tmp_path, SHOP)
    path = project / "src/features/products/components/Bad.tsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    found = [(v["rule"], v["file"]) for v in check_frontend_conventions(project, plan)]
    assert (rule, "src/features/products/components/Bad.tsx") in found


def test_conventions_report_owned_changes_missing_files_and_long_components(tmp_path):
    project, plan = scaffolded(tmp_path, SHOP)
    (project / "src/lib/api/queries.ts").write_text("// edited\n")
    (project / "src/components/app/AppList.tsx").unlink()
    (project / "src/app/products/page.tsx").write_text("export default function Page() {\n  return null;\n}\n")
    logic = "\n".join(f"  const value{i} = {i};" for i in range(35))
    long = project / "src/features/products/components/Long.tsx"
    long.parent.mkdir(parents=True, exist_ok=True)
    long.write_text(f"export function Long() {{\n{logic}\n  return (\n    <div />\n  );\n}}\n")
    found = {(v["rule"], v["file"]) for v in check_frontend_conventions(project, plan)}
    # an app's kit and route files are all the generator's: a change or a deletion is an owned-file change
    assert {
        ("owned-files", "src/lib/api/queries.ts"),
        ("owned-files", "src/components/app/AppList.tsx"),
        ("owned-files", "src/app/products/page.tsx"),
    } <= found
    assert ("custom-hooks", "src/features/products/components/Long.tsx") in found


def test_tool_output_parsers():
    tsc = "src/app/page.tsx(12,7): error TS2322: Type 'string' is not assignable to type 'number'.\n"
    assert typescript_errors(tsc) == [
        {"file": "src/app/page.tsx", "line": 12, "code": "TS2322",
         "message": "Type 'string' is not assignable to type 'number'."},
    ]  # fmt: skip
    eslint = json.dumps(
        [
            {
                "filePath": "/work/src/app/page.tsx",
                "messages": [
                    {"ruleId": "react-hooks/rules-of-hooks", "severity": 2, "line": 4, "message": "Hook called"},
                    {"ruleId": "no-console", "severity": 1, "line": 5, "message": "warning only"},
                ],
            }
        ]
    )
    assert eslint_failures(eslint) == [
        {"file": "src/app/page.tsx", "line": 4, "code": "react-hooks/rules-of-hooks", "message": "Hook called"}
    ]


def test_routes_check_reads_the_build_output(tmp_path):
    _, _, tracker = inputs(TRACKER)
    project = tmp_path / "dynamic"
    (project / ".next").mkdir(parents=True)
    built = [route["route"] for route in tracker["routes"] if route["route"] != "/tasks"]
    manifest = {(route.rstrip("/") + "/page"): route for route in built}
    (project / ".next/app-path-routes-manifest.json").write_text(json.dumps(manifest))
    result = routes_check(project, tracker)
    assert result.status == "failed" and result.details == [
        {"file": "src/app/tasks/page.tsx", "message": "route /tasks is not in the build output"}
    ]
    _, _, landing = inputs(LANDING)
    project = tmp_path / "static"
    for route in ("", "services", "work", "about", "contact"):
        (project / "out" / route).mkdir(parents=True, exist_ok=True)
        (project / "out" / route / "index.html").write_text("<html></html>")
    assert routes_check(project, landing).status == "passed"


def test_dockerfiles_agree_with_overlay_pnpm_version():
    manifest = load_manifest()
    pnpm_version = manifest["baseLock"]["pnpmVersion"]
    expected_clause = f"pnpm@{pnpm_version}"

    for mode in ("dynamic", "static"):
        dockerfile = (OVERLAY_DIR / "files" / mode / "Dockerfile").read_text()
        assert expected_clause in dockerfile, f"{mode}/Dockerfile does not use {expected_clause}"
        assert "AS deps" in dockerfile
        assert "pnpm fetch --frozen-lockfile" in dockerfile
