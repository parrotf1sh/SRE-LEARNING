"""Tests for Prometheus metrics endpoint."""
import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_red_and_business_metrics(client):
    create_response = await client.post("/tasks", json={"title": "metrics task"})
    assert create_response.status_code == 201

    response = await client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body
    assert 'task_operations_total{operation="create",result="success"}' in body
