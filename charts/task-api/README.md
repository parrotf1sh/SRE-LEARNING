# Task-API Helm Chart

Task-API（FastAPI + MySQL + Redis）的 Helm Chart。默认从腾讯云 TCR 公开仓库拉取镜像；数据库和 Redis 凭据由外部 Secret 注入，不会写入 Git。

## 资源清单

| 资源 | 模板 | 默认启用 | 说明 |
|------|------|----------|------|
| Deployment | `templates/deployment.yaml` | 是 | 2 副本，滚动更新 `maxUnavailable: 0` |
| Service | `templates/service.yaml` | 是 | ClusterIP，端口 8000 |
| ConfigMap | `templates/configmap.yaml` | 是 | 非敏感环境变量 |
| ServiceAccount | `templates/serviceaccount.yaml` | 是 | 不挂载 Kubernetes API token |
| Ingress | `templates/ingress.yaml` | 否 | 默认 `traefik`，K3s 可直接使用 |
| HTTPRoute | `templates/httproute.yaml` | 否 | 需要 Gateway API CRD |
| HPA | `templates/hpa.yaml` | 否 | 需要 metrics-server |
| ServiceMonitor | `templates/servicemonitor.yaml` | 否 | 需要 Prometheus Operator，且应用需暴露 `/metrics` |

Secret 不由 Chart 创建。`templates/secret.yaml` 已移除，避免外部 Secret 变更被误认为会触发 Pod 滚动更新。

## 前置条件

1. Kubernetes 1.23+
2. Helm 3.x
3. 节点可访问 `ccr.ccs.tencentyun.com`
4. 已创建数据库和 Redis 的 Secret
5. 可选：Ingress Controller、Gateway API CRD、metrics-server、Prometheus Operator

## 快速开始

```bash
helm install task-api ./charts/task-api \
  --namespace task-api \
  --create-namespace
```

默认镜像为 `ccr.ccs.tencentyun.com/sre-learning/task-api:dev-75165fe`（linux/amd64）。发布新镜像后更新 tag：

```bash
helm upgrade task-api ./charts/task-api \
  --namespace task-api \
  --set image.tag=dev-xxxxxxx
```

> 使用 `--set` 升级时，未显式指定的参数会回落到 Chart 默认值。生产环境建议把覆盖项写入独立的 values 文件，并用 `-f` 升级。

不要长期使用 `dev-latest`：`imagePullPolicy: IfNotPresent` 会让已缓存该 tag 的节点继续使用旧镜像。

## 必需的 Secret

```bash
kubectl create secret generic task-api-db-secret \
  --from-literal=DB_HOST=mysql.default.svc.cluster.local \
  --from-literal=DB_PORT=3306 \
  --from-literal=DB_USER=root \
  --from-literal=DB_PASSWORD='<password>' \
  --from-literal=DB_NAME=task_api \
  -n task-api

kubectl create secret generic task-api-redis-secret \
  --from-literal=REDIS_NODES='redis-node-0:6379,redis-node-1:6380' \
  -n task-api
```

| Secret | 必需键 |
|--------|--------|
| `task-api-db-secret` | `DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` |
| `task-api-redis-secret` | `REDIS_NODES` |

如果外部 Secret 的键名与上表不同，可以用 `env` + `valueFrom.secretKeyRef` 显式映射；显式 `env` 会覆盖 `envFrom` 注入的同名变量：

```yaml
env:
  - name: DB_HOST
    valueFrom:
      secretKeyRef:
        name: my-db-secret
        key: host
```

Secret 不由 Helm 管理，修改后需要手动重启：

```bash
kubectl rollout restart deployment/task-api -n task-api
```

## 关键配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `image.repository` | `ccr.ccs.tencentyun.com/sre-learning/task-api` | TCR 公开仓库 |
| `image.tag` | `dev-75165fe` | 必须显式指定，避免回退到不存在的 `appVersion` |
| `image.pullPolicy` | `IfNotPresent` | 配合不可变短 SHA tag 使用 |
| `replicaCount` | `2` | 启用 HPA 后由 HPA 管理 |
| `containerPort` | `8000` | 修改时同步修改 `args` 中的 `--port`；`service.port` 可独立设置 |
| `service.port` | `8000` | Service 端口 |
| `securityContext.runAsUser` | `999` | 与镜像内 `appuser` 的 UID/GID 一致 |
| `securityContext.readOnlyRootFilesystem` | `true` | 自动挂载可写的 `/tmp` emptyDir |
| `serviceAccount.create` | `true` | 创建独立 ServiceAccount |
| `serviceAccount.automountServiceAccountToken` | `false` | 应用不需要访问 Kubernetes API |
| `healthCheck.enabled` | `true` | 启动探针和存活探针使用 TCP，就绪探针解析 `/health` 响应体 |

存活探针只检查 TCP 端口，避免 MySQL/Redis 故障时反复重启 Pod；就绪探针解析 `/health` 返回的 `status` 字段，MySQL 异常时把 Pod 从 Service 端点中移除。Redis 仅作为缓存，断开时应用会回退到 MySQL，因此不影响就绪状态。

## 路由

默认不创建 Ingress 或 HTTPRoute，可先使用端口转发：

```bash
kubectl port-forward svc/task-api 8000:8000 -n task-api
```

### Ingress

```bash
helm upgrade task-api ./charts/task-api -n task-api \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=task-api.example.com
```

K3s 默认 IngressClass 为 `traefik`；使用 ingress-nginx 时设置 `ingress.className=nginx`。

### HTTPRoute

需要先安装 Gateway API CRD，并确认 Gateway 监听器名称：

```bash
helm upgrade task-api ./charts/task-api -n task-api \
  --set httpRoute.enabled=true \
  --set httpRoute.hostnames[0]=task-api.example.com \
  --set httpRoute.parentRefs[0].name=traefik-gateway \
  --set httpRoute.parentRefs[0].namespace=default \
  --set httpRoute.parentRefs[0].sectionName=https
```

`httpRoute.enabled` 和 `ingress.enabled` 不能同时为 `true`。启用 HTTPRoute 时 Helm 会检查 `gateway.networking.k8s.io/v1` 是否存在。

## 监控

应用当前没有 `/metrics` 端点，因此 `serviceMonitor.enabled` 默认关闭。直接启用会创建 ServiceMonitor，但 Prometheus 抓取会得到 404。实现指标导出后再启用：

```bash
helm upgrade task-api ./charts/task-api -n task-api \
  --set serviceMonitor.enabled=true
```

启用时 Helm 会检查 `monitoring.coreos.com/v1` 是否存在。

## HPA

```bash
helm upgrade task-api ./charts/task-api -n task-api \
  --set autoscaling.enabled=true
```

需要集群安装 metrics-server。启用后 Deployment 不再渲染 `replicas`，副本数由 HPA 管理。

默认只按 CPU 扩缩容。内存利用率按 `requests` 计算，Python 应用常驻内存较高，默认关闭内存指标；确需使用时设置 `autoscaling.targetMemoryUtilizationPercentage`。

## 升级、回滚和卸载

```bash
helm history task-api -n task-api
helm rollback task-api 1 -n task-api
helm uninstall task-api -n task-api
```

Chart 不创建 PVC，卸载不会删除任何持久化数据。

## 已知限制

- 应用启动时会执行数据库建表和 Redis 初始化，依赖不可用时 Pod 无法启动；请先确保 MySQL/Redis 可用。
- 应用 `/health` 在 MySQL 异常时仍返回 HTTP 200；Chart 的就绪探针通过解析响应体中的 `status` 判断，已规避该问题。
- `/health` 的总体状态只考虑 MySQL。Redis 仅作为缓存，断开时应用会回退到 MySQL，因此不标记为 unhealthy。
- 镜像默认 `CMD ["python", "run.py"]` 使用 `reload=True`。Chart 通过 `command: [uvicorn]` 和 `args` 覆盖；长期应在 `run.py` 中关闭 reload。
- 当前 TCR 镜像只有 linux/amd64 架构，arm64 节点需要重新构建多架构镜像。
- 部署前应确认 `image.tag` 与目标代码版本一致；短 SHA tag 必须能在 TCR 中找到。

## 排障

- `ImagePullBackOff`：确认 `image.tag` 在 TCR 中存在；私有仓库需要 `imagePullSecrets`；K3s 节点还要检查 `/etc/rancher/k3s/registries.yaml` 是否配置了不可用的镜像加速。
- `CreateContainerConfigError`：Secret 不存在或缺少必需键。
- `CrashLoopBackOff`：应用启动时会连接 MySQL/Redis，先确认依赖可用，再查看 `kubectl logs`。
- 访问 404：确认 Ingress/HTTPRoute 的 host 和 path 与应用路由匹配；应用路由为 `/health`、`/tasks`、`/docs`。

## 渲染验证

`helm lint` 使用内置的能力集，无法识别集群中的 CRD；启用 HTTPRoute 或 ServiceMonitor 的配置请用 `helm template --api-versions` 验证。

```bash
helm lint ./charts/task-api
helm template task-api ./charts/task-api -n task-api
helm template task-api ./charts/task-api -n task-api --set ingress.enabled=true
helm template task-api ./charts/task-api -n task-api \
  --set httpRoute.enabled=true --api-versions gateway.networking.k8s.io/v1
helm template task-api ./charts/task-api -n task-api \
  --set serviceMonitor.enabled=true --api-versions monitoring.coreos.com/v1
helm template task-api ./charts/task-api -n task-api --set autoscaling.enabled=true
```
