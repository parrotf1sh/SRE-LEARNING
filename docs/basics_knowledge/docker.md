# docker

## docker的基本组成

镜像（image）、容器（container）、仓库（repository）

# 常用命令

## 镜像命令

```
# 列出本地主机上的镜像
docker images
-a 含历史
-q 只显示镜像id

# 搜索镜像
docker search 镜像名
--limit N 只列出N个镜像

# 拉去镜像
docker pull 镜像名[:TAG]

# 查看镜像容器数据卷所占空间
docker system df

# 删除镜像
docker rmi 镜像名
删除全部 $(docker images -qa)
```

## 容器命令

```
# 新建 + 启动容器
docker run [options] IMAGE [command] [arg...]
--name 容器新名字
-d 后台运行
-i 交互式运行容器
-t 为容器重新分配一个伪输入终端=====> 一般一起使用 -it
-P 随机端口映射
-p 宿主机暴露端口:docker暴露端口 指定端口映射

# 列出当前所有正在运行的容器
docker ps [options]
-a 包含历史运行过的
-l 最新创建的
-n num 最近num个
-q 静默模式，只显示容器编号

# 退出容器
exit：run进去容器，exit退出，容器停止
ctrl+p+q：run进去容器，ctrl+p+q，容器不停止

# 启动已经停止运行的容器
docker start 容器id或容器名
# 重启
docker restart 容器id或容器名
# 停止
docker stop 容器id或容器名
# 强制停止
docker kill 容器id或容器名

# 删除已停止的容器
docker rm 容器ID或容器名

# 查看容器日志
docker logs 容器ID或容器名

# 查看容器内运行的进程
docker top 容器ID或容器名

# 查看容器内部细节
docker inspect 容器ID或容器名

# 进入正在运行的容器
docker exec -it 容器ID bashShell			# 更推荐此方式
docker attach 容器ID
# attach直接进入容器启动命令的终端，不会启动新的进程。用exit退出，会导致容器的停止
# exec是在容器中打开新的终端，并且可以启动新的进程。用exit退出，不会导致容器停止

# 从容器内拷贝文件到主机上
docker cp 容器ID:容器内路径 目的主机路径

# 导入和导出容器
# export 导出容器的内容留作为一个tar归档文件
# import 从tar包中的内容创建一个新的文件系统再导入为镜像
docker export 容器ID > 文件名.tar
cat 文件名.tar | docker import -镜像用户/镜像名：镜像版本号
```

 ## 镜像commit操作

```
提交容器副本使之成为一个新的镜像
docker commit -m=“提交的描述信息” -a=“作者” 容器ID 要创建的目标镜像名:[标签名]
```

## 私有库

```
下载镜像registry

docker run -d -p 5000:5000 -v /fish/myregistry/:/tmp/registry --privileged=ture registry
默认情况，仓库被创建在容器的/var/lib/registry目录下，使用容器卷映射，方便宿主机联调

curl -XGET http://192.168.111.162:5000/v2/_catalog

docker tag fishubuntu:1.1 192.168.111.162:5000/fishubuntu:1.1

"insecure-registries":["192.168.111.162:5000"]

docker push 192.168.111.162:5000/fishubuntu:1.1

docker pull 192.168.111.162:5000/fishubuntu:1.1
```

## 容器数据卷

```
docker run -it -v /宿主机绝对路径:/容器内目录 --privileged=ture 镜像名

# 容器对数据卷可读可写 默认就是rw
docker run -it -v /宿主机绝对路径:/容器内目录:rw --privileged=ture 镜像名
# 容器只读read only
docker run -it -v /宿主机绝对路径:/容器内目录:ro --privileged=ture 镜像名

# 容器继承数据卷
docker run -it --privileged=ture --volumes-from 父类(容器名) 镜像名
```

## mysql

```
docker run -d -p 3306:3306 --privileged=ture \
	-v /fish/mysql/log:/var/log/mysql \
	-v /fish/mysql/data:/var/lib/mysql \
	-v /fish/mysql/conf:/etc/mysql/conf.d \
	-e MYSQL_ROOT_PASSWORD=123456 \
	--name=mtsql mysql:5.7

# 解决中文乱码
# 在conf目录下添加my.cnf
[client]
default_character_set=utf8
[mysqld]
collation_server = utf8_general_ci
character_set_server = utf8
```

## redis

```
将redis.conf文件模版拷贝进/app/redis目录下
1）开启redis验证（可选）
requirepass 123
2）允许redis外地连接（必须）
注释掉 # bind 127.0.0.1
3）daemonize no （必须）
4）redis数据持久化（可选）
appendonly yes

docker run -d -p 6379:6379 --privileged=ture \
	-v /app/redis/redis.conf:/etc/redis/redis.conf \
	-v /app/redis/data:/data \
	--name=myr3 redis:6.0.8 redis-server /etc/redis/redis.conf
```

# 复杂安装

## mysql主从复制（一主一从）

```
1)主服务器容器实例
2）进入/mydata/mysql-master/conf目录下新建my.cnf
[mysqld]
## 设置server_id，同一局域网中需要唯一
server_id=101 
## 指定不需要同步的数据库名称
binlog-ignore-db=mysql  
## 开启二进制日志功能
log-bin=mall-mysql-bin  
## 设置二进制日志使用内存大小（事务）
binlog_cache_size=1M  
## 设置使用的二进制日志格式（mixed,statement,row）
binlog_format=mixed  
## 二进制日志过期清理时间。默认值为0，表示不自动清理。
expire_logs_days=7  
## 跳过主从复制中遇到的所有错误或指定类型的错误，避免slave端复制中断。
## 如：1062错误是指一些主键重复，1032错误是因为主从数据库数据不一致
slave_skip_errors=1062

3)master容器实例内创建数据同步用户
CREATE USER 'slave'@'%' IDENTIFIED BY '123456';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'slave'@'%';

4)从服务器容器实例
5)/mydata/mysql-slave/conf目录下新建my.cnf
[mysqld]
## 设置server_id，同一局域网中需要唯一
server_id=102
## 指定不需要同步的数据库名称
binlog-ignore-db=mysql  
## 开启二进制日志功能，以备Slave作为其它数据库实例的Master时使用
log-bin=mall-mysql-slave1-bin  
## 设置二进制日志使用内存大小（事务）
binlog_cache_size=1M  
## 设置使用的二进制日志格式（mixed,statement,row）
binlog_format=mixed  
## 二进制日志过期清理时间。默认值为0，表示不自动清理。
expire_logs_days=7  
## 跳过主从复制中遇到的所有错误或指定类型的错误，避免slave端复制中断。
## 如：1062错误是指一些主键重复，1032错误是因为主从数据库数据不一致
slave_skip_errors=1062  
## relay_log配置中继日志
relay_log=mall-mysql-relay-bin  （自己写）
## log_slave_updates表示slave将复制事件写进自己的二进制日志
log_slave_updates=1  
## slave设置为只读（具有super权限的用户除外）
read_only=1

6)在主mysql容器实例
show master status;
7）在从mysql容器
change master to master_host='宿主机ip', master_user='slave', master_password='123456', 
master_port=3307, master_log_file='mall-mysql-bin.000001', master_log_pos=617, master_connect_retry=30;
# master_host：主数据库的IP地址；
# master_port：主数据库的运行端口；
# master_user：在主数据库创建的用于同步数据的用户账号；
# master_password：在主数据库创建的用于同步数据的用户密码；
# master_log_file：指定从数据库要复制数据的日志文件，通过查看主数据的状态，获取File参数；
# master_log_pos：指定从数据库从哪个位置开始复制数据，通过查看主数据的状态，获取Position参数；
# master_connect_retry：连接失败重试的时间间隔，单位为秒。

# 在从数据库中查看主从同步状态
show slave status \G;
# 在从数据库中开启主从同步
start slave;
```



## redis集群（三主三从，扩容，缩容）

cluster（集群）模式 哈希槽分区进行亿级数据存储

单机单台是不可能的，必定使用分布式存储

三种解决方案：

**1）哈希取余分区**

hash(key) % N个机器台数，计算出哈希值，用来决定数据映射到哪一个节点上。

优点：

简单粗暴，直接有效，只需要预估好数据规划好节点，例如3台、8台、10台，就能保证一段时间的数据支撑。使用Hash算法让固定的一部分请求落到同一台服务器上，这样每台服务器固定处理一部分请求（并维护这些请求的信息），起到负载均衡+分而治之的作用。

缺点：

原来规划好的节点，进行扩容或者缩容就比较麻烦，不管扩缩，每次数据变动导致节点有变动，映射关系需要重新进行计算，在服务器个数固定不变时没有问题，如果需要弹性扩容或故障停机的情况下，原来的取模公式就会发生变化：Hash(key)/3会变成Hash(key) /?。此时地址经过取余运算的结果将发生很大变化，根据公式获取的服务器也会变得不可控。

某个redis机器宕机了，由于台数数量变化，会导致hash取余全部数据重新洗牌。

**2）一致性哈希算法分区**

　　一致性哈希算法在1997年由麻省理工学院中提出的，设计目标是为了解决分布式缓存数据变动和映射问题，某个机器宕机了，分母数量改变了，自然取余数不行了。

====>提出一致性Hash解决方案。 目的是当服务器个数发生变动时， 尽量减少影响客户端到服务器的映射关系

​	3大步骤:

​	a.算法构建一致性哈希环

​	一致性哈希算法必然有个hash函数并按照算法产生hash值，这个算法的所有可能哈希值会构成一个全量集，这个集合可以成为一个hash空间[0,2^32-1]，这个是一个线性空间，但是在算法中，我们通过适当的逻辑控制将它首尾相连(0 = 2^32),这样让它逻辑上形成了一个环形空间。

​	它也是按照使用取模的方法，前面笔记介绍的节点取模法是对节点（服务器）的数量进行取模。而一致性Hash算法是对2^32取模，简单来说，一致性Hash算法将整个哈希值空间组织成一个虚拟的圆环，如假设某哈希函数H的值空间为0-2^32-1（即哈希值是一个32位无符号整形），整个哈希环如下图：整个空间按顺时针方向组织，圆环的正上方的点代表0，0点右侧的第一个点代表1，以此类推，2、3、4、……直到2^32-1，也就是说0点左侧的第一个点代表2^32-1， 0和2^32-1在零点中方向重合，我们把这个由2^32个点组成的圆环称为Hash环。

​	b.服务器IP节点映射

​	将集群中各个IP节点映射到环上的某一个位置。

​	将各个服务器使用Hash进行一个哈希，具体可以选择服务器的IP或主机名作为关键字进行哈希，这样每台机器就能确定其在哈希环上的位置。

​	c.key落到服务器的落键规则

​	当我们需要存储一个kv键值对时，首先计算key的hash值，hash(key)，将这个key使用相同的函数Hash计算出哈希值并确定此数据在环上的位置，从此位置沿环顺时针“行走”，第一台遇到的服务器就是其应该定位到的服务器，并将该键值对存储在该节点上。

​	如我们有Object A、Object B、Object C、Object D四个数据对象，经过哈希计算后，在环空间上的位置如下：根据一致性Hash算法，数据A会被定为到Node A上，B被定为到Node B上，C被定为到Node C上，D被定为到Node D上。



容错性

假设Node C宕机，可以看到此时对象A、B、D不会受到影响，只有C对象被重定位到Node D。一般的，在一致性Hash算法中，如果一台服务器不可用，则受影响的数据仅仅是此服务器到其环空间中前一台服务器（即沿着逆时针方向行走遇到的第一台服务器）之间数据，其它不会受到影响。简单说，就是C挂了，受到影响的只是B、C之间的数据，并且这些数据会转移到D进行存储。

扩展性

数据量增加了，需要增加一台节点NodeX，X的位置在A和B之间，那收到影响的也就是A到X之间的数据，重新把A到X的数据录入到X上即可，不会导致hash取余全部数据重新洗牌。

数据倾斜问题

一致性Hash算法在服务节点太少时，容易因为节点分布不均匀而造成数据倾斜（被缓存的对象大部分集中缓存在某一台服务器上）问题，例如系统中只有两台服务器，数据的分布和节点的位置有关，因为这些节点不是均匀的分布在哈希环上的，所以数据在进行存储时达不到均匀分布的效果。

**3）哈希槽分区**

​	哈希槽实质就是一个数组，数组[0,2^14 -1]形成hash slot空间。

​	解决均匀分配的问题，在数据和节点之间又加入了一层，把这层称为哈希槽（slot），用于管理数据和节点之间的关系，现在就相当于节点上放的是槽，槽里放的是数据。槽解决的是粒度问题，相当于把粒度变大了，这样便于数据移动。哈希解决的是映射问题，使用key的哈希值来计算所在的槽，便于数据分配。

​	一个集群只能有16384个槽，编号0-16383（0-2^14-1）。这些槽会分配给集群中的所有主节点，分配策略没有要求。可以指定哪些编号的槽分配给哪个主节点。集群会记录节点和槽的对应关系。解决了节点和槽的关系后，接下来就需要对key求哈希值，然后对16384取余，余数是几key就落入对应的槽里。slot = CRC16(key) % 16384。以槽为单位移动数据，因为槽的数目是固定的，处理起来比较容易，这样数据移动问题就解决了。

​	Redis 集群中内置了 16384 个哈希槽，redis 会根据节点数量大致均等的将哈希槽映射到不同的节点。当需要在 Redis 集群中放置一个 key-value时，redis 先对 key 使用 crc16 算法算出一个结果，然后把结果对 16384 求余数，这样每个 key 都会对应一个编号在 0-16383 之间的哈希槽，也就是映射到某个节点上。

```
0-16383
此时有三台redis节点
0-16383=====>砍成三段=====>0-5460/5461-10992/10993-16383
比如A的取余的值为6373，落在第二个槽内====>就被分到第二个节点
```

### 实际架构

```
master1				master1				master1
6381
```

| Master1<br />6381 | Master2<br />6382 | Master3<br />6383 |
| ----------------- | ----------------- | ----------------- |
|                   |                   |                   |
| Slave1<br />6385  | Slave2<br />6386  | Slave3<br />6384  |

```
# 新建6个docker容器实例
docker run --name redis-node-1 --net host --privileged=true -v /data/redis/share/redis-node-1:/data redis:6.0.8 --cluster-enabled yes appendonly yes --port 6381

docker run --name redis-node-2 --net host --privileged=true -v /data/redis/share/redis-node-2:/data redis:6.0.8 --cluster-enabled yes appendonly yes --port 6382

docker run --name redis-node-3 --net host --privileged=true -v /data/redis/share/redis-node-3:/data redis:6.0.8 --cluster-enabled yes appendonly yes --port 6383

docker run --name redis-node-4 --net host --privileged=true -v /data/redis/share/redis-node-4:/data redis:6.0.8 --cluster-enabled yes appendonly yes --port 6384

docker run --name redis-node-5 --net host --privileged=true -v /data/redis/share/redis-node-5:/data redis:6.0.8 --cluster-enabled yes appendonly yes --port 6385

docker run --name redis-node-6 --net host --privileged=true -v /data/redis/share/redis-node-6:/data redis:6.0.8 --cluster-enabled yes appendonly yes --port 6386

# 进入容器redis-node-1并为6台机器构建集群关系
docker exec -it redis-node-1 /bin/bash

# 构建主从关系
redis-cli --cluster create 192.168.?.?:6381 192.168.?.?:6382 192.168.?.?:6383 192.168.?.?:6384 192.168.?.?:6385 192.168.?.?:6386 --cluster-replicas 1
# --cluster-replicas 1  表示为每一个master创建一个slave节点

# 连接6381，查看节点状态  redis-cli -p 6381
cluster info
cluster nodes
```

#### 主从容错切换迁移

##### 数据读写存储

```
redis-cli -p 6381 -c
-c优化路由，不然会存不进去

# 查看集群信息
redis-cli --cluster check 192.168.111.147:6381
```

#### 主从扩容

```
1)新建6387、6388两个节点
2)进入6387容器实例内部
3）将新增的6387节点（空槽号）作为master节点加入集群
redis-cli --cluster add-node IP:6387 IP:6381
# 此时是没有槽位的
4）检查集群情况
5）重新分派槽号
redis-cli --cluster reshard IP:端口(6381)
====>
多少槽位想要移动？4096（四台平分，16384/4）
移动到哪个节点？6397的ID
all/done？all
6）检查集群情况
====>原来的每一台都分给它匀一点（重新分配成本太高）
7）为主节点6387分配从节点6388
redis-cli --cluster add-node IP:slave端口 IP:master端口 \
	--cluster-slave --cluster-master-id 新master节点ID
8）检查集群情况
```

#### 主从缩容

```
1)将新从节点删除
redis-cli --cluster del-node IP:端口 新从机ID
2)将6387的槽号分配给6381
redis-cli --cluster reshard IP:端口(6381)
多少槽位想要移动？4096
移动到哪个节点？6381的ID（一次性给6381）
从谁那里拿槽位？6387的ID
all/done？done
3）将6387删除
redis-cli --cluster del-node IP:端口 新主机ID
```



# Dockerfile

Dockerfile是用来构建docker镜像的文本文件，是由一条条构建镜像所需的指令和参数构成的脚本

编写Dockerfile------>docker build命令构建镜像------>docker run依镜像运行容器实例

1. 每条保留字指令都必须为大写字母且后面要跟随至少一个参数
2. 指令按照从上到下，顺序执行
3. \#表示注释
4. 每条指令都会创建一个新的镜像层并对镜像进行提交

## 保留字

```
FROM
基础镜像，当前新镜像是基于哪个镜像的，指定一个已经存在的镜像作为模板，第一条必须是from

MAINTAINER
镜像维护者的姓名和邮箱地址

RUN
容器构建时需要运行的命令
# RUN是在 docker build时运行

EXPOSE
当前容器对外暴露出的端口

WORKDIR
指定在创建容器后，终端默认登陆的进来工作目录，一个落脚点

USER
指定该镜像以什么样的用户去执行，如果都不指定，默认是root

ENV
用来在构建镜像过程中设置环境变量

ADD
将宿主机目录下的文件拷贝进镜像且会自动处理URL和解压tar压缩包
COPY
类似ADD，拷贝文件和目录到镜像中。
将从构建上下文目录中 <源路径> 的文件/目录复制到新的一层的镜像内的 <目标路径> 位置
# COPY src dest  /	COPY ["src", "dest"]

VOLUME
容器数据卷，用于数据保存和持久化工作

CMD
指定容器启动后的要干的事情
# Dockerfile 中可以有多个 CMD 指令，但只有最后一个生效，CMD 会被 docker run 之后的参数替换。
# 和RUN命令的区别
● CMD是在docker run 时运行。
● RUN是在 docker build 时运行。

ENTRYPOINT
# 也是用来指定一个容器启动时要运行的命令
# 类似于 CMD 指令，但是ENTRYPOINT不会被docker run后面的命令覆盖， 而且这些命令行参数会被当作参数送给 ENTRYPOINT 指令指定的程序。
# ENTRYPOINT可以和CMD一起用，一般是变参才会使用 CMD ，这里的 CMD 等于是在给 ENTRYPOINT 传参。
# 当指定了ENTRYPOINT后，CMD的含义就发生了变化，不再是直接运行其命令而是将CMD的内容作为参数传递给ENTRYPOINT指令，他两个组合会变成<ENTRYPOINT>"<CMD>""
# 在执行docker run的时候可以指定 ENTRYPOINT 运行所需的参数。
# 如果 Dockerfile 中如果存在多个 ENTRYPOINT 指令，仅最后一个生效。
```

### 构建案例

```
vim Dockerfile
====>
FROM centos
MAINTAINER zzyy<zzyybs@126.com>

ENV MYPATH /usr/local
WORKDIR $MYPATH

#安装vim编辑器
RUN yum -y install vim
#安装ifconfig命令查看网络IP
RUN yum -y install net-tools
#安装java8及lib库
RUN yum -y install glibc.i686
RUN mkdir /usr/local/java
#ADD 是相对路径jar,把jdk-8u171-linux-x64.tar.gz添加到容器中,安装包必须要和Dockerfile文件在同一位置
ADD jdk-8u171-linux-x64.tar.gz /usr/local/java/
#配置java环境变量
ENV JAVA_HOME /usr/local/java/jdk1.8.0_171
ENV JRE_HOME $JAVA_HOME/jre
ENV CLASSPATH $JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar:$JRE_HOME/lib:$CLASSPATH
ENV PATH $JAVA_HOME/bin:$PATH

EXPOSE 80

CMD echo $MYPATH
CMD echo "success--------------ok"
CMD /bin/bash
<====

docker build -t 新镜像名字:TAG .    <----.表示在当前目录下
```

##### 虚悬镜像

```
查看
docker image ls -f dangling=true

删除
docker image prune
```



# 整合微服务

假设已经打包好了业务jar包（fish.jar）

```
# 基础镜像使用java
FROM java:8
# 作者
MAINTAINER fish
# VOLUME 指定临时文件目录为/tmp，在主机/var/lib/docker目录下创建了一个临时文件并链接到容器的/tmp
VOLUME /tmp
# 将jar包添加到容器中并更名为fish_docker.jar
ADD fish.jar fish_docker.jar
# 运行jar包
RUN bash -c 'touch /fish_docker.jar'
ENTRYPOINT ["java","-jar","/fish_docker.jar"]
#暴露6001端口作为微服务
EXPOSE 6001
```



# docker网络

docker启动后会产生一个名为docker0的虚拟网桥

```
docker network ls
```

作用：

容器间的互联和通信以及端口映射

容器IP变动时可以通过服务名直接网络通信而不受影响

## 网络模式

bridge模式：使用--network bridge指定，默认使用docker0

​	为每一个容器分配、设置IP等，并将容器连接到一个docker0

host模式：使用--network host指定

​	容器将不会虚拟出自己的网卡，配置自己的IP等，而是使用宿主机的IP和端口

none模式：使用--network none指定

​	容器有独立的Network namespace，但并没有对其进行任何网络设置，如分配veth pair和网桥连接，IP等

container模式：使用--network container:NAME或者容器ID指定

​	新创建的容器不会创建自己的网卡和配置自己的IP，而是和一个指定的容器共享IP，端口范围等

### 自定义网络

```
docker network create fish_network

docker run -d -p 8081:8080 --network fish_network --name tomcat81 镜像名
docker run -d -p 8082:8080 --network fish_network --name tomcat82 镜像名

ping tomcat82
===> ping容器名字是可以ping通的
```



# docker-compose容器编排

```
# 启动所有docker compose服务
docker compose up
# -d 后台运行

# 停止并删除容器、网络
docker compose down
-v 删除数据卷

# 进入容器实例内部 docker-compose exec docker-compose.yml文件中写的服务id /bin/bash
docker compose exec yml里面的服务id

# 展示当前docker-compose编排多的运行的所有容器
docker compose ps

# 展示当前docker-compose编排过的容器进程
docker compose top

# 查看容器输出日志
docker compose logs yml里面的服务id

# 检查配置 -q有问题才输出
docker compose config

# 重启服务
docker compose restart

# 启动服务
docker compose start

# 停止服务
docker compose stop
```

# 轻量级可视化工具portainer

```
docker run -d -p 8000:8000 -p 9000:9000 
--name portainer 
--restart=always 
-v /var/run/docker.sock:/var/run/docker.sock 
-v portainer_data:/data 
portainer/portainer 
```

# CAdvisor监控收集+InfluxDB存储数据+Grafana图形化





# 日志切割轮转

1）docker日志驱动:不适合多节点/集群

```
在 docker-compose.yml 中配置：
services:
  task-api:
    # ... 其他配置
    logging:
      driver: json-file
      options:
        max-size: "100m"    # 单个日志文件最大 100MB
        max-file: "3"       # 保留 3 个文件（当前 + 2 个历史）
```

2)应用层日志轮转

```
logging_config.py

from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    filename="/var/log/task-api/app.log",
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=5,                # 保留 5 个备份
    encoding='utf-8'
)
```

3)集中式日志系统

```
容器 → Filebeat/Fluentd → Elasticsearch/Kafka → Kibana/Dashboard

常用工具：
ELK Stack：Elasticsearch + Logstash + Kibana
EFK Stack：Elasticsearch + Fluentd + Kibana
Loki + Grafana：轻量级，适合 K8s
```

