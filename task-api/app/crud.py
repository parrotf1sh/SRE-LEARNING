import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models import Task
from app.schemas import TaskCreate, TaskResponse
from app import redis_client as redis_module
from app.config import settings

logger = logging.getLogger("task_api.crud")

CACHE_KEY_TASKS = "cache:tasks:list"
CACHE_KEY_COUNT = "cache:tasks:count"


async def _invalidate_cache():
    if not redis_module.redis_client:
        return
    try:
        await redis_module.redis_client.delete(CACHE_KEY_TASKS, CACHE_KEY_COUNT)
    except Exception as e:
        logger.warning(f"Redis delete error: {e}")


async def get_all_tasks(db: AsyncSession) -> tuple[list[TaskResponse], bool]:
    logger.info(f"get_all_tasks called, redis_client={redis_module.redis_client is not None}")
    
    if redis_module.redis_client:
        try:
            cached = await redis_module.redis_client.get(CACHE_KEY_TASKS)
            if cached:
                logger.info("Cache hit for tasks list")
                return [TaskResponse(**t) for t in json.loads(cached)], True
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    tasks = [TaskResponse.model_validate(t) for t in result.scalars().all()]

    if redis_module.redis_client:
        try:
            data = json.dumps([t.model_dump(mode="json") for t in tasks])
            await redis_module.redis_client.set(CACHE_KEY_TASKS, data, ex=settings.cache_ttl)
            logger.info(f"Cache set for tasks list, TTL={settings.cache_ttl}s")
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    return tasks, False


async def get_task_count(db: AsyncSession) -> tuple[int, bool]:
    if redis_module.redis_client:
        try:
            cached = await redis_module.redis_client.get(CACHE_KEY_COUNT)
            if cached is not None:
                logger.info("Cache hit for task count")
                return int(cached), True
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

    result = await db.execute(select(func.count()).select_from(Task))
    count = result.scalar()

    if redis_module.redis_client:
        try:
            await redis_module.redis_client.set(CACHE_KEY_COUNT, str(count), ex=settings.cache_ttl)
            logger.info(f"Cache set for task count, TTL={settings.cache_ttl}s")
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    return count, False


async def create_task(db: AsyncSession, task_in: TaskCreate) -> Task:
    task = Task(**task_in.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await _invalidate_cache()
    return task


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    result = await db.execute(delete(Task).where(Task.id == task_id))
    await db.commit()
    if result.rowcount > 0:
        await _invalidate_cache()
        return True
    return False
