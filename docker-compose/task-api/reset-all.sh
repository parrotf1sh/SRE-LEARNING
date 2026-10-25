#!/bin/bash

set -e

echo "=== 开始完全重置环境 ==="

# 1. 停止并删除所有容器、网络、数据卷
echo "1. 清理旧环境..."
sudo docker compose down -v

# 2. 重新构建镜像
echo "2. 重新构建 task-api 镜像..."
sudo docker compose build --no-cache task-api

# 3. 启动所有服务
echo "3. 启动所有服务..."
sudo docker compose up -d

echo "4. 等待服务初始化..."
sleep 30

# 4. 初始化 MySQL 主从复制
echo "5. 初始化 MySQL 主从复制..."
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-root_password} ./mysql/init-replication.sh

# 5. 初始化 Redis Cluster
echo "6. 初始化 Redis Cluster..."
./redis/init-cluster.sh

# 6. 验证
echo "7. 验证服务状态..."
sudo docker compose ps

echo ""
echo "=== 重置完成！==="
echo "测试 API: curl http://localhost/health"
