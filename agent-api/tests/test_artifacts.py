import asyncio
import io
import json
import zipfile

import pytest

from src.engines import EngineContext, PromptLibrary
from src.engines.fake_engine import DEMO_SCENARIO, FakeEngine, FakeStep
from src.orchestrator.context import JobContext
from src.orchestrator.nodes import write_artifacts
from src.orchestrator.validation import StaticValidationRunner
from workflow_helpers import completed_generation, run_job, runner_ctx, submit

pytestmark = pytest.mark.usefixtures("clean_redis")


@pytest.fixture(scope="module")
def workspaces(tmp_path_factory):
    return tmp_path_factory.mktemp("workspaces")


@pytest.fixture(scope="module")
def completed(client, workspaces):
    return completed_generation(client, workspaces)


def _artifacts(client, headers, generation_id) -> dict[str, dict]:
    response = client.get(f"/api/v1/generations/{generation_id}/artifacts", headers=headers)
    assert response.status_code == 200, response.text
    return {item["name"]: item for item in response.json()["items"]}


def _download(client, headers, generation_id, artifact) -> bytes:
    response = client.get(f"/api/v1/generations/{generation_id}/artifacts/{artifact['artifactId']}", headers=headers)
    assert response.status_code == 200, response.text
    assert artifact["name"] in response.headers["content-disposition"]
    return response.content


def test_completed_generation_is_packaged(client, user_headers, completed):
    artifacts = _artifacts(client, user_headers, completed)

    assert set(artifacts) == {
        "backend.zip",
        "manifest.json",
        "plan.json",
        "repair-1.patch",
        "report.json",
        "report.md",
        "spec.json",
        "validation-1.json",
        "validation-2.json",
    }, "no openapi.json: the static validator (sandbox off) does not start the app"
    source = zipfile.ZipFile(io.BytesIO(_download(client, user_headers, completed, artifacts["backend.zip"])))
    names = source.namelist()
    assert "src/main.py" in names and "Dockerfile" in names
    assert not [n for n in names if n.startswith((".bga/", ".git/", ".claude/"))]

    manifest = json.loads(_download(client, user_headers, completed, artifacts["manifest.json"]))
    assert manifest["manifestVersion"] == "1.0" and manifest["architecture"] == "fastapi-skills-hexagonal"
    assert manifest["api"]["source"] == "plan" and len(manifest["operations"]) == 10
    assert manifest["artifacts"]["source"] == artifacts["backend.zip"]["artifactId"]
    assert manifest["artifacts"]["manifest"] == artifacts["manifest.json"]["artifactId"]
    assert {m["name"] for m in manifest["modules"]} == {"projects", "tasks"}

    report = json.loads(_download(client, user_headers, completed, artifacts["report.json"]))
    assert report["outcome"] == "COMPLETED" and report["validationAttempts"] == 2
    assert [r["attempt"] for r in report["repairs"]] == [1]
    assert b"src/" in _download(client, user_headers, completed, artifacts["repair-1.patch"])

    detail = client.get(f"/api/v1/generations/{completed}", headers=user_headers).json()
    assert {a["name"] for a in detail["artifacts"]} == set(artifacts) and detail["preview"] is None


def test_repackaging_is_idempotent(client, user_headers, completed, workspaces):
    before = _artifacts(client, user_headers, completed)
    manifest = json.loads(_download(client, user_headers, completed, before["manifest.json"]))

    async def repackage():
        async with runner_ctx(workspaces) as runner:
            ctx = JobContext(
                completed,
                FakeEngine(workspaces),
                EngineContext(conventions="rules"),
                PromptLibrary(),
                StaticValidationRunner(),
                runner.store,
                runner.events,
                runner.workspaces,
                runner.workspaces.path_for(completed),
            )
            await write_artifacts(ctx, {"validation": manifest["validation"]}, completed=True)

    asyncio.run(repackage())

    after = _artifacts(client, user_headers, completed)
    assert {n: (a["artifactId"], a["sha256"]) for n, a in after.items()} == {
        n: (a["artifactId"], a["sha256"]) for n, a in before.items()
    }


def test_failed_generation_exposes_diagnostics(client, user_headers, tmp_path):
    broken = {"src/x.py": "def broken(:\n"}
    engine = FakeEngine(tmp_path, {**DEMO_SCENARIO, "repair_code": [FakeStep(write=broken)], "*": [FakeStep()]})
    generation_id = submit(client, user_headers, maxRepairAttempts=1)
    assert run_job(tmp_path, generation_id, engine=engine) == "FAILED"

    artifacts = _artifacts(client, user_headers, generation_id)

    assert "backend.zip" not in artifacts and "manifest.json" not in artifacts
    assert {"report.json", "report.md", "repair-1.patch", "validation-1.json", "validation-2.json"} <= set(artifacts)
    report = json.loads(_download(client, user_headers, generation_id, artifacts["report.json"]))
    assert report["outcome"] == "FAILED" and "repair attempt" in report["error"]


def test_browse_generated_files(client, user_headers, completed):
    url = f"/api/v1/generations/{completed}/files"

    root = client.get(url, headers=user_headers).json()
    assert root["type"] == "dir" and {"name": "src", "path": "src", "type": "dir", "size": None} in root["entries"]
    src = client.get(url, params={"path": "src/"}, headers=user_headers).json()
    assert any(e["path"] == "src/main.py" and e["type"] == "file" for e in src["entries"])
    main = client.get(url, params={"path": "src/main.py"}, headers=user_headers).json()
    assert main["type"] == "file" and "FastAPI" in main["content"]

    assert client.get(url, params={"path": "../../etc/passwd"}, headers=user_headers).status_code == 400
    assert client.get(url, params={"path": "nope.txt"}, headers=user_headers).status_code == 404


def test_artifacts_are_owner_scoped(client, user_headers, login, completed):
    other = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}
    artifact = next(iter(_artifacts(client, user_headers, completed).values()))

    assert client.get(f"/api/v1/generations/{completed}/artifacts", headers=other).status_code == 404
    url = f"/api/v1/generations/{completed}/artifacts/{artifact['artifactId']}"
    assert client.get(url, headers=other).status_code == 404
    assert client.get(f"/api/v1/generations/{completed}/files", headers=other).status_code == 404
    assert client.get(f"/api/v1/generations/{completed}/artifacts/art_nope", headers=user_headers).status_code == 404
