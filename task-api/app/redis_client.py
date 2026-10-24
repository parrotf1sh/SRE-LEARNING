import redis.asyncio as aioredis
from redis.asyncio.cluster import RedisCluster, ClusterNode
from app.config import settings

redis_client: RedisCluster | None = None


async def init_redis():
    global redis_client
    nodes = [
        ClusterNode(host=host, port=port)
        for host, port in settings.redis_cluster_nodes
    ]
    redis_client = RedisCluster(
        startup_nodes=nodes,
        decode_responses=True,
    )
    await redis_client.initialize()


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
