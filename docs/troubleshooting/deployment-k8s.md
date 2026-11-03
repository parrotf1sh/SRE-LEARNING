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

