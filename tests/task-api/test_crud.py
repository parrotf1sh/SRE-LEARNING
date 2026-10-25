"""Unit tests for CRUD operations and caching logic."""
import pytest
import json
from unittest.mock import patch

from app.crud import get_all_tasks, create_task, delete_task, CACHE_KEY_TASKS
from app.schemas import TaskCreate


@pytest.mark.asyncio
async def test_get_all_tasks_no_cache(db_session, fake_redis):
    """Should fetch tasks from database when cache is empty."""
    await fake_redis.flushall()

    with patch("app.crud.redis_module.redis_client", fake_redis):
        tasks, cache_hit = await get_all_tasks(db_session)

    assert cache_hit is False
    assert isinstance(tasks, list)


@pytest.mark.asyncio
async def test_get_all_tasks_with_cache(db_session, fake_redis):
    """Should return cached tasks when available."""
    cached_data = json.dumps([
        {
            "id": 1,
            "title": "Cached task",
            "description": "",
            "status": "pending",
            "priority": "medium",
            "assignee": "",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
    ])
    await fake_redis.set(CACHE_KEY_TASKS, cached_data)

    with patch("app.crud.redis_module.redis_client", fake_redis):
        tasks, cache_hit = await get_all_tasks(db_session)

    assert cache_hit is True
    assert len(tasks) == 1
    assert tasks[0].title == "Cached task"


@pytest.mark.asyncio
async def test_create_task_invalidates_cache(db_session, fake_redis):
    """Should invalidate cache after creating a task."""
    await fake_redis.set(CACHE_KEY_TASKS, "[]")

    with patch("app.crud.redis_module.redis_client", fake_redis):
        task_in = TaskCreate(title="New task")
        await create_task(db_session, task_in)

    cached = await fake_redis.get(CACHE_KEY_TASKS)
    assert cached is None


@pytest.mark.asyncio
async def test_delete_task_invalidates_cache(db_session, fake_redis):
    """Should invalidate cache after deleting a task."""
    await fake_redis.set(CACHE_KEY_TASKS, "[]")

    with patch("app.crud.redis_module.redis_client", fake_redis):
        task_in = TaskCreate(title="To delete")
        task = await create_task(db_session, task_in)
        await fake_redis.set(CACHE_KEY_TASKS, "[]")

        await delete_task(db_session, task.id)

    cached = await fake_redis.get(CACHE_KEY_TASKS)
    assert cached is None


@pytest.mark.asyncio
async def test_delete_task_not_found(db_session, fake_redis):
    """Should return False when deleting non-existent task."""
    with patch("app.crud.redis_module.redis_client", fake_redis):
        result = await delete_task(db_session, 99999)

    assert result is False
