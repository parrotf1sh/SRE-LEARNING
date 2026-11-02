# Task-API Helm Chart

为 Task-API 应用（FastAPI + MySQL + Redis）设计的 Helm Chart。

## 包含的资源

| 资源 | 文件 | 作用 |
|------|------|------|
| Deployment | `templates/deployment.yaml` | 定义 Pod、副本和升级策略 |
| Service | `templates/service.yaml` | 提供稳定的内部访问入口 |
| ConfigMap | `templates/configmap.yaml` | 保存不敏感的业务配置 |
| Secret 引用 | `templates/secret.yaml` | 注入数据库、Redis 等连接凭据 |
| ServiceMonitor | `templates/servicemonitor.yaml` | 让 Prometheus 自动发现指标 |
| HTTPRoute | `templates/httproute.yaml` | Gateway API 路由规则 |
| HPA | `templates/hpa.yaml` | 根据负载自动扩缩容（可选） |

## 快速开始

### 前置条件

1. Kubernetes 集群（1.19+）
2. Helm 3.x
3. 已创建数据库和 Redis 的 Secret

### 安装 Chart

```bash
# 基础安装
helm install task-api ./charts/task-api \
  --namespace default \
  --create-namespace

# 自定义配置安装
helm install task-api ./charts/task-api \
  --namespace default \
  --set image.tag=v1.0.0 \
  --set replicaCount=3 \
  --set autoscaling.enabled=true

# 使用 values 文件安装
helm install task-api ./charts/task-api \
  --namespace default \
  -f my-values.yaml
```

### 创建必需的 Secret

```bash
# 数据库 Secret
kubectl create secret generic task-api-db-secret \
  --from-literal=DB_HOST=mysql.default.svc.cluster.local \
  --from-literal=DB_PORT=3306 \
  --from-literal=DB_USER=root \
  --from-literal=DB_PASSWORD=yourpassword \
  --from-literal=DB_NAME=task_api \
  -n default

# Redis Secret
kubectl create secret generic task-api-redis-secret \
  --from-literal=REDIS_NODES="redis-node-0:6379,redis-node-1:6380" \
  -n default
```

## 配置参数

### 全局配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `global.namespace` | 部署命名空间 | `""` (使用 release 的命名空间) |
| `replicaCount` | 副本数 | `2` |

### 镜像配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `image.repository` | 镜像仓库 | `ghcr.io/parrotf1sh/task-api` |
| `image.tag` | 镜像标签 | `dev-latest` |
| `image.pullPolicy` | 拉取策略 | `IfNotPresent` |
| `imagePullSecrets` | 镜像拉取密钥 | `[]` |

### Service 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `service.type` | Service 类型 | `ClusterIP` |
| `service.port` | 服务端口 | `8000` |
| `service.targetPort` | 容器端口 | `8000` |

### HTTPRoute 配置（Gateway API）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `httpRoute.enabled` | 是否启用 HTTPRoute | `true` |
| `httpRoute.hostnames` | 域名列表 | `["task-api.example.com"]` |
| `httpRoute.parentRefs` | 父 Gateway 引用 | 见 `values.yaml` |
| `httpRoute.rules` | 路由规则 | 见 `values.yaml` |

### 资源配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `resources.requests.cpu` | CPU 请求 | `100m` |
| `resources.requests.memory` | 内存请求 | `128Mi` |
| `resources.limits.cpu` | CPU 限制 | `500m` |
| `resources.limits.memory` | 内存限制 | `512Mi` |

### HPA 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `autoscaling.enabled` | 是否启用 HPA | `false` |
| `autoscaling.minReplicas` | 最小副本数 | `2` |
| `autoscaling.maxReplicas` | 最大副本数 | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | CPU 目标利用率 | `70` |
| `autoscaling.targetMemoryUtilizationPercentage` | 内存目标利用率 | `80` |

### 健康检查配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `healthCheck.enabled` | 是否启用健康检查 | `true` |
| `healthCheck.path` | 健康检查路径 | `/health` |
| `healthCheck.initialDelaySeconds` | 初始延迟 | `10` |
| `healthCheck.periodSeconds` | 检查间隔 | `10` |

### ServiceMonitor 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `serviceMonitor.enabled` | 是否启用 ServiceMonitor | `true` |
| `serviceMonitor.interval` | 抓取间隔 | `30s` |
| `serviceMonitor.path` | 指标路径 | `/metrics` |

### Secret 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `secrets.enabled` | 是否启用 Secret 引用 | `true` |
| `secrets.database.secretName` | 数据库 Secret 名称 | `task-api-db-secret` |
| `secrets.redis.secretName` | Redis Secret 名称 | `task-api-redis-secret` |

## 使用示例

### 示例 1：开发环境

```yaml
# dev-values.yaml
replicaCount: 1

image:
  tag: dev-latest

resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 256Mi

autoscaling:
  enabled: false

serviceMonitor:
  enabled: false
```

```bash
helm install task-api-dev ./charts/task-api -f dev-values.yaml
```

### 示例 2：生产环境

```yaml
# prod-values.yaml
replicaCount: 3

image:
  tag: v1.0.0

resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

httpRoute:
  enabled: true
  hostnames:
    - "task-api.prod.example.com"

serviceMonitor:
  enabled: true
  interval: 15s
```

```bash
helm install task-api-prod ./charts/task-api -f prod-values.yaml
```

## 升级和回滚

### 升级

```bash
# 升级版本
helm upgrade task-api ./charts/task-api \
  --set image.tag=v1.1.0

# 使用新配置升级
helm upgrade task-api ./charts/task-api -f new-values.yaml
```

### 回滚

```bash
# 查看历史版本
helm history task-api

# 回滚到上一版本
helm rollback task-api

# 回滚到指定版本
helm rollback task-api 2
```

## 测试

```bash
# 验证模板渲染
helm template task-api ./charts/task-api

# 检查配置错误
helm lint ./charts/task-api

# 使用自定义配置检查
helm lint ./charts/task-api -f my-values.yaml
```

## 卸载

```bash
# 卸载应用
helm uninstall task-api

# 卸载并删除 PVC
helm uninstall task-api --no-hooks
```

## 高级用法

### 使用 External Secrets Operator

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: task-api-db-secret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: cluster-secret-store
    kind: ClusterSecretStore
  target:
    name: task-api-db-secret
  data:
    - secretKey: DB_HOST
      remoteRef:
        key: /task-api/db/host
    - secretKey: DB_PASSWORD
      remoteRef:
        key: /task-api/db/password
```

### 自定义环境变量

```yaml
# values.yaml
env:
  - name: CUSTOM_VAR
    value: "custom-value"
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: api-key-secret
        key: api-key
```

### 挂载 ConfigMap 为文件

```yaml
# 在 deployment.yaml 中添加
volumes:
  - name: config-volume
    configMap:
      name: {{ include "task-api.fullname" . }}-config

containers:
  - name: {{ .Chart.Name }}
    volumeMounts:
      - name: config-volume
        mountPath: /app/config
        readOnly: true
```
