#!/bin/bash
# Task-API Helm Chart 验证脚本

set -e

echo "======================================================================"
echo "  Task-API Helm Chart 验证脚本"
echo "======================================================================"
echo ""

# 检查 Helm 是否安装
if ! command -v helm &> /dev/null; then
    echo "❌ 错误: 未找到 helm 命令"
    echo ""
    echo "安装方法:"
    echo "  macOS:    brew install helm"
    echo "  Linux:    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    echo "  Windows:  choco install kubernetes-helm"
    exit 1
fi

echo "✅ Helm 版本: $(helm version --short)"
echo ""

# 检查 Chart 结构
echo "📋 检查 Chart 结构..."
if [ ! -f "charts/task-api/Chart.yaml" ]; then
    echo "❌ 错误: 未找到 charts/task-api/Chart.yaml"
    exit 1
fi

if [ ! -f "charts/task-api/values.yaml" ]; then
    echo "❌ 错误: 未找到 charts/task-api/values.yaml"
    exit 1
fi

echo "✅ Chart 结构正确"
echo ""

# Lint 检查
echo "🔍 运行 Lint 检查..."
if helm lint charts/task-api/; then
    echo "✅ Lint 检查通过"
else
    echo "❌ Lint 检查失败"
    exit 1
fi
echo ""

# 模板渲染测试
echo "📝 测试模板渲染..."
if helm template test-release charts/task-api/ > /dev/null; then
    echo "✅ 模板渲染成功"
else
    echo "❌ 模板渲染失败"
    exit 1
fi
echo ""

# 显示渲染的资源数量
echo "📊 统计渲染的资源..."
RESOURCE_COUNT=$(helm template test-release charts/task-api/ | grep -c "^kind:" || true)
echo "✅ 将创建 $RESOURCE_COUNT 个 Kubernetes 资源"
echo ""

# 列出资源类型
echo "📋 资源类型列表:"
helm template test-release charts/task-api/ | grep "^kind:" | sort | uniq -c
echo ""

# 测试不同配置
echo "🧪 测试自定义配置..."
if helm template test-release charts/task-api/ \
    --set replicaCount=3 \
    --set autoscaling.enabled=true \
    --set serviceMonitor.enabled=false > /dev/null; then
    echo "✅ 自定义配置测试通过"
else
    echo "❌ 自定义配置测试失败"
    exit 1
fi
echo ""

echo "======================================================================"
echo "  ✅ 所有验证通过！"
echo "======================================================================"
echo ""
echo "下一步操作:"
echo ""
echo "1. 创建必需的 Secret:"
echo "   kubectl create secret generic task-api-db-secret \\"
echo "     --from-literal=DB_HOST=mysql.default.svc.cluster.local \\"
echo "     --from-literal=DB_PORT=3306 \\"
echo "     --from-literal=DB_USER=root \\"
echo "     --from-literal=DB_PASSWORD=yourpassword \\"
echo "     --from-literal=DB_NAME=task_api"
echo ""
echo "2. 安装 Chart:"
echo "   helm install task-api ./charts/task-api"
echo ""
echo "3. 查看部署状态:"
echo "   kubectl get all -l app.kubernetes.io/name=task-api"
echo ""
echo "4. 查看渲染的模板:"
echo "   helm template task-api ./charts/task-api"
echo ""
