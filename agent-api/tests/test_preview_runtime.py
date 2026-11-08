"""A frontend preview starts from the frontend lane's validated build (2026-11-08): building the ZIP's Dockerfile
installs and builds again (about two minutes on a laptop), while the validation has just built the same source. The
runtime is that build with the project's own last Dockerfile stage as a build context (about ten seconds); without
it, or when it is older than a source, the preview builds the ZIP as before."""

import io
import os
import tarfile
import time
from pathlib import Path

from docker.errors import BuildError, ImageNotFound

from src.orchestrator.packaging import PREVIEW_RUNTIME, ArtifactWriter, build_preview_runtime, write_frontend
from src.preview.docker_frontend_preview import DockerFrontendPreviewRuntime

OVERLAY = Path(__file__).parents[1] / "templates" / "nextjs_overlay" / "files"


def _built(project: Path, kind: str = "dynamic") -> Path:
    """A generated frontend after `next build`: sources first, the build after them."""
    (project / "src" / "app").mkdir(parents=True)
    (project / "src" / "app" / "page.tsx").write_text("export default function Page() { return null; }\n")
    (project / "package.json").write_text("{}\n")
    (project / "Dockerfile").write_text((OVERLAY / kind / "Dockerfile").read_text())
    (project / "public").mkdir()
    (project / "public" / "logo.svg").write_text("<svg/>")
    if kind == "static":
        (project / "nginx.conf").write_text("server {}\n")
        (project / "out").mkdir()
        (project / "out" / "index.html").write_text("<html></html>")
    past = time.time() - 60
    for path in project.rglob("*"):
        os.utime(path, (past, past))
    standalone = project / ".next" / "standalone"
    (standalone / "node_modules" / ".pnpm" / "next@16" / "node_modules" / "next").mkdir(parents=True)
    (standalone / "server.js").write_text("// server\n")
    (standalone / "node_modules" / "next").symlink_to(".pnpm/next@16/node_modules/next")
    (project / ".next" / "static" / "chunks").mkdir(parents=True)
    (project / ".next" / "static" / "chunks" / "main.js").write_text("// chunk\n")
    (project / ".next" / "BUILD_ID").write_text("build-1")
    return project


def _members(data: bytes) -> dict[str, tarfile.TarInfo]:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        return {member.name: member for member in archive.getmembers()}


def _dockerfile(data: bytes) -> str:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        return archive.extractfile("Dockerfile").read().decode()


def test_the_runtime_is_the_validated_build_with_the_projects_last_stage(tmp_path):
    data = build_preview_runtime(_built(tmp_path))
    assert data is not None
    members = _members(data)
    assert {"rootfs/app/server.js", "rootfs/app/.next/static/chunks/main.js", "rootfs/app/public/logo.svg"} <= set(
        members
    ), "where the stage's copies put them"
    assert members["rootfs/app/node_modules/next"].issym(), "pnpm's relative links stay links"
    assert not any("page.tsx" in name for name in members), "only what the last stage copies"
    dockerfile = _dockerfile(data)
    assert dockerfile.startswith("FROM node:22-bookworm-slim\n")
    assert dockerfile.count("COPY ") == 1 and "COPY --chown=node:node rootfs/app/ /app/" in dockerfile, "one layer"
    assert 'CMD ["node", "server.js"]' in dockerfile and "pnpm" not in dockerfile and "--from" not in dockerfile


def test_a_static_site_copies_its_export_and_its_server_config(tmp_path):
    data = build_preview_runtime(_built(tmp_path, "static"))
    assert data is not None
    assert {"nginx.conf", "out/index.html"} <= set(_members(data))
    dockerfile = _dockerfile(data)
    assert "COPY nginx.conf /etc/nginx/conf.d/default.conf" in dockerfile, "outside a WORKDIR: copies of their own"
    assert "COPY out /usr/share/nginx/html" in dockerfile


def test_no_runtime_when_a_source_changed_after_the_build_or_there_is_no_build(tmp_path):
    project = _built(tmp_path / "changed")
    (project / "src" / "app" / "page.tsx").write_text("export default function Page() { return 1; }\n")
    assert build_preview_runtime(project) is None
    project = _built(tmp_path / "unbuilt")
    (project / ".next" / "BUILD_ID").unlink()
    assert build_preview_runtime(project) is None


def test_a_runtime_that_no_longer_matches_the_zip_is_emptied(tmp_path):
    project = _built(tmp_path / "frontend")
    writer = ArtifactWriter(tmp_path / "artifacts", "gen_1")
    write_frontend(writer, project)
    assert {a.name for a in writer.written} == {"frontend.zip", PREVIEW_RUNTIME}
    (project / "src" / "app" / "page.tsx").write_text("// changed\n")
    write_frontend(writer, project)
    runtime = next(a for a in writer.written if a.name == PREVIEW_RUNTIME)
    assert runtime.size == 0 and (tmp_path / "artifacts" / runtime.path).read_bytes() == b""


class _Images:
    def __init__(self, fail_runtime: bool = False):
        self.builds: list[dict] = []
        self.fail_runtime = fail_runtime

    def get(self, tag):
        raise ImageNotFound(tag)

    def build(self, **kwargs):
        self.builds.append(kwargs)
        if kwargs.get("custom_context") and self.fail_runtime:
            raise BuildError("no such base image", [])
        return None, iter([{"stream": "Step 1/5\n"}])


class _Client:
    def __init__(self, images):
        self.images = images


def test_the_preview_image_is_built_from_the_runtime_when_there_is_one(tmp_path):
    runtime = tmp_path / PREVIEW_RUNTIME
    runtime.write_bytes(build_preview_runtime(_built(tmp_path / "frontend")))
    images = _Images()
    log = DockerFrontendPreviewRuntime(client=_Client(images))._ensure_image("gen_1", tmp_path / "missing.zip", runtime)
    assert len(images.builds) == 1 and images.builds[0]["custom_context"] and images.builds[0]["encoding"] == "gzip"
    assert log.startswith("built from the validated build")


def test_a_runtime_that_fails_to_build_falls_back_to_the_zip(tmp_path):
    runtime = tmp_path / PREVIEW_RUNTIME
    runtime.write_bytes(build_preview_runtime(_built(tmp_path / "frontend")))
    import zipfile

    source = tmp_path / "frontend.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("Dockerfile", "FROM scratch\n")
    images = _Images(fail_runtime=True)
    DockerFrontendPreviewRuntime(client=_Client(images))._ensure_image("gen_1", source, runtime)
    assert [bool(build.get("custom_context")) for build in images.builds] == [True, False], "then the ZIP's Dockerfile"
