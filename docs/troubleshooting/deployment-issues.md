# 任务管理 API 部署排障报告

**文档版本**: 1.0  
**最后更新**: 2026-10-25  
**适用范围**: FastAPI + MySQL 主从 + Redis Cluster + Docker Compose 架构

---

## 目录

1. [排障方法论](#排障方法论)
2. [Redis Cluster 部署问题](#redis-cluster-部署问题)
3. [MySQL 主从复制问题](#mysql-主从复制问题)
4. [task-api 应用问题](#task-api-应用问题)
5. [Docker 构建与部署问题](#docker-构建与部署问题)
6. [综合排障检查清单](#综合排障检查清单)

---

## 排障方法论

### 核心原则

1. **先观察，后行动**: 查看日志和状态，不要盲目修改配置
2. **分层排查**: 基础设施 → 中间件 → 应用层 → 业务逻辑
3. **最小变量法**: 一次只改一个变量，验证后再改下一个
4. **记录一切**: 每次操作和结果都要记录，便于回溯

### 通用排查流程

```
1. 确认故障现象
   └─ 具体错误信息是什么？
   └─ 影响范围多大？
   └─ 是持续还是间歇性？

2. 收集日志
   └─ 容器日志: sudo docker compose logs -f [service]
   └─ 应用日志: 查看 JSON 结构化日志中的 error/warning
   └─ 系统日志: dmesg, journalctl

3. 检查状态
   └─ 容器状态: sudo docker compose ps
   └─ 健康检查: 查看 health status
   └─ 网络连接: sudo docker exec [container] ping [target]

4. 定位根因
   └─ 从错误信息提取关键词
   └─ 对照本文档的关键词索引
   └─ 检查配置一致性

5. 修复验证
   └─ 修复后重启相关服务
   └─ 验证功能恢复正常
   └─ 监控 5-10 分钟确认无复发
```

---

## Redis Cluster 部署问题

### 问题 1: cluster-bus-port 配置错误

**故障现象**
- Redis 容器启动后立即退出
- 日志报错: `Invalid configuration directive for cluster-bus-port`

**排查过程**
1. 查看容器日志: `sudo docker compose logs redis-node-1`
2. 发现关键词: `Invalid configuration directive`
3. 检查 Redis 版本: `redis:7.4.11`
4. 查阅 Redis 7.4 文档，发现 cluster-bus-port 不再支持显式配置

**故障根因**
Redis 7.x 版本中，cluster-bus-port 自动计算为 client_port + 10000，不支持手动配置。

**修复操作**
```bash
# 删除所有 redis.conf 中的 cluster-bus-port 配置
for i in {1..6}; do
  sed -i '/cluster-bus-port/d' docker-compose/task-api/redis/node$i/redis.conf
done

# 重启 Redis 容器
sudo docker compose restart redis-node-{1..6}
```

**恢复验证**
```bash
# 检查所有 Redis 容器运行状态
sudo docker compose ps | grep redis

# 验证集群通信端口
sudo docker exec redis-node-1 redis-cli -p 6379 CLUSTER NODES
# 应看到每个节点有两个端口：6379(client) 和 16379(bus)
```

**经验总结**
- **关键词**: `Invalid configuration directive` → 检查配置项是否与版本兼容
- **排查思路**: 版本差异 → 查阅官方文档 → 移除过时配置
- **预防措施**: 部署前确认配置项与镜像版本的兼容性

---

### 问题 2: Redis Cluster 未初始化

**故障现象**
- task-api 启动失败
- 日志报错: `RedisClusterException: All slots are not covered. 0 of 16384 covered`
- 应用无法连接 Redis

**排查过程**
1. 查看 task-api 日志: `sudo docker compose logs task-api`
2. 发现关键词: `All slots are not covered`
3. 手动进入容器检查集群状态:
   ```bash
   sudo docker exec -it redis-node-1 redis-cli -p 6379
   > CLUSTER INFO
   # 返回 cluster_state:fail
   > CLUSTER NODES
   # 返回空或只有单个节点
   ```
4. 确认集群未执行初始化

**故障根因**
Redis Cluster 容器启动后，需要手动执行 `redis-cli --cluster create` 命令初始化集群拓扑。容器自动启动不会自动创建集群。

**修复操作**
```bash
# 执行集群初始化脚本
cd docker-compose/task-api
bash redis/init-cluster.sh

# 或手动执行
sudo docker exec -it redis-node-1 redis-cli --cluster create \
  127.0.0.1:6379 127.0.0.1:6380 127.0.0.1:6381 \
  127.0.0.1:6382 127.0.0.1:6383 127.0.0.1:6384 \
  --cluster-replicas 1
```

**恢复验证**
```bash
# 验证集群状态
sudo docker exec redis-node-1 redis-cli -p 6379 CLUSTER INFO
# 应返回: cluster_state:ok, cluster_size:3

# 验证槽位分配
sudo docker exec redis-node-1 redis-cli -p 6379 CLUSTER NODES | grep master
# 应看到 3 个 master，每个负责 5461-5462 个槽位

# 重启 task-api
sudo docker compose restart task-api

# 验证应用连接
curl http://localhost/tasks
# 应正常返回数据
```

**经验总结**
- **关键词**: `All slots are not covered` → 集群未初始化或节点未加入
- **排查思路**: 检查 CLUSTER INFO → 检查 CLUSTER NODES → 确认初始化命令
- **启动顺序**: Redis 容器健康 → 执行 init-cluster.sh → 启动 task-api
- **预防措施**: 在 reset-all.sh 中自动化集群初始化步骤

---

## MySQL 主从复制问题

### 问题 1: 认证插件不兼容

**故障现象**
- Slave_IO_Running: Connecting（持续重连）
- Slave_SQL_Running: Yes
- Seconds_Behind_Master: NULL
- 错误日志: `Authentication plugin 'caching_sha2_password' reported error: Authentication requires secure connection`

**排查过程**
1. 检查从库复制状态:
   ```bash
   sudo docker exec -it mysql-master mysql -uroot -p
   mysql> SHOW SLAVE STATUS\G
   ```
2. 发现关键词: `Last_IO_Error: ... caching_sha2_password`
3. 检查 repl_user 认证方式:
   ```sql
   SELECT user, host, plugin FROM mysql.user WHERE user='repl_user';
   # 返回: plugin = caching_sha2_password
   ```
4. 确认 MySQL 8.0 默认使用 caching_sha2_password，但主从复制需要 mysql_native_password

**故障根因**
MySQL 8.0 默认认证插件为 caching_sha2_password，该插件要求加密连接。主从复制的 IO 线程默认不使用加密连接，导致认证失败。

**修复操作**
```bash
# 修改 init-replication.sh，使用 mysql_native_password 创建 repl_user
# 关键代码:
CREATE USER 'repl_user'@'%' IDENTIFIED WITH mysql_native_password WITH 'your_password';

# 重建用户（如果已存在）
sudo docker exec -it mysql-master mysql -uroot -p
mysql> DROP USER 'repl_user'@'%';
mysql> CREATE USER 'repl_user'@'%' IDENTIFIED WITH mysql_native_password WITH 'your_password';
mysql> GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';
mysql> FLUSH PRIVILEGES;

# 重新配置从库
sudo docker exec -it mysql-slave mysql -uroot -p
mysql> STOP SLAVE;
mysql> CHANGE MASTER TO
  MASTER_HOST='mysql-master',
  MASTER_USER='repl_user',
  MASTER_PASSWORD='your_password',
  MASTER_LOG_FILE='mysql-bin.000001',
  MASTER_LOG_POS=0;
mysql> START SLAVE;
```

**恢复验证**
```bash
# 检查复制状态
sudo docker exec -it mysql-slave mysql -uroot -p
mysql> SHOW SLAVE STATUS\G
# 应返回:
# Slave_IO_Running: Yes
# Slave_SQL_Running: Yes
# Seconds_Behind_Master: 0

# 测试数据同步
# 在主库创建测试数据
sudo docker exec -it mysql-master mysql -uroot -p
mysql> USE task_api;
mysql> INSERT INTO tasks (title, description) VALUES ('test', 'replication test');

# 在从库查询
sudo docker exec -it mysql-slave mysql -uroot -p
mysql> USE task_api;
mysql> SELECT * FROM tasks WHERE title='test';
# 应能看到刚插入的数据
```

**经验总结**
- **关键词**: `caching_sha2_password` + `secure connection` → 认证插件不兼容
- **排查思路**: SHOW SLAVE STATUS → 查看 Last_IO_Error → 检查用户认证插件
- **修复原则**: 主从复制用户必须使用 mysql_native_password
- **预防措施**: 在 init-repl.sql 中明确指定 WITH mysql_native_password

---

### 问题 2: Docker Socket 权限不足

**故障现象**
- init-replication.sh 脚本执行失败
- 报错: `permission denied` 或 `Cannot connect to the Docker daemon`

**排查过程**
1. 查看脚本执行输出，发现 docker 命令失败
2. 检查当前用户权限: `groups`
3. 确认用户不在 docker 组
4. 尝试手动执行: `docker ps` → 失败
5. 尝试: `sudo docker ps` → 成功

**故障根因**
Ubuntu 系统默认不允许普通用户直接访问 Docker socket (/var/run/docker.sock)，需要 sudo 权限或加入 docker 组。

**修复操作**
```bash
# 方案 1: 脚本中所有 docker 命令加 sudo（推荐）
# 修改 init-replication.sh 和 init-cluster.sh
# 将所有 docker exec 改为 sudo docker exec

# 方案 2: 将当前用户加入 docker 组（需重新登录）
sudo usermod -aG docker $USER
# 然后重新登录或执行: newgrp docker
```

**恢复验证**
```bash
# 验证脚本可以正常执行
bash docker-compose/task-api/mysql/init-replication.sh
# 应看到: "MySQL replication setup completed successfully"
```

**经验总结**
- **关键词**: `permission denied` + `docker` → 权限问题
- **排查思路**: 检查用户组 → 测试 docker 命令 → 确认是否需要 sudo
- **最佳实践**: 初始化脚本中使用 sudo，确保在任何环境下都能执行

---

### 问题 3: 密码不一致

**故障现象**
- 容器内测试: `mysql -uroot -proot_password` 返回 `Access denied`
- 实际密码是: `root_password_123456`

**排查过程**
1. 查看 docker-compose.yml，发现硬编码密码: `MYSQL_ROOT_PASSWORD=root_password`
2. 查看 .env.example，发现用户修改了实际密码
3. 确认 docker-compose.yml 没有使用环境变量替换

**故障根因**
docker-compose.yml 中硬编码了默认密码，用户在 .env 文件中修改密码后，yml 文件没有使用环境变量替换，导致密码不一致。

**修复操作**
```yaml
# 修改 docker-compose.yml，使用环境变量替换
environment:
  MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root_password}
# 这样会优先读取 .env 文件中的 MYSQL_ROOT_PASSWORD，如果没有则使用默认值
```

**恢复验证**
```bash
# 重启 MySQL 容器
sudo docker compose down mysql-master mysql-slave
sudo docker compose up -d mysql-master mysql-slave

# 使用正确密码测试
sudo docker exec -it mysql-master mysql -uroot -p${MYSQL_ROOT_PASSWORD}
# 应成功进入 MySQL shell
```

**经验总结**
- **关键词**: `Access denied` + 确认密码正确 → 检查配置一致性
- **排查思路**: 对比 .env 和 docker-compose.yml → 确认是否使用变量替换
- **最佳实践**: 所有敏感配置使用 `${VAR:-default}` 格式，支持环境变量覆盖

---

## task-api 应用问题

### 问题 1: Python 模块导入陷阱（关键问题）

**故障现象**
- 日志显示: `"Redis initialized"` 成功
- 但请求日志显示: `"redis_client=False"`
- 缓存未命中，每次都查询数据库
- 手动检查 Redis 有数据，但应用读不到

**排查过程**
1. 查看应用日志:
   ```bash
   sudo docker compose logs -f task-api
   ```
2. 发现矛盾: 初始化成功，但使用时 redis_client=False
3. 添加调试日志:
   ```python
   logger.info(f"get_all_tasks called, redis_client={redis_client is not None}")
   ```
4. 确认 redis_client 在 crud.py 中始终为 None
5. 检查导入方式:
   ```python
   from app.redis_client import redis_client  # 问题所在
   ```
6. 理解 Python 模块导入机制: 导入的是值（None），不是引用

**故障根因**
Python 的 `from module import variable` 导入的是变量在导入时刻的值，而不是引用。当 `init_redis()` 后续修改 `redis_client` 全局变量时，crud.py 中导入的仍然是旧的 None 值。

**修复操作**
```python
# 错误方式（导入值）
from app.redis_client import redis_client

# 正确方式（导入模块引用）
from app import redis_client as redis_module

# 使用时通过模块访问
if redis_module.redis_client:
    await redis_module.redis_client.get(key)
```

**恢复验证**
```bash
# 重建镜像
sudo docker compose build task-api
sudo docker compose up -d task-api

# 查看日志
sudo docker compose logs -f task-api

# 第一次请求（应缓存未命中，设置缓存）
curl http://localhost/tasks
# 日志: "Cache set for tasks list, TTL=60s"

# 第二次请求（应缓存命中）
curl http://localhost/tasks
# 日志: "Cache hit for tasks list"
# 响应: "cache":{"hit":true,"ttl":60}
```

**经验总结**
- **关键词**: 初始化成功但使用时为 None → Python 模块导入陷阱
- **排查思路**: 检查导入方式 → 理解值导入 vs 引用导入 → 添加调试日志确认
- **修复原则**: 全局状态变量必须通过模块引用访问，不能直接导入值
- **预防措施**: 对全局状态（如数据库连接、客户端实例）统一使用 `import module` 方式

---

### 问题 2: pool_pre_ping 兼容性问题

**故障现象**
- 健康检查失败: `MySQL health check failed`
- 错误日志: `AsyncAdapt_aiomysql_connection.ping() missing 1 required positional argument: 'reconnect'`

**排查过程**
1. 查看健康检查日志:
   ```bash
   sudo docker compose logs task-api | grep -i health
   ```
2. 发现关键词: `ping() missing ... argument`
3. 检查 database.py 配置:
   ```python
   engine = create_async_engine(settings.database_url, pool_pre_ping=True)
   ```
4. 搜索 aiomysql 文档，发现 pool_pre_ping 与 aiomysql 存在兼容性问题

**故障根因**
SQLAlchemy 的 pool_pre_ping 功能在 aiomysql 驱动下存在 bug，调用 ping() 方法时参数不匹配。

**修复操作**
```python
# 移除 pool_pre_ping 参数
engine = create_async_engine(
    settings.database_url,
    echo=False,
    # pool_pre_ping=True  # 移除此行
)
```

**恢复验证**
```bash
# 重启 task-api
sudo docker compose restart task-api

# 检查健康状态
sudo docker compose ps | grep task-api
# 应显示: (healthy)

# 验证功能
curl http://localhost/health
# 应返回: {"status":"healthy","mysql":"connected","redis":"connected"}
```

**经验总结**
- **关键词**: `ping() missing argument` → aiomysql 兼容性问题
- **排查思路**: 检查 SQLAlchemy 配置 → 搜索驱动兼容性 → 移除问题参数
- **替代方案**: 使用应用层心跳检测代替连接池级别的 pre_ping

---

### 问题 3: Logger 命名不一致

**故障现象**
- 日志格式混乱，部分显示 `app.crud`，部分显示 `task_api.crud`
- 日志过滤和聚合困难

**排查过程**
1. 查看日志输出:
   ```bash
   sudo docker compose logs task-api | jq .logger
   ```
2. 发现不一致:
   - `task_api.main`
   - `task_api.tasks`
   - `app.crud` ← 不一致
3. 检查 crud.py 代码:
   ```python
   logger = logging.getLogger(__name__)  # 问题所在
   ```
4. 其他模块使用显式命名:
   ```python
   logger = logging.getLogger("task_api.tasks")
   ```

**故障根因**
使用 `__name__` 会自动生成模块路径（如 `app.crud`），而其他模块使用显式命名（如 `task_api.tasks`），导致命名不一致。

**修复操作**
```python
# 统一使用显式命名
logger = logging.getLogger("task_api.crud")
```

**恢复验证**
```bash
# 重启应用
sudo docker compose restart task-api

# 检查日志命名
sudo docker compose logs task-api | jq .logger
# 应全部显示: task_api.*
```

**经验总结**
- **最佳实践**: 统一使用显式 logger 命名，格式为 `project.module`
- **好处**: 便于日志过滤、聚合和权限控制

---

## Docker 构建与部署问题

### 问题 1: 缺少 curl 导致健康检查失败

**故障现象**
- task-api 容器状态: `(unhealthy)`
- 健康检查日志: `curl: command not found`

**排查过程**
1. 查看容器状态:
   ```bash
   sudo docker compose ps
   # task-api: (unhealthy)
   ```
2. 查看健康检查日志:
   ```bash
   sudo docker inspect --format='{{json .State.Health}}' task-api | jq
   ```
3. 发现错误: `curl: command not found`
4. 检查 Dockerfile 基础镜像: `python:3.11-slim`
5. 确认 slim 版本不包含 curl

**故障根因**
python:3.11-slim 是精简版镜像，不包含 curl 等常用工具，而健康检查依赖 curl。

**修复操作**
```dockerfile
# 在 Dockerfile 中安装 curl
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
```

**恢复验证**
```bash
# 重建镜像
sudo docker compose build task-api
sudo docker compose up -d task-api

# 等待 30 秒后检查状态
sudo docker compose ps | grep task-api
# 应显示: (healthy)
```

**经验总结**
- **关键词**: `command not found` → 缺少依赖包
- **排查思路**: 检查基础镜像 → 确认缺失工具 → 在 Dockerfile 中安装
- **最佳实践**: 在 Dockerfile 中明确列出所有依赖，不依赖镜像默认配置

---

### 问题 2: 国内网络下载超时

**故障现象**
- Docker 构建时 pip 安装超时: `TimeoutError: The read operation timed out`
- apt-get 更新超时

**排查过程**
1. 查看构建日志，发现下载速度慢或超时
2. 测试网络:
   ```bash
   curl -I https://pypi.org/simple/
   curl -I https://deb.debian.org/
   ```
3. 确认是国际出口带宽问题

**故障根因**
国内访问 PyPI 和 Debian 官方源速度慢，容易超时。

**修复操作**
```dockerfile
# 使用清华镜像源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' \
    /etc/apt/sources.list.d/debian.sources

RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**恢复验证**
```bash
# 重建镜像，观察下载速度
sudo docker compose build --no-cache task-api
# 应看到下载速度明显提升
```

**经验总结**
- **关键词**: `TimeoutError` + `pip install` → 网络问题
- **排查思路**: 测试网络延迟 → 确认源地址 → 切换国内镜像
- **最佳实践**: 在国内环境部署时，默认使用清华/阿里云镜像

---

### 问题 3: 启动顺序问题

**故障现象**
- task-api 启动失败，状态: `(unhealthy)`
- nginx 未启动
- 日志显示 Redis Cluster 未初始化

**排查过程**
1. 查看启动顺序:
   ```bash
   sudo docker compose ps
   # 发现 task-api 和 Redis 同时启动
   ```
2. 查看 task-api 日志:
   ```bash
   sudo docker compose logs task-api
   # 发现: Redis Cluster 未初始化
   ```
3. 检查 reset-all.sh 脚本，发现启动顺序不合理

**故障根因**
docker-compose.yml 中 task-api 依赖 Redis，但只是等待容器健康，不等待集群初始化完成。Redis 容器健康 ≠ 集群可用。

**修复操作**
```bash
# 修改 reset-all.sh，调整启动顺序
# 1. 启动 MySQL 和 Redis 容器
sudo docker compose up -d mysql-master mysql-slave redis-node-{1..6}

# 2. 等待容器健康
sleep 10

# 3. 初始化 MySQL 主从复制
bash mysql/init-replication.sh

# 4. 初始化 Redis Cluster
bash redis/init-cluster.sh

# 5. 验证集群状态
# ...

# 6. 最后启动 task-api 和 nginx
sudo docker compose up -d task-api nginx
```

**恢复验证**
```bash
# 执行完整重置脚本
bash reset-all.sh

# 检查所有服务状态
sudo docker compose ps
# 应全部显示: (healthy)

# 验证功能
curl http://localhost/tasks
# 应正常返回数据
```

**经验总结**
- **关键认知**: 容器健康 ≠ 服务可用（如 Redis 容器健康 ≠ 集群可用）
- **排查思路**: 检查依赖服务的实际可用性，不仅看容器状态
- **最佳实践**: 在编排脚本中明确启动顺序，手动控制初始化流程

---

## 综合排障检查清单

### 快速诊断流程

```
1. 容器状态检查
   □ sudo docker compose ps
   □ 所有容器是否 (healthy)?
   □ 是否有容器反复重启?

2. 日志检查
   □ sudo docker compose logs -f [service]
   □ 是否有 ERROR/WARNING 级别日志?
   □ 是否有关键词: timeout, connection refused, permission denied?

3. 网络连通性
   □ 容器间能否 ping 通?
   □ 端口是否正确监听?
   □ 防火墙是否放行?

4. 配置一致性
   □ .env 和 docker-compose.yml 密码是否一致?
   □ 端口映射是否正确?
   □ 环境变量是否正确传递?

5. 依赖服务可用性
   □ MySQL 主从复制是否正常? (SHOW SLAVE STATUS)
   □ Redis Cluster 是否初始化? (CLUSTER INFO)
   □ 应用是否正确连接中间件?
```

### 常见关键词索引

| 关键词 | 可能原因 | 排查方向 |
|--------|---------|---------|
| `All slots are not covered` | Redis Cluster 未初始化 | 执行 init-cluster.sh |
| `caching_sha2_password` | MySQL 认证插件不兼容 | 改用 mysql_native_password |
| `Access denied` | 密码错误或权限不足 | 检查密码一致性，确认用户权限 |
| `Connection refused` | 服务未启动或端口错误 | 检查容器状态和端口配置 |
| `TimeoutError` | 网络问题或服务无响应 | 检查网络连通性，查看服务日志 |
| `permission denied` | 权限不足 | 检查文件权限，是否需要 sudo |
| `command not found` | 缺少依赖包 | 在 Dockerfile 中安装 |
| `Invalid configuration directive` | 配置项与版本不兼容 | 查阅官方文档，移除过时配置 |
| `ping() missing argument` | 驱动兼容性问题 | 搜索已知问题，调整配置参数 |
| `redis_client=False` | Python 模块导入陷阱 | 检查导入方式，使用模块引用 |

### 恢复验证标准

修复完成后，必须验证以下内容:

1. **容器状态**: 所有容器 `(healthy)`
2. **功能测试**: 核心 API 正常响应
3. **缓存验证**: 第二次请求应命中缓存
4. **数据同步**: MySQL 主从数据一致
5. **日志检查**: 无 ERROR 级别日志
6. **持续监控**: 观察 5-10 分钟无复发

---

## 附录: 常用诊断命令

```bash
# 查看所有容器状态
sudo docker compose ps

# 查看实时日志
sudo docker compose logs -f [service]

# 进入容器调试
sudo docker exec -it [container] /bin/bash

# 检查 MySQL 复制状态
sudo docker exec -it mysql-slave mysql -uroot -p -e "SHOW SLAVE STATUS\G"

# 检查 Redis Cluster 状态
sudo docker exec -it redis-node-1 redis-cli -p 6379 CLUSTER INFO
sudo docker exec -it redis-node-1 redis-cli -p 6379 CLUSTER NODES

# 测试 API 缓存
curl -v http://localhost/tasks
curl -v http://localhost/tasks  # 第二次应命中缓存

# 查看容器资源使用
sudo docker stats

# 重启单个服务
sudo docker compose restart [service]

# 重建并重启
sudo docker compose build [service] && sudo docker compose up -d [service]
```

---

**文档维护说明**: 遇到新的故障场景时，按照相同格式补充到对应章节，保持文档的持续更新和实用性。
