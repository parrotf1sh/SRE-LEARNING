# 排障思路

| 用户感受到的问题         | 可能设计的层次   | 首先区分什么                         |
| ------------------------ | ---------------- | ------------------------------------ |
| 域名无法访问，但IP可以   | DNS/HTTP/TLS     | 是域名解析失败，还是Host、证书的问题 |
| IP不可达                 | 网络层           | 路由、网络隔离、丢包                 |
| 连接80端口被拒绝         | 传输层或访问策略 | 服务是否监听、是否主动拒绝           |
| TCP连接成功，但HTTPS报错 | TLS              | 证书、协议、密钥协商                 |
| HTTPS正常，但API返回502  | 反向代理/应用层  | Nginx与后端之间是否异常              |
| 接口返回504              | 代理/后端处理    | 上游连接或响应是否超时               |
| 大量CLOSE_WAIT           | TCP/应用         | 应用是否及时关闭Socket               |
| 页面偶尔特别慢           | 多层次           | DNS、RTT、重传、TLS、应用处理耗时    |

络排障要沿着请求路径逐段分析，而不是看到某一个错误就直接推断最终原因。

```
Nginx 返回 504，虽然表现为 HTTP 层的状态码，但真正原因可能是：
数据库出现慢查询
       ↓
后端请求处理耗时升高
       ↓
Nginx 等待上游响应
       ↓
超过上游读取超时阈值
       ↓
Nginx 返回 504

也可能是：
Nginx 和后端之间网络丢包严重
       ↓
TCP 重传和延迟增加
       ↓
后端响应未及时到达
       ↓
Nginx 返回 504

这两种情况都表现为 504，但一个主要是应用与数据库问题，另一个主要是网络问题。
```



# 典型的https网页访问

#### 1）DNS域名解析

www.example.com → 服务器 IP 地址

#### 2)IP路由与数据转发

找到通往目标服务器的网络路径

#### 3）TCP建立连接

通过三次握手建立可靠传输连接

#### 4）TLS安全握手

验证服务器身份，协商加密密钥

#### 5）HTTP请求和响应

浏览器发送 GET，服务器返回 HTML

#### 6）浏览器渲染页面

解析 HTML、CSS、JavaScript，显示内容



# OSI七层模型与TCP/IP模型

| **层次** | **名称**   | **作用**                 | **典型协议与技术**     |
| -------- | ---------- | ------------------------ | ---------------------- |
| 7        | 应用层     | 为应用提供网络服务       | HTTP、DNS、SMTP        |
| 6        | 表示层     | 数据编码、转换、加密等   | 字符编码、数据表示概念 |
| 5        | 会话层     | 管理通信会话             | 会话管理机制           |
| 4        | 传输层     | 端到端通信、端口、可靠性 | TCP、UDP               |
| 3        | 网络层     | IP寻址与跨网络路由       | IPv4、IPv6、ICMP       |
| 2        | 数据链路层 | 相邻节点的数据帧传输     | Ethernet、Wi-Fi        |
| 1        | 物理层     | 传输二进制比特           | 网线、光纤、无线信号   |

如果 HTTP 请求失败：究竟是 IP 不可达、TCP 连接无法建立，还是 HTTP 服务本身存在问题。



# 子网掩码

IP 地址包含两个逻辑部分：

- 网络部分：标识所在网络。
- 主机部分：标识该网络中的接口地址。

子网掩码用于区分这两部分。

```
IP 地址：
192.168.1.10

子网掩码：
255.255.255.0

CIDR 表示：
192.168.1.10/24

IP AND Mask 进行按位与运算

11000000.10101000.00000001.00001010
11111111.11111111.11111111.00000000
---------------------------------------
11000000.10101000.00000001.00000000

得到网络地址：
192.168.1.0
这个网段可以写成：
192.168.1.0/24
对于传统 IPv4 /24 子网：
- 网络地址：192.168.1.0
- 广播地址：192.168.1.255
- 常规可用主机地址：192.168.1.1 ～ 192.168.1.254
- 可用主机地址数：254
```



# 默认网关

网关可以理解为主机通往其他网络的下一跳设备。

```
主机 A：192.168.1.10/24
主机 B：192.168.1.20/24

默认网关：192.168.1.1

当主机 A 向 B 发送数据：192.168.1.10 → 192.168.1.20
两台主机处于相同子网中，在常见以太网环境下，A 可以通过 ARP 获取 B 的 MAC 地址，并在本地链路发送数据，不必经过默认网关转发。

如果主机 A 访问：8.8.8.8
目标不在当前子网内，主机通常会根据路由表，选择默认网关 192.168.1.1 作为下一跳

IP 数据包的目标地址依然是 8.8.8.8，而当前以太网帧的目标 MAC 地址通常是默认网关的 MAC
```

## ARP 协议（Address Resolution Protocol）

ARP负责在 IPv4 局域网中，把下一跳 IPv4 地址解析为对应的链路层 MAC 地址

```
我要找 192.168.1.1
↓
ARP 查询
↓
获得网关 MAC 地址
↓
构造以太网帧
↓
交给网关
```

IPv6 不使用 ARP，而是通过 ICMPv6 的 Neighbor Discovery等机制完成类似工作

## 路由

当一个 IP 数据包要去往其他网络时，应该从哪个网络接口发出，并交给哪个下一跳？

```
目标网络            下一跳
192.168.1.0/24     本地网卡
10.0.0.0/8         192.168.1.254
0.0.0.0/0          192.168.1.1

目标 IP	匹配路由
192.168.1.20	本地直连网络
10.2.3.4	下一跳 192.168.1.254
8.8.8.8	默认网关 192.168.1.1
```

当服务器访问 `10.10.2.5` 失败时，并不能直接认定对方服务宕机。首先需要弄清楚：目标位于哪个网段？路由表会选择哪条路径？安全策略是否允许访问？返回的数据包能否回到源主机？



# TCP

## tcp与udp的区别

TCP（Transmission Control Protocol）是传输层协议，特点是：

- 面向连接。
- 提供可靠、有序的字节流传输。
- 具备确认、重传、流量控制和拥塞控制机制。
- 不保留应用层消息边界。

用于：SSH、HTTP/1.1、HTTP/2

UDP（User Datagram Protocol）也是传输层协议，但它不提供 TCP 那样的连接管理和可靠传输保证。

用于：DNS、实时通信、QUIC

## 三次握手

TCP 三次握手的主要目的是：

1. 双方确认连接建立所需的通信信息。
2. 交换并确认初始序列号。
3. 协商 TCP 连接参数，例如 MSS、窗口扩大选项、SACK 支持等。
4. 建立双方的连接状态。

#### 第一次握手

```
客户端向服务器发送：
Flags: SYN(Synchronize)
Seq: x
====>我希望与你建立 TCP 连接，这是我选择的初始序列号 x

客户端进入 SYN_SENT 状态。
服务端如果正在监听目标端口，就可以处理这个 SYN。
```

#### 第二次握手

```
服务器返回：
Flags: SYN, ACK
Seq: y
Ack: x + 1
====>我收到了你的 SYN，也同意建立连接。我的初始序列号是 y，接下来期望收到你的序列号 x+1

此时服务器处于 SYN_RECV 状态。
```

#### 第三次握手

```
客户端返回：
Flags: ACK（Acknowledgment Number,表示接收方下一步期望收到的字节序列号）
Seq: x + 1		（Sequence Number,表示当前 TCP 报文段中数据的序列位置）
Ack: y + 1
====>我收到了你的 SYN，并确认你的初始序列号。连接可以建立。

客户端发送第三次握手的 ACK 后，进入 ESTABLISHED 状态；服务器在收到有效的第三次握手后也进入 ESTABLISHED。
此后双方就可以传输应用数据。
```

#### 建立连接后

```
连接建立后，客户端发送 100 字节数据
Seq = 1001
数据长度 = 100 字节

服务器收到连续的这 100 字节后可以回复：
ACK = 1101

序列号 1001～1100 的字节已经收到，下一步希望收到序列号为 1101 的字节
```

#### 为什么是三次握手，而不是两次？

三次握手的关键是：双方都需要交换自己的初始序列号，并获得对方的确认。

第一次握手：客户端告诉服务端自己的初始序列号。

第二次握手：服务端确认客户端的序列号，同时告诉客户端自己的序列号。

第三次握手：客户端确认服务端的序列号。

如果只有前两次，服务端还无法确认客户端是否成功接收自己的 SYN。

第三次握手能帮助双方正确建立和同步连接状态，避免一些旧报文、丢包等情况下出现的状态问题。

## 四次挥手

#### 第一次挥手：客户端发送 FIN

```
我已经没有更多数据要发送给你了。
客户端进入 FIN_WAIT_1。
```

#### 第二次挥手：服务器返回 ACK

```
我知道你不再发送数据了。
客户端收到 ACK 后通常进入 FIN_WAIT_2。
服务器进入 CLOSE_WAIT，此时仍然可能继续向客户端发送剩余数据。
```

#### 第三次挥手：服务器发送 FIN

```
当服务器也准备结束自己的发送方向时，会发送 FIN。
服务器进入 LAST_ACK。
(服务器可能将第二次的 ACK 与自己的 FIN 合并发送)
```

#### 第四次挥手：客户端返回 ACK

```
客户端确认收到服务器的 FIN，进入 TIME_WAIT。
服务器收到 ACK 后，连接关闭。
```

#### 为什么需要 TIME_WAIT？

`TIME_WAIT` 是 TCP 排障中非常常见的状态。

主动关闭连接的一方通常进入 `TIME_WAIT`，并在经典 TCP 语义下等待约 `2 × MSL`(报文段最大生存时间)。

TIME_WAIT 有两个主要作用：

1. 允许主动关闭方在对方重传 FIN 时再次回复 ACK。
2. 降低旧连接中延迟报文干扰后续相同四元组连接的风险。

因此：

看到 TIME_WAIT 并不一定是故障。

例如，高并发短连接业务产生大量 TIME_WAIT 连接是常见现象。

真正需要关注的是它们是否与端口资源紧张、连接频繁创建、性能下降等问题相关。



```
机制	保护对象	主要目标
流量控制	接收方	不要把接收方缓冲区撑满
拥塞控制	网络	不要把网络传输路径压垮
```

### TCP常见状态

| LISTEN      | 等待新的连接请求                 | 服务是否正常监听端口                         |
| ----------- | -------------------------------- | -------------------------------------------- |
| SYN_SENT    | 已发送 SYN，等待响应             | 连接可能正在建立或遇到超时                   |
| SYN_RECV    | 收到 SYN，等待握手完成           | 大量出现时关注建连压力、丢包或异常流量       |
| ESTABLISHED | TCP 连接已经建立                 | 连接存在，但不代表应用业务正常               |
| FIN_WAIT_1  | 主动发送 FIN，等待确认           | 正在关闭连接                                 |
| FIN_WAIT_2  | 本端 FIN 已被确认，等待对方 FIN  | 对端尚未完成关闭                             |
| CLOSE_WAIT  | 已收到对端 FIN，等待本地应用关闭 | 长时间、大量积累需要关注应用是否正确释放连接 |
| LAST_ACK    | 本端已发送 FIN，等待最后 ACK     | 正在完成关闭                                 |
| TIME_WAIT   | 主动关闭方等待旧连接报文消退     | 短连接场景较常见                             |
| CLOSING     | 双方几乎同时发起关闭             | 相对少见                                     |
| CLOSED      | 连接已关闭                       | 不再是活动 TCP 连接                          |

#### ESTABLISHED:连接建立了，不等于应用正常

```
客户端 ↔ Nginx：ESTABLISHED

这只能说明 TCP 连接已经建立。
Nginx 仍然可能：
- 没有及时处理 HTTP 请求。
- 正在等待后端服务。
- 后端数据库响应缓慢。
- 因内部错误无法返回正常页面。
```

#### CLOSE_WAIT：对方已经关闭，自己还没有关闭

```
客户端发送 FIN
       ↓
服务器 TCP 内核收到 FIN
       ↓
服务器回复 ACK
       ↓
服务器进入 CLOSE_WAIT
       ↓
等待应用调用 close() 等操作

如果应用程序一直不关闭对应 Socket，连接就可能长期停留在 CLOSE_WAIT。
当在生产环境发现大量持续不消失的 CLOSE_WAIT 时，可以重点检查：
- 应用是否忘记关闭连接。
- 是否有异常分支没有释放网络资源。
- 应用是否卡住，不能完成关闭流程。
```

#### TIME_WAIT：正常的 TCP 关闭保护机制

```
主动关闭连接的一方通常进入 TIME_WAIT。
Nginx 主动关闭大量短连接
       ↓
服务器上出现很多 TIME_WAIT

这可能完全正常。
如果大量 TIME_WAIT 同时伴随端口资源耗尽或请求失败，则应结合连接复用、端口使用及请求模式一起分析。
```



# 网络超时

```
问题							发生阶段									典型表现
DNS 解析失败		建立目标 TCP 连接之前				无法解析域名
连接超时				TCP 建连阶段							长时间未成功建立连接
连接拒绝				TCP 建连阶段							目标明确拒绝连接，常见于收到 RST
TLS 握手失败		TCP 建连之后							证书错误、协议不兼容或握手失败
读取超时				连接已建立之后							一段时间未收到预期响应数据
连接重置				连接交互过程中							收到 RST，连接被异常终止
```

连接超时Connection Timed Out）可能原因：

- 防火墙或安全组丢弃了连接请求。
- 目标 IP 不可达。
- 路由配置错误。
- 目标机器宕机或网络不通。
- SYN 或 SYN-ACK 丢失。

连接拒绝（Connection Refused）

目标主机可达，但这个端口没有服务监听，操作系统可能返回 TCP RST。

读取超时（Read Timeout）

```
客户端 → Nginx：TCP 建连成功
客户端 → Nginx：GET /api
Nginx → 后端服务：请求已转发
后端服务：数据库查询卡住
客户端：长时间等待
```



# DNS

传统 DNS 查询通常使用 UDP 53 端口，但 DNS 也支持 TCP 53。

TCP 可能用于：

- 某些响应过大或 UDP 响应被截断的场景。
- DNS 区域传送。
- 其他需要 TCP 的 DNS 通信。

另外，现代 DNS 还有加密传输方式：

- DoT（DNS over TLS）：通常使用 TCP 853。
- DoH（DNS over HTTPS）：通常通过 HTTPS，使用 443 端口。
- DoQ（DNS over QUIC）：基于 QUIC。

# HTTP

HTTP 的主要特点包括：

- 请求与响应模型。
- 使用请求方法、URL、Header、Body 等组织信息。
- 协议本身是无状态的。
- 可以利用 Cookie、Session、Token 等技术维持应用会话。



安全方法（Safe Method）

例如 GET、HEAD，语义上用于读取，不应该主动改变服务器的业务状态。

幂等方法（Idempotent Method）

同样的请求重复执行多次，其预期业务效果与执行一次相同。



DELETE 通常也被定义为幂等方法，虽然第二次删除的响应码可能与第一次不同。

POST 则一般不保证幂等。

网络超时后客户端可能进行请求重试。如果把非幂等操作直接重复执行，就可能产生重复下单、重复扣款等问题。



# TLS

```
客户端                              服务器
   |                                   |
   |--------- ClientHello ----------->|
   |  支持的 TLS 版本                  |
   |  加密算法、密钥交换信息           |
   |                                   |
   |<-------- ServerHello ------------|
   |  选择的参数、密钥交换信息         |
   |                                   |
   |<---- 加密的服务器认证消息 --------|
   |  Certificate                      |
   |  CertificateVerify                |
   |  Finished                         |
   |                                   |
   |------ 客户端 Finished ---------->|
   |                                   |
   |======= 加密应用数据传输 =========|
   

1. 客户端提出支持的协议版本、加密套件和密钥交换参数。
2. 服务端选择相应参数，双方建立握手密钥。
3. 服务端提供证书并证明自己拥有相应密钥。
4. 客户端验证证书链、域名及其他安全条件。
5. 双方确认握手完成，开始使用协商出的密钥保护 HTTP 数据。
```

```
证书已经过期
证书域名不匹配
证书链配置错误
客户端与服务器 TLS 协议不兼容
反向代理的 TLS 配置错误

当 https:// 访问失败时，需要分清楚究竟是 TCP 失败、TLS 失败，还是 HTTP 处理失败。
```



# dig

```
dig [@DNS服务器] 域名 [记录类型] [选项]

dig @1.1.1.1 example.com A
dig	执行 DNS 查询
@1.1.1.1	指定 Cloudflare 公共 DNS 服务器
example.com	要查询的域名
A	查询 IPv4 地址记录

最简单的查询
dig example.com
只查看解析结果
dig example.com +short
指定 DNS 服务器
dig @8.8.8.8 example.com
假设在腾讯云服务器上发现某个域名解析结果异常,比较不同解析器的返回结果
dig example.com
dig @1.1.1.1 example.com
dig @8.8.8.8 example.com

示例输出：
;; ->>HEADER<<- opcode: QUERY,
;; status: NOERROR, id: 12345
;; flags: qr rd ra; QUERY: 1,
;; ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; QUESTION SECTION:
;www.example.com.       IN  A

;; ANSWER SECTION:
www.example.com. 300 IN A 192.0.2.10

;; Query time: 24 msec
;; SERVER: 192.168.1.1#53(UDP)
;; MSG SIZE  rcvd: 60

HEADER：DNS 响应头
NOERROR	DNS 查询处理成功	不代表一定有需要的记录
NXDOMAIN	被查询的域名不存在	可能是拼写、配置或域名问题
SERVFAIL	DNS 服务器无法完成查询	可能是上游解析、DNSSEC 等问题
REFUSED	DNS 服务器拒绝执行查询	可能是权限或查询策略限制
FORMERR	DNS 查询报文格式错误	查询报文无法被正确处理

flags：DNS 标志位
qr	这是一个响应报文
rd	客户端请求递归查询
ra	服务器表示支持递归查询
aa	权威回答标志
tc	DNS 响应被截断
ad	DNSSEC 相关数据已获验证的标志

QUESTION SECTION：查询的问题
ANSWER SECTION：DNS 回答

Query time 与 SERVER
Query time: 24 msec 表示本次 DNS 查询耗费约 24 毫秒。
SERVER 表示实际响应本次 dig 查询的 DNS 服务器地址和端口。

+short	简洁输出	dig example.com +short
+noall +answer	只显示回答记录	dig example.com +noall +answer
@server	指定 DNS 服务器	dig @1.1.1.1 example.com
+trace	跟踪 DNS 委派解析过程	dig example.com +trace
+tcp	使用 TCP 进行 DNS 查询	dig example.com +tcp
-x	反向 DNS 查询	dig -x 8.8.8.8
+timeout=2	设置单次查询等待时间	dig example.com +timeout=2
+tries=1	设置查询尝试次数	dig example.com +tries=1
-4 / -6	限制 DNS 查询的传输使用 IPv4/IPv6	dig -4 example.com
```



# tcpdump

```
基本语法
sudo tcpdump [选项] [过滤表达式]

sudo tcpdump -i any -nn 'tcp port 80'
- -i any：从系统支持的常规网络接口捕获数据包。
- -nn：不将 IP 转换为域名，也不将端口转换为服务名称。
- 'tcp port 80'：只捕获 TCP 80 端口相关的数据包。
```

```
重要的参数
参数									作用													示例
-i									指定抓包接口											-i eth0
-D									列出可用抓包接口									tcpdump -D
-n									不解析 IP 对应的主机名							-n
-nn									同时禁止主机名和端口服务名解析				-nn
-c									捕获指定数量的数据包后退出						-c 20
-v、-vv、-vvv					显示更多协议细节									-vv
-A									以 ASCII 形式显示数据内容						-A
-X									以十六进制和 ASCII 显示内容						-X
-s									设置每个数据包捕获的最大字节数					-s 0
-w									将原始数据包保存到文件								-w test.pcap
-r									读取保存的抓包文件									-r test.pcap
-tttt								显示可读的完整日期和时间						-tttt
-S									显示绝对 TCP 序列号								-S
```

## 过滤表达式

### 根据 IP 地址过滤

```
只观察某个 IP 相关的流量：
sudo tcpdump -i any -nn 'host 203.0.113.10'
这个过滤条件匹配源地址或目的地址为该 IP 的数据包

只观察该 IP 发出的数据包
sudo tcpdump -i any -nn 'src host 203.0.113.10'

只观察发往该 IP 的数据包：
sudo tcpdump -i any -nn 'dst host 203.0.113.10'

- src：源地址。
- dst：目的地址。
- host：主机地址。
```

### 根据端口过滤

```
抓取 80 端口相关流量：
sudo tcpdump -i any -nn 'port 80'

抓取 TCP 443：
sudo tcpdump -i any -nn 'tcp port 443'

抓取 UDP 53：
sudo tcpdump -i any -nn 'udp port 53'

只抓目的端口为 8080 的 TCP 流量：
sudo tcpdump -i any -nn 'tcp dst port 8080'

抓取指定端口范围：
sudo tcpdump -i any -nn 'tcp portrange 8000-9000'
```

### 据协议过滤

```
只捕获 TCP：
sudo tcpdump -i any -nn tcp
只捕获 UDP：
sudo tcpdump -i any -nn udp
只捕获 IPv4 ICMP：
sudo tcpdump -i any -nn icmp
只捕获 ARP：
sudo tcpdump -i any -nn arp
```

### 组合条件：and、or、not

```
只捕获与指定 IP 和 TCP 443 端口相关的数据包
sudo tcpdump -i any -nn 'host 203.0.113.10 and tcp port 443'
表示抓取 TCP 80 或 443 的流量
sudo tcpdump -i any -nn 'tcp port 80 or tcp port 443'
排除 SSH 端口：
sudo tcpdump -i any -nn 'tcp and not port 22'

sudo tcpdump -i any -nn 'host 203.0.113.10 and (tcp port 80 or tcp port 443)'
```

## TCP 抓包输出

```
sudo tcpdump -i any -nn 'tcp port 80'
====>
10:00:00.100 IP 192.0.2.10.50000 >
203.0.113.10.80: Flags [S],
seq 1000, length 0

10:00:00.120 IP 203.0.113.10.80 >
192.0.2.10.50000: Flags [S.],
seq 2000, ack 1001, length 0

10:00:00.130 IP 192.0.2.10.50000 >
203.0.113.10.80: Flags [.],
ack 2001, length 0

tcpdump 输出	TCP 标志	含义
[S]	SYN	请求建立连接
[S.]	SYN + ACK	同步序列号并确认对方 SYN
[.]	ACK	确认信息
[P.]	PSH + ACK	常见于携带数据的报文
[F.]	FIN + ACK	发送方向准备关闭
[R]	RST	重置连接
[R.]	RST + ACK	重置连接并带有确认标志
```

## 过滤 TCP 标志位

如果一台服务器有几千条 TCP 连接，只想观察新的连接请求，可以根据 TCP Flags 过滤。

```
只看 SYN 发起连接的报文
sudo tcpdump -i any -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) == tcp-syn'
SYN 位被设置，并且 ACK 位没有被设置
tcp[tcpflags]代表访问 TCP 首部的标志位字段
& 表示按位与操作
tcp-syn|tcp-ack 表示构造 SYN 与 ACK 的标志掩码

只看 SYN-ACK 报文
sudo tcpdump -i any -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) == (tcp-syn|tcp-ack)'
要求 SYN 和 ACK 位同时为 1。
这个过滤表达式可以帮助判断服务器是否返回 SYN-ACK。

只观察 RST
sudo tcpdump -i any -nn 'tcp[tcpflags] & tcp-rst != 0'
RST 通常与连接拒绝、连接重置等场景相关

只观察 FIN
sudo tcpdump -i any -nn 'tcp[tcpflags] & tcp-fin != 0'
用于观察 TCP 连接正常关闭过程中的 FIN

只观察 ACK
sudo tcpdump -i any -nn 'tcp[tcpflags] & tcp-ack != 0'
这个命令确实能抓取 ACK 标志被设置的报文。但它无法只抓第三次握手。
建立连接之后，大量正常 TCP 数据报文也携带 ACK 标志。

要确认第三次握手，需要结合：
- 连接的源 IP、目标 IP、源端口、目标端口。
- 前面的 SYN、SYN-ACK。
- Seq、Ack。
- 报文的时间顺序。
```

# 实战一：使用 tcpdump 观察 DNS 查询

```
第一步：启动 DNS 抓包
打开终端 A：
sudo tcpdump -i any -nn 'udp port 53 or tcp port 53'
同时观察 UDP 和 TCP 的 53 端口流量

第二步：触发 DNS 查询
打开终端 B：
dig @1.1.1.1 example.com A

第三步：观察 DNS over TCP
dig @1.1.1.1 example.com A +tcp

18:45:04.755971 eth0  Out IP 10.0.0.2.51341 > 1.1.1.1.53: 40627+ [1au] A? baidu.com. (50)
18:45:04.823285 eth0  In  IP 1.1.1.1.53 > 10.0.0.2.51341: 40627 4/0/1 A 110.242.74.102, A 111.63.65.247, A 111.63.65.103, A 124.237.177.164 (102)

18:45:45.278760 eth0  Out IP 10.0.0.2.50023 > 1.1.1.1.53: Flags [S], seq 479675985, win 64660, options [mss 1220,sackOK,TS val 414256172 ecr 0,nop,wscale 9], length 0
18:45:45.353059 eth0  In  IP 1.1.1.1.53 > 10.0.0.2.50023: Flags [S.], seq 1622438615, ack 479675986, win 65535, options [mss 1424,sackOK,TS val 3388855794 ecr 414256172,nop,wscale 13], length 0
18:45:45.353104 eth0  Out IP 10.0.0.2.50023 > 1.1.1.1.53: Flags [.], ack 1, win 127, options [nop,nop,TS val 414256247 ecr 3388855794], length 0
18:45:45.353178 eth0  Out IP 10.0.0.2.50023 > 1.1.1.1.53: Flags [P.], seq 1:53, ack 1, win 127, options [nop,nop,TS val 414256247 ecr 3388855794], length 52 2874+ [1au] A? baidu.com. (50)
18:45:45.428180 eth0  In  IP 1.1.1.1.53 > 10.0.0.2.50023: Flags [.], ack 53, win 16, options [nop,nop,TS val 3388855869 ecr 414256247], length 0
18:45:45.428965 eth0  In  IP 1.1.1.1.53 > 10.0.0.2.50023: Flags [P.], seq 1:105, ack 53, win 16, options [nop,nop,TS val 3388855870 ecr 414256247], length 104 2874 4/0/1 A 110.242.74.102, A 124.237.177.164, A 111.63.65.247, A 111.63.65.103 (102)
18:45:45.428988 eth0  Out IP 10.0.0.2.50023 > 1.1.1.1.53: Flags [.], ack 105, win 127, options [nop,nop,TS val 414256323 ecr 3388855870], length 0
18:45:45.429713 eth0  Out IP 10.0.0.2.50023 > 1.1.1.1.53: Flags [F.], seq 53, ack 105, win 127, options [nop,nop,TS val 414256323 ecr 3388855870], length 0
18:45:45.504718 eth0  In  IP 1.1.1.1.53 > 10.0.0.2.50023: Flags [F.], seq 105, ack 54, win 16, options [nop,nop,TS val 3388855945 ecr 414256323], length 0
18:45:45.504767 eth0  Out IP 10.0.0.2.50023 > 1.1.1.1.53: Flags [.], ack 106, win 127, options [nop,nop,TS val 414256398 ecr 3388855945], length 0
```

# 实战二：完整观察 TCP 三次握手与 HTTP 请求

```
sudo tcpdump -i lo -nn -s 0 -A 'tcp port 8000'
-i lo          只捕获回环接口
-nn            不解析名称
-s 0           使用足够大的捕获长度
-A             以 ASCII 显示负载内容
tcp port 8000  过滤 TCP 8000 端口

curl --http1.1 --noproxy '*' -v http://127.0.0.1:8000/
- --http1.1：明确使用 HTTP/1.1。
- --noproxy '*'：避免系统代理影响这个本机实验。
- -v：显示请求和响应的详细信息。
```

# 保存抓包文件

```
sudo tcpdump -i lo -nn -s 0 -w /tmp/http-test.pcap 'tcp port 8000'

sudo tcpdump -nn -r /tmp/http-test.pcap
查看 ASCII 负载：
sudo tcpdump -nn -A -r /tmp/http-test.pcap
```

