# 端口占用故障排查

## 1. 故障现象

```
sudo systemctl start nginx
====>
Job for nginx.service failed because the control process exited with error code.
See "systemctl status nginx.service" and "journalctl -xeu nginx.service" for details.
failure;status=1
```



## 2. 故障复现

```
sudo python3 -m http.server 80 --bind 127.0.0.1
====>
Serving HTTP on 127.0.0.1 port 80 (http://127.0.0.1:80/) ...
```



## 3. 排查过程

```
sudo journalctl -u nginx -n 50 --no-pager
====>
Oct 19 15:04:20 VM-0-2-ubuntu systemd[1]: Starting nginx.service - nginx - high performance web server...
Oct 19 15:04:20 VM-0-2-ubuntu nginx[2264773]: nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
Oct 19 15:04:21 VM-0-2-ubuntu nginx[2264773]: nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
Oct 19 15:04:21 VM-0-2-ubuntu nginx[2264773]: nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
Oct 19 15:04:22 VM-0-2-ubuntu nginx[2264773]: nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
Oct 19 15:04:22 VM-0-2-ubuntu nginx[2264773]: nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
Oct 19 15:04:23 VM-0-2-ubuntu nginx[2264773]: nginx: [emerg] still could not bind()
Oct 19 15:04:23 VM-0-2-ubuntu systemd[1]: nginx.service: Control process exited, code=exited, status=1/FAILURE
Oct 19 15:04:23 VM-0-2-ubuntu systemd[1]: nginx.service: Failed with result 'exit-code'.
Oct 19 15:04:23 VM-0-2-ubuntu systemd[1]: Failed to start nginx.service - nginx - high performance web server.
```



## 4. 故障根因

```
nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
```



## 5. 修复操作

```
sudo ss -lntp '( sport = :80 )'
====>
State    Recv-Q   Send-Q     Local Address:Port     Peer Address:Port  Process                                 
LISTEN   0        5              127.0.0.1:80            0.0.0.0:*      users:(("python3",pid=2264301,fd=3))

# 可以看到这个端口被一个python程序占用

# 确认这个程序是执行什么业务之后
kill 2264301

```



## 6. 恢复验证

```
sudo systemctl status nginx
====>
● nginx.service - nginx - high performance web server
     Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled; preset: enabled)
     Active: active (running) since Mon 2026-10-19 15:10:10 CST; 15s ago
 Invocation: c569c3ebfef946bebaed44ef45d62377
       Docs: https://nginx.org/en/docs/
    Process: 2266177 ExecStart=/usr/sbin/nginx -c ${CONFFILE} (code=exited, status=0/SUCCESS)
   Main PID: 2266178 (nginx)
      Tasks: 3 (limit: 2882)
     Memory: 3.5M (peak: 3.9M)
        CPU: 12ms
     CGroup: /system.slice/nginx.service
             ├─2266178 "nginx: master process /usr/sbin/nginx -c /etc/nginx/nginx.conf"
             ├─2266179 "nginx: worker process"
             └─2266180 "nginx: worker process"

Oct 19 15:10:10 VM-0-2-ubuntu systemd[1]: Starting nginx.service - nginx - high performance web server...
Oct 19 15:10:10 VM-0-2-ubuntu systemd[1]: Started nginx.service - nginx - high performance web server.

curl -I http://127.0.0.1
====>
HTTP/1.1 200 OK
Server: nginx/1.30.6
Date: Mon, 19 Oct 2026 07:10:35 GMT
Content-Type: text/html
Content-Length: 896
Last-Modified: Fri, 02 Oct 2026 14:33:28 GMT
Connection: keep-alive
ETag: "6abfc0b8-380"
Accept-Ranges: bytes
```



## 7. 经验总结

先看日志确定是什么原因的错误，发现是端口问题，再去找对应端口被谁用了。如果重要那就换端口，不重要就kill。