#!/bin/bash

# 等待所有 Redis 节点就绪
echo "Waiting for Redis nodes to be ready..."
for port in 6379 6380 6381 6382 6383 6384; do
    node_num=$(($port - 6378))
    until docker exec redis-node-$node_num redis-cli -p $port ping | grep -q PONG; do
        echo "Waiting for redis-node-$node_num:$port..."
        sleep 2
    done
    echo "redis-node-$node_num:$port is ready"
done

echo "All Redis nodes are ready. Creating cluster..."

# 在 redis-node-1 容器内创建集群
docker exec -it redis-node-1 redis-cli --cluster create \
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
echo "Cluster info:"
docker exec redis-node-1 redis-cli -p 6379 cluster info | grep cluster_state

echo "Cluster nodes:"
docker exec redis-node-1 redis-cli -p 6379 cluster nodes
