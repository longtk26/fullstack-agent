import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from src.libs.database.session import SessionDep
from src.libs.exceptions import ConflictException
from src.modules.projects.ports.output.project_repository import IProjectRepository
from src.modules.shared.domain.entities import ProjectEntity
from src.modules.shared.infrastructure.models import ProjectModel


class ProjectRepository(IProjectRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, project: ProjectEntity) -> ProjectEntity:
        model = self.__to_model(project)
        self.session.add(model)
        self.__flush()
        return self.__to_entity(model)

    def find_by_id(self, project_id: uuid.UUID) -> ProjectEntity | None:
        model = self.session.get(ProjectModel, project_id)
        return self.__to_entity(model) if model else None

    def list(self, sort: tuple[str, bool] | None, limit: int, offset: int) -> tuple[list[ProjectEntity], int]:
        query = select(ProjectModel)
        total = self.session.exec(select(func.count()).select_from(query.subquery())).one()
        if sort:
            column = col(getattr(ProjectModel, sort[0]))
            query = query.order_by(column.desc() if sort[1] else column.asc(), col(ProjectModel.id))
        else:
            query = query.order_by(col(ProjectModel.created_at), col(ProjectModel.id))
        models = self.session.exec(query.offset(offset).limit(limit)).all()
        return [self.__to_entity(model) for model in models], total

    def update(self, project: ProjectEntity) -> ProjectEntity:
        model = self.session.get(ProjectModel, project.id)
        for key, value in project.model_dump(exclude={"id", "created_at"}).items():
            setattr(model, key, value)
        self.__flush()
        return self.__to_entity(model)

    def delete(self, project_id: uuid.UUID) -> None:
        model = self.session.get(ProjectModel, project_id)
        if model is not None:
            self.session.delete(model)
            self.session.flush()

    def __flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ConflictException("A project with this name already exists") from exc

    def __to_entity(self, model: ProjectModel) -> ProjectEntity:
        return ProjectEntity.model_validate(model.model_dump())

    def __to_model(self, entity: ProjectEntity) -> ProjectModel:
        # exclude_none: let the model's default factories fill id / created_at
        return ProjectModel(**entity.model_dump(exclude_none=True))


IProjectRepoDep = Annotated[IProjectRepository, Depends(ProjectRepository)]
