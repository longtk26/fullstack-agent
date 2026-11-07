"""The storage plugin (Story 10.5): file and image fields as object keys, presigned uploads, the use-case checks,
signed read URLs, the contract's upload sources and scenarios, and the local store's sandbox and preview wiring."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import codegen_gaps, module_files, module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.integration.contract import build_contract, contract_operations
from src.orchestrator.plugins import REGISTRY, extended_spec
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def storage_spec(tmp_path: Path, auth: bool = False) -> dict:
    """two-entity: a project has a cover image (optional), a task a PDF attachment of at most 1 MB (optional)."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    project = next(entity for entity in raw["entities"] if entity["name"] == "Project")
    project["fields"].append({"name": "cover", "type": "image", "required": False, "nullable": True})
    task = next(entity for entity in raw["entities"] if entity["name"] == "Task")
    task["fields"].append({"name": "attachment", "type": "file", "required": False, "nullable": True,
                           "accept": ["application/pdf"], "maxSize": 1048576})  # fmt: skip
    if auth:
        raw["auth"] = {"type": "jwt", "roles": ["member"]}
        for op in raw["operations"]:
            op["auth"] = "jwt"
    (tmp_path / "storage-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "storage-spec.json")


def _module(plan: dict, name: str) -> dict:
    return next(module for module in plan["modules"] if module["name"] == name)


def _files(spec: dict, plan: dict, name: str) -> dict[str, str]:
    module = _module(plan, name)
    return module_files(plan, extended_spec(spec), module) | module_tests(plan, extended_spec(spec), module)


def test_file_fields_are_object_keys_with_their_rules(tmp_path):
    plan = build_plan(storage_spec(tmp_path))
    task = next(m for m in plan["models"] if m["entity"] == "Task")
    attachment = next(c for c in task["columns"] if c["apiName"] == "attachment")
    assert attachment["type"] == "string" and attachment["maxLength"] == 512
    assert attachment["file"] == {"kind": "file", "accept": ["application/pdf"], "maxSize": 1048576,
                                  "prefix": "task/attachment"}  # fmt: skip
    project = next(m for m in plan["models"] if m["entity"] == "Project")
    cover = next(c for c in project["columns"] if c["apiName"] == "cover")
    assert cover["file"]["accept"] == ["image/png", "image/jpeg", "image/webp", "image/gif"]
    assert project["label"]["apiName"] == "name"  # a key never names a record
    assert {"name": "storage", "version": "1"} in plan["plugins"]
    assert _module(plan, "files")["plugin"] == "storage" and "files_router" in plan["routers"]["order"]
    assert codegen_gaps(_module(plan, "tasks")) == []


def test_use_cases_check_the_upload_and_responses_sign_a_url(tmp_path):
    spec = storage_spec(tmp_path)
    plan = build_plan(spec)
    files = _files(spec, plan, "tasks")
    create = files["src/modules/tasks/usecases/create_task_usecase.py"]
    assert 'check_upload(storage, FILE_RULES["Task.attachment"], dto.attachment)' in create
    update = files["src/modules/tasks/usecases/update_task_usecase.py"]
    assert "if dto.attachment is not None and dto.attachment != current.attachment:" in update
    router = files["src/modules/tasks/presenter/router.py"]
    assert "storage: ObjectStorageDep," in router and "usecase.execute(body, storage)" in router
    dto = files["src/modules/tasks/presenter/dtos/task_response_dto.py"]
    assert '"attachment_url": signed_url(entity.attachment)' in dto and "attachment_url: str | None" in dto
    tests = files["tests/modules/tasks/test_task_api.py"]
    assert '"attachment": uploaded("Task.attachment"),' in tests  # the payload holds a real upload
    assert 'uploaded("Task.attachment", size=1048577)' in tests and "FILE_NOT_FOUND" in tests


def test_an_update_that_leaves_the_file_out_checks_no_upload(tmp_path):
    """A PATCH body without the file field (only the creator sets it): the update's DTO has no such field, so its use
    case checks no upload and its route takes no storage (a generated `dto.photo` there was a 500 on every update)."""
    spec = storage_spec(tmp_path)
    update = next(op for op in spec["operations"] if op["operationId"] == "task.update")
    update["request"] = {"fields": ["title"]}
    plan = build_plan(spec)
    files = _files(spec, plan, "tasks")
    usecase = files["src/modules/tasks/usecases/update_task_usecase.py"]
    assert "attachment" not in files["src/modules/tasks/presenter/dtos/update_task_dto.py"]
    assert "dto.attachment" not in usecase and "check_upload" not in usecase
    assert (
        'check_upload(storage, FILE_RULES["Task.attachment"], dto.attachment)'
        in files["src/modules/tasks/usecases/create_task_usecase.py"]
    ), "the create still checks it"


def test_the_project_has_the_storage_library_presign_module_settings_and_startup(tmp_path):
    from src.orchestrator.plugins.app import plugin_files

    spec = storage_spec(tmp_path, auth=True)
    plan = build_plan(spec)
    files = plugin_files(plan)
    assert '"Task.attachment": FileRule(' in files["src/libs/storage/catalog.py"]
    assert "ensure_bucket()\n    yield" in files["src/main.py"]
    usecase = files["src/modules/files/usecases/presign_usecase.py"]
    assert "key = new_key(rule, dto.filename, owner)" in usecase  # signed in: the caller's folder
    assert "current_user: CurrentUserDep" in files["src/modules/files/presenter/router.py"]
    assert "def test_presign_upload_then_read(client):" in files["tests/modules/files/test_files_api.py"]
    names = {setting.name for setting in REGISTRY["storage"].settings(plan)}
    assert names >= {"storage_endpoint", "storage_public_endpoint", "storage_bucket", "storage_secret_key"}
    for relative, source in files.items():
        if relative.endswith(".py"):
            compile(source, relative, "exec")


def test_the_contract_says_where_files_come_from_and_how_to_upload(tmp_path):
    contract = build_contract(storage_spec(tmp_path))
    schemas = contract["components"]["schemas"]
    upload = schemas["CreateTaskRequest"]["properties"]["attachment"]["x-bga"]
    assert upload["source"] == "upload" and upload["upload"]["presign"] == "files.presign"
    assert schemas["TaskResponse"]["properties"]["attachmentUrl"]["format"] == "uri"
    assert contract["x-bga"]["entities"]["Task"]["fileFields"] == [
        {"field": "attachment", "urlField": "attachmentUrl", "kind": "file"}
    ]
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    assert [s["name"] for s in ops["files.presign"]["x-bga"]["scenarios"]] == [
        "success", "wrong type", "too large", "unknown field"]  # fmt: skip
    missing = next(s for s in ops["task.create"]["x-bga"]["scenarios"] if s["name"] == "attachment not uploaded")
    assert missing["expect"] == {"status": 400, "code": "FILE_NOT_FOUND"}
    fixtures = contract["x-bga"]["fixtures"]["Task"]
    assert fixtures[0]["attachment"] == "task/attachment/shared/seed/1.pdf"
    assert {"key": "task/attachment/shared/seed/1.pdf", "contentType": "application/pdf"} in contract["x-bga"][
        "storage"
    ]["objects"]


def test_accept_and_max_size_are_for_file_fields_only():
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["entities"][0]["fields"].append({"name": "notes", "type": "string", "accept": ["text/plain"]})
    raw["entities"][0]["fields"].append({"name": "scan", "type": "file", "accept": ["not a type"]})
    paths = {issue.path for issue in validate_spec_data(raw).report.errors}
    assert any(path.endswith("/accept") for path in paths) and any(path.endswith("/accept/0") for path in paths)


def test_the_local_store_names_buckets_and_spots_projects_with_files(tmp_path):
    import zipfile

    from src.preview.docker_preview import _has_storage
    from src.sandbox import object_store

    assert object_store.bucket("bga-preview", "gen_01ABC") == "bga-preview-gen-01abc"
    with zipfile.ZipFile(tmp_path / "with.zip", "w") as archive:
        archive.writestr(object_store.MARKER, "")
    with zipfile.ZipFile(tmp_path / "without.zip", "w") as archive:
        archive.writestr("src/main.py", "")
    assert _has_storage(tmp_path / "with.zip") and not _has_storage(tmp_path / "without.zip")


def test_a_seeds_outside_photo_urls_are_kept_and_the_calls_send_keys(tmp_path):
    """A drafted seed with demo photos (Unsplash links): the records keep and show them; the smoke seed uploads the
    key code would have given each such row, and the scenarios send that key, since uploads take keys only."""
    spec = storage_spec(tmp_path)
    photos = ["https://images.unsplash.com/photo-1519741497674-611481863552", "http://example.org/b.jpg"]
    spec["seed"] = [
        {"entity": "Project", "records": [{"name": f"Series {n}", "cover": url} for n, url in enumerate(photos, 1)]}
    ]
    contract = build_contract(spec)
    fixtures = contract["x-bga"]["fixtures"]["Project"]
    assert [row["cover"] for row in fixtures] == photos, "the records keep the photos"
    keys = [item["key"] for item in contract["x-bga"]["storage"]["objects"]]
    assert "project/cover/shared/seed/1.png" in keys and "project/cover/shared/seed/2.png" in keys
    assert not any(key.startswith("http") for key in keys), "nothing uploads under a URL"
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    for op_id in ("project.create", "project.update"):
        for scenario in ops[op_id]["x-bga"].get("scenarios", []):
            cover = (scenario.get("body") or {}).get("cover")
            assert cover is None or not cover.startswith("http"), (op_id, scenario["name"], cover)
    success = next(s for s in ops["project.create"]["x-bga"]["scenarios"] if s["name"] == "success")
    assert success["body"]["cover"] == "project/cover/shared/seed/1.png"


def test_the_read_url_of_an_outside_link_is_the_link():
    library = (
        Path(__file__).parents[1] / "templates/plugins/storage/backend/files/src/libs/storage/dependencies.py"
    ).read_text()
    assert 'if key.startswith(("https://", "http://")):\n        return key' in library
