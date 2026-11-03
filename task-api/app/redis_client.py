from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.asyncio.cluster import ClusterNode, RedisCluster

from app.config import settings

logger = logging.getLogger("task_api.redis")

redis_client: Redis | RedisCluster | None = None


async def _detect_mode(nodes: list[tuple[str, int]]) -> tuple[str, tuple[str, int]]:
    last_error: Exception | None = None
    for host, port in nodes:
        probe = Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        try:
            info = await probe.execute_command("INFO", "cluster")
            if "cluster_enabled:1" in str(info):
                return "cluster", (host, port)
            return "standalone", (host, port)
        except Exception as exc:
            last_error = exc
        finally:
            try:
                await probe.close()
            except Exception:
                pass
    raise RuntimeError(f"Redis 不可达，无法自动识别模式: {last_error}")


async def init_redis():
    global redis_client
    nodes = settings.redis_cluster_nodes
    if not nodes:
        raise RuntimeError("REDIS_NODES 为空")

    mode = settings.redis_mode.strip().lower()
    if mode not in {"auto", "standalone", "cluster"}:
        raise ValueError(f"不支持的 REDIS_MODE: {mode}")

    standalone_node = nodes[0]
    if mode == "auto":
        mode, standalone_node = await _detect_mode(nodes)
        logger.info("Redis mode auto-detected: %s (%s:%s)", mode, *standalone_node)
    elif mode == "standalone":
        logger.info("Redis mode forced: standalone (%s:%s)", *standalone_node)
    else:
        logger.info("Redis mode forced: cluster (%d startup nodes)", len(nodes))

    if mode == "standalone":
        host, port = standalone_node
        redis_client = Redis(host=host, port=port, decode_responses=True)
        await redis_client.ping()
    else:
        redis_client = RedisCluster(
            startup_nodes=[ClusterNode(host=host, port=port) for host, port in nodes],
            decode_responses=True,
        )
        await redis_client.initialize()


async def close_redis():
    if redis_client:
        await redis_client.close()
