# Task API Docker Compose 部署指南

完整的容器化部署方案，包含 Nginx 反向代理、MySQL 主从复制、Redis Cluster（3主3从）和后端任务管理 API。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                   (task-api-network)                     │
│                                                          │
│  ┌─────────┐                                            │
│  │  nginx  │ :80 → 反向代理到 task-api:8000             │
│  └────┬────┘                                            │
│       │                                                 │
│  ┌────▼─────────┐                                       │
│  │  task-api    │ :8000 (内部)                           │
│  └──┬───────┬───┘                                       │
│     │       │                                           │
│     │       └──────────────────────┐                   │
│     │                              │                   │
│  ┌──▼──────────┐            ┌──────▼──────────────┐   │
│  │ mysql-master│            │  Redis Cluster      │   │
│  │    :3306    │            │  (6 nodes)          │   │
│  └──┬──────────┘            │  6379-6384          │   │
│     │                       └─────────────────────┘   │
│  ┌──▼──────────┐                                       │
│  │ mysql-slave │                                       │
│  │    :3306    │                                       │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
docker-compose/task-api/
├── docker-compose.yml          # 容器编排主文件
├── nginx/
│   └── nginx.conf              # Nginx 反向代理配置
├── mysql/
│   ├── master/
│   │   ├── my.cnf              # Master 配置（server-id=1, binlog）
│   │   └── init-repl.sql       # 创建复制用户
│   ├── slave/
│   │   └── my.cnf              # Slave 配置（server-id=2, read-only）
│   └── init-replication.sh     # 主从复制初始化脚本
└── redis/
    ├── node1/redis.conf        # Redis 节点 1 配置
    ├── node2/redis.conf        # Redis 节点 2 配置
    ├── node3/redis.conf        # Redis 节点 3 配置
    ├── node4/redis.conf        # Redis 节点 4 配置
    ├── node5/redis.conf        # Redis 节点 5 配置
    ├── node6/redis.conf        # Redis 节点 6 配置
    └── init-cluster.sh         # Redis Cluster 初始化脚本
```

## 快速开始

### 1. 启动所有容器

```bash
cd docker-compose/task-api
docker compose up -d
```

等待所有服务健康检查通过（约 30-60 秒）：

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 2. 初始化 MySQL 主从复制

所有容器启动后，执行主从复制初始化脚本：

```bash
MYSQL_ROOT_PASSWORD=your_password ./mysql/init-replication.sh
```

验证主从状态：

```bash
# 进入 slave 容器
docker exec -it mysql-slave mysql -uroot -proot_password

# 查看 slave 状态
SHOW SLAVE STATUS\G

# 确认以下字段：
# Slave_IO_Running: Yes
# Slave_SQL_Running: Yes
# Seconds_Behind_Master: 0
```

### 3. 初始化 Redis Cluster

执行集群初始化脚本：

```bash
./redis/init-cluster.sh
```

验证集群状态：

```bash
# 进入任意 Redis 节点
docker exec -it redis-node-1 redis-cli -p 6379

# 查看集群信息
cluster info
# 确认 cluster_state:ok

# 查看节点分布
cluster nodes
# 应看到 3 个 master 和 3 个 slave
```

### 4. 访问服务

通过 Nginx 访问后端 API：

```bash
# 健康检查
curl http://localhost/health

# 查询任务
curl http://localhost/tasks

# 创建任务
curl -X POST http://localhost/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"测试任务","priority":"high"}'
```

## 调试指南

### 进入容器内部

```bash
# MySQL Master
docker exec -it mysql-master mysql -uroot -proot_password

# MySQL Slave
docker exec -it mysql-slave mysql -uroot -proot_password

# Redis 节点（以 node-1 为例）
docker exec -it redis-node-1 redis-cli -p 6379

# 后端 API
docker exec -it task-api sh
```

### MySQL 调试

```sql
-- 在 master 上查看 binlog
SHOW MASTER STATUS;
SHOW BINARY LOGS;

-- 在 slave 上查看复制状态
SHOW SLAVE STATUS\G

-- 手动同步（如果需要）
STOP SLAVE;
START SLAVE;
```

### Redis Cluster 调试

```bash
# 查看集群信息
cluster info

# 查看节点分布
cluster nodes

# 查看槽位分配
cluster slots

# 测试写入（会自动路由到正确的 master）
set test_key "hello"
get test_key

# 查看 key 在哪个槽
cluster keyslot test_key
```

## 数据持久化

所有数据使用 Docker 命名卷持久化：

- `mysql_master_data` - MySQL Master 数据
- `mysql_slave_data` - MySQL Slave 数据
- `redis_node1_data` ~ `redis_node6_data` - Redis 各节点数据

**清除数据重新初始化：**

```bash
docker-compose down -v  # -v 参数会删除所有卷
docker-compose up -d
```

## 常用操作

### 停止服务

```bash
docker-compose down
```

### 重启单个服务

```bash
docker-compose restart task-api
```

### 查看实时日志

```bash
docker-compose logs -f task-api
docker-compose logs -f mysql-master
docker-compose logs -f redis-node-1
```

### 重新构建镜像

```bash
docker-compose build --no-cache task-api
docker-compose up -d task-api
```

## 端口映射

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|---------|-----------|------|
| Nginx | 80 | **80** | 对外暴露，HTTP 入口 |
| Task API | 8000 | 不暴露 | 仅内部访问，通过 Nginx 代理 |
| MySQL Master | 3306 | 不暴露 | 仅内部访问 |
| MySQL Slave | 3306 | 不暴露 | 仅内部访问 |
| Redis Cluster | 6379-6384 | 不暴露 | 仅内部访问 |

**调试时进入容器内部：**

```bash
# 虽然端口不对外暴露，但可以通过 docker exec 进入容器调试
docker exec -it mysql-master mysql -uroot -proot_password
docker exec -it redis-node-1 redis-cli -p 6379
```

## 环境变量

后端服务的环境变量在 `docker-compose.yml` 中配置：

```yaml
environment:
  DB_HOST: mysql-master          # 使用容器名作为主机名
  DB_PORT: 3306
  DB_USER: root
  DB_PASSWORD: root_password
  DB_NAME: task_api
  REDIS_NODES: redis-node-1:6379,redis-node-2:6380,...  # Redis Cluster 节点列表
```

## 故障排查

### 容器启动失败

```bash
# 查看详细日志
docker-compose logs mysql-master
docker-compose logs redis-node-1

# 检查健康检查状态
docker inspect --format='{{.State.Health.Status}}' mysql-master
```

### Redis Cluster 初始化失败

```bash
# 手动进入容器初始化
docker exec -it redis-node-1 redis-cli -p 6379 \
  --cluster create \
  redis-node-1:6379 redis-node-2:6380 redis-node-3:6381 \
  redis-node-4:6382 redis-node-5:6383 redis-node-6:6384 \
  --cluster-replicas 1 --cluster-yes
```

### MySQL 主从同步延迟

```bash
# 在 slave 上检查
docker exec -it mysql-slave mysql -uroot -proot_password -e "SHOW SLAVE STATUS\G" | grep Seconds_Behind_Master
```

## 安全建议

1. **修改默认密码**：编辑 `docker-compose.yml` 中的 `MYSQL_ROOT_PASSWORD`
2. **防火墙配置**：云服务器只开放 80 端口，MySQL 和 Redis 端口不对外暴露
3. **定期备份**：MySQL 数据卷需要定期备份到外部存储
