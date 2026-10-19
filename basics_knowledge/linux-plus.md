

线上某个 Web 服务突然无法访问，可能的原因包括：

- 服务进程已经退出。
- 服务正在运行，但没有监听正确的端口。
- 端口被其他进程占用了。
- 服务器内存不足，进程被系统杀死。
- 磁盘空间用完，服务无法写入日志。
- 配置文件存在语法错误，导致服务启动失败。



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

