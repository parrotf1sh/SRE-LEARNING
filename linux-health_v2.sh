#!/usr/bin/env bash

set -uo pipefail

export LC_ALL=C

# ==================================================
# 1. 配置区域
# ==================================================

# CPU 使用率阈值
CPU_WARN=${CPU_WARN:-80}
CPU_CRIT=${CPU_CRIT:-90}

# 内存使用率阈值
MEM_WARN=${MEM_WARN:-80}
MEM_CRIT=${MEM_CRIT:-90}

# 磁盘使用率阈值
DISK_WARN=${DISK_WARN:-80}
DISK_CRIT=${DISK_CRIT:-90}

# inode 使用率阈值
INODE_WARN=${INODE_WARN:-80}
INODE_CRIT=${INODE_CRIT:-90}

# 需要检查的服务
SERVICE_NAME="nginx"

# HTTP 健康检查地址
HEALTH_URL=${HEALTH_URL:-http://127.0.0.1/}

# 告警计数器
WARN_COUNT=0
CRIT_COUNT=0

# ==================================================
# 2. 通用函数
# ==================================================

# 打印分隔线
separator() {
    echo "------------------------------------------"
}

# 打印检查标题
section() {
    echo
    separator
    echo "$1"
    separator
}

# 普通信息
info() {
    echo "[INFO] $1"
}

# 正常状态
ok() {
    echo "[OK] $1"
}

# 警告状态
warning() {
    echo "[WARNING] $1"

    WARN_COUNT=$((WARN_COUNT + 1))
}

# 严重告警
critical() {
    echo "[CRITICAL] $1"

    CRIT_COUNT=$((CRIT_COUNT + 1))
}

# ==================================================
# 3. 通用阈值判断函数
# ==================================================

check_threshold() {

    local name="$1"
    local value="$2"
    local warn="$3"
    local crit="$4"

    # 检查指标是否为非负整数
    if [[ ! "$value" =~ ^[0-9]+$ ]]; then
        critical "$name 无法获取有效指标"
        return
    fi

    if (( value >= crit )); then

        critical "$name: ${value}% (严重阈值: ${crit}%)"

    elif (( value >= warn )); then

        warning "$name: ${value}% (警告阈值: ${warn}%)"

    else

        ok "$name: ${value}%"

    fi
}

# ==================================================
# 4. 读取 CPU 累积时间
# ==================================================

cpu_sample() {

    local tag user nice system idle iowait
    local irq softirq steal rest

    read -r tag user nice system idle iowait \
        irq softirq steal rest < /proc/stat

    local total=$((user + nice + system + idle + \
                   iowait + irq + softirq + steal))

    local idle_all=$((idle + iowait))

    echo "$total $idle_all"
}

# ==================================================
# 5. 检查运行权限和阈值配置
# ==================================================

if (( EUID != 0 )); then
    echo "请使用 sudo 运行此脚本"
    exit 3
fi

# 防止设置无效的阈值
for metric in CPU MEM DISK INODE; do

    warn_name="${metric}_WARN"
    crit_name="${metric}_CRIT"

    warn_value="${!warn_name}"
    crit_value="${!crit_name}"

    if [[ ! "$warn_value" =~ ^[0-9]+$ ]] ||
       [[ ! "$crit_value" =~ ^[0-9]+$ ]]; then

        echo "错误：${metric} 阈值必须是整数"
        exit 3
    fi

    if (( warn_value >= crit_value || crit_value > 100 )); then

        echo "错误：${metric} 阈值设置不合理"
        exit 3
    fi

done

# ==================================================
# 6. 系统基本信息
# ==================================================

echo "=========================================="
echo "       Linux Health Check V2.0"
echo "=========================================="

echo "巡检时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "主机名称: $(hostname)"
echo "内核版本: $(uname -r)"

section "1. 系统运行时间与负载"

uptime

echo
info "逻辑 CPU 数量: $(nproc)"

info "Load Average: $(awk '{print $1, $2, $3}' /proc/loadavg)"

# ==================================================
# 7. CPU 使用率
# ==================================================

section "2. CPU 使用率检查"

# 第一次采样
read -r total1 idle1 < <(cpu_sample)

# 等待一秒
sleep 1

# 第二次采样
read -r total2 idle2 < <(cpu_sample)

total_delta=$((total2 - total1))
idle_delta=$((idle2 - idle1))

if (( total_delta > 0 )); then

    cpu_usage=$((100 * (total_delta - idle_delta) / total_delta))

    check_threshold "CPU 使用率" \
        "$cpu_usage" "$CPU_WARN" "$CPU_CRIT"

else

    critical "CPU 使用率采样失败"

fi


# ==================================================
# 8. 内存与 Swap 检查
# ==================================================

section "3. 内存使用情况"

free -h

# 读取 /proc/meminfo
read -r mem_total mem_available swap_total swap_free < <(
    awk '
    /^MemTotal:/ {
        mt=$2
    }
    /^MemAvailable:/ {
        ma=$2
    }
    /^SwapTotal:/ {
        st=$2
    }
    /^SwapFree:/ {
        sf=$2
    }
    END {
        print mt, ma, st, sf
    }
    ' /proc/meminfo
)

if (( mem_total > 0 )); then

    # 使用 MemAvailable 计算内存使用率
    mem_usage=$((100 * (mem_total - mem_available) / mem_total))

    check_threshold "内存使用率" \
        "$mem_usage" "$MEM_WARN" "$MEM_CRIT"

else

    critical "无法获取系统内存信息"

fi

# Swap 使用情况
if (( swap_total > 0 )); then

    swap_used=$((swap_total - swap_free))
    swap_usage=$((100 * swap_used / swap_total))

    info "Swap 使用率: ${swap_usage}%"

else

    info "系统未启用 Swap"

fi


# ==================================================
# 9. 磁盘空间检查
# ==================================================

section "4. 根文件系统磁盘空间"

df -h /

disk_usage=$(
    df -P / | awk '
        NR == 2 {
            gsub("%", "", $5)
            print $5
        }
    '
)

check_threshold "根文件系统使用率" \
    "$disk_usage" "$DISK_WARN" "$DISK_CRIT"


# ==================================================
# 10. inode 检查
# ==================================================

section "5. inode 使用情况"

df -i /

inode_usage=$(
    df -Pi / | awk '
        NR == 2 {
            gsub("%", "", $5)
            print $5
        }
    '
)

check_threshold "inode 使用率" \
    "$inode_usage" "$INODE_WARN" "$INODE_CRIT"


# ==================================================
# 11. 文件句柄检查
# ==================================================

section "6. 文件句柄信息"

if [[ -r /proc/sys/fs/file-nr ]]; then

    read -r allocated unused maximum < /proc/sys/fs/file-nr

    info "系统已分配文件句柄: $allocated"
    info "系统文件句柄上限: $maximum"

else

    warning "无法读取系统文件句柄信息"

fi


# ==================================================
# 12. CPU 与内存占用最高的进程
# ==================================================

section "7. CPU 占用最高的 5 个进程"

ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 6

section "8. 内存占用最高的 5 个进程"

ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 6


# ==================================================
# 13. TCP 监听端口
# ==================================================

section "9. TCP 监听端口"

ss -lntp


# ==================================================
# 14. Nginx 服务检查
# ==================================================

section "10. Nginx 服务状态"

if systemctl is-active --quiet "$SERVICE_NAME"; then

    ok "$SERVICE_NAME 服务运行正常"

else

    service_state=$(
        systemctl is-active "$SERVICE_NAME" 2>/dev/null || true
    )

    critical "$SERVICE_NAME 服务异常，状态: $service_state"

fi


# ==================================================
# 15. Nginx 配置检查
# ==================================================

section "11. Nginx 配置检查"

if command -v nginx >/dev/null 2>&1; then

    if nginx_output=$(nginx -t 2>&1); then

        ok "Nginx 配置文件检查通过"

    else

        critical "Nginx 配置文件检查失败"

        echo "$nginx_output"

    fi

else

    critical "未找到 Nginx 程序"

fi


# ==================================================
# 16. HTTP 健康检查
# ==================================================

section "12. HTTP 健康检查"

if command -v curl >/dev/null 2>&1; then

    if http_code=$(
        curl --noproxy '*' \
            -s \
            -o /dev/null \
            -w '%{http_code}' \
            --connect-timeout 2 \
            --max-time 5 \
            "$HEALTH_URL"
    ); then

        if [[ "$http_code" =~ ^[0-9]{3}$ ]] &&
           (( 10#$http_code >= 200 && 10#$http_code < 400 )); then

            ok "HTTP 检查成功，状态码: $http_code"

        else

            critical "HTTP 响应异常，状态码: $http_code"

        fi

    else

        critical "HTTP 请求失败: $HEALTH_URL"

    fi

else

    warning "未安装 curl，跳过 HTTP 检查"

fi


# ==================================================
# 17. 巡检结果汇总
# ==================================================

section "13. 巡检结果汇总"

echo "WARNING 数量: $WARN_COUNT"
echo "CRITICAL 数量: $CRIT_COUNT"

echo

if (( CRIT_COUNT > 0 )); then

    echo "[CRITICAL] 巡检发现严重异常"
    exit 2

elif (( WARN_COUNT > 0 )); then

    echo "[WARNING] 巡检发现需要关注的指标"
    exit 1

else

    echo "[OK] 所有启用的告警检查均正常"
    exit 0

fi
