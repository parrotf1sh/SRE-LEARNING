# MiniOps

SRE 运维监控工具箱，用于自动检查 FastAPI、MySQL、Redis 及对应容器的健康状态，支持磁盘/内存监控、告警通知、数据库备份与恢复。

## 功能概览

| 功能 | 命令 | 说明 |
|------|------|------|
| 健康检查 | `miniops check` | 检查 HTTP/MySQL/Redis/Docker/系统 状态 |
| 测试告警 | `miniops alert` | 发送测试告警到配置的通道 |
| 数据库备份 | `miniops backup` | mysqldump 逻辑备份 + 自动轮转 |
| 恢复指南 | `miniops restore` | 输出恢复步骤说明或执行恢复 |
| 定时巡检 | `miniops daemon` | 后台持续运行，定期执行检查 |
| 状态报告 | `miniops report` | 输出当前状态报告（表格/JSON） |

## 快速开始

### 1. 安装依赖

```bash
cd scripts/py/MiniOps
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/default.yaml`，根据你的环境调整：

```yaml
targets:
  http:
    - url: "http://localhost:80/health"   # nginx 暴露的 health endpoint
  mysql:
    - container: "task-api-mysql-master-1"
  redis:
    - { container: "task-api-redis-node-1-1", port: 6379 }
    # ... 其他节点
```

环境变量会自动覆盖配置中的敏感值：
- `MYSQL_ROOT_PASSWORD` — MySQL 密码
- `WEBHOOK_URL` — Webhook 告警地址
- `SMTP_HOST` / `SMTP_USERNAME` / `SMTP_PASSWORD` — 邮件配置

### 3. 运行检查

```bash
# 全量检查
python -m miniops.cli check

# 只检查 MySQL 和 Redis
python -m miniops.cli check --only mysql,redis

# JSON 格式输出
python -m miniops.cli check --format json

# 输出到日志文件
python -m miniops.cli check --log-file miniops.log
```

## 运行示例

### 健康检查

```bash
$ python -m miniops.cli check

MiniOps Health Check Report
  2026-10-25 10:30:00 UTC
------------------------------------------------------------------------
  CATEGORY     NAME                                STATUS      LATENCY  MESSAGE
------------------------------------------------------------------------
  docker       task-api-mysql-master-1             OK         12.3ms  Up 2 hours (healthy)
  docker       task-api-mysql-slave-1              OK         12.3ms  Up 2 hours (healthy)
  docker       task-api-redis-node-1-1             OK         12.3ms  Up 2 hours (healthy)
  docker       task-api-task-api-1                 OK         12.3ms  Up 2 hours (healthy)
  http         http://localhost:80/health           OK          5.2ms  HTTP 200 OK
  mysql        task-api-mysql-master-1             OK          8.1ms  MySQL ping OK
  mysql        task-api-mysql-master-1-replication OK         12.4ms  Replication OK
  redis        task-api-redis-node-1-1:6379        OK          3.5ms  Redis PING OK
  redis        redis-cluster                       OK          6.8ms  Cluster OK (6 nodes, 3 masters)
  system       disk-/                              OK          0.1ms  45.2% used (120.5/256.0 GB)
  system       memory                              OK          0.0ms  62.3% used (10.0/16.0 GB)
------------------------------------------------------------------------
  Total: 11  |  OK: 11  |  FAIL: 0
```

### 模拟故障检测

```bash
# 停止 task-api 容器
$ docker stop task-api-task-api-1

# 运行检查
$ python -m miniops.cli check

MiniOps Health Check Report
------------------------------------------------------------------------
  CATEGORY     NAME                                STATUS      LATENCY  MESSAGE
------------------------------------------------------------------------
  docker       task-api-task-api-1                 FAIL       15.2ms  Exited (0) 1 minute ago
  http         http://localhost:80/health           FAIL      5002.1ms  Connection refused
  ...
------------------------------------------------------------------------
  Total: 11  |  OK: 9  |  FAIL: 2

# 恢复容器
$ docker start task-api-task-api-1

# 再次检查 — 状态自动恢复
$ python -m miniops.cli check
  Total: 11  |  OK: 11  |  FAIL: 0
```

### 数据库备份

```bash
# 执行备份
$ python -m miniops.cli backup
Backup completed: ./backups/mysql_backup_20261025_103000.sql.gz (2.35 MB)

# 列出已有备份
$ python -m miniops.cli backup --list
File                                                         Size  Modified
------------------------------------------------------------------------------------------
./backups/mysql_backup_20261025_103000.sql.gz               2.35MB  2026-10-25T10:30:00
```

### 恢复数据库

```bash
# 查看恢复指南
$ python -m miniops.cli restore --file ./backups/mysql_backup_20261025_103000.sql.gz

# 执行恢复（会覆盖现有数据，请谨慎）
$ python -m miniops.cli restore --file ./backups/mysql_backup_20261025_103000.sql.gz --execute
```

### 定时巡检（daemon 模式）

```bash
# 前台运行（默认每 5 分钟检查一次）
$ python -m miniops.cli daemon

# 后台运行
$ nohup python -m miniops.cli daemon --log-file miniops.log &

# 使用系统 crontab（替代方案）
# crontab -e
*/5 * * * * cd /path/to/MiniOps && python -m miniops.cli check --log-file miniops.log
```

### 告警配置

告警通道默认关闭。启用步骤：

**Webhook（企业微信/钉钉/飞书）：**

```bash
# 1. 设置环境变量
export WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 2. 编辑 config/default.yaml
#    alerting.channels[0].enabled: true
#    alerting.channels[0].platform: "wecom"  # 或 dingtalk / feishu

# 3. 测试
python -m miniops.cli alert
```

**邮件告警：**

```bash
# 1. 设置环境变量
export SMTP_HOST="smtp.example.com"
export SMTP_USERNAME="alert@example.com"
export SMTP_PASSWORD="your_password"

# 2. 编辑 config/default.yaml
#    alerting.channels[1].enabled: true
#    alerting.channels[1].recipients: ["oncall@example.com"]

# 3. 测试
python -m miniops.cli alert
```

## 项目结构

```
scripts/py/MiniOps/
├── miniops/
│   ├── cli.py              # CLI 入口（子命令模式）
│   ├── config.py            # 配置加载（YAML + 环境变量覆盖）
│   ├── runner.py            # 编排：调度所有 checker，汇总结果
│   ├── reporter.py          # 输出：终端表格 + JSON + 日志文件
│   ├── scheduler.py         # daemon 模式：定时巡检
│   ├── result.py            # 数据结构：CheckResult, Alert
│   ├── checker/
│   │   ├── base.py          # BaseChecker 抽象基类
│   │   ├── http_checker.py  # HTTP 端点检查
│   │   ├── mysql_checker.py # MySQL ping + 主从复制检查
│   │   ├── redis_checker.py # Redis Cluster PING + 集群状态
│   │   ├── docker_checker.py # 容器运行状态检查
│   │   └── system_checker.py # 磁盘空间 + 内存使用
│   ├── alerter/
│   │   ├── base.py          # BaseAlerter 抽象基类
│   │   ├── webhook.py       # Webhook 告警（企业微信/钉钉/飞书）
│   │   └── email_alerter.py # SMTP 邮件告警
│   └── backup/
│       ├── mysql_backup.py  # mysqldump 备份 + 压缩 + 轮转
│       └── restore.py       # 恢复指南生成 + 执行
├── config/
│   └── default.yaml         # 默认配置
├── tests/                   # 单元测试
├── requirements.txt
└── README.md
```

## 设计说明

### Checker 架构

所有 checker 实现 `BaseChecker` 接口，返回 `list[CheckResult]`。Runner 通过 `ThreadPoolExecutor` 并发执行不同 category 的 checker。

MySQL 和 Redis 检查通过 `docker exec` 在容器内执行命令，无需在宿主机安装客户端工具，同时顺带验证容器存活状态。

### 告警级别

| 级别 | 触发条件 |
|------|---------|
| `critical` | HTTP/MySQL/Redis/Docker 检查失败 |
| `warning` | 系统资源超过 warn 阈值、磁盘/内存告警 |

### 备份策略

- 使用 `mysqldump --all-databases --single-transaction` 做一致性全量备份
- 自动 gzip 压缩
- 保留最近 N 份备份（默认 7 份），自动轮转清理旧备份
- 不包含 Redis RDB 快照

## 测试

```bash
cd scripts/py/MiniOps
pip install pytest pytest-asyncio
pytest tests/ -v
```

## 与 health-checker 的关系

MiniOps 从 `scripts/py/health-checker/` 演进而来，复用了：
- `CheckResult` 数据结构（扩展了 category、details 字段）
- 重试逻辑（`check_with_retry`）
- JSON 日志格式
- 并发调度模式

原有 health-checker 保留不动，MiniOps 是独立的新工具。
