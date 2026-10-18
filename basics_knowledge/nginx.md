# conf:nginx

 cgi(Common Gateway Interface)通用网关接口，主要解决的问题是从客户端发送一个请求和数据，服务端获取到请求和数据后可以调用CGI程序处理相应结果给客户端的一种标准规范。

/etc/nginx/
├── conf.d
│   └── default.conf
├── fastcgi_params
├── mime.types
├── modules -> /usr/lib/nginx/modules
├── nginx.conf
├── scgi_params
└── uwsgi_params

- **错误日志**：`/var/log/nginx/error.log`
- **访问日志**：`/var/log/nginx/access.log`

Nginx 的 PID 文件存放在 **/run/nginx.pid**

二进制文件在/usr/sbin/nginx

# nginx服务的信号控制

ps -ef | grep nginx

常用的信号包括：

- **HUP**：重载配置文件，无需重启服务
- **QUIT**：优雅关闭，等待工作进程处理完当前请求后退出
- **TERM/INT**：快速关闭
- **USR1**：重新打开日志文件（用于日志轮转、切割）
- **USR2**：平滑升级到新的 Nginx 二进制文件 老的pid后面会带一个oldbin
- **WINCH**：所有子进程不在接受处理新链接

使用方式为 kill -信号名 PID



# nginx命令行控制

Options:
  -?,-h         : this help
  -v            : show version and exit
  -V            : show version and configure options then exit
  -t            : test configuration and exit
  -T            : test configuration, dump it and exit
  -q            : suppress non-error messages during configuration testing
  -s signal     : send signal to a master process: **stop(->TERM/INT), quit(QUIT), reopen(USR1), reload(HUP)**
  -p prefix     : set prefix path (default: /etc/nginx/)
  -e filename   : set error log file (default: /var/log/nginx/error.log)
  -c filename   : set configuration file (default: /etc/nginx/nginx.conf)
  -g directives : set global directives out of configuration file用来补充nginx配置文件，向nginx服务指定启动时应用全局的配置



# nginx.conf

```
user  nginx;      # 用来指定启动运行工作进程的用户及用户组（权限访问控制）
# master_processes on/off; 用来指定是否开启工作进程
worker_processes  auto;   # 可以和服务器cpu数量保持一致 num/auto
# daemon on/off; 独立于控制终端 

error_log  /var/log/nginx/error.log notice;
# 日志级别 debub试/info信息/notice通知/warn警告/error错误/crit临界/alert警报/emerg紧急
# 若设置为info以下等级，会带来大量磁盘I/O影响性能
pid        /run/nginx.pid;

events {
		# accept_mutex on/off; 用来设置nginx网络连接序列化 off会惊群 on会一个个唤醒接受防止争抢
		# multi_accept on/off; 用来设置是否允许同时接收多个网络请求
    worker_connections  1024;  # 单个worker进程最大连接数
    # use method; 可选值有select/poll/epoll/kqueue等，用于nginx优化
}

http {
		# 定义MIME-Type（网络资源的媒体类型）
    include       /etc/nginx/mime.types;
    # 可以放在http、server、location中
    default_type  application/octet-stream;

		# 自定义服务器日志
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

		# 设置是否使用sendfile传输文件，提高处理静态资源的能力
    sendfile        on;
		# 设置长连接的超时时间
    keepalive_timeout  65;
    # keepalive_requests 100;  设置一个keep-alive连接使用的次数

    include /etc/nginx/conf.d/*.conf;
}
# 在http块中
server {
    listen       80;
    server_name  localhost;

    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
    }

    error_page   500 502 503 504  /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }

}
```



# nginx服务操作

## 配置成系统服务

在`/usr/lib/systemd/system/`目录下添加nginx.service

```
[Unit]
Description=nginx - high performance web server
Documentation=https://nginx.org/en/docs/
After=network-online.target remote-fs.target nss-lookup.target
Wants=network-online.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
Environment="CONFFILE=/etc/nginx/nginx.conf"
EnvironmentFile=-/etc/default/nginx
ExecStart=/usr/sbin/nginx -c ${CONFFILE}
ExecReload=/bin/sh -c "/bin/kill -s HUP $(/bin/cat /run/nginx.pid)"
ExecStop=/bin/sh -c "/bin/kill -s TERM $(/bin/cat /run/nginx.pid)"

[Install]
WantedBy=multi-user.target
```

然后就可以用systemctl命令来控制，新版已经自动注册了



# 静态资源部署

## listen

利用官方文档：nginx.org/en/docs/http/ngx_http_core_module.html#listen

```
Syntax:	listen address[:port] [default_server] [ssl] [http2 | quic] [proxy_protocol] [setfib=number] [fastopen=number] [backlog=number] [rcvbuf=size] [sndbuf=size] [accept_filter=filter] [deferred] [bind] [ipv6only=on|off] [reuseport] [multipath] [so_keepalive=on|off|[keepidle]:[keepintvl]:[keepcnt]];
listen port [default_server] [ssl] [http2 | quic] [proxy_protocol] [setfib=number] [fastopen=number] [backlog=number] [rcvbuf=size] [sndbuf=size] [accept_filter=filter] [deferred] [bind] [ipv6only=on|off] [reuseport] [multipath] [so_keepalive=on|off|[keepidle]:[keepintvl]:[keepcnt]];
listen unix:path [default_server] [ssl] [http2 | quic] [proxy_protocol] [backlog=number] [rcvbuf=size] [sndbuf=size] [accept_filter=filter] [deferred] [bind] [so_keepalive=on|off|[keepidle]:[keepintvl]:[keepcnt]];
Default:	
listen *:80 | *:8000;
Context:	server
```

## server_name

### 1)精确匹配（优先级0）

```
server{
		listen 80;
		server_name www.itfish.cn www.itbone.cn
}
```

### 2)使用通配符

```
server{
		listen 80;
		server_name *.itfish.cn（优先级1） www.itbone.*（优先级2）
}
```

### 3)使用正则表达式

```
server{
		listen 80;
		server_name ~^www\.(\w+)\.com$;（优先级3）
		return 200 $1;
}
~后不能加空格，括号可以取值
```

优先级4 default_server

# location

```
Syntax:	location [ = | ~ | ~* | ^~ | @] uri { ... }
location $variable { ... }
location @name { ... }
Default:	—
Context:	server, location
```

#### 不带符号（要求必须以指定模式开始）

location /abc {}

那么    ip:80/abc,ip:80/abcedf 都是能访问到的

#### = （与指定模式精确匹配）

location =/abc {}  ->  ip:80/abc

#### ~ | ~*

~ ：区分大小写

~*：不区分大小写

location ~^/abc\w$ {}     ->     ip:80/abce  (abc是不行的不符合正则，至少有四位)

#### ^~

用于不包含正则表达式的uri，一旦匹配到，就不继续搜索其他模式。

# 设置请求资源目录root/alias

#### root：设置请求的跟目录

处理结果：root路径+location路径

#### alias：用来更改location的URI

处理结果：使用alias路径替换location路径

# error_page

#### 1)指定具体跳转地址

```
error_page   404  http://www.fishbone.cn;
```

#### 2) 指定重定向地址

```
error_page   404  /50x.html;
error_page   500 502 503 504  /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }
```

#### 3) 使用location的@完成错误信息展示

```
error_page   404  @jump_to_error;
    location @jump_to_error {
        ...
    }
```

#### 4)可选项=[response]改变返回状态码

```
error_page   404 =200 /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }
```

# 静态资源优化配置

```
sendfile on;
tcp_nopush on; 在sendfile打开的状态下才会生效，用以提升网络包的传输效率
tcp_nodeplay on; 在keep-alive开启才生效，用以提高网络包传输的实时性
```

未使用sendfile的处理流程：

客户端浏览器发送请求==>服务器用户区nginx去read内核缓冲区==>内核缓冲区从磁盘copy资源再向应用程序缓冲区copy资源==>应用程序缓冲区向内核区socket缓冲区copy==>socket缓冲区向网卡copy==>再发送会浏览器

使用sendfile：

客户端浏览器发送请求==>服务器用户区nginx发送sendfile（）向内核缓冲区==>内核缓冲区copy磁盘资源==>内核缓冲区直接给socket缓冲区copy==>socket缓冲区再给网卡

# 静态资源压缩

```
ngx_http_gzip_module模块（默认）
ngx_http_gzip_static_module模块（需要配置）
ngx_http_gunzip_module模块（需要配置）
```

### ngx_http_gzip_module模块

```
gzip on;

gzip_types mime-type;	看具体要压缩什么类型

gzip_comp_level 1-9;	1的压缩程度最低，效率最高   一般设置为6比较平衡

gzip_vary on;	是否携带"Vary:Accept-Encoding"的响应头部，告诉接收方数据经过Gzip压缩处理

gzip_buffers numbersize;默认就行

gzip_disable 正则;	
针对不同种类客户端发起的请求，选择性开启或关闭gzip功能。根据user-agent排除指定浏览器。

gzip_http_version 默认即可，针对http协议版本选择性开启或关闭gzip功能

gzip_min_length 20;	针对传输数据的大小，选择性开启或关闭gzip功能
默认为20字节，不带单位；1024 / 10K｜k / 10m｜M
依靠响应头信息中的Content-Length，建议设置到1K以上

gzip_proxied off | expired | no-cache | no-store | private | no_last_modified | no_etag | auth | any ...;
设置是否对服务器返回结果进行gzip压缩（用在反向代理）
```

#### gzip和sendfile冲突问题

gzip进行压缩需要转到用户态，但是sendfile是不经过用户进程的

======>所以需要用到ngx_http_gzip_static_module模块

### ngx_http_gzip_static_module模块

```
gzip_static on | off | always;
```

检查与访问资源同名的.gz文件时，response中以gzip相关的header返回.gz文件的内容

# 浏览器缓存相关指令

### expires

用来控制页面缓存。控制http应答中的“expires”和“cache-control”

```
expires time | epoch | max | off
time：整数或负数，指定过期时间，如果是负数cache-control=no-cache；其他为max-age=time
epoch：no-cache ｜ max：10年

 location ~ .*\.(html|js|css|png)$ { 
        expires max;
        add_header Cache-Control no-store;
    }
```

### add_header

添加指定的响应头和响应值

```
must-revalidate	可缓存但必须再向源服务器进行确认
no-cache	缓存前必须确认其有效性
no-store	不缓存请求或响应的任何内容
no-transform	代理不可更改的媒体类型
public	可向任意方提供响应的缓存
private	仅向特定用户返回响应
proxy-revalidate	要求中间缓存服务器对缓存的响应有效性再确认
max-age=<秒>	响应最大age值
s-maxage=<秒>	公共缓存服务器响应的最大age值
```

# nginx的跨域问题

有两台服务器分别为A、B，如果从服务器A的页面发送异步请求到服务器B获取数据，如果服务器A何服务器B不满足同源策略，则就会出现跨域问题。

同源策略：协议、ip（域名）、端口相同

```
server B
location /getUser{
		add_header Access-Control-Allow-Origin A服务器域名:端口;
		add_header Access-Control-Allow-Methods GET,POST,PUT,DELETE;
}
```

# 静态资源防盗链

通过查看referer和内容进行匹配，若匹配到了就讲变量设置为0，反之则设置为1（不区分大小写）

```
location ~*\.(png|jpg|gif){
		valid_referers none blocked www.fish.com
		if ($invalid_referer){
				return 403;
		}
		root 目录;
}

location /images {
		valid_referers none blocked www.fish.com
		if ($invalid_referer){
				return 403;
		}
		root 目录;
}
```

但是referer限制比较粗========>第三方模块ngx_http_accesskey_module

# Rewrite功能

用于实现URL重写

应用场景：域名跳转、域名镜像、独立域名、目录自动添加“/”、合并目录、防盗链的实现

### set 设置新变量

```
Syntax:	set $variable value;
Default:	—
Context:	server, location, if
```

### if

```
if ($http_user_agent ~ MSIE) {
    rewrite ^(.*)$ /msie/$1 break;
}
if ($http_cookie ~* "id=([^;]+)(?:;|$)") {
    set $id $1;
}
if ($request_method = POST) {
    return 405;
}
if ($slow) {
    limit_rate 10k;
}
if ($invalid_referer) {
    return 403;
}
```

### break

```
Syntax:	break;
Default:	—
Context:	server, location, if
```

中断当前相同作用域中的其他nginx配置；终止当前匹配并把当前的URI在本location进行重定向访问处理

### rewrite

通过正则表达式改变URI，可以同时存在一个或者多个指令，按照顺序依次对URL进行匹配和处理

```
Syntax:	rewrite regex replacement [flag];
Default:	—
Context:	server, location, if

flag
last：重新走 location 匹配；
break：不再匹配新 location，直接继续在当前 location 往下执行；
redirect /permanent：直接返回重定向响应给浏览器。302临时重定向 /301永久重定向

location /download/ {
    rewrite ^(/download/.*)/media/(.*)\..*$ $1/mp3/$2.mp3 break;
    rewrite ^(/download/.*)/audio/(.*)\..*$ $1/mp3/$2.ra  break;
    return  403;
}
```

### rewrite_log

是否开启URL重写日志的输出功能

```
Syntax:	rewrite_log on | off;
Default:	
rewrite_log off;
Context:	http, server, location, if
```

以notice级别输出到error_log

```
rewrite_log on;
error_log error.log notice;方便调试，不然日志量太大
```

## rewrite案例

### 域名跳转

```
server {
		listen	80;
		server_name	www.fishbone.space;
		rewrite 200;
}

server {
		listen	80;
		server_name	www.fishbone1.cn www.fishbone2.com;
		rewrite ^(.*) http://www.fishbone.space$1;
}
```

### 域名镜像

```
server {
		listen	80;
		server_name	www.fishbone.space;
		rewrite 200;
}

server {
		listen	80;
		server_name	www.fishbone1.cn www.fishbone2.com;
		location /user {
				rewrite ^/user(.*)$ http://www.fishbone.space$1;
		}
		location /emp {
				return 200;
		}
}
```

### 独立域名

```
server {
		listen	81;
		server_name	search.fishbone.space;
		rewrite ^(.*) http://www.fishbone.space/search$1;
}
server {
		listen	82;
		server_name	item.fishbone.space;
		rewrite ^(.*) http://www.fishbone.space/item$1;
}
server {
		listen	83;
		server_name	cart.fishbone.space;
		rewrite ^(.*) http://www.fishbone.space/cart$1;
}
```

## 合并目录 和 防盗链优化



# 反向代理

ngx_http_proxy_module

#### proxy_pass 设置被代理服务器地址

```
Syntax:	proxy_pass URL;
Default:	—
Context:	location, if in location, limit_except

location /server{}
proxy_pass http://192.168.200.146;
			======>http://192.168.200.146/server/index.html
proxy_pass http://192.168.200.146/;     <=====加/的区别
			======>http://192.168.200.146/index.html
```

#### proxy_set_header 更改nginx服务器接收到的客户端请求的请求头信息，然后将新的请求头发送给代理的服务器

```
Syntax:	proxy_set_header field value;
Default:	
proxy_set_header Host $proxy_host;
proxy_set_header Connection close;
Context:	http, server, location
```

#### proxy_redirect 重制头信息中的“location”和“refresh”的值

```
Syntax:	proxy_redirect default;
proxy_redirect off;
proxy_redirect redirect replacement;
Default:	
proxy_redirect default;
Context:	http, server, location

被代理服务器
server {
		listen	8081;
		server_name	localhost;
		if (!-f $request_filename){
				return 302 http://192.168.200.146;
		}
}
==========> 这样就会暴露被代理服务器

代理服务器
server {
		listen	8081;
		server_name	localhost;
		location /{
				proxy_pass http://192.168.200.146:8081/;
				proxy_redirect http://192.168.200.146 http://192.168.200.133;
		}
}
server {
		listen	80;
		server_name	localhost;
		location /{
				proxy_pass http://192.168.200.146/;
		}
}
```



## 服务器1，2，3存在两种情况

第一种情况：三台服务器的内容不一样

```
代理服务器
server {
		listen	8082;
		server_name	localhost;
		location /server1 {
				proxy_pass http://192.168.200.146:9001/;
		}
		location /server2 {
				proxy_pass http://192.168.200.146:9002/;
		}
		location /server3 {
				proxy_pass http://192.168.200.146:9003/;
		}
}
```

第二种情况：三台服务器的内容一样 ======> 负载均衡



# ngx_http_ssl_module

```
Syntax:	ssl on | off;
Default:	
ssl off;
Context:	http, server

server{
		listen 443 ssl;
}
```

```
为当前这个虚拟主机指定一个带有PEM格式证书的证书
Syntax:	ssl_certificate file;
Default:	—
Context:	http, server

用来指定PEM secret key文件的路径
Syntax:	ssl_certificate_key file;
Default:	—
Context:	http, server

server {
    listen              443 ssl;
    server_name         example.com;

    ssl_certificate     example.com.rsa.crt;
    ssl_certificate_key example.com.rsa.key;

    ssl_certificate     example.com.ecdsa.crt;
    ssl_certificate_key example.com.ecdsa.key;
    ...
}
```

```
配置用于SSL会话的缓存
Syntax:	ssl_session_cache off | none | [builtin[:size]] [shared:name:size];
Default:	
ssl_session_cache none;
Context:	http, server

off
严格禁止使用会话缓存：Nginx 明确告知客户端，会话不可复用。
none
软性不允许使用会话缓存：Nginx 告知客户端会话可以复用，但实际上不会在缓存中存储会话参数。
builtin
OpenSSL 内置缓存；仅单个 worker 进程可用。缓存大小由 `sessions`（会话数）指定；若不设置大小，默认可存放 20480 个会话。使用内置缓存可能引发内存碎片。
shared
所有 worker 进程之间共享的缓存。缓存大小单位为字节；1MB 大约可以存储 4000 个会话。每个共享缓存需要设置一个自定义名称。同名缓存可在多个虚拟主机中共用。
该缓存还用于自动生成、存储并定期轮换 TLS session ticket 密钥（1.23.2 新增），除非通过 `ssl_session_ticket_key` 指令显式单独配置密钥。

两种缓存类型可以同时使用，示例：
ssl_session_cache builtin:1000 shared:SSL:10m;
但只使用 shared 缓存、不搭配 builtin 缓存效率更高。
```

```
开启SSL会话功能后，设置客户端能够反复使用存储在缓存中的会话参数时间
Syntax:	ssl_session_timeout time;
Default:	
ssl_session_timeout 5m;
Context:	http, server
```

```
允许的密码，密码指定为OpenSSL支持的格式（openssl ciphers可以查看）
Syntax:	ssl_ciphers ciphers;
Default:	
ssl_ciphers HIGH:!aNULL:!MD5;
Context:	http, server

ssl_ciphers ALL:!aNULL:!EXPORT56:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2:+EXP;
```

```
指定是否服务器密码优先客户端密码
Syntax:	ssl_prefer_server_ciphers on | off;
Default:	
ssl_prefer_server_ciphers off;
Context:	http, server
```



# 反向代理调优

### buffer和cache

buffer（缓冲）：解决不同设备之间数据传递速度不一致导致的性能低的问题，缓冲中的数据一旦此次操作完成后，就可以删除

cache（缓存）：将被代理服务器的数据缓存一份到代理服务器。缓存中的数据可以重复使用，只有满足特定条件才会删除

```
Syntax:	proxy_buffering on | off;
Default:	
proxy_buffering on;
Context:	http, server, location

指定单个连接从代理服务器读取响应的缓存区的个数和大小
Syntax:	proxy_buffers number size;
Default:	
proxy_buffers 8 4k|8k;
Context:	http, server, location

被代理服务器获取的第一部分响应数据的大小
Syntax:	proxy_buffer_size size;
Default:	
proxy_buffer_size 4k|8k;
Context:	http, server, location

限制同时处于busy状态的缓冲总大小
Syntax:	proxy_busy_buffers_size size;
Default:	
proxy_busy_buffers_size 8k|16k;
Context:	http, server, location

当缓冲区存满后，仍未被nginx服务器完全接受，响应数据就会被临时存放在磁盘文件上，该指令设置文件路径
Syntax:	proxy_temp_path path [level1 [level2 [level3]]];
Default:	
proxy_temp_path proxy_temp;
Context:	http, server, location

path最多设置3层 /usr/local/src
proxy_temp_path /spool/nginx/proxy_temp 1 2;

设置磁盘上缓冲文件的大小
Syntax:	proxy_temp_file_write_size size;
Default:	
proxy_temp_file_write_size 8k|16k;
Context:	http, server, location
```



# 负载均衡

#### dns负载均衡

可靠性低、负载均衡不均衡

## 四/七层负载均衡

四层负载均衡指的是OSI七层模型中的传输层，主要是基于IP+PORT的负载均衡

实现方式：

1）硬件：F5 BIG-IP、Radware等

2）软件：LVS、Nginx、Hayproxy等

七层负载均衡指的是OSI七层模型中的应用层，主要是基于虚拟的URL或主机IP的负载均衡

实现方式：软件==>Nginx、Hayproxy等

**区别：**四层负载均衡数据包是在底层就进行了分发，而七层负载均衡数据包则在最顶端进行分发，所以四层负载均衡的效率比七层负载均衡高

四层负载均衡不识别域名，七层负载均衡识别域名

其实还有二层、三层负载均衡，二层是在数据链路层基于mac地址来实现负载均衡，三层是在网络层，一般采用虚拟IP地址的方式实现负载均衡

实际环境采用的模式：四层负载（LVS）+七层负载（Nginx）

## 七层ngx_http_upstream_module

```
定义一组服务器，可以是监听不同端口的服务器，也可以是同时监听TCP和Unix socket的服务器，默认权重为1
Syntax:	upstream name { ... }
Default:	—
Context:	http

指定后端服务器的名称和一些参数，可以使用域名、IP、端口或者Unix socket
Syntax:	server address [parameters];
Default:	—
Context:	upstream

upstream backend {
		server 192.168.200.146:9001 down;
		server 192.168.200.146:9002 backup;
		server 192.168.200.146:9003 max_fails=3 fail_timeout=15;
}
server{
		listen 8083;
		server_name localhost;
		location / {
				proxy_pass http://backend;
		}
}
```

| 状态         | 概述                              |
| ------------ | --------------------------------- |
| down         | 当前的server暂时不参与负载均衡    |
| backup       | 预留的备份服务器                  |
| max_fails    | 允许请求失败的次数                |
| fail_timeout | 经过max_fails失败后，服务暂停时间 |
| max_conns    | 限制最大的接收连接数              |

### 负载均衡策略

| 算法       | 说明                          |
| ---------- | ----------------------------- |
| 轮询       | 默认                          |
| weight     | 权重                          |
| ip_hash    | ip分配                        |
| least_conn | 最少连接                      |
| url_hash   | URL分配（要配合缓存命中使用） |
| fair       | 响应时间(第三方模块)          |

```
upstream backend {
		server 192.168.200.146:9001 weight=10;    值越大，被分配的概率越大
		server 192.168.200.146:9002 weight=5;
		server 192.168.200.146:9003 weight=3;
}

upstream backend {
		ip_hash;    比如说防止用户反复登录
		server 192.168.200.146:9001;
		server 192.168.200.146:9002;
		server 192.168.200.146:9003;
}
========>无法保证负载均衡，设置后权重等方法将不起作用
========>可以不使用ip_hash；设置redis缓存，将用户的session保存在缓存中

upstream backend {
		least_conn;   适合请求处理时长不一致造成服务器过载的情况
		server 192.168.200.146:9001;
		server 192.168.200.146:9002;
		server 192.168.200.146:9003;
}

upstream backend {
		hash $request_uri;
		server 192.168.200.146:9001;
		server 192.168.200.146:9002;
		server 192.168.200.146:9003;
}

upstream backend {
		fair;
		server 192.168.200.146:9001;
		server 192.168.200.146:9002;
		server 192.168.200.146:9003;
}
==========>nginx-upstream-fair模块
在nginx源码中ngx_http_upstream.h中找到ngx_http_upstream_srv_conf_s在模块中添加default_port属性
in_port_t	default_port
```

#### 对特定资源实现负载均衡

```
upstream videobackend {
		server 192.168.200.146:9001;
		server 192.168.200.146:9002;
}

upstream filebackend {
		server 192.168.200.146:9003;
		server 192.168.200.146:9004;
}
server{
		listen 8083;
		server_name localhost;
		location /video/ {
				proxy_pass http://videobackend;
		}
		location /file/ {
				proxy_pass http://filebackend;
		}
}
```

#### 带有URL重写的负载均衡

```
upstream backend {
		server 192.168.200.146:9001;
		server 192.168.200.146:9002;
		server 192.168.200.146:9003;
}
server{
		listen 8083;
		server_name localhost;
		location /file/ {
				rewrite ^(/file/.*) /server/$1 last;
		}
		location /server {
				proxy_pass http://backend;
		}
}
```

## 四层ngx_stream_core_module

```
Syntax:	stream { ... }
Default:	—
Context:	main       和http指令同级别
```

安装redis

```
cd redis-8.8.3/
make PREFIX=/home/ubuntu/redis/redis01 install
cp redis-core/redis-8.8.3/redis.conf redis/redis01/
bin/redis-server ./redis.conf
ps -ef|grep redis
```

```
stream{
		upstream redisbackend{
				server 192.168.200.146:6379;
				server 192.168.200.146:6378;
		}
		upstream tomcatbackend{
				server 192.168.200.146:8080;
		}
		server {
				listen	81;
				proxy_pass redisbackend;
		}
		server {
				listen	82;
				proxy_pass tomcatbackend;
		}
}
```

**若同时配置了四/七层负载均衡，并且同时监听82端口，那么是四层负载均衡生效**



# 缓存集成

1.url+.... => key

2.key + MD5 => 字符串（密文）

3.缓存目录 /usr/local/proxy_cache

4./usr/local/proxy_cache/a/b3

5.判断缓存目录有没有所访问的数据对应的目录

6.定期清除

```
Syntax:	proxy_cache_path path [levels=levels] [use_temp_path=on|off] keys_zone=name:size [inactive=time] [max_size=size] [min_free=size] [manager_files=number] [manager_sleep=time] [manager_threshold=time] [loader_files=number] [loader_sleep=time] [loader_threshold=time] [purger=on|off] [purger_files=number] [purger_sleep=time] [purger_threshold=time];
Default:	—
Context:	http
如：proxy_cache_path /data/nginx/cache levels=1:2 keys_zone=one:10m;
levels最多可以设置3层 每层的取值为1｜2
levels=1:2	缓存空间有两层目录，第一次是1个字母，第二次是2个字母
若加密后的值为 0694e2107d
levels=1:2	最终路径为：/data/nginx/cache/d/07
levels=2:1:2	最终路径为：/data/nginx/cache/7d/0/21
levels=2:2:2	最终路径为：/data/nginx/cache/7d/10/e2

keys_zone=itfish:200m	缓存区的名称是itfish，大小为200M，1M大概能存储8000个keys
inactive=1d	缓存数据在1天内没有被访问就会被删除
max_size=20g	最大缓存空间，若被存满，默认覆盖缓存时间最长的资源
```

```
Syntax:	proxy_cache zone | off;
Default:	
proxy_cache off;
Context:	http, server, location
用来开启或关闭代理缓存，若为开启则指定使用哪个缓存器进行缓存

Syntax:	proxy_cache_key string;
Default:	
proxy_cache_key $scheme$proxy_host$request_uri;
Context:	http, server, location
设置web缓存的key值
proxy_cache_key "$host$request_uri $cookie_user";
proxy_cache_key $scheme$proxy_host$uri$is_args$args;

Syntax:	proxy_cache_valid [code ...] time;
Default:	—
Context:	http, server, location
对不同返回状态码的URL设置不同的缓存时间
proxy_cache_valid 200 302 10m;
proxy_cache_valid 404      1m;
为200和302的响应设置10分钟缓存，为404的响应URL设置1分钟缓存
proxy_cache_valid 5m;
只有200、301、302被缓存
proxy_cache_valid any      1m;
所有响应状态码的URL都设置1分钟

Syntax:	proxy_cache_min_uses number;
Default:	
proxy_cache_min_uses 1;
Context:	http, server, location
设置资源被访问多少次后被缓存

Syntax:	proxy_cache_methods GET | HEAD | POST ...;
Default:	
proxy_cache_methods GET HEAD;
Context:	http, server, location
设置缓存哪些http方法
```

# 缓存清除

### 删除对应的缓存目录

```
rm -rf /data/nginx/cache/
```

### 第三方模块 ngx_cache_purge

# 设置资源不缓存

不是所有的数据都适合进行缓存

```
Syntax:	proxy_no_cache string ...;
Default:	—
Context:	http, server, location
定义不将数据进行缓存的条件

proxy_no_cache $cookie_nocache $arg_nocache$arg_comment;
proxy_no_cache $http_pragma    $http_authorization;

Syntax:	proxy_cache_bypass string ...;
Default:	—
Context:	http, server, location
设置不从缓存中获取数据的条件

proxy_cache_bypass $cookie_nocache $arg_nocache$arg_comment;
proxy_cache_bypass $http_pragma    $http_authorization;

多个条件中至少有一个不为空且不等于0，则条件满足成立
$cookie_nocache
当前请求的cookie中键的名称为nocache对应的值
$arg_nocache$arg_comment
当前请求的参数中属性名为nocache和comment对应的属性值
```



# nginx高可用

keepalived ======> VRRP协议（虚拟路由冗余协议）

keepalived.org

```
./configure --sysconf=/etc --prefix=/usr/local
/etc/keepalived/keepalived.conf
/usr/local/sbin目录下的keepalived系统配置脚本
```

### keepalived.conf

分为3个部分：global、vrrp、LVS

#### 自动漂移

1.keepalived配置文件中添加对应的配置项

```
vrrp_script 脚本名称
{
	script	脚本位置
	interval	3  #执行时间间隔
	weight -20	#动态调整vrrp_instance的优先级
}
vrrp_instance VI_1{
	...
	track_script{
		ck_nginx
	}
	...
}
```

2.脚本ck_nginx.sh

```
#!/bin/bash

num=`ps -C nginx --no-header | wc -l`
if [$num -eq 0];then
	/usr/local/nginx/sbin/nginx
	sleep 2
	if [`ps -C nginx --no-header | wc -l` -eq 0];then
		killall keepalived
	fi
fi
```

3.为脚本文件设置权限

```
chmod 755 ck_nginx.sh
```

在修好nginx服务器后，master好了又会抢占vip，发生两次业务切换

在配置文件加入nopreempt非抢占（只能用于state为backup）所以把state都设置成backup，让其通过priority来竞争。



# 下载站点ngx_http_autoindex_module

该模块处理以/结尾的请求，并生成目录列表

```
Syntax:	autoindex on | off;
Default:	
autoindex off;
Context:	http, server, location

Syntax:	autoindex_exact_size on | off;
Default:	
autoindex_exact_size on;
Context:	http, server, location
指定是否在目录列表展示文件的详细大小

Syntax:	autoindex_format html | xml | json | jsonp;
Default:	
autoindex_format html;
Context:	http, server, location
设置目录列表的格式

Syntax:	autoindex_localtime on | off;
Default:	
autoindex_localtime off;
Context:	http, server, location
对应html格式，是否在目录列表上显示时间
off文件的GMT时间/on显示文件的服务器时间

location /download {
		root /usr/local;
		autoindex on;
		autoindex_exact_size off;
		autoindex_format html;
		autoindex_localtime on;
		auth_basic 'please input your auth';
		auth_basic_user_file htpasswd;
}
```

# 用户认证模块ngx_http_auth_basic_module

```
Syntax:	auth_basic string | off;
Default:	
auth_basic off;
Context:	http, server, location, limit_except

Syntax:	auth_basic_user_file file;
Default:	—
Context:	http, server, location, limit_except
指定用户名和密码所在文件

用htpasswd工具生成
htpasswd -c /path/htpasswd username 创建用户
htpasswd -b /path/htpasswd username password 新增用户和密码
htpasswd -D /path/htpasswd username 删除
htpasswd -v /path/htpasswd username 验证
```



# 使用lua扩展nginx

### 方式1

luajit.org安装

lua_nginx_module

更改目录名 mv lua_nginx_module-0.10.16rc4 lua_nginx_module

导入环境变量

export LUAJIT_LIB=/usr/local/lib

export LUAJIT_INC=/usr/local/include/luajit-2.0

### 方式2 OpenRestry

在nginx.conf下添加测试

```
location /lua {
	degault_type 'text/html';
	content_by_lua 'ngx.say("<h1>HELLO,OpenRestry</h1>")';
}
```

```
location /getByGender{
	default_type 'text/html';
	set_by_lua $param "
		local uri_args = ngx.req.get_uri_args()
		local name = uri_args['name']
		local gender = uri_args['gender']
		if gender=='1' then
			return name..'先生'
		elseif gender=='0' then
			return name..'女士'
		else
			return name
		end
	";
	charset utf-8;
	return 200 $param;
}
```

**HttpRedis、HttpRedis2Module、Lua_resty_redis**

```
redis = require "resty.redis"
redis,err = redis:new()
ok,err=redis:connect(host,port[,options_table])
# 设置连接Redis的连接信息 ok连接成功返回1，失败返回nil。err返回对应的错误信息
redis:set_timeout(time)
ok,err = redis:close()
# 关闭当前连接


location /testRedis{
	default_type "text/html";
	
	content_by_lua_block{
		local redis = require "resty.redis"
		local redisObj = redis:new()
		redisObj:set_timeout(1000)
		local ok,err = redisObj:connect("192.168.200.111",6379)
		if not ok then
			ngx.say("failed", err)
			return
		end
		ok,err = redisObj:set("username","ROSE")
		if not ok then
			ngx.say("failed", err)
			return
		end
		local res,err = redisObj:get("username")
		ngx..say(res)
		redisObj:close()
	}
}
```

**1)ngx_lua、lua_resty_mysql**

**2)drizzle_nginx_module(HttpDrizzleModule)**

```
local mysql = require "resty.mysql"
db,err = mysql:new()
ok,err=db:connect(options)
# options是lua表 里面包含host,port,user,password,database
db:set_timeout(time)
db:close
bytes,err = db:send_query(sql)
# 异步向远程mysql发送一个查询 成功则返回成功发送的字节数 错误则返回nil和错误描述
res,err,errcode,selstate = db:read_result()
res,err,errcode,selstate = db:read_result(rows)
# res返回一个描述ok包或结果集包的lua表（rows指定返回结果集的最大值，默认为4）
# 如果是查询，则返回一个容纳多行的数组，每行是一个数据列的key-value对
# 如果是增删改则返回{insert_id=0,server_status=2,warning_count=1,affected_rows=2,message=nil}

location /testMysql{
	content_by_lua_block{
		local mysql = require "resty.mysql"
		local db = mysql:new()
		local ok,err = db:connect{
			host='192.168.200.111',
			port=3306,
			user='root',
			password='123456'
			database='nginx_db'
		}
		db:set_timeout(1000)
		db:send_query('select * from users where id = 2')
		local res,err,errcode,sqlstate = db:read_result()
		ngx.say(res[1].id..','..res[1].username..','..res[1].birthday)
		db:close()
	}
}
```

### lua_cjson

```
db:send_query('select * from users')
for i,v in ipairs(res) do
	ngx.say(v.id..','..v.username..','..v.birthday)
end

local cjson = require "cjson"
cjson.encode(res)

location /testMysql{
	...
	local cjson = require "cjson"
		db:send_query('select * from users where id = 2')
		local res,err,errcode,sqlstate = db:read_result()
		ngx.say(cjson.encode(res))
	...
	}
}

======>
可以设置全局的cjson
和server同级
init_by_lua_block{
	cjson = require "cjson"
}
```

### 增删改

```
优化send_query和read_result

res,err,errcode,sqlstate = db:query(sql[,rows])

...
	local res,err,errcode,sqlstate = db:query('select * from users where id = 2')
	
	local sql = 'insert into users(username,birthday) values('fish','...','...')'
	local sql = "update users set username = 'fishbone' where id = 3"
	local sql = "delete from users where id = 3"
	local res,err,errcode,sqlstate = db:query(sql)
...
```



# 使用ngx_lua完成redis缓存预热

