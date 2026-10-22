# Task API

一个用于 SRE 运维学习的任务管理后端服务。基于 FastAPI 构建，MySQL 持久化存储，Redis 缓存加速。

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 异步 REST API |
| 数据库 | MySQL | 任务数据持久化 |
| 缓存 | Redis | 热点查询缓存，TTL 60s |
| ORM | SQLAlchemy 2.0 | 异步模式 (aiomysql) |
| 日志 | Python logging | 结构化 JSON 格式 |

## 项目结构

```
task-api/
├── app/
│   ├── main.py            # FastAPI 应用入口，生命周期管理
│   ├── config.py           # 配置管理（环境变量）
│   ├── database.py         # MySQL 异步引擎与会话
│   ├── redis_client.py     # Redis 异步客户端
│   ├── models.py           # SQLAlchemy ORM 模型
│   ├── schemas.py          # Pydantic 请求/响应模型
│   ├── crud.py             # CRUD 操作 + 缓存读写逻辑
│   ├── middleware.py        # 请求日志中间件
│   ├── logging_config.py   # JSON 日志格式化
│   └── routers/
│       ├── health.py       # 健康检查端点
│       └── tasks.py        # 任务管理端点
├── requirements.txt
├── .env.example            # 环境变量模板
├── .gitignore
└── run.py                  # 启动入口
```

## 快速开始

### 1. 环境准备

- Python 3.10+
- MySQL 5.7+ / 8.0+
- Redis 6.0+

### 2. 初始化数据库

```sql
CREATE DATABASE IF NOT EXISTS task_api CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE task_api;

CREATE TABLE tasks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200)  NOT NULL,
    description VARCHAR(1000) DEFAULT '',
    status      VARCHAR(20)   NOT NULL DEFAULT 'pending',
    priority    VARCHAR(20)   NOT NULL DEFAULT 'medium',
    assignee    VARCHAR(100)  DEFAULT '',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_assignee (assignee)
) ENGINE=InnoDB;

-- 示例数据（可选）
INSERT INTO tasks (title, description, status, priority, assignee) VALUES
('部署监控系统', '在预发环境部署 Prometheus + Grafana', 'pending', 'high', '张三'),
('修复登录接口 500', '用户反馈登录偶发 500，需排查数据库连接池', 'done', 'high', '李四'),
('编写巡检脚本', '编写 Linux 日常巡检脚本，覆盖 CPU/内存/磁盘', 'pending', 'medium', '王五');
```

> 服务启动时也会自动建表（`init_db()`），手动执行 SQL 的好处是可以带示例数据。

### 3. 安装依赖

```bash
cd task-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 MySQL 和 Redis 连接信息：

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=task_api

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
```

### 5. 启动服务

```bash
python run.py
```

服务默认监听 `0.0.0.0:8000`，启动后可访问：

- Swagger 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## API 接口

### 健康检查

```
GET /health
```

返回服务状态及 MySQL、Redis 连通性：

```json
{
  "status": "healthy",
  "mysql": { "status": "connected", "latency_ms": 1.23 },
  "redis": { "status": "connected", "latency_ms": 0.45 }
}
```

### 查询任务列表

```
GET /tasks
GET /tasks?status=pending
GET /tasks?assignee=张三
```

响应包含缓存命中信息：

```json
{
  "tasks": [ ... ],
  "total": 3,
  "cache": { "hit": false, "ttl": 0 }
}
```

- 无过滤条件时走 Redis 缓存，`cache.hit` 标识是否命中
- 带 `status` / `assignee` 过滤时直接查 DB，不走缓存

### 创建任务

```
POST /tasks
Content-Type: application/json

{
  "title": "新任务",
  "description": "任务描述",
  "status": "pending",
  "priority": "high",
  "assignee": "李四"
}
```

字段说明：

| 字段 | 类型 | 必填 | 可选值 | 默认值 |
|------|------|------|--------|--------|
| title | string | 是 | - | - |
| description | string | 否 | - | "" |
| status | string | 否 | pending, done | pending |
| priority | string | 否 | low, medium, high | medium |
| assignee | string | 否 | - | "" |

### 删除任务

```
DELETE /tasks/{id}
```

成功返回 `204 No Content`，任务不存在返回 `404`。

## 缓存策略

采用 **Cache-Aside + 写时失效** 模式：

```
读请求 → Redis 命中? → 是 → 直接返回
                    → 否 → 查 MySQL → 写入 Redis (TTL=60s) → 返回

写请求 → 写 MySQL → 删除 Redis 缓存 key → 下次读请求自动回填
```

缓存的 key：

| Key | 内容 | 失效时机 |
|-----|------|----------|
| `cache:tasks:list` | 全量任务列表 JSON | 创建/删除任务时 DEL |
| `cache:tasks:count` | 任务总数 | 创建/删除任务时 DEL |

设计要点：

- **先写 DB，再删缓存**：避免并发场景下脏数据回填
- **删除而非更新**：简单可靠，由下次读请求自行回填
- **TTL 兜底**：即使删缓存失败，60s 后自动过期，DB 是 source of truth
- **Redis 故障降级**：Redis 不可用时所有操作直接走 DB，不影响业务

## 日志格式

所有请求输出结构化 JSON 日志，便于日志采集和分析：

```json
{
  "timestamp": "2026-10-22T14:30:00",
  "level": "INFO",
  "logger": "task_api.middleware",
  "message": "GET /tasks 200",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "GET",
  "path": "/tasks",
  "status_code": 200,
  "duration_ms": 12.34
}
```

每个请求自动分配 `X-Request-ID`（也可通过请求头传入自定义值），响应头中同样返回该 ID，方便链路追踪。

## SRE 实验建议

| 实验 | 操作 | 观察 |
|------|------|------|
| 缓存命中 | 连续调用 `GET /tasks` 两次 | 第二次 `cache.hit` 变为 `true` |
| 缓存失效 | 执行 `POST /tasks` 后再 `GET /tasks` | `cache.hit` 回到 `false` |
| 依赖故障 | 停掉 Redis (`systemctl stop redis`) | 服务正常运行，所有请求走 DB |
| 健康检查 | 停掉 MySQL | `/health` 返回 `status: unhealthy` |
| 日志分析 | 发送多个请求后用 `jq` 过滤日志 | 按 status_code / duration_ms 分析 |
| 请求追踪 | 带 `X-Request-ID` 头发送请求 | 日志和响应头中返回相同 ID |
