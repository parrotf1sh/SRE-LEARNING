"""Tests for task CRUD endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_task(client):
    """Should create a new task and return 201."""
    task_data = {
        "title": "Test task",
        "description": "Test description",
        "status": "pending",
        "priority": "medium",
        "assignee": "test_user"
    }

    response = await client.post("/tasks", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test task"
    assert data["description"] == "Test description"
    assert data["status"] == "pending"
    assert data["priority"] == "medium"
    assert data["assignee"] == "test_user"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_task_minimal(client):
    """Should create a task with only required fields."""
    task_data = {"title": "Minimal task"}

    response = await client.post("/tasks", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal task"
    assert data["description"] == ""
    assert data["status"] == "pending"
    assert data["priority"] == "medium"
    assert data["assignee"] == ""


@pytest.mark.asyncio
async def test_create_task_invalid_status(client):
    """Should reject invalid status value."""
    task_data = {
        "title": "Test task",
        "status": "invalid_status"
    }

    response = await client.post("/tasks", json=task_data)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_empty_title(client):
    """Should reject empty title."""
    task_data = {"title": ""}

    response = await client.post("/tasks", json=task_data)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks_empty(client):
    """Should return empty list when no tasks exist."""
    response = await client.get("/tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["tasks"] == []
    assert data["total"] == 0
    assert "cache" in data


@pytest.mark.asyncio
async def test_list_tasks_with_data(client):
    """Should return all tasks."""
    await client.post("/tasks", json={"title": "Task 1"})
    await client.post("/tasks", json={"title": "Task 2"})

    response = await client.get("/tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["tasks"]) == 2


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(client):
    """Should filter tasks by status."""
    await client.post("/tasks", json={"title": "Task 1", "status": "pending"})
    await client.post("/tasks", json={"title": "Task 2", "status": "done"})

    response = await client.get("/tasks?status=pending")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_tasks_filter_by_assignee(client):
    """Should filter tasks by assignee."""
    await client.post("/tasks", json={"title": "Task 1", "assignee": "alice"})
    await client.post("/tasks", json={"title": "Task 2", "assignee": "bob"})

    response = await client.get("/tasks?assignee=alice")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["assignee"] == "alice"


@pytest.mark.asyncio
async def test_delete_task(client):
    """Should delete an existing task and return 204."""
    create_response = await client.post("/tasks", json={"title": "To delete"})
    task_id = create_response.json()["id"]

    delete_response = await client.delete(f"/tasks/{task_id}")

    assert delete_response.status_code == 204

    list_response = await client.get("/tasks")
    assert list_response.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_task_not_found(client):
    """Should return 404 when deleting non-existent task."""
    response = await client.delete("/tasks/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
