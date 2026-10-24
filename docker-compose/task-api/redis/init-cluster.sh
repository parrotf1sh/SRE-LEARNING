#!/bin/bash

# 等待所有 Redis 节点就绪
echo "Waiting for Redis nodes to be ready..."
for port in 6379 6380 6381 6382 6383 6384; do
    until redis-cli -h redis-node-$(($port - 6378)) -p $port ping | grep -q PONG; do
        echo "Waiting for redis-node-$(($port - 6378)):$port..."
        sleep 2
    done
    echo "redis-node-$(($port - 6378)):$port is ready"
done

echo "All Redis nodes are ready. Creating cluster..."

# 创建集群：3 主 3 从
# --cluster-replicas 1 表示每个 master 配 1 个 slave
redis-cli --cluster create \
    redis-node-1:6379 \
    redis-node-2:6380 \
    redis-node-3:6381 \
    redis-node-4:6382 \
    redis-node-5:6383 \
    redis-node-6:6384 \
    --cluster-replicas 1 \
    --cluster-yes

echo "Redis cluster created successfully!"

# 验证集群状态
redis-cli -h redis-node-1 -p 6379 cluster info
redis-cli -h redis-node-1 -p 6379 cluster nodes
