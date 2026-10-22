#!/usr/bin/env bash

set -u

echo "=================================="
echo "      Linux Health Report"
echo "=================================="

echo ""
echo "[1] 基本信息"
hostname
date
uptime

echo ""
echo "[2] 内存使用情况"
free -h

echo ""
echo "[3] 根文件系统磁盘空间"
df -h /

echo ""
echo "[4] 根文件系统 Inode"
df -i /

echo ""
echo "[5] CPU 使用率最高的进程"
ps -eo pid,ppid,stat,comm,%cpu,%mem --sort=-%cpu | head -n 6

echo ""
echo "[6] TCP 监听端口"
ss -lnt

echo ""
echo "[7] Nginx 服务状态"
systemctl is-active nginx || true

echo ""
echo "[8] Redis 服务状态"
systemctl is-active redis || true

echo ""
echo "=================================="
echo "         Report End"
echo "=================================="
