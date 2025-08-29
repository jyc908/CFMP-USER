#!/bin/bash
# start-k8s.sh

echo "启动 CFMP Kubernetes 应用..."




# 构建镜像
echo "构建投诉服务镜像..."
docker build -t user-service .

export KUBECTL="k3s kubectl"

docker save user-service:latest > user-service.tar

echo "将镜像导入 K3s..."
k3s ctr images import user-service.tar


docker save mysql:8.0 > mysql.tar
echo "将镜像导入 K3s..."
k3s ctr images import mysql.tar

# 部署应用
echo "部署应用..."
$KUBECTL delete -f k8s/ --ignore-not-found=true 2>/dev/null || true
sleep 3
$KUBECTL apply -f k8s/

# 等待启动
echo "等待应用启动..."
$KUBECTL wait --for=condition=ready pod -l app=user-service --timeout=300s 2>/dev/null || true
$KUBECTL wait --for=condition=ready pod -l app=user-db --timeout=300s 2>/dev/null || true

# 运行数据库迁移
echo "运行数据库迁移..."
$KUBECTL exec deployment/user-service -- python manager.py migrate

# 显示访问地址
echo ""
echo "部署完成！访问地址："
echo "服务端口: 30080 (NodePort)"
echo ""
$KUBECTL get pods
$KUBECTL get services
