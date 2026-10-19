# 服务异常退出故障排查

## 1. 故障现象

描述服务异常的具体表现。

## 2. 故障复现

```
sudo systemd-run --unit=week2-exit /bin/sh -c 'exit 1'
====>
Running as unit: week2-exit.service; invocation ID: 993c99a49d644bd7879f7c4ee3186cbe

exit 1
====> 会话断开
```



## 3. 排查过程

```
sudo systemctl status week2-exit --no-pager -l
====>
× week2-exit.service - [systemd-run] /bin/sh -c "exit 1"
     Loaded: loaded (/run/systemd/transient/week2-exit.service; transient)
  Transient: yes
     Active: failed (Result: exit-code) since Mon 2026-10-19 15:15:28 CST; 1min 53s ago
   Duration: 7ms
 Invocation: 993c99a49d644bd7879f7c4ee3186cbe
    Process: 2267429 ExecStart=/bin/sh -c exit 1 (code=exited, status=1/FAILURE)
   Main PID: 2267429 (code=exited, status=1/FAILURE)
   Mem peak: 1.9M
        CPU: 4ms

Oct 19 15:15:28 VM-0-2-ubuntu systemd[1]: Started week2-exit.service - [systemd-run] /bin/sh -c "exit 1".
Oct 19 15:15:28 VM-0-2-ubuntu systemd[1]: week2-exit.service: Main process exited, code=exited, status=1/FAILURE
Oct 19 15:15:28 VM-0-2-ubuntu systemd[1]: week2-exit.service: Failed with result 'exit-code'.
failure;status=3

sudo journalctl -u week2-exit -n 30 --no-pager
====>
Oct 19 15:15:28 VM-0-2-ubuntu systemd[1]: Started week2-exit.service - [systemd-run] /bin/sh -c "exit 1".
Oct 19 15:15:28 VM-0-2-ubuntu systemd[1]: week2-exit.service: Main process exited, code=exited, status=1/FAILURE
Oct 19 15:15:28 VM-0-2-ubuntu systemd[1]: week2-exit.service: Failed with result 'exit-code'.
```



## 4. 故障根因

```
status=1/FAILURE
```



## 5. 修复操作

```
sudo systemctl reset-failed week2-exit
```



## 6. 恢复验证

/

## 7. 经验总结

服务进程退出，不一定代表 systemd 出错。

systemd 只是根据 Unit 配置启动并管理进程。

进程本身为什么退出，还需要结合退出码、日志及程序行为进行分析。