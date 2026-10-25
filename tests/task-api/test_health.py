"""Tests for health check endpoint."""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Health check should return status and component info."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "mysql" in data
    assert "redis" in data
    assert data["status"] in ["healthy", "unhealthy"]


@pytest.mark.asyncio
async def test_health_check_mysql_info(client):
    """Health check should include MySQL connection info."""
    response = await client.get("/health")
    data = response.json()

    assert "status" in data["mysql"]
    assert data["mysql"]["status"] in ["connected", "disconnected"]


@pytest.mark.asyncio
async def test_health_check_redis_info(client):
    """Health check should include Redis connection info."""
    response = await client.get("/health")
    data = response.json()

    assert "status" in data["redis"]
    assert data["redis"]["status"] in ["connected", "disconnected", "not_initialized"]
