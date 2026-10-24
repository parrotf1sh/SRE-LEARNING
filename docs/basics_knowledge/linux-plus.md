

线上某个 Web 服务突然无法访问，可能的原因包括：

- 服务进程已经退出。
- 服务正在运行，但没有监听正确的端口。
- 端口被其他进程占用了。
- 服务器内存不足，进程被系统杀死。
- 磁盘空间用完，服务无法写入日志。
- 配置文件存在语法错误，导致服务启动失败。

```
              用户报告服务异常
                       │
                       ▼
              1. 确认故障现象
                       │
                       ▼
              2. 查看服务状态
                 systemctl status
                       │
                       ▼
              3. 查看日志证据
                   journalctl
                       │
                       ▼
              4. 检查相关资源
             ps / top / free / df / ss
                       │
                       ▼
              5. 提出故障假设
                       │
                       ▼
              6. 验证假设并修复
                       │
                       ▼
              7. 验证服务恢复
                       │
                       ▼
              8. 记录根因与预防措施
```

| 排查维度 | 内存不足                         | 磁盘空间不足                    |
| -------- | -------------------------------- | ------------------------------- |
| 常用命令 | `free -h`                        | `df -h`                         |
| 深入检查 | `ps`、`top`、OOM 日志            | `du`、`df -i`                   |
| 常见现象 | 进程被杀、服务卡顿、内存分配失败 | 文件写入失败、日志无法写入      |
| 典型报错 | `Out of memory`                  | `No space left on device`       |
| 核心原因 | 可用内存不足或内存限制被触发     | 文件系统空间或 inode 等资源不足 |



发现异常进程
      ↓
确定 PID 与进程用途
      ↓
尝试正常退出（SIGTERM）
      ↓
检查进程是否退出
      ↓
必要时再考虑 SIGKILL



```
top
=======>
%Cpu(s): 25.0 us, 5.0 sy, 68.0 id, 2.0 wa

uptime
=======>
11:35:42 up 3 days,  load average: 0.50, 0.80, 1.20
```

```
free -h
=====>
               total   used   free  shared  buff/cache  available
Mem:           1.9Gi   650Mi  180Mi  25Mi    1.1Gi       1.1Gi
Swap:          1.0Gi      0B  1.0Gi
# 重点参考 available  结合 Swap 活动、内存压力、OOM 日志及业务表现进行判断

swapon --show  # 如果没有输出，通常表示当前没有启用 Swap

sudo journalctl -k -b | grep -Ei 'oom|out of memory|killed process'
========>Out of memory: Killed process 1234 (java)
```

```
df -h
=====>
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        40G   12G   26G  32% /

# du 某个目录或文件占用了多少空间
sudo du -sh /var/log
=====>2.3G    /var/log
# 查看其下一级目录的占用情况
sudo du -h -d 1 /var/log

# 查看 inode
df -i
=====>No space left on device
```

#### 文件描述符与nginx

假设一个 Nginx Worker 进程同时处理大量网络连接。这些连接会消耗文件描述符。如果进程达到了文件描述符数量限制，新连接可能无法正常建立。   ==========>Too many open files

```
# 查看文件描述符限制
ulimit -n
=======>1024		表示当前 Shell 进程的打开文件描述符软限制

# 查看指定进程的文件描述符
ls /proc/<PID>/fd

sudo ls /proc/1234/fd
sudo ls -1 /proc/1234/fd | wc -l
```

### 当服务器 CPU 使用率异常升高时，可以先用这两条命令识别可疑进程

```
# 找出 CPU 使用率最高的进程
ps aux --sort=-%cpu | head -10
aux：显示进程及资源使用情况,--sort=-%cpu：按照 CPU 使用率从高到低排序
# 查看内存使用率最高的进程
ps aux --sort=-%mem | head -10
```

```
top
快捷键	作用
P	按 CPU 使用率排序
M	按内存使用率排序
1	切换每个逻辑 CPU 的使用情况
H	切换线程显示
q	退出
```

### 排查内存问题

```
free -h  /	free -h -s 2 # 持续观察
ps aux --sort=-%mem | head -10
sudo journalctl -k -b | grep -Ei 'oom|out of memory|killed process'
系统内存是否紧张、哪些进程内存占用较高，以及内核是否记录了 OOM 事件
```

### 排查磁盘问题

```
df -h
df -i
sudo du -sh /var/log

# 查找占用空间较大的目录
sudo du -xhd1 /var 2>/dev/null | sort -h
-x：只统计同一文件系统中的内容。
-h：使用易读的容量单位。
-d1：只显示一层目录深度。
sort -h：按照容量大小排序。
==========>排查：/var 下究竟哪个目录占用了大量磁盘空间？

有时 df 显示磁盘空间已经用完，但 du 统计的文件总量明显偏小
<==========某个大文件已经被删除，但仍然被运行中的进程打开
# 检查被删除但仍处于打开状态的文件
sudo lsof +L1
```

### 查看网络连接和端口

```
sudo ss -lntp
-l	只显示监听中的 Socket
-n	显示数字形式的 IP 和端口
-t	查看 TCP
-p	显示相关进程信息
==========>
State   Recv-Q Send-Q Local Address:Port    Process

LISTEN  0      511    0.0.0.0:80           users:(("nginx",pid=2001,fd=6))

LISTEN  0      128    0.0.0.0:22           users:(("sshd",pid=820,fd=3))

# 指定端口占用者
sudo ss -lntp '( sport = :8080 )'
======>LISTEN 0 128 0.0.0.0:8080 users:(("python3",pid=3562,fd=3))
# 接下来进一步查看进程
ps -fp 3562
```

### systemd 与 systemctl

```
# 查看Unit配置
systemctl cat nginx
======>
[Unit]
Description=A high performance web server
After=network.target

[Service]
Type=forking
ExecStart=/usr/sbin/nginx
ExecReload=/usr/sbin/nginx -s reload
ExecStop=/sbin/start-stop-daemon --stop ...

[Install]
WantedBy=multi-user.target
```

`[Unit]`：描述服务及其依赖关系等信息。

`[Service]`：定义如何启动、停止、重载服务，以及服务进程如何运行。

`[Install]`：定义服务如何参与开机启动等安装关系。

```
# 修改 systemd Unit 配置后，需要执行
sudo systemctl daemon-reload
```

#### redis纳入管理

```
sudo vim /etc/systemd/system/redis.service

[Unit]
Description=Redis Server
After=network.target

[Service]
Type=forking
ExecStart=/home/ubuntu/redis/redis01/bin/redis-server /home/ubuntu/redis/redis01/redis.conf
ExecStop=/home/ubuntu/redis/redis01/bin/redis-cli shutdown
Restart=always
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl start redis
sudo systemctl enable redis
```

### journalctl 日志检索

```
sudo journalctl -u nginx
-u 用于指定 Unit

# 查看最近 50 条日志
sudo journalctl -u nginx -n 50 --no-pager
--no-pager 表示直接输出日志，不进入分页查看界面

# 查看本次系统启动后的日志
sudo journalctl -u nginx -b
# 查看最近 30 分钟的日志
sudo journalctl -u nginx --since "30 minutes ago"

# 看错误级别日志
sudo journalctl -p err -b
```

# 服务启动失败怎么排查

```
sudo systemctl start nginx
======>Job for nginx.service failed

1.查看服务状态
sudo systemctl status nginx --no-pager -l

2.查看日志
sudo journalctl -u nginx -b -n 100 --no-pager
# 通过日志判断是配置错误、端口冲突，还是其他问题

3.检查 Nginx 配置
sudo nginx -t

4.检查端口
sudo ss -lntp '( sport = :80 )'

5.检查资源
free -h
df -h
df -i
# 必要时继续检查内核日志

6.修复并验证
curl -I http://127.0.0.1
```



# sed

一个可以在命令行中批量查找、修改、删除和输出文本的工具

```
sed [选项] '操作规则' 文件

sed 's/旧内容/新内容/' 文件
s：substitute，替换。默认情况下，只替换每一行中第一次匹配到的内容
/：分隔符。
旧内容：需要匹配的文本。
新内容：替换后的文本。

# 替换第一次出现的内容
echo "error error error" | sed 's/error/warning/'
====>warning error error

# g 作用于每一行，而不是把整个文件当作一行
echo "error error error" | sed 's/error/warning/g'
warning warning warning

# 查看第 3 行
sed -n '3p' test.log
-n：禁止默认输出所有行。
3p：打印第 3 行。
# 查看第 2～4 行
sed -n '2,4p' test.log

# 过滤包含某个关键词的行
sed -n '/ERROR/p' test.log

# 删除匹配的行
sed '/INFO/d' test.log
# 这里并没有真正删除源文件中的数据，只是把符合条件的行从输出中排除。
# 默认情况下，sed 不会直接修改原始文件。


# 真正修改文件
sed -i 's/旧内容/新内容/' 文件
-i 表示就地修改文件
# 会生成 .bak 备份文件 
sed -i.bak 's/旧内容/新内容/' 文件
```

# awk

`awk` 更擅长**提取字段、过滤数据、统计和计算**

```
USER    CPU    MEM
nginx   10     100
mysql   30     500
redis   15     200
哪个进程 CPU 占用最高？
哪些进程内存占用超过 200？
所有进程的 CPU 数值之和是多少？

awk '条件 {执行操作}' 文件

echo "nginx 20 100" | awk '{print $1}'
====>nginx
$0 → 整行    nginx      20      100
              │         │       │
              ▼         ▼       ▼
             $1        $2      $3
NF	当前行的字段数量
NR	当前处理的记录编号，默认以行为单位
FS	输入字段分隔符
OFS	输出字段分隔符

Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        40G   12G   26G  32% /

df -h / | awk 'NR==2 {print $5}'
====>32%
 
# gsub：批量替换
# 假设想得到数字 32，而不是 32%
df -P / | awk 'NR==2 {gsub(/%/, "", $5); print $5}'
df -P，是为了获得更适合脚本解析的 POSIX 风格输出

# 条件过滤
cat > process.txt <<'EOF'
进程名称 CPU数值 内存数值
nginx 10 100
mysql 30 500
redis 15 200
java 90 800
EOF
# 找出 CPU 数值超过 20 的进程
awk '$2 > 20 {print $1, $2}' process.txt
====>mysql 30
		java 90

# 算第二列数值总和
awk '{sum += $2} END {print sum}' process.txt
# END 表示所有记录处理结束后，再执行里面的代码

# 自定义分隔符
root:x:0:0:root:/root:/bin/bash
# -F ':' 表示指定冒号为分隔符
awk -F ':' '{print $1, $7}' /etc/passwd
====>root /bin/bash

192.168.1.10 - - [19/Oct/2026:10:00:00 +0800] "GET / HTTP/1.1" 200 612 "-" "curl/8.0"
192.168.1.11 - - [19/Oct/2026:10:00:01 +0800] "GET /abc HTTP/1.1" 404 153 "-" "curl/8.0"
192.168.1.12 - - [19/Oct/2026:10:00:02 +0800] "GET / HTTP/1.1" 200 612 "-" "curl/8.0"
192.168.1.13 - - [19/Oct/2026:10:00:03 +0800] "GET /test HTTP/1.1" 500 200 "-" "curl/8.0"

sudo awk '{count[$9]++} END {for (code in count) print code, count[code]}' \
    /var/log/nginx/access.log | sort -n
====>
200 2
404 1
500 1

count[$9]++	表示以第九列作为分类依据，对出现次数进行累加

作用：比如服务突然出现大量 500 错误时，可以使用它初步统计问题规模
```

# vmstat 系统整体性能分析

```
vmstat 1 5
# 1 → 每隔 1 秒采样
# 5 → 共输出 5 次
====>
procs -----------memory---------- ---swap-- -----io---- -system-- -------cpu-------
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st gu
 2  0      0 1394384 156068 1878932    0    0     1    59  892    4  0  0 99  0  0  0
 0  0      0 1394436 156068 1878976    0    0     0     0  666  556  0  1 100  0  0  0
 0  0      0 1394436 156068 1878976    0    0     0     0  603  519  0  0 100  0  0  0
 0  0      0 1394436 156068 1878980    0    0     0    60 1063 1245  1  1 99  0  0  0
 0  0      0 1394436 156068 1878980    0    0     0     0 1160 1561  1  1 99  0  0  0
 
`r` 正在运行或等待 CPU 的可运行任务数
`b` 阻塞等待 I/O 完成等事件的任务数
不能单独凭借 r 或 b 判断根因
如果持续看到较大的 si、so，并且业务响应明显变慢，则应该调查是否存在内存压力
但如果切换次数异常增大，同时系统性能恶化，就值得进一步检查线程数量、锁竞争和任务调度情况
如果 %st 持续偏高，可能说明虚拟 CPU 没有及时获得宿主机的计算时间

# 跳过启动以来的第一份统计报告
vmstat -y 1 5
```

| 观察到的现象            | 初步排查方向             |
| ----------------------- | ------------------------ |
| `r` 持续较高、`id` 很低 | CPU 竞争                 |
| `si`、`so` 持续较高     | Swap 活动、内存压力      |
| `b`、`wa` 持续较高      | I/O 等待                 |
| `st` 持续较高           | 虚拟化调度相关问题       |
| `cs` 异常增大           | 上下文切换、线程调度问题 |

```
r  b   si  so  us sy id wa st
0  8    0   0   5  3 32 60  0

CPU 有较多时间处于 I/O 等待状态，而且阻塞任务较多。
下一步应该重点调查 I/O，而不是直接认为 CPU 算力不足
```

# iostat

```
iostat -x -y 1 3
# -x	显示扩展 I/O 统计
iostat -xz -y 1 3
# -z 表示省略采样期间没有活动的设备

await：平均 I/O 请求耗时
如果某个磁盘的 w_await 从平时的 2ms 上升到 100ms，同时数据库写入延迟明显增加，那么这就值得重点排查

aqu-sz：平均 I/O 队列长度
aqu-sz = 4.5 表示采样期间平均有约 4.5 个未完成的 I/O 请求 块设备层面的 I/O 并发积压情况

aqu-sz 持续升高 && await 持续升高  ==> 表示 I/O 请求的处理速度跟不上到达速度

进一步定位：
- 哪个进程正在产生大量磁盘 I/O？
- 是数据库写入还是日志写入？
- 是否存在云盘性能限制？
- 是否出现异常的批量任务？
iotop、pidstat -d 等工具定位具体进程
```

# 查看文件系统信息

```
lsblk -f
```

# tee同时输出和保存日志

```
sudo ./linux-health.sh | tee health.log
在终端显示巡检结果。
保存一份到 health.log

# -a 追加
sudo ./linux-health.sh | tee -a health.log
# 保存标准错误输出
sudo ./linux-health.sh 2>&1 | tee -a health.log
```

# curl

###  -I：只查看响应头

```
curl -I http://127.0.0.1/
====>
HTTP/1.1 200 OK
Server: nginx
Content-Type: text/html
Content-Length: 615
```

### -v：显示详细请求过程

```
curl -v http://127.0.0.1/
====>
* Trying 127.0.0.1:80...
* Connected to 127.0.0.1 (127.0.0.1) port 80
> GET / HTTP/1.1
> Host: 127.0.0.1
> User-Agent: curl/8.x
> Accept: */*
<
< HTTP/1.1 200 OK
< Server: nginx
< Content-Type: text/html
```

### 状态码

| 状态码  | 含义                  | 常见排查方向                   |
| ------- | --------------------- | ------------------------------ |
| 200     | OK                    | 请求正常处理                   |
| 201     | Created               | 资源创建成功                   |
| 204     | No Content            | 请求成功但无响应体             |
| 301     | Moved Permanently     | 永久重定向                     |
| 302     | Found                 | 临时重定向                     |
| 400     | Bad Request           | 请求参数或格式问题             |
| 401     | Unauthorized          | 需要认证或认证失败             |
| 403     | Forbidden             | 权限不足                       |
| 404     | Not Found             | 路径或资源不存在               |
| 429     | Too Many Requests     | 请求受到限流                   |
| **500** | Internal Server Error | 服务端内部错误                 |
| **502** | Bad Gateway           | 网关或反向代理获得无效上游响应 |
| **503** | Service Unavailable   | 服务暂时不可用                 |
| **504** | Gateway Timeout       | 网关等待上游响应超时           |

### -o：将响应体保存到文件

```
curl -o index.html http://127.0.0.1/

# 只想检查请求，不想保存响应体
curl -o /dev/null http://127.0.0.1/

*******
curl -s -o /dev/null http://127.0.0.1/
*******
发起 HTTP 请求。
不显示进度信息。
丢弃响应体。
```

### -s 和 -S：静默模式

```
curl -s http://127.0.0.1/
# 会隐藏进度信息和 curl 的错误提示。===>不利于发现故障

******
curl -sS http://127.0.0.1/
******
-S：在静默模式下仍显示错误信息。
```

### -w：自定义输出信息

```
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1/
====>200
# 输出 HTTP 状态码并换行
-w '%{http_code}\n'

# 用 Shell 获取 HTTP 状态码
http_code=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1/)
```

### -f 和 --fail-with-body：让 HTTP 错误触发失败

默认情况下，HTTP 404、500 等响应并不一定让 curl 命令返回非零退出码。

```
# 如果希望 HTTP 状态码达到 400 或以上时，让 curl 返回失败状态
curl -f http://127.0.0.1/not-exist
但 -f 通常不会输出 HTTP 错误响应体

# 同时保留错误响应体
curl --fail-with-body -sS http://127.0.0.1/not-exist
```

### curl 超时、重试与重定向

```
--connect-timeout：连接超时
# 最多允许 3 秒完成连接阶段
curl --connect-timeout 3 http://127.0.0.1/

--max-time：整个请求的超时限制
# 整个请求最多执行 5 秒
curl --max-time 5 http://127.0.0.1/
```

### -L：自动跟随重定向

```
假设服务器返回：     服务器要求客户端访问新的地址
HTTP/1.1 301 Moved Permanently
Location: https://example.com/

curl -I http://example.com/
====>可能只看到重定向响应
# 让 curl 自动跟随重定向
curl -L http://example.com/

# 限制重定向次数
curl -L --max-redirs 5 http://example.com/
```

### --retry：请求失败自动重试

```
curl --retry 3 https://example.com/

--retry 3` | 最多额外重试 3 次 |
--retry-delay 1` | 重试之间等待 1 秒 |
--retry-max-time 15` | 限制整个重试过程允许的总时间 |
--connect-timeout 3` | 单次连接超时 |
--max-time 5` | 单次请求总超时 |

curl 默认并不会对所有错误进行重试，而是重点处理超时和某些临时性 HTTP 错误，例如 408、429、500、502、503、504 等
```

### -X：指定 HTTP 方法

| 方法   | 典型用途       |
| ------ | -------------- |
| GET    | 查询数据       |
| POST   | 提交或创建数据 |
| PUT    | 更新或替换资源 |
| PATCH  | 部分更新       |
| DELETE | 删除资源       |
| HEAD   | 获取响应头     |

```
curl -X GET http://127.0.0.1/
```

### -H：添加请求头

```
curl -H 'Accept: application/json' http://127.0.0.1:8080/api/health
告诉服务器：客户端希望接收 JSON 格式的数据

一台 Nginx 服务器运行多个网站：
curl -H 'Host: app.example.test' http://127.0.0.1/
可以测试 Nginx 根据 Host 选择相应虚拟主机的行为
```

### -d：发送请求数据

```
# 向一个示例 API 发送 JSON 数据
curl -X POST -H 'Content-Type: application/json' \
  -d '{"username":"sre","role":"admin"}' http://127.0.0.1:8080/api/users
# -d 默认会让 curl 使用 POST，因此一般不需要显式指定 -X POST

--json：简化 JSON 请求
curl --json '{"username":"sre"}' http://127.0.0.1:8080/api/users
```

### -G 与 --data-urlencode：安全构造查询参数

```
/api/search?q=linux sre 参数中包含空格，不能随意拼接 URL
curl -G --data-urlencode 'q=linux sre' http://127.0.0.1:8080/api/search
-G：将数据作为 URL 查询参数发送，使用 GET 请求。
--data-urlencode：对参数进行 URL 编码。
```

## curl 性能分析

用户反馈：网站访问需要 5 秒，但是服务器 CPU 和内存都没有明显异常。

```
客户端发起请求
1. DNS 解析
2. 建立 TCP 连接
3. TLS 握手（HTTPS）
4. 发送 HTTP 请求
5. 等待服务器开始响应
6. 接收响应数据
请求完成
```

| curl -w              | 含义                                        |
| -------------------- | ------------------------------------------- |
| `time_namelookup`    | 从开始到 DNS 解析完成的累计时间             |
| `time_connect`       | 从开始到 TCP 连接完成的累计时间             |
| `time_appconnect`    | 从开始到 TLS 等应用层连接握手完成的累计时间 |
| `time_starttransfer` | 从开始到收到第一个响应字节的累计时间        |
| `time_total`         | 整个请求耗时                                |
| `http_code`          | HTTP 响应状态码                             |
| `remote_ip`          | 实际连接的远端 IP                           |
| `size_download`      | 下载的响应体字节数                          |

```
curl -sS -o /dev/null -w 'HTTP状态码: %{http_code}\nDNS耗时: %{time_namelookup}s\nTCP连接耗时: %{time_connect}s\nTLS握手完成时间: %{time_appconnect}s\n首字节时间: %{time_starttransfer}s\n总耗时: %{time_total}s\n' https://example.com/
====>
HTTP状态码: 200
DNS耗时: 0.003373s
TCP连接耗时: 0.012106s
TLS握手完成时间: 0.034626s
首字节时间: 0.043832s
总耗时: 0.043863s

以提出初步判断：请求在连接建立后，到收到首个响应字节之间耗费了较多时间
接下来应该进一步调查：
- Nginx 是否在等待上游服务？
- 后端接口是否存在慢查询？
- 后端线程池是否耗尽？
- 是否存在网络传输延迟？
```



Q:用户反映网站访问非常慢，你会如何定位？

A:首先区分 DNS、连接建立、TLS 和 HTTP 响应阶段，通过 curl 的时间指标初步定位慢在哪个环节，再结合 Nginx 日志、系统资源以及应用监控继续分析。



### --resolve：绕过正常 DNS 解析，指定目标 IP

```
curl --resolve 'app.example.test:80:127.0.0.1' http://app.example.test/
新服务器上线前验证网站。
DNS 切换前检查新节点。
排查 DNS 问题。
验证 Nginx 虚拟主机。
验证 HTTPS 证书与域名匹配情况。
```

### -4 与 -6：指定 IPv4 或 IPv6

```
curl -4 https://example.com/
curl -6 https://example.com/

如果 IPv4 正常而 IPv6 失败，就可以进一步检查：
- DNS AAAA 记录。
- IPv6 路由。
- IPv6 防火墙规则。
- 服务监听地址。
- 云服务器 IPv6 配置。
```

### -k：忽略 HTTPS 证书验证

```
curl -k https://example.com/
```



## curl 常见错误码及排查方法

| curl 退出码 | 含义                                | 典型排查方向                 |
| ----------- | ----------------------------------- | ---------------------------- |
| 0           | 命令成功完成                        | 仍需检查 HTTP 状态码         |
| 6           | 无法解析主机名                      | DNS、域名配置                |
| 7           | 无法连接目标                        | 端口监听、服务、防火墙、网络 |
| 22          | HTTP 错误，且启用了相应失败判断参数 | HTTP 4xx/5xx                 |
| 28          | 操作超时                            | 网络、后端处理、超时设置     |
| 35          | TLS/SSL 连接阶段出错                | TLS 协议、握手配置           |
| 52          | 服务器没有返回有效响应数据          | 服务或中间设备异常           |
| 60          | SSL 证书验证失败                    | 证书、CA、域名、有效期       |
