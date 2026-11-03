| 数据类型                   | 推荐备份方式                     |
| -------------------------- | -------------------------------- |
| Kubernetes 集群状态        | K3s SQLite 一致性备份            |
| MySQL 业务数据             | 数据库逻辑备份或一致性物理备份   |
| Redis 数据                 | 根据缓存可重建性决定是否需要备份 |
| GitOps 配置                | Git 仓库版本历史                 |
| Prometheus / Loki 历史数据 | 根据保留要求与存储后端决定       |

```
SHA=$(git rev-parse HEAD | cut -c1-7)
TAG="dev-${SHA}"
IMAGE="ccr.ccs.tencentyun.com/sre-learning/task-api"

echo "$IMAGE:$TAG"

docker build \
  -f docker/task-api/Dockerfile \
  -t "$IMAGE:$TAG" \
  -t "$IMAGE:dev-latest" \
  task-api/
  
docker login ccr.ccs.tencentyun.com --username=<TCR_USERNAME>

docker push "$IMAGE:$TAG"
docker push "$IMAGE:dev-latest"
```

```
kubectl port-forward svc/argocd-server -n argocd 8080:443
  
ssh -N -L 8080:127.0.0.1:8080 ubuntu@43.142.11.53
```



```
kubectl -n task-api create secret generic mysql-credentials \
  --from-literal=MYSQL_ROOT_PASSWORD='<ROOT_PASSWORD>' \
  --from-literal=MYSQL_PASSWORD='<APP_PASSWORD>'

kubectl -n task-api create secret generic task-api-db-secret \
  --from-literal=DB_HOST=mysql.task-api.svc.cluster.local \
  --from-literal=DB_PORT=3306 \
  --from-literal=DB_USER=taskapi \
  --from-literal=DB_PASSWORD='<APP_PASSWORD>' \
  --from-literal=DB_NAME=task_api

kubectl -n task-api create secret generic task-api-redis-secret \
  --from-literal=REDIS_NODES=redis.task-api.svc.cluster.local:6379
```

区分：

- 基础设施是否正常；
- Kubernetes 工作负载是否正常；
- 应用接口是否正常；
- 依赖服务是否正常；
- 用户是否真的受到影响。



#### 第一层：基础设施指标

| 指标            | 监控意义             |
| --------------- | -------------------- |
| CPU 使用率      | 节点计算资源是否紧张 |
| 内存使用率      | 是否存在内存压力     |
| 磁盘使用率      | 是否有空间耗尽风险   |
| 磁盘读写延迟    | 存储是否存在性能瓶颈 |
| 网络收发速率    | 网络吞吐趋势         |
| 网络错误/丢包   | 是否存在网络异常     |
| Node Ready 状态 | 节点是否正常参与调度 |

数据来源主要是 node-exporter、kubelet 及相关 Kubernetes 指标。

#### 第二层：Kubernetes 工作负载指标

| 指标                     | 监控意义                  |
| ------------------------ | ------------------------- |
| Pod Running / Ready 数量 | 应用实例是否健康          |
| Deployment 可用副本数    | 是否达到期望容量          |
| Pod 重启次数             | 是否存在反复崩溃          |
| Container CPU 使用量     | 是否存在资源争用          |
| Container 内存工作集     | 是否存在内存压力          |
| CPU Throttling           | 是否因 CPU limit 导致限流 |
| PVC 使用率               | 有状态服务容量是否不足    |
| HPA 当前/期望副本数      | 扩缩容行为是否合理        |

#### 第三层：Task-API 业务指标

这一层最重要。优先实现 HTTP 服务常用的 RED 指标：

- Rate：每秒请求数（RPS）。
- Errors：请求错误数量、错误率。
- Duration：请求耗时，尤其是 P95、P99 延迟。

还可以加上：

- 当前活跃请求数。
- 数据库连接池使用量。
- Redis 请求失败率。
- Task 创建成功/失败次数（如果你的项目具有这些业务操作）。

建议请求指标按 HTTP 方法、规范化路由模板、状态码分类，避免用原始用户 ID、任务 ID 作为指标标签。

为了支持 P95、P99 延迟分析，HTTP 请求耗时最好使用 Histogram 指标，而不仅仅记录平均响应时间。

#### 第四层：数据库与缓存指标

使用 mysqld-exporter、redis-exporter 等组件采集。

| MySQL                    | Redis                |
| ------------------------ | -------------------- |
| 实例在线状态             | 实例在线状态         |
| 当前连接数               | 当前客户端连接数     |
| 慢查询情况               | 内存使用量           |
| InnoDB 相关指标          | 命中率、缓存淘汰次数 |
| 查询吞吐                 | 每秒处理命令数       |
| 主从复制延迟（如果启用） | 复制状态（如果启用） |
| 存储空间                 | Key 过期、驱逐情况   |
