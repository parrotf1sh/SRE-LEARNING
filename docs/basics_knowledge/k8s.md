# kubernetes

## 为什么出现k8s

### 集群场景

IAAS（Infrastructure as a Servive）基础设施即服务

====>openstack框架

PAAS（platform as a service）平台是服务

====>k8s/Rancher/Mesos

SAAS（Software as a service）

### PAAS

##### docker swarm（轻）

##### Mesos（稳）

##### k8s：

+ 服务发现和负载均衡
+ 存储编排（添加任何本地或云服务器）
+ 自动部署和回滚
+ 自动分配CPU/内存资源-弹性伸缩
+ 自我修复（需要时启动新容器）
+ Secret（安全相关信息）和配置管理
+ 大型规模的支持
+ 开源

### 架构

```
master:

kubectl -----> api server <----> etcd（键值对数据库）
								|				|
						scheduler		controller manager
						
node:

kubelet		kube proxy
pod=>container
```



# Pod, k8s网络

## pod（容器组）

### Pause（pod内的其他容器共享它的网络、IPC、PID）

+ Pod内部第一个启动的容器
+ 初始化网络栈
+ 挂载需要的存储卷
+ 回收僵尸进程

## 网络

### calico架构

Felix

+ 管理网络接口
+ 编写路由
+ 编写ACL
+ 报告状态

bird（BGP Client）

BGP Client将通过BGP协议广播告诉剩余calico节点，从而实现网络互通。

confd

通过监听etcd以了解BGP配置和全局默认值的更改。confd根据etcd数据的更新动态生成BIRD配置文件



vxlan/IPIP/BGP



# 资源清单

名称空间级别：

+ 工作负载型资源：pod、ReplicaSet、Deployment
+ 服务发现及负载均衡型资源：Service、Ingress
+ 配置与存储型资源：Volume、CSI
+ 特殊类型的存储卷：ConfigMap、Secre

集群级资源

+ Namespace、Node、ClusterRole、ClusterRoleBinding

元数据型资源

+ HPA、PodTemplate、LimitRange



## 资源清单编写

### 结构

```
# 接口组版本 可以通过 ‘kubectl explain 资源名’ 	查看
apiVersion: v1
# 类别
kind: Pod
# 元数据
metadata:
# 期望
spec:
# 状态
status:
```

```
kubectl create -f yaml文件
```

```
# 获取当前的资源
kubectl get pods -A
	-n 命名空间
	-o wide 可以看到IP、node
	--show-labels	查看标签
	-l 具备的key/具备的具体的标签value
	-w 监视

# 通过k8s进入容器内
kubectl exec -it pod名 -c 容器名 -- /bin/bash

# 查看日志
kubectl logs pod名 -c 容器名

# 查看资源对象的详细描述
kubectl describe pod pod名

# 删除资源对象
kubectl delete 类别 对象名
```

### pod的生命周期

Pause贯穿整个生命周期

1）initC（初始化容器）

一定是顺序执行的，当前一个返回退出码为0，下一个才会执行。

假设第二个初始化容器退出码不为0，那么就要从第一个初始化容器重新运行。

2）mainC（主要的业务容器）

|容器初始化====>启动后钩子==================================关闭前钩子====>关闭信号|

​					==>启动命令（可能钩子还没有执行完毕就开始执行）

探针：

｜启动探测｜================就绪探测=============================================|

｜                ｜	|===========存活探测=============================================｜

> [!NOTE]
>
> 钩子、探针都是节点的kubelet进行执行



#### 就绪探测readinessProbe：

​	如果pod内部的容器不添加就绪探测，默认就绪。

​	如果添加了就绪探测，只有就绪通过以后，才标记修改为就绪状态。当前pod内的所有的容器都就绪，才标记当前pod就绪。

​	成功：将当前的容器标记为就绪

​	失败：静默

​	未知：静默

方式：

+ HTTP Get方式
+ EXEC方式
+ TCP Check方式（不常用）

#### 存活探测livenessProbe：

​	如果pod内部不指定存活探测，可能会发生容器运行但是无法提供服务的情况

​	成功：静默

​	失败：根据重启策略进行重启的操作

​	未知：静默 

#### 启动探测startupProbe：

​	保障存活探测在执行的时候不会因为时间设定问题导致无限死亡或者延迟很长的情况

​	成功：开始允许存活探测 就绪探测开始执行

​	失败：静默

​	未知：静默

#### 钩子：

类型：exec和http

```
apiVersion: v1
kind: Pod
metadata:
  name: lifecycle-pod
  labels:
    app: lifecycle-pod
spec:
  containers:
    - name: lifecycle-container
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:busybox
      command: ["/bin/sh","-c","touch /tmp/live; sleep 600;rm -rf /tmp/live;sleep 3600"]
      livenessProbe:
        exec:
          command: ["test","-e","/tmp/live"]
        initialDelaySeconds: 1
        periodSeconds: 3
      lifecycle:
        postStart:
          httpGet:
            host: 192.168.66.12
            path: index.html
            port: 1234
        preStop:
          httpGet:
            host: 192.168.66.12
            path: index.html
            port: 1234
    - name: myapp-container
      image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/wangyanglinux/myapp:v1.0
      livenessProbe:
        httpGet:
          port: 80
          path: /index.html
        initialDelaySeconds: 1
        periodSeconds: 3
        timeoutSeconds: 3
      readinessProbe:
        httpGet:
          port: 80
          path: /index1.html
        initialDelaySeconds: 1
        periodSeconds: 3
  initContainers:
    - name: init-myservice
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:busybox
      command: ["sh","-c","until nslookup myservice;do echo waiting for myservice;sleep 2;done;"]
    - name: init-mydb48
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:busybox
      command: ["sh","-c","until nslookup mydb;do echo waiting for mydb; sleep 2;done;"]
```



# pod控制器

## ReplicationController和ReplicaSet

RC用来确保容器应用的副本数始终保持在用户定义的副本数

RS可以替换RC，且支持集合式的selector

```
apiVersion: v1
kind: ReplicationController
metadata:
  name: rc-demo
spec:
  replicas: 3
  selector:
    app: rc-demo
  template:
    metadata:
      labels:
        app: rc-demo
    spec:
      containers:
      - name: rc-demo-container
        image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/wangyanglinux/myapp:v1.0
        env:
        - name: GET_HOSTS_GROM
          value: dns
        - name: zhangsan
          value: "123"
        ports:
        - containerPort: 80
```

```
# 调整副本数量
kubectl scale rc rc名 --replicas=5
```

```
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: rs-ml-demo
spec:
  replicas: 3
  selector:
    matchLabels:		# 匹配标签
      app: rs-ml-demo
      domain: lty
  template:
    metadata:
      labels:
        app: rs-ml-demo
        domain: lty
        version: v1
    spec:
      containers:
      - name: rs-ml-demo-container
        image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/wangyanglinux/myapp:v1.0
        env:
        - name: GET_HOSTS_GROM
          value: dns
        - name: zhangsan
          value: "123"
        ports:
        - containerPort: 80
```

selector.matchExpressions

rs在标签选择器上，除了可以定义键值对的选择形式，还支持matchExpression字段，提供多种选择。

- in	label的值在某个列表中
- NotIn	label的值不在某个列表中
- Exists	某个label存在
- DoesNotExist		某个label不存在

```
selector:
    matchExpressions:
      - key: app
        operator: Exists
        
selector:
    matchExpressions:
    - key: app
      operator: In
      values:
      - spring-k8s
      - hahah  
```



## Deployment

 Deployment为pod和RS提供了一个声明式定义（declarative）方法，用来代替以前的RC来方便管理应用

Deployment先创建出RS，再由RS去创建pod

+ 定义Deployment来创建pod和RS
+ 滚动升级和回滚应用
+ 扩容和缩容
+ 暂停和继续Deployment

```
# 命令式
kubectl replace -f deployment.yaml

# 声明式
kubectl apply -f deployment.yaml

# 现有的和正在运行的不同
kubectl diff -f deployment.yaml

# --record 记录命令，查看每次revision的变化
kubectl create -f deployment.yaml --record

# 自动扩缩容
kubectl autoscale deployment deployment名 --min=10 --max=15 --cpu-percent=80

# 修改容器
kubectl set image deployment/deployment名 容器名=镜像名

# 金丝雀部署理念
kubectl patch deployment deployment名 -p \
	'{"spec":{"strategy":{"rollingUpdate":{"maxSurge":1,"maxUnavailable":0}}}}'

kubectl patch deployment deployment名 --patch '期望镜像'  \
	&& kubectl rollout pause deploy deployment名
	
kubectl rollout resume deploy deployment名

# 回滚
kubectl rollout undo deployment/deployment名

# 回滚状态
kubectl rollout status deployment deployment名
echo $? ====> 返回码为0   可以用在脚本中

# 查看历史版本
kubectl rollout history deployment/deployment名

# 回滚到指定版本
kubectl rollout undo deployment/deployment名 --to-revision=2

# 回滚暂停
kubectl rollout pause3 deployment/deployment名

# 直接进etcd改
kubectl edit deployment deployment名
```

```
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: myapp-deploy
  name: myapp-deploy
spec:
  selector:
    matchLabels:
      app: myapp-deploy
  template:
    metadata:
      labels:
        app: myapp-deploy
    spec:
      containers:
      - name: myapp
        image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
```



## DeamonSet

确保全部（或一些）node上运行一个pod的副本。当有node加入集群时，也会为他们新增一个pod。当有node从集群移除时，这些pod也会被回收。删除DaemonSet将会删除它创建的所有pod

+ 运行集群存储daemon，例如在每个node上运行‘glusterd’、‘ceph’
+ 在每个node上运行日志收集daemon，例如‘fluentd’、‘logstash’
+ 在每个node上运行监控daemon，例如Prometheus Node Exporter、‘collectd’、Datadog代理、New Relic代理，或Ganglia ‘gmond’

```
apiVersion: apps/v1                                                           
kind: DaemonSet                                                               
metadata:                                                                     
  name: daemonset-demo                                                        
  labels:                                                                     
    app: daemonset-demo                                                       
spec:                                                                         
  selector:                                                                   
    matchLabels:                                                              
      name: daemonset-demo                                                    
  template:                                                                   
    metadata:                                                                 
      labels:                                                                 
        name: daemonset-demo                                                  
    spec:                                                                     
      containers:                                                             
      - name: daemonset-demo-container                                        
        image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0 
```

```
# 快速获取资源清单模版
kubectl create deployment myapp --image=镜像名 --dry-run -o yaml > deployment.yaml.tmp
```



## Job

负责批处理任务，保证批处理任务的一个或多个pod成功结束（返回码为0）

+ spec.template格式同Pod
+ RestartPolicy仅支持Nerver或OnFailue
+ 单个Pod时，默认Pod成功运行后Job即结束
+ spec.completions标志job结束需要成功运行的pod个数，默认为1
+ spec.parallelism标志并行运行的pod的个数，默认为1
+ spec.activeDeadlineSeconds标志失败Pod的重试最大时间，超过这个时间不会继续重试

```
apiVersion: batch/v1
kind: Job
metadata:
  name: rand
spec:    
  template:
    metadata:
      name: rand
    spec:
      containers:
      - name: rand
        image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:randexitv1
        args: ["--exitcode=1"]                                                                                                                                
      restartPolicy: Never
```



## CronJob

管理基于时间的job，在给定的时间点只运行一次，周期性的在给定时间点运行

spec.schedule：调度，必须字段，指定任务运行周期

spec.jobTemplate：job模版，必须字段，指定需要运行的任务

spec.startingDeadlineSeconds：启动job期限（秒级别），可选。如果因为任何原因而错过了被调度的时间，那么错过执行时间的job将被认为是失败的。如果没有指定，则没有期限

spec.concurrencyPolicy：并发策略，可选。指定了如何处理被cron job创建的job的并发执行。只允许下面策略的一种：

+ Allow：默认，允许并发运行job
+ Forbid：禁止并发运行，如果前一个还没有完成，则直接跳过下一个
+ Replace：取消当前正在运行的job，用一个新的来替换

spec.suspend：挂起，可选。true，后续所有执行都会被挂起。对已经开始执行的job不起作用。默认值为false

spec.successfulJobsHistoryLimit和spec.faildJobsHistoryLimit：历史限制，可选。指定了可以保留多少完成和失败的Job。默认情况，分别被设置为3和1。设置限制的值为0，相关类型的job完成后将不会被保留

```
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cronjob-demo
spec:
  schedule: "*/1 * * * *"
  jobTemplate:
    spec:
      completions: 3
      template:
        spec:
          containers:
          - name: crontab-demo-container
            image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:busybox
            args:
            - /bin/sh
            - -c
            - date; echo Hello from the kubernetes cluster
          restartPolicy: OnFailure
```



# Service 暴露服务的重要方式

在k8s集群中，每个node运行一个kube-proxy进程。kube-proxy负责为Service实现了一种VIP（虚拟IP）的形式

Sec dns域名

```
svcName.名字空间.svc.dominName.
	dominName		cluster.local.
```

## 工作原理

### userspace（已经被移除）

kube-proxy监听APISERVER将Service变化修改本地的iptables规则，代理来自当前节点pod的用户请求

### iptables

kube-proxy监听APISERVER将Service变化修改本地的iptables规则，相对于用户空间，kube-proxy功能解耦压力较小

### ipvs

```
kubectl edit configmap kube-proxy -n kube-system
mode:"ipvs"
# 杀死重建
kubectl delete pod -n kube-system -l k8s-app=kube-proxy

# 查看ipvs规则
ipvsadm -Ln
```

## 工作模式

### 类型

+ ClusterIp：默认类型，自动分配一个仅Cluster内部可以访问的虚拟IP
+ NodePort：在ClusterIP基础上为Service在每台机器上绑定一个端口，这样可以通过\<NodeIP>：NodePort来访问服务
+ LoadBalance：在NodePort的基础上，借助cloud provider创建一个外部负载均衡器，并将请求转发到\<NodeIP>：NodePort
+ ExternalName：把集群外部的服务引入到集群内部来，在集群内部直接使用。没有任何类型代理被创建（1.7以上版本的kube-dns支持）

### ClusterIp

```
apiVersion: v1
kind: Service
metadata:  
  name: myapp-clusterip
  namespace: default                                                                                                                                       
spec:      
  type: ClusterIP
  selector:
    app: myapp
    release: stabel
    svc: clusterip
  ports:   
  - name: http
    port: 80
    targetPort: 80
```

#### 持久化连接

```
kubectl edit svc svc名
service.spec.sessionAffinity:ClientIP
(默认3小时超时)
```

### NodePort

```
apiVersion: v1     
kind: Service      
metadata:          
  name: myapp-nodeport
  namespace: default
spec:              
  type: NodePort   
  selector:        
    app: myapp     
    release: stabel
    svc: nodeport  
  ports:           
  - name: http     
    port: 80       
    targetPort: 80 
    nodePort: 30010   
```

### LoadBalance(实现高可用，只能以云的方式使用)

### ExternalName

```
kind: Service                
apiVersion: v1               
metadata:                    
  name: my-service-1         
  namespace: default         
spec:                        
  type: ExternalName         
  externalName: www.baidu.com 
```



### endpoints

+ 有标签选择器：自动创建一个同名的endpoints资源对象
+ 没有定义标签选择器：不会创建同名的endpoints资源对象，需要管理员手动创建匹配对象

```
apiVersion: v1    
kind: Service     
metadata:         
  name: nginx-noselector
spec:             
  ports:          
  - protocol: TCP 
    port: 6666    
    targetPort: 80
===========================
apiVersion: v1
kind: Endpoints
metadata:    
  name: nginx-noselector
subsets:     
  - addresses:                                                        
    - ip: 192.168.66.10
    ports:   
    - port: 80
    
# 多个IP
- addresses:
     ' - ip: 172.17.0.2
     - ip: 172.17.0.3
     - ip: 172.17.0.4'
     ... ...
```

#### 特殊情况

默认需要pod就绪，且标签符合才会被抓取，但是可以设置不就绪也被抓取。

```
spec:                           
  publishNotReadyAddresses: true  
```



# k8s存储

## 存储分类

+ 元数据
  + configMap：用于保存配置数据（明文）
  + Secret：用于保存敏感数据（编码）
  + Downward API：容器在运行时从kubernetes API服务器获取有关它们自身的信息
+ 真实数据
  + Volume：用于存储临时或者持久性数据
  + PersistentVolume：申请制的持久化存储

## configMap（注入的机制）

+ 共享：每一次在读取文件的时候，都会发生网络IO
+ 注入：一次注入后，多次读取不再消耗网络IO

```
kubectl create configmap game-config --from-file=hongfu.file
###
文件内部必须是一行一对的 k=v， 可以在使用的时候注入至pod内部变成环境变量
1.txt
	name=fish
	passwd=123
	
文件名 > key			文件内容 > value
###

kubectl create cm literal-config --from-literal=name=dave --from-literal=passwd=pass
```

#### 将configmap作为pod的env

```
apiVersion: v1
kind: ConfigMap
metadata:
  name: literal-config
  namespace: default
data:
  name: dava
  password: pass

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: env-config
  namespace: default
data:
  log_level: INFO

---
apiVersion: v1          
kind: Pod               
metadata:               
  name: cm-env-test-pod 
spec:                   
  containers:           
    - name: test-container  
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0 
      command: ["/bin/sh","-c","env"]
      env:              
        - name: USERNAME
          valueFrom:    
            configMapKeyRef:
              name: literal-config
              key: name 
        - name: PASSWORD
          valueFrom:    
            configMapKeyRef:
              name: literal-config
              key: password 
      envFrom:          
        - configMapRef: 
            name: env-config
  restartPolicy: Never 
```

#### configmap作为启动命令

```
apiVersion: v1
kind: Pod                                                                                 metadata:
  name: cm-command-pod
spec:
  containers:
    - name: myapp-container
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      command: [ "/bin/sh","-c ","echo $(USERNAME) $(PASSWORD)" ]
      env:
        - name: USERNAME
          valueFrom:
            configMapKeyRef:
              name: literal-config
              key: name
        - name: PASSWORD
          valueFrom:
            configMapKeyRef:
              name: literal-config
              key: password
  restartPolicy: Never
```

#### 将configmap作为文件使用

```
apiVersion: v1
kind: Pod
metadata:
  name: cm-volume-pod
spec:
  containers:
    - name: myapp-container
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      volumeMounts:
        - name: config-volume
          mountPath: /etc/config
  volumes:
    - name: config-volume
      configMap:
        name: literal-config
  restartPolicy: Never
```

可以做热更新，配置的文件是软连接的形式

强制触发热更新

```
kubectl patch deployment nginx-test --patch '{"spec": {"template": {"metadata"{"annotations": {"version/config": "666666666" }}}}}'
```

更新ConfigMap后：

- 使用该ConfigMap挂载的Env不会同步更新
- 使用该ConfigMap挂载的Volume中的数据需要一段时间(实测大概10s)才能同步更新

#### 不可改变配置

configmap和secret都有一个可选配置，设置各个configmap和secret为不可变的。

+ 防止意外（非预期）更新导致应用程序中断
+ 通过将configmap标记为不可变来关闭kube-apiserver对其的监视，从而显著降低kube-apiserver的负载，提升集群性能

```
kind:ConfigMap

# 直接添加(不可逆)
immutable: true

metadata:...
```



## Secret（编码，并不是非对称加密）

分发到需要访问secret的pod所在的机器节点来保障安全性

只会存储在节点的内存中，永不写入物理存储，节点删除secret时就不需要擦除磁盘数据

etcd以加密形式存secret

| 内置类型                            | 用法                                         |
| ----------------------------------- | -------------------------------------------- |
| Opaque                              | 用户定义的任意数据                           |
| kubernetes.io/service-account-token | 服务账号令牌                                 |
| kubernetes.io/dockercfg             | ~/.dockercfg文件的序列化形式（老版本docker） |
| kubernetes.io//dockerconfigjson     | ~/.dockercfg/config.json文件的序列化形式     |
| kubernetes.io/basic-auth            | 用于基本身份认证的凭据                       |
| kubernetes.io/ssh-auth              | 用于SSH身份认证的凭据                        |
| kubernetes.io/tls                   | 用于TLS客户端或者服务器端的数据              |
| bootstrap.kubernetes.io/token       | 启动引导令牌数据                             |

## Opaque（未指定，默认是这个类型）

```
[root@k8s-master01 7]# echo -n "admin" | base64 
YWRtaW4=
[root@k8s-master01 7]# echo -n "5h5hjk52hjk4324" | base64            
NWg1aGprNTJoams0MzI0

apiVersion: v1
kind: Secret
metadata:
  name: mysecret
type: Opaque
data:
  username: YWRtaW4=
  password: NWg1aGprNTJoams0MzI0
```

### 用作env

```
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: opaque-secret-env
  name: opaque-secret-env-deploy
spec:
  replicas: 5
  selector:
    matchLabels:
      app: op-se-env-pod
  template:                                                                                          
    metadata:
      labels:
        app: op-se-env-pod
    spec:
      containers:
        - name: myapp-container
          image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
          ports:
            - containerPort: 80
          env:
            - name: TEST_USER
              valueFrom:
                secretKeyRef:
                  name: mysecret
                  key: username
            - name: TEST_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysecret
                  key: password
```

### volume方案

```
apiVersion: v1
kind: Pod
metadata:
  name: secret-volume-pod
  labels:
    name: secret-volume
spec:    
  containers:
    - name: myapp-container
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      volumeMounts:
        - name: volumes12
          mountPath: "/data"
  volumes:
    - name: volumes12
      secret:
        secretName: mysecret 
        
				defaultMode: 256   =====>		权限为400（根据八进制），同理420->rwx为644
				items:						======>		只引入部分键，子路径卷挂载将会不支持热更新
          - key: username
            path: my-group/my-username 
```



## Downward API

+ 提供容器元数据
+ 动态配置
+ 与kubernetes环境集成

### 通过env

```
apiVersion: v1 
kind: Pod      
metadata:      
  name: downward-api-env-example
spec:          
  containers:  
    - name: my-container
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      env:     
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: CPU_REQUEST
          valueFrom:
            resourceFieldRef:
              resource: requests.cpu                                                       
        - name: CPU_LIMIT
          valueFrom:
            resourceFieldRef:
              resource: limits.cpu
        - name: MEMORY_REQUEST
          valueFrom:
            resourceFieldRef:
              resource: requests.memory
        - name: MEMORY_LIMIT
          valueFrom:
            resourceFieldRef:
              resource: limits.memory
  restartPolicy: Never
```

### 通过volume

```
apiVersion: v1 
kind: Pod      
metadata:      
  name: downward-api-volune-example.yaml
spec:          
  containers:  
    - name: my-container
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      resources:
        limits:
          cpu: "1"
          memory: "512Mi"
        requests:
          cpu: "0.5"
          memory: "256Mi"
      volumeMounts:
        - name: downward-api-volume
          mountPath: /etc/podinfo
  volumes:     
    - name: downward-api-volume
      downwardAPI:
        items: 
          - path: "annotations"
            fieldRef:
              fieldPath: metadata.annotations
          - path: "labels"
            fieldRef:
              fieldPath: metadata.labels
          - path: "name"
            fieldRef:
              fieldPath: metadata.name
          - path: "namespace"
            fieldRef:
              fieldPath: metadata.namespace
          - path: "uid"
            fieldRef:
              fieldPath: metadata.uid
          - path: "cpuRequest"
            resourceFieldRef:
              containerName: my-container
              resource: requests.cpu
          - path: "memoryRequest"
            resourceFieldRef:
              containerName: my-container
              resource: requests.memory
          - path: "cpuLimit"
            resourceFieldRef:
              containerName: my-container
              resource: limits.cpu
          - path: "memoryLimit"
            resourceFieldRef:
              containerName: my-container
              resource: limits.memory                                                     
  restartPolicy: Never
```

### 基于apiServer访问集群

```
1.RBAC.yaml
# 授权访问apiServer
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding                                                                             
metadata:
  name: test-api-cluster-admin-binding
subjects:
  - kind: ServiceAccount
    name: test-api
    namespace: default
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io

kubectl apply -f 1.RBAC.yaml
kubectl create sa test-api
---------------------------------------------------------
2.pod.yaml

apiVersion: v1
kind: Pod
metadata:
  name: curl
spec:  
  serviceAccountName: test-api
  containers:
    - name: main
      image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/curlimages/curl:latest     
      command: ["sleep","9999"]
-------------------------------------------------------------
root@curl:/# TOKEN=$( cat /var/run/secrets/kubernetes.io/serviceaccount/token )
root@curl:/# CAPATH="/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
root@curl:/# NS=$( cat /var/run/secrets/kubernetes.io/serviceaccount/namespace )
root@curl:/# curl -H "Authorization: Bearer $TOKEN" --cacert $CAPATH \ https://kubernetes/api/v1/namespaces/$NS/pods
```



## Volume数据持久化

### emptyDir

当pod被分配给节点时，首先创建‘emptyDir’卷，并且只要该pod在该节点上运行，该卷就会存在，初始为空。pod中的容器可以读取和写入emptyDir卷中的相同文件。从节点中删除pod时，emptyDir中的数据将被永久删除。

容器崩溃不会从节点中移除pod，所以emptyDir在容器崩溃时是安全的。

+ 作为暂存空间，例如用于基于磁盘的合并排序、用作长时间计算崩溃恢复时的检查点
+ web服务器容器提供数据时，保存内容管理器容器提取的文件

```
[root@k8s-master01 7]# vi volume-emptydir-disk-pod.yaml
apiVersion: v1      
kind: Pod           
metadata:           
  name: volume-emptydir-disk-pod
spec:               
  containers:       
    - name: myapp   
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      ports:        
        - containerPort: 80
      volumeMounts: 
        - name: logs-volume                                                                         mountPath: /usr/local/nginx/logs
    - name: busybox 
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:busybox
      command: ["/bin/sh","-c","touch /logs/access.log && tail -f /logs/access.log"]
      volumeMounts: 
        - name: logs-volume
          mountPath: /logs
  volumes:          
    - name: logs-volume
      emptyDir: {}  
```

#### 以共享内存方式

```
apiVersion: v1 
kind: Pod      
metadata:      
  name: volume-emptydir-mem
spec:          
  containers:  
    - name: myapp
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      ports:   
        - containerPort: 80
      resources:
        limits: 	# 软限制
          cpu: "1"
          memory: 1024Mi
        requests:	# 初始值
          cpu: "1"
          memory: 1024Mi
      volumeMounts:
        - name: mem-volume
          mountPath: /data
  volumes:     
    - name: mem-volume
      emptyDir:
        medium: Memory
        sizeLimit: 500Mi
```



### hostPath

将主机节点的文件系统中的文件或目录挂载到集群中

+ 运行需要访问docker内部的容器；使用/var/lib/docker的hostPath
+ 在容器中运行cAdvisor；使用/dev/cgroups的hostPath
+ 允许pod指定给定的hostPath是否应该在pod运行之前存在，是否应该创建，以及它应该以什么形式存在

除了所需的path属性之外，用户还可以为hostPath卷指定type

```
apiVersion: v1     
kind: Pod          
metadata:          
  name: hostpath-pod
spec:              
  containers:      
    - name: myapp  
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      volumeMounts:
        - name: test-volume
          mountPath: /test-pd
  volumes:         
    - name: test-volume
      hostPath:    
        path: /test                                                   
        type: Directory
```



### PV/PVC（持久卷/持久卷申请）

+ 容量：PV的值不小于PVC要求，可以大于最好一致
+ 读写策略：完全匹配
  + 单节点读写-ReadWriteOnce-RWO
  + 多节点只读-ReadOnlyMany-ROX
  + 多节点读写-ReadWriteMany-RWX
+ 存储类：PV的类与PVC的类必须一致，不存在包容降级关系

##### 回收策略

+ Retain（保留）：手动回收
+ Recycle（回收）：基本擦除（rm -rf /thevolume/*）,之前写的数据就被删除了
+ Delete（删除）：关联的存储资产（例如AWS EBS、GCE PD、Azure Disk和OpenStack Cinder卷）将被删除

当前只有NFS和HostPath支持回收策略，AWS EBS、GCE PD、Azure Disk和OpenStack Cinder卷支持删除策略

##### 状态

+ Available（可用）一块空闲资源没有被任何声明所绑定
+ Bound（已绑定）卷已经被声明绑定
+ Released（已释放）声明被删除，但是资源还未被集群重新声明
+ Faild（失败）该卷的自动回收失败

#### 实际操作

1）安装NFS

2）部署PV

```
apiVersion: v1
kind: PersistenVolume                                                                     metadata:
name: nfspv1
spec:  
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Recycle
  storageClassName: nfs
  nfs: 
    path: /nfsdata/1
    server: 192.168.66.10
```

3）创建服务并使用PVC

```
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  ports:
    - port: 80
      name: web
  clusterIP: None	<======无头服务
  selector:
    app: nginx

---
apiVersion: apps/v1
kind: StatefulSet			<=====有状态控制器
metadata:
  name: web
spec:
  selector:
    matchLabels:
      app: nginx
  serviceName: "nginx"
  replicas: 3
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
          ports:
            - containerPort: 80
              name: web
          volumeMounts:
            - name: www
              mountPath: /usr/local/nginx/html
  volumeClaimTemplates:
    - metadata:
        name: www
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: "nfs"
        resources:
          requests:
            storage: 1Gi
```

### StatefulSet控制器

+ 有序创建，有序回收

+ 数据持久化pod级别

​		pod > pvc > pv > nfs  

+ 稳定的网络访问方式（域名：podName(statefulSetName-num).headlessSvcName.nsName.svc.domainName.）



## storageClass存储类

是一种资源对象，用于定义持久卷的动态供给策略。允许管理员定义不同类型的存储，并制定如何动态创建持久卷以供应用程序使用。

```
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-client
  namespace: nfs-storageclass
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
parameters:
  pathPattern: ${.PVC.namespace}/${.PVC.name}
  onDelete: delete
```

```
apiVersion: v1               
kind: PersistentVolumeClaim  
metadata:                    
  name: test-claim           
  annotations:               
spec:                        
  accessModes:               
    - ReadWriteMany          
  resources:                 
    requests:                
      storage: 1Mi           
  storageClassName: nfs-client
                             
---                          
apiVersion: v1               
kind: Pod                    
metadata:                    
  name: test-pod             
spec:                        
  containers:                
    - name: test-pod         
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
      volumeMounts:          
        - name: nfs-pvc      
          mountPath: "/usr/local/nginx/html"
  restartPolicy: "Never"     
  volumes:                   
    - name: nfs-pvc          
      persistentVolumeClaim: 
        claimName: test-claim  
```



# 调度器

把定义的pod分配到集群的节点上

sheduler是作为单独的程序运行的，启动之后会一直监听APIserver，获取PodSpec.NodeName为空的pod，对每个pod都会创建一个binding，表明该pod应该放到哪个节点上

+ 公平：如何保证每个节点都能被分配资源
+ 资源高效利用：集群所有资源最大化被使用
+ 效率：调度的性能要好，能够尽快地对大批量的pod完成调度工作
+ 灵活：允许用户根据自己的需求控制调度的逻辑

（过滤不满足条件的）预选----->（按照优先级排序）优选，如果中间任何一步骤有错误，就直接返回错误



## 亲和性

### 节点亲和性=========>匹配节点标签

spec.affinity.nodeAffinity

+ preferredDuringSchedulingIgnoredDuringExecution软性策略

+ requiredDuringSchedulingIgnoredDuringExecution硬性策略

```
apiVersion: v1   
kind: Pod        
metadata:        
  name: node-affinity-preferred
  labels:        
    app: node-affinity-preferred
spec:            
  containers:    
    - name: node-affinity-preferred-pod
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
  affinity:      
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 1
          preference:
            matchExpressions:
              - key: domain
                operator: In                                                                                                                               
                values:
                  - xinxianghf
```

### pod亲和性

```
apiVersion: v1                                 
kind: Pod                                      
metadata:                                      
  name: pod-aff-prefer                         
  labels:                                      
    app: pod-aff                               
spec:                                          
  containers:                                  
    - name: myapp                              
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
  affinity:                                    
    podAffinity:                               
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 1                            
          podAffinityTerm:                     
            labelSelector:                     
              matchExpressions:                
                - key: app                     
                  operator: In                 
                  values:                      
                    - pod-1                    
            topologyKey: kubernetes.io/hostname 
```

### pod反亲和性

```
apiVersion: v1             
kind: Pod                  
metadata:                  
  name: pod-antiaff-prefer 
  labels:                  
    app: pod-aff           
spec:                      
  containers:              
    - name: myapp          
      image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
  affinity:                
    podAntiAffinity:       
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 1        
          podAffinityTerm: 
            labelSelector: 
              matchExpressions:
                - key: app 
                  operator: In
                  values:  
                    - pod-2                                           
            topologyKey: kubernetes.io/hostname
```



## 污点和容忍

Taint和toleration相互配合，可以避免pod被分配到不合适的节点上。每个节点都可以应用一个或多个taint，这表示对于那些不能容忍这些taint 的pod是不会被该节点接受的。如果将toleration应用于pod上，则表示这些pod可以（但不要求）被调度到具有匹配taint的节点上

### 污点组成

```
key=value:effect
```

每个污点有一个key和value作为污点的标签，其中value可以为空，effect描述污点的作用。

+ NoSchedule：将不会将pod调度到具有该污点的node上
+ PreferNoSchedule：将尽量避免将pod调度到具有该污点的node上
+ NoExecute：将不会将pod调度到具有该污点的node上，同时会将node上已经存在的pod驱逐出去

```
# 设置污点
kubectl taint node nodeName key=value:NoSchedule

# 删除污点
kubectl taint node nodeName key=value:NoSchedule-
```

### 容忍

```
tolerations:
	-key:"key1"
	 operator:"Equal"
	 value:"value1"
	 effect:"NoSchedule"

tolerations:
	-key:"key1"
	 operator:"Equal"
	 value:"value1"
	 effect:"NoExecute"
	 tolerationSeconds:3600
	 
# 当不指定value时，表示容忍所有的污点value
-key:"key1"
 operator:"Exists"
 effect:"NoSchedule"
# 当不指定key时，表示容忍所有的污点key
-operator:"Exists"
# 当不指定effect值时，表示容忍所有的污点
-key:"key"
 operator:"Exists"
# 有多个master存在时，防止资源浪费，可以设置为尽可能不调度
```

### 固定节点调度(跳过调度策略)

```
spec:
	nodeName: k8s-node01
```

##### 指定节点标签调度(没办法跳过调度策略如污点)

```
spec:               
	nodeSelector:     
		type: nodeselect
```



# 安全

## 安全机制

api server作为外部控制的入口，内部封装（3A服务）：认证==>鉴权==>准入控制

## 认证

### 类型

+ HTTP Token
+ HTTP Base（用户名密码）
+ HTTPS证书认证（基于CA根证书签名的客户端身份认证方式，双向HTTPS）

### 需要认证的类型

组件：

+ 无需加密（使用kubeadm安装，与api server处于同一台机器，通过127.0.0.1非安全地址访问）
  + controller manager、scheduler
+ 需要加密
  + 证书手动签发：kube-proxy、kubectl
  + 自动签发：kubelet

pod：

​	（ServiceAccount）SA，secret资源对象的一种，其中包含三个部分

	+ token，使用api server私钥签名的JWT（适用于单点登录），用于访问api server时，server端认证
	+ ca.crt，根证书，用于client端验证api server发送的证书
	+ namespace，标识这个service-account-token的作用域名空间

如果使用kubeadm安装，kubelet首次访问apiserver时，使用token做认证，通过后，controller manager会为kubelet生成一个证书，以后的访问都是用证书认证

--token 用于apiserver识别kubelet是否合法

--discovery-token-ca-cert-hash 用于kubelet确认apiserver发送来的证书是否合法

#### kubeconfig

包含集群参数（CA证书、api server地址），客户端参数，集群context信息。kubenetes组件通过启动时指定不同的kubeconfig文件可以切换到不同的集群



## 鉴权

### RBAC（role-based access control）基于角色的访问控制

+ 对集群中的资源和非资源均拥有完整的覆盖
+ 整个RBAC完全由几个API对象完成，同其他的API对象一样，可以用kubectl或API进行操作
+ 可以在运行时进行调整，无需重启API server

引入的顶级资源对象

```
ROLE（角色）
CLUSTERROLE（集群角色）

ROLEBINDING（角色绑定）
CLUSTERROLEBINDING（集群角色绑定）

ROLE	+ ROLEBINDING
CLUSTERROLE	+ CLUSTERROLEBINDING
CLUSTERROLE	+	ROLEBINDING				(降维，作用域被限制)
```

### 创建一个用户只能管理dev名字空间

创建证书>转换为kubeconfig文件>创建名字空间>角色绑定

```
[root@k8s-master01 ]# vim devuser-csr.json
{                
  "CN": "devuser", 
  "hosts": [],   
  "key": {       
    "algo": "rsa", 
    "size": 2048 
  },             
  "names": [     
    {            
      "C": "CN", 
      "ST": "BeiJing",
      "L": "BeiJing",
      "O": "k8s",                                                     
      "OU": "System"
    }            
  ]              
} 
```

```
证书工具集：cfssl、cfssljson、cfssl-certinfo

[root@k8s-master01 ~]# cd /etc/kubernetes/pki/
[root@k8s-master01 pki]# cfssl gencert -ca=ca.crt -ca-key=ca.key -profile=kubernetes /root/devuser-csr.json | cfssljson -bare devuser

# 生成config文件
## 将集群信息写入config文件
export KUBE_APISERVER="https://192.168.66.10:6443"
kubectl config set-cluster kubernetes \
--certificate-authority=ca.crt \
--embed-certs=true \
--server=${KUBE_APISERVER} \
--kubeconfig=devuser.kubeconfig

## 将用户信息写入config文件
kubectl config set-credentials devuser \
--client-certificate=devuser.pem \
--client-key=devuser-key.pem \
--embed-certs=true \
--kubeconfig=devuser.kubeconfig

## 设置上下文context，写入config文件
kubectl config set-context kubernetes \
--cluster=kubernetes \
--user=devuser \
--namespace=dev \
--kubeconfig=devuser.kubeconfig

# 设置context激活
kubectl config use-context kubernetes --kubeconfig=devuser.kubeconfig

# 创建一个权限绑定rolebinding-clusterrole,名字是devuser-admin-binding，权限给用户devuser，作用namespace=dev
kubectl create rolebinding devuser-admin-binding --clusterrole=admin --user=devuser --namespace=dev
```

配合linux做隔离

```
# 查看官方已经准备好的集群角色
kubectl get clusterrole
```



## 准入控制

+ 额外功能的添加
+ 有权限但是不合理行为的过滤



# HELM

+ Chart：是创建一个应用的信息集合，包含各种k8s对象的配置模版、参数定义、依赖关系、文档说明等。时应用部署的自包含逻辑单元。可以理解为类似镜像。
+ Release：是chart的运行实例，代表了一个正在运行的应用。当chart被安装到k8s集群，就生成一个release。chart能够多次安装到同一个集群，每次安装都是一个release。可以理解为容器。

+ Helm cli：helm客户端组件，负责和api server通信
+ Repository：用于发布和存储chart的仓库

```
# 查看chart中的可配置选项
helm show values bitnami/apache

# 使用yaml格式的文件覆盖上述任意配置选项，并在安装过程中使用该文件
vim values.yaml
service:
	type:NodePort

helm install -f values.yaml bitnamei/apache --generate-name

# 升级
helm upgrade -f values.yaml release名 chartming

# 查看配置是否生效
helm get values release名

# 回滚
helm rollback release名 版本名

# 查看修订版本
helm history release名

# 删除
helm uninstall release名 --keep-history（保留记录）
```

## 创建自己的chart

```
# 创建一个模版
helm create myapp
# 删除不要的文件
rm -rf values.yaml templates/
# 编写templates下的service和deployment资源清单
[root@k8s-master01 templates]# cat nodePort.yaml 
apiVersion: v1
kind: Service
metadata:
  labels:
    app: myapp-test
  name: myapp-test-202601121623-svc
spec:
  ports:
    - name: 80-80
      port: 80
      protocol: TCP
      targetPort: 80
      nodePort: 31111
  selector:
    app: myapp-test
  type: NodePort
  
[root@k8s-master01 templates]# cat deployment.yaml 
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-test-202601121623-deploy
  labels:
    app: myapp-test
spec:
  replicas: 5
  selector:
    matchLabels:
      app: myapp-test
  template:
    metadata:
      labels:
        app: myapp-test
    spec:
      containers:
      - image: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share:myappv1.0
        name: myapp

# 部署发布
helm install myapp myapp/
```

## 动态性

```
# 编辑NOTES.txt文件，这个文件时helm install时的提示信息
[root@k8s-master01 myapp]# vi templates/NOTES.txt
1、这是一个测试的 myapp chart                                    
                                                                 
2、myapp release 名字: myapp-test-{{ now | date "20060102030405" }}-deploy
                                                                 
3、service 名字: myapp-test-{{ now | date "20260102030405" }}-svc 

# 编辑deployment资源文件
[root@k8s-master01 templates]# vi deployment.yaml 
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-test-{{ now | date "20060102030405" }}-deploy
  labels:
    app: myapp-test
spec:  
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: myapp-test
  template:
    metadata:
      labels:
        app: myapp-test
    spec:
      containers:
      - image: {{ .Values.image.repository }}:{{ .Values.image.tag }}                                                                                           
        name: myapp
        
# 编辑service资源文件
[root@k8s-master01 templates]# vi nodePort.yaml 
apiVersion: v1
kind: Service
metadata:
  labels:
    app: myapp-test
  name: myapp-test-{{ now | date "20060102030405" }}-svc
spec:
  ports:
    - name: 80-80
      port: 80
      protocol: TCP
      targetPort: 80
      {{- if eq .Values.service.type "NodePort" }}
      nodePort: {{ .Values.service.nodeport }}
      {{- end}}
  selector:
    app: myapp-test
  type: {{ .Values.service.type | quote }}

# 编辑values文件，定义变量值
[root@k8s-master01 myapp]# vi values.yaml 
# Default values for myapp.
# This is a YAML-formatted file.
# Declare variables to be passed into your templates.
 
replicaCount: 5
                                                                                                                                                                
image:
  repository: registry.cn-hangzhou.aliyuncs.com/wangyangshare/share
  tag: "v1.0"
 
service:
  type: NodePort
  nodeport: 32321
```



## ingress-nginx（已经停止维护）

```
修改values.yaml文件
1- 修改hostNetwork的值为true
2-dnsPolicy的值修改为: ClusterFirstWithHostNet
3-kind类型更改为: DaemonSet
4-关闭所有镜像的digest
5-ingressClassResource.default=true

关于dnsPolicy
ClusterFirstWithHostsNet：
- 当Pod的hostNetwork设置为true时，使用该DNS策略。
- 这意味着Pod的网络命名空间与主机共享，Pod使用主机的网络线。
- 在此配置下，Pod将首先尝试通过主机上的DNS解析DNS请求，如果主机上没有找到，则会将请求发送到kube-dns服务，由kube-dns进行处理。
- 这种策略适用于需要主机与主机网络共享的特殊情况，但它不会为Pod提供专用的DNS解析功能。

ClusterFirst：
- 这是kubernets中默认的DNS策略。
- 当Pod的hostNetwork设置为false或未设置时，使用该策略。
- 在此策略下，Pod首先尝试通过kube-dns解析DNS请求。如果kube-dns无法解析，则会向上级DNS服务器继续发起请求。
- 这种策略适用于大多数情况，其中Pod需要使用Kubernetes集群中的DNS服务解析其他pod或服务的主机名
```

## Gateway API （代替ingress）





# 镜像仓库Harbor

### 创建名字空间

```
[root@k8s-master01 habor]# vi namespace-harbor.yaml
apiVersion: v1 
kind: Namespace                                                            
metadata:      
  name: harbor 
```



# 日志

## 以前的EFK或者ELK方案（分布式日志收集方案）

日志收集：fluentd、Logstash

存储端：elastic search

GUI：kibana

优势：功能完善、丰富案例

劣势：资源消耗量大、灵活性差

## Loki

收集：Prom tail（停止维护）=====>Grafana Alloy

存储端：Grafana loki

GUI：Grafana

优势：资源消耗低、灵活性强-云原生、搜索速度快

劣势：案例少



# 资源监控（prometheus）

组件：

cAdvisor----->Prometheus

Kube-state-metrics\metrics server

grafana、Alertmanager



