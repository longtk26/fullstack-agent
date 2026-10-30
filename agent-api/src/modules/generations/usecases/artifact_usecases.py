import posixpath
import zipfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends

from src.configs import config
from src.engines.workspace import WorkspaceViolation, ensure_inside
from src.libs.exceptions import BadRequestException, ConflictException, ErrorCode, NotFoundException
from src.modules.generations.ports.output import IArtifactRepoDep
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.shared.domain.entities import ArtifactEntity, UserEntity

SOURCE_ARTIFACT = "backend.zip"
SOURCE_ARTIFACTS = {"backend": SOURCE_ARTIFACT, "frontend": "frontend.zip"}
MAX_TEXT_BYTES = 1_000_000


def artifact_file(artifact: ArtifactEntity) -> Path:
    """The path comes from the DB row (written by the worker), never from the request; still kept under the root."""
    root = Path(config.artifact_root)
    try:
        path = ensure_inside(root / artifact.path, root)
    except WorkspaceViolation as exc:
        raise NotFoundException("Artifact file not found") from exc
    if not path.is_file():
        raise NotFoundException("Artifact file not found")
    return path


class ArtifactUsecase:
    def __init__(self, getter: GetGenerationUsecaseDep, artifact_repo: IArtifactRepoDep):
        self.getter = getter
        self.artifact_repo = artifact_repo

    async def list(self, generation_id: str, user: UserEntity) -> list[ArtifactEntity]:
        self.getter.load(generation_id, user)
        return self.artifact_repo.list_for_generation(generation_id)

    async def file(self, generation_id: str, artifact_id: str, user: UserEntity) -> tuple[ArtifactEntity, Path]:
        self.getter.load(generation_id, user)
        artifact = self.artifact_repo.find(generation_id, artifact_id)
        if artifact is None:
            raise NotFoundException("Artifact not found")
        return artifact, artifact_file(artifact)


class BrowseFilesUsecase:
    """Read-only view of the generated source, served from the packaged ZIP (workspaces are temporary):
    `backend.zip`, or `frontend.zip` with `source="frontend"` (the Assets gallery, Story 15.2)."""

    def __init__(self, getter: GetGenerationUsecaseDep, artifact_repo: IArtifactRepoDep):
        self.getter = getter
        self.artifact_repo = artifact_repo

    async def execute(self, generation_id: str, user: UserEntity, path: str, source: str = "backend") -> dict[str, Any]:
        self.getter.load(generation_id, user)
        artifact = self.artifact_repo.find_by_name(generation_id, SOURCE_ARTIFACTS[source])
        if artifact is None:
            raise ConflictException("The generation has no packaged source yet", code=ErrorCode.ARTIFACT_MISSING)
        wanted = _normalize(path)
        with zipfile.ZipFile(artifact_file(artifact)) as archive:
            infos = {info.filename: info for info in archive.infolist() if not info.is_dir()}
            if wanted in infos:
                info = infos[wanted]
                if info.file_size > MAX_TEXT_BYTES:
                    raise ConflictException("File is larger than 1 MB; download the ZIP", code=ErrorCode.FILE_NOT_TEXT)
                try:
                    content = archive.read(info).decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ConflictException("Binary file; download the ZIP", code=ErrorCode.FILE_NOT_TEXT) from exc
                return {"path": wanted, "type": "file", "size": info.file_size, "content": content}
            prefix = f"{wanted}/" if wanted else ""
            entries: dict[str, dict[str, Any]] = {}
            for name, info in infos.items():
                if not name.startswith(prefix):
                    continue
                head, _, rest = name[len(prefix) :].partition("/")
                if rest:
                    entries.setdefault(head, {"name": head, "path": prefix + head, "type": "dir", "size": None})
                else:
                    entries[head] = {"name": head, "path": name, "type": "file", "size": info.file_size}
            if not entries:
                raise NotFoundException("No such file or directory")
            ordered = sorted(entries.values(), key=lambda e: (e["type"] != "dir", e["name"]))
            return {"path": wanted, "type": "dir", "entries": ordered}


def _normalize(path: str) -> str:
    cleaned = posixpath.normpath("/" + path.strip()).lstrip("/")
    if cleaned == ".":
        return ""
    if "\\" in path or "\x00" in path or any(part == ".." for part in path.split("/")):
        raise BadRequestException("Invalid path")
    return cleaned


ArtifactUsecaseDep = Annotated[ArtifactUsecase, Depends(ArtifactUsecase)]
BrowseFilesUsecaseDep = Annotated[BrowseFilesUsecase, Depends(BrowseFilesUsecase)]
