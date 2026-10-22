import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.schemas import TaskCreate, TaskResponse, TaskListResponse, CacheMeta
from app.crud import get_all_tasks, create_task, delete_task

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger("task_api.tasks")


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    assignee: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if status or assignee:
        from sqlalchemy import select
        from app.models import Task

        query = select(Task)
        if status:
            query = query.where(Task.status == status)
        if assignee:
            query = query.where(Task.assignee == assignee)
        query = query.order_by(Task.created_at.desc())

        result = await db.execute(query)
        tasks = [TaskResponse.model_validate(t) for t in result.scalars().all()]
        return TaskListResponse(
            tasks=tasks,
            total=len(tasks),
            cache=CacheMeta(hit=False, ttl=0),
        )

    tasks, cache_hit = await get_all_tasks(db)
    return TaskListResponse(
        tasks=tasks,
        total=len(tasks),
        cache=CacheMeta(hit=cache_hit, ttl=settings.cache_ttl if cache_hit else 0),
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create(task_in: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = await create_task(db, task_in)
    logger.info("Task created: id=%s title=%s", task.id, task.title)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def remove(task_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    logger.info("Task deleted: id=%s", task_id)
