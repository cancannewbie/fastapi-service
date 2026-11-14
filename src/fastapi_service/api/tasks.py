"""Authenticated task management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import UserModel
from ..db.session import get_session
from ..db.task_model import TaskModel
from ..errors import NotFoundError
from ..task_schemas import Task, TaskCreate, TaskUpdate
from .auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])
Session = Annotated[AsyncSession, Depends(get_session)]
User = Annotated[UserModel, Depends(get_current_user)]


async def find_task(session: AsyncSession, owner_id: int, task_id: int) -> TaskModel:
    task = await session.scalar(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.owner_id == owner_id)
    )
    if task is None:
        raise NotFoundError(f"Task {task_id} does not exist")
    return task


@router.get("")
async def list_tasks(session: Session, user: User) -> list[Task]:
    result = await session.scalars(
        select(TaskModel).where(TaskModel.owner_id == user.id).order_by(TaskModel.id)
    )
    return [Task.model_validate(task) for task in result]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, session: Session, user: User) -> Task:
    task = TaskModel(owner_id=user.id, **payload.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return Task.model_validate(task)


@router.get("/{task_id}")
async def get_task(task_id: int, session: Session, user: User) -> Task:
    return Task.model_validate(await find_task(session, user.id, task_id))


@router.patch("/{task_id}")
async def update_task(task_id: int, payload: TaskUpdate, session: Session, user: User) -> Task:
    task = await find_task(session, user.id, task_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await session.commit()
    await session.refresh(task)
    return Task.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, session: Session, user: User) -> Response:
    task = await find_task(session, user.id, task_id)
    await session.delete(task)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
