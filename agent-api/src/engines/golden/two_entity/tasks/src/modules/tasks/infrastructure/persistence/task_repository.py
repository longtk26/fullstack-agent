import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from src.libs.database.session import SessionDep
from src.libs.exceptions import BadRequestException, ConflictException, ErrorCode
from src.modules.shared.domain.entities import TaskEntity
from src.modules.shared.infrastructure.models import TaskModel
from src.modules.tasks.ports.output.task_repository import ITaskRepository

FOREIGN_KEY_VIOLATION = "23503"


class TaskRepository(ITaskRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, task: TaskEntity) -> TaskEntity:
        model = self.__to_model(task)
        self.session.add(model)
        self.__flush()
        return self.__to_entity(model)

    def find_by_id(self, task_id: uuid.UUID) -> TaskEntity | None:
        model = self.session.get(TaskModel, task_id)
        return self.__to_entity(model) if model else None

    def list(
        self, filters: dict[str, Any], sort: tuple[str, bool] | None, limit: int, offset: int
    ) -> tuple[list[TaskEntity], int]:
        query = select(TaskModel)
        for attribute, value in filters.items():
            query = query.where(col(getattr(TaskModel, attribute)) == value)
        total = self.session.exec(select(func.count()).select_from(query.subquery())).one()
        if sort:
            column = col(getattr(TaskModel, sort[0]))
            query = query.order_by(column.desc().nulls_last() if sort[1] else column.asc().nulls_last())
        query = query.order_by(col(TaskModel.id))
        models = self.session.exec(query.offset(offset).limit(limit)).all()
        return [self.__to_entity(model) for model in models], total

    def update(self, task: TaskEntity) -> TaskEntity:
        model = self.session.get(TaskModel, task.id)
        for key, value in task.model_dump(exclude={"id"}).items():
            setattr(model, key, value)
        self.__flush()
        return self.__to_entity(model)

    def delete(self, task_id: uuid.UUID) -> None:
        model = self.session.get(TaskModel, task_id)
        if model is not None:
            self.session.delete(model)
            self.session.flush()

    def __flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            if getattr(exc.orig, "pgcode", None) == FOREIGN_KEY_VIOLATION:
                message = "The referenced project does not exist"
                raise BadRequestException(message, ErrorCode.REFERENCE_NOT_FOUND) from exc
            raise ConflictException("The task conflicts with an existing record") from exc

    def __to_entity(self, model: TaskModel) -> TaskEntity:
        return TaskEntity.model_validate(model.model_dump())

    def __to_model(self, entity: TaskEntity) -> TaskModel:
        return TaskModel(**entity.model_dump(exclude_none=True))


ITaskRepoDep = Annotated[ITaskRepository, Depends(TaskRepository)]
