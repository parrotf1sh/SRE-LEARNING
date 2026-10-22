# Nginx 配置错误故障排查

## 1. 故障现象

```
sudo nginx -t
====>
nginx: [emerg] unknown directive "test_bad_directive" in /etc/nginx/nginx.conf:1
nginx: configuration file /etc/nginx/nginx.conf test failed
failure;status=1

sudo systemctl restart nginx
====>
Job for nginx.service failed because the control process exited with error code.
See "systemctl status nginx.service" and "journalctl -xeu nginx.service" for details.
failure;status=1
```



## 2. 故障复现

```
sudo cp -a nginx.conf nginx.conf.bak

sudo vim nginx.conf
=>在第一行输入test_bad_directive on;
```



## 3. 排查过程

```
sudo journalctl -u nginx -n 50 --no-pager
====>
Oct 19 14:52:24 VM-0-2-ubuntu systemd[1]: Starting nginx.service - nginx - high performance web server...
Oct 19 14:52:24 VM-0-2-ubuntu nginx[2261770]: nginx: [emerg] unknown directive "test_bad_directive" in /etc/nginx/nginx.conf:1
Oct 19 14:52:24 VM-0-2-ubuntu systemd[1]: nginx.service: Control process exited, code=exited, status=1/FAILURE
Oct 19 14:52:24 VM-0-2-ubuntu systemd[1]: nginx.service: Failed with result 'exit-code'.
Oct 19 14:52:24 VM-0-2-ubuntu systemd[1]: Failed to start nginx.service - nginx - high performance web server.
```



## 4. 故障根因

nginx: [emerg] unknown directive "test_bad_directive" in /etc/nginx/nginx.conf:1

## 5. 修复操作

```
# 改正错误的配置文件
sudo cp -a nginx.conf.bak nginx.conf

sudo nginx -t
====>
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```



## 6. 恢复验证

```
curl -I http://127.0.0.1
====>
HTTP/1.1 200 OK
Server: nginx/1.30.6
Date: Mon, 19 Oct 2026 06:58:44 GMT
Content-Type: text/html
Content-Length: 896
Last-Modified: Fri, 02 Oct 2026 14:33:28 GMT
Connection: keep-alive
ETag: "6abfc0b8-380"
Accept-Ranges: bytes
```



## 7. 经验总结

无法启动进程，先查看对应日志。在日志中找到具体报错信息。改好重启后需要验证。

