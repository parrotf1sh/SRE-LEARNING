# GitOps 持续交付学习指南

## 📚 目录结构

```
sre-lreaning/
├── task-api/                      # 应用代码
├── charts/                        # Helm Charts
│   └── task-api/                 # Task-API Chart
│       ├── Chart.yaml            # Chart 元数据
│       ├── values.yaml           # 默认配置
│       ├── .helmignore           # 打包忽略文件
│       ├── README.md             # Chart 文档
│       └── templates/            # Kubernetes 资源模板
│           ├── _helpers.tpl      # 辅助模板
│           ├── NOTES.txt         # 安装后提示
│           ├── deployment.yaml   # Deployment
│           ├── service.yaml      # Service
│           ├── configmap.yaml    # ConfigMap
│           ├── secret.yaml       # Secret 引用说明
│           ├── httproute.yaml    # HTTPRoute (Gateway API)
│           ├── servicemonitor.yaml # ServiceMonitor (Prometheus)
│           └── hpa.yaml          # HPA (自动扩缩容)
├── scripts/
│   └── validate-chart.sh         # Chart 验证脚本
└── docs/
    └── gitops-guide.md           # 本文档
```

## 🎯 学习目标

完成本指南后，你将掌握：

1. ✅ Helm Chart 的结构和编写方法
2. ✅ Kubernetes 资源的模板化配置
3. ✅ Argo CD 的安装和配置（国内源）
4. ✅ GitOps 工作流的完整实现
5. ✅ GitHub Actions + GHCR + Argo CD 的集成

---

## 阶段一：Helm Chart 详解

### 1.1 Chart 包含的资源

| 资源 | 文件 | 作用 | 关键配置 |
|------|------|------|----------|
| **Deployment** | `deployment.yaml` | 定义 Pod、副本和升级策略 | `replicaCount`, `image`, `strategy` |
| **Service** | `service.yaml` | 提供稳定的内部访问入口 | `service.type`, `service.port` |
| **ConfigMap** | `configmap.yaml` | 保存不敏感的业务配置 | `config.*` |
| **Secret 引用** | `secret.yaml` | 注入数据库、Redis 等连接凭据 | `secrets.*` |
| **ServiceMonitor** | `servicemonitor.yaml` | 让 Prometheus 自动发现指标 | `serviceMonitor.*` |
| **HTTPRoute** | `httproute.yaml` | Gateway API 路由规则 | `httpRoute.*` |
| **HPA** | `hpa.yaml` | 根据负载自动扩缩容 | `autoscaling.*` |

### 1.2 验证 Chart

```bash
# 运行验证脚本
./scripts/validate-chart.sh

# 或手动验证
helm lint charts/task-api/
helm template task-api charts/task-api/
```

### 1.3 安装 Chart

```bash
# 1. 创建命名空间
kubectl create namespace task-api

# 2. 创建必需的 Secret
kubectl create secret generic task-api-db-secret \
  --from-literal=DB_HOST=mysql.default.svc.cluster.local \
  --from-literal=DB_PORT=3306 \
  --from-literal=DB_USER=root \
  --from-literal=DB_PASSWORD=yourpassword \
  --from-literal=DB_NAME=task_api \
  -n task-api

kubectl create secret generic task-api-redis-secret \
  --from-literal=REDIS_NODES="redis-node-0:6379,redis-node-1:6380" \
  -n task-api

# 3. 安装 Chart
helm install task-api ./charts/task-api \
  --namespace task-api \
  --set image.tag=dev-latest

# 4. 查看部署状态
kubectl get all -n task-api
```

---

## 阶段二：安装 Argo CD（国内源）

### 2.1 安装前准备

```bash
# 确保 kubectl 可以访问集群
kubectl cluster-info

# 检查集群版本（需要 1.19+）
kubectl version --short
```

### 2.2 安装 Argo CD

```bash
# 1. 创建命名空间
kubectl create namespace argocd

# 2. 安装 Argo CD（使用国内镜像）
# 方法 A：通过镜像代理（推荐）
kubectl apply -n argocd -f \
  https://mirror.ghproxy.com/https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 方法 B：手动替换镜像地址
# 下载官方安装文件
wget https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml -O argocd-install.yaml

# 替换镜像地址（使用阿里云镜像）
sed -i '' 's|quay.io/argoproj/|registry.cn-hangzhou.aliyuncs.com/argoproj/|g' argocd-install.yaml

# 应用修改后的配置
kubectl apply -n argocd -f argocd-install.yaml

# 3. 等待所有组件就绪
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/part-of=argocd \
  -n argocd \
  --timeout=300s

# 4. 查看 Pod 状态
kubectl get pods -n argocd
```

### 2.3 暴露 Argo CD UI

```bash
# 方法 1：NodePort（推荐用于学习）
kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "NodePort"}}'

# 获取 NodePort
NODE_PORT=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.ports[0].nodePort}')
echo "Argo CD UI: https://<你的服务器IP>:${NODE_PORT}"

# 方法 2：LoadBalancer（云环境）
kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "LoadBalancer"}}'

# 方法 3：端口转发（本地测试）
kubectl port-forward svc/argocd-server -n argocd 8443:443
echo "Argo CD UI: https://localhost:8443"
```

### 2.4 获取初始密码

```bash
# 获取 admin 账号初始密码
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# 或使用 Argo CD CLI
argocd admin initial-password -n argocd
```

### 2.5 安装 Argo CD CLI

```bash
# macOS
brew install argocd

# Linux (amd64)
curl -sSL -o argocd \
  https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd
sudo mv argocd /usr/local/bin/

# 验证安装
argocd version --client
```

---

## 阶段三：配置 Argo CD

### 3.1 登录 Argo CD CLI

```bash
# 获取 argocd-server 地址
ARGOCD_SERVER=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):443
# 或使用 NodePort
ARGOCD_SERVER=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}'):$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.ports[0].nodePort}')

# 登录
argocd login $ARGOCD_SERVER \
  --username admin \
  --insecure
```

### 3.2 添加 GitHub 仓库

```bash
# 方法 1：使用 Personal Access Token（推荐）
# 1. 在 GitHub 创建 PAT：Settings → Developer settings → Personal access tokens → Fine-grained tokens
# 2. 权限：Contents: Read-only

# 添加仓库
argocd repo add https://github.com/<你的用户名>/sre-lreaning.git \
  --username <你的GitHub用户名> \
  --password <PAT>

# 验证连接
argocd repo list
```

### 3.3 添加 GHCR 镜像仓库

```bash
# 创建 GHCR 凭据
# 1. 创建 PAT，权限：read:packages

# 添加 GHCR 仓库
argocd repo add ghcr.io/<你的用户名> \
  --type helm \
  --name ghcr \
  --username <你的GitHub用户名> \
  --password <PAT>
```

### 3.4 创建 Argo CD Application

```yaml
# argocd-task-api.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: task-api
  namespace: argocd
spec:
  project: default
  
  source:
    repoURL: https://github.com/<你的用户名>/sre-lreaning.git
    targetRevision: dev
    path: charts/task-api
    helm:
      valueFiles:
        - values.yaml
      parameters:
        - name: image.repository
          value: ghcr.io/<你的用户名>/task-api
        - name: image.tag
          value: dev-latest
        - name: httpRoute.hostnames[0]
          value: task-api.example.com
  
  destination:
    server: https://kubernetes.default.svc
    namespace: task-api
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

```bash
# 创建 Application
argocd app create task-api \
  --repo https://github.com/<你的用户名>/sre-lreaning.git \
  --revision dev \
  --path charts/task-api \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace task-api \
  --auto-prune \
  --self-heal

# 同步应用
argocd app sync task-api

# 查看应用状态
argocd app get task-api
```

---

## 阶段四：GitOps 工作流

### 4.1 完整流程

```
开发者推送代码到 dev 分支
    ↓
GitHub Actions 触发
    ↓
Job 1: 运行测试
    ↓
Job 2: 构建镜像 → 推送到 GHCR
    ↓
Argo CD 检测到 Git 变化（每 3 分钟轮询）
    ↓
Argo CD 拉取最新的 Helm Chart
    ↓
Argo CD 渲染 Kubernetes manifests
    ↓
Argo CD 同步到集群（滚动更新）
    ↓
部署完成
```

### 4.2 测试 GitOps 流程

```bash
# 1. 修改代码
echo "# Update for GitOps test" >> task-api/README.md

# 2. 提交并推送
git add .
git commit -m "test: trigger GitOps deployment"
git push origin dev

# 3. 观察 GitHub Actions
# 访问 https://github.com/<你的用户名>/sre-lreaning/actions

# 4. 观察 Argo CD 同步
argocd app get task-api
# 或访问 Argo CD UI

# 5. 验证部署
kubectl get pods -n task-api -w
```

### 4.3 回滚操作

```bash
# 方法 1：通过 Argo CD CLI
argocd app history task-api
argocd app rollback task-api <revision>

# 方法 2：通过 Git
git revert <commit-hash>
git push origin dev
# Argo CD 会自动检测到变化并回滚
```

---

## 常见问题

### Q1: Argo CD 无法拉取私有仓库？

```bash
# 检查仓库连接
argocd repo list

# 重新添加仓库
argocd repo add <repo-url> --username <user> --password <token>

# 测试连接
argocd repo get <repo-url>
```

### Q2: Helm Chart 渲染失败？

```bash
# 验证模板
helm template task-api ./charts/task-api --debug

# 检查 values.yaml
helm lint ./charts/task-api --strict
```

### Q3: Secret 未正确注入？

```bash
# 检查 Secret 是否存在
kubectl get secret -n task-api

# 检查 Deployment 环境变量
kubectl exec -it <pod-name> -n task-api -- env | grep DB_
```

### Q4: ServiceMonitor 未被 Prometheus 发现？

```bash
# 检查 Prometheus Operator 是否安装
kubectl get pods -n monitoring

# 检查 ServiceMonitor
kubectl get servicemonitor -n task-api

# 检查 Prometheus 配置
kubectl port-forward svc/prometheus-operator -n monitoring 9090:9090
# 访问 http://localhost:9090/targets
```

---

## 学习资源

- [Helm 官方文档](https://helm.sh/docs/)
- [Argo CD 官方文档](https://argo-cd.readthedocs.io/)
- [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/)
- [GitOps 最佳实践](https://opengitops.dev/)

---

## 下一步

1. 配置 HTTPS（使用 cert-manager）
2. 集成 External Secrets Operator
3. 配置多环境部署（dev/staging/prod）
4. 实现蓝绿部署或金丝雀发布
5. 配置告警规则（Prometheus AlertManager）
