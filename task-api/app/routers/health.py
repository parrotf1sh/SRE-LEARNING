import time
import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.redis_client import redis_client

router = APIRouter(tags=["health"])
logger = logging.getLogger("task_api.health")


async def _check_mysql() -> dict:
    start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "connected", "latency_ms": latency}
    except Exception as e:
        logger.warning("MySQL health check failed: %s", e)
        return {"status": "disconnected", "error": str(e)}


async def _check_redis() -> dict:
    start = time.perf_counter()
    try:
        if not redis_client:
            return {"status": "not_initialized"}
        await redis_client.ping()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "connected", "latency_ms": latency}
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return {"status": "disconnected", "error": str(e)}


@router.get("/health")
async def health_check():
    mysql_info = await _check_mysql()
    redis_info = await _check_redis()

    healthy = mysql_info["status"] == "connected"
    return {
        "status": "healthy" if healthy else "unhealthy",
        "mysql": mysql_info,
        "redis": redis_info,
    }
