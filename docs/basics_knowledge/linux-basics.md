### ls

-a all 全部文件
-l list
-h 看文件大小和 -l组合使用 -lh

### cd

change directory
cd 不带路径回到home

### pwd

print work directory

| 目录  | 类型       | 核心特点                 | 持久保存？     |
| :---- | :--------- | :----------------------- | :------------- |
| /etc  | 配置       | 静态配置文件             | 磁盘持久       |
| /var  | 可变数据   | 日志、数据库、运行数据   | 磁盘持久       |
| /proc | 伪文件系统 | 内核 / 进程实时信息      | 内存，重启消失 |
| /home | 用户目录   | 用户代码、文件、ssh 密钥 | 磁盘持久       |
| /tmp  | 临时目录   | 临时缓存文件             | 重启清空       |

### mkdir

make directory
mkdir [-p] path
-p 自动创建不存在的父目录，适用于创建连续多层级目录
mkdir -p sre/learn/test

### touch 创建文件

### cat/more（空格翻页，q退出查看） 查看文件

### less（比more更好用）

常用快捷键：

- `空格`：向下翻一页
- `b`：向上翻一页
- `回车`：向下一行
- `↑ ↓`：上下单行移动
- `/关键词`：向下搜索，`n` 下一个匹配，`N` 上一个
- `?关键词`：向上搜索
- `q`：退出 less
- `g`：跳到文件开头；`G`：跳到文件末尾（看日志很常用）

### cp [-r] 参数1 参数2
-r 用于复制文件夹使用，表示递归

### mv path1 path2
若path2不存在，则是改名

### rm
rm [-r -f] 参数1 参数2 ...... 参数n
-r 用于删除目录
-f 表示force 强制删除
可以用通配符

 ### which 要查找的命令

### find 起始路径 -name "被查找文件名"
可以使用通配符*
#### find 起始路径 -size +/-n[kMG]

+、-表示大于小于 n表示大小数字 k(小写字母)MG表示单位
查找小于10KB文件 find / -size -10k

### grep 从文件中通过关键字过滤文件行
grep [-n] 关键字 文件路径
-n 表示在结果中显示匹配的行的行号
关键字用""包围

### wc 统计文件的行数、单词数量
wc [-c -m -l -w] 文件路径
-c 统计bytes数量
-m 统计字符数量
-l 统计行数
-w 统计单词数量

### |管道符
将管道符左边命令的结果，作为右边命令的输入
cat test.txt | grep "关键词"
cat test.txt | wc -l
ls | grep "test" 效果是过滤出test文件
ls -l /usr/bin | grep xxd
ls -l /user/bin | wc -l 效果是可以看这个文件夹下有多少个文件，因为显示了行数
还可以嵌套使用
统计文件中带有itcast关键字有几行
cat test.txt | grep itcast | wc -l

### echo 参数

#### 反引号``   （mac键盘con+com+空格 搜grave）

被反引号包围的内容会被当命令执行

echo pwd 返回 pwd，而echo `pwd` 返回的是当前路径

### 重定向符

\> 将左侧命令结果**覆盖**写入符号右侧指定文件中

\>> 将左侧命令结果**追加**写入符号右侧指定文件中

### tail [-f -num] 路径

跟踪文件

-f 表示持续跟踪

-num 表示查看尾部多少行 不填默认10行

### vi/vim

命令模式：不能进行文本编辑，所敲按键全为命令，以命令驱动执行不同的功能

输入模式：编辑模式

底线命令模式：通常用于保存、退出

命令 i 当前光标位置进入输入模式

​	a 当前光标之后进入输入模式

​	I 当前行开头 A当前行结尾

​	o 当前光标下一行 O当前光标上一行

​	/ 进入搜索模式 n向下继续搜索 N向上继续搜索

底线命令 :set nu 显示行号 :set paste (仅黏贴文本防止格式错乱)

### su [-] [用户名]（switch user）

\- 表示是否在切换用户后加载环境变量

用户名省略默认切换到root

exit回退上一个用户或ctrl+d

### sudo 其他命令

临时为这一条命令赋予root权限（需要配置sudo认证）

用root用户执行visudo，自动打开/etc/sudoers

在文件最后一行中添加: (NOPASSWD:ALL表示使用sudo命令无需输入密码

```
用户名 ALL=(ALL)	NOPASSWD:ALL   （中间为tab制表符）
```

### 用户组管理（需要root用户执行）

创建用户组 groupadd 用户组名

删除用户组 groupdel 用户组名

### 用户管理

#### 创建用户 useradd [-g -d] 用户名 

-g指定用户的组，不指定就会创建同名组并加入 

-d指定用户home路径，不指定默认在/home/用户名

#### 删除用户 userdel [-r] 用户名  

-r删除用户的home目录

#### 查看用户所属组 id [用户名]

#### 修改用户所属组 usermod -aG 用户组 用户名

### getent passwd 查看当前系统中有哪些用户

![截屏2026-10-13 21.01.16](/Users/ygding/文件/sre-lreaning/week1/截屏2026-10-13 21.01.16.png)

用户名：密码（x）：用户id：组id：描述信息（无用）：HOME目录：执行终端（默认bash）

### getent group 查看用户组

组名称：组认证（x）：组id

![截屏2026-10-13 21.08.03](/Users/ygding/文件/sre-lreaning/week1/截屏2026-10-13 21.08.03.png)

文件文件夹的权限控制信息｜文件文件夹所属用户｜文件文件夹所属用户组

权限信息 共十个槽位

第1位 -或d或l -表示文件 d表示目录 l表示软链接  

后9位 r或- w或- x或- 分别为所属用户权限 所属用户组权限 其他用户权限

r 若为文件夹，则表示可以查看文件夹内容 如ls

w 若为文件夹，则表示可以在文件夹内创建删除改名

x 表示文件可以作为程序执行；若为文件夹，则表示可以更改工作目录到此文件夹，即cd

### chmod

```
chmod [-R] 权限 文件或文件夹
```

-R 对文件夹内全部内容应用同样的操作

chmod u=rwx,g=rx,o=x hello.txt

**r记为4，w记为2，x记为1**

751 rwx（7）r-x（5）--x（1）

chmod 751 hello.txt

### chown

```
chown [-R] [用户]:[用户组] 文件或文件夹
```

### history 

查看历史输入过的命令

可以通过 !命令前缀，自动执行上一次匹配前缀的命令

ctrl + r 输入内容匹配历史命令

### 安装

centOS：yum [-y] [install / remove / search] 软件名称

ubuntu：apt [-y] [install / remove / search] 软件名称

### systemctl

控制软件启动、停止、开机自启

```
systemstl start / stop / status / enable / disable 服务名
```

enable 开启开机自启

### 软链接

```
ln -s 参数1 参数2
```

-s 创建软链接 参数1 被链接的文件（夹） 参数2 要链接去的目的地

ln -s /etc/yum.conf ~/yum.conf

### date

```
date [-d] [+%Y-%m-%d %H:%M:%S]
```

-d 按照给定的字符串显示日期，用于日期计算

Date -d "+1 day" +%Y-%m-%d 表示显示后一天的日期

### ps -ef

查看进程信息

`aux` = **查看系统全部进程 + 带上 CPU / 内存等资源信息** ps aux和ps -ef差不多

kill [-9] 进程号 关闭指定进程号的进程，-9表示强制关闭

### top

查看系统资源占用

### df -h

磁盘信息监控

或 iostat -x

### sar -n DEV num1 num2

-n 查看网络 DEV表示查看网络接口。num1表示刷新间隔，num2表示查看次数

### ping [-c num] ip或主机名

### wget [-b] url

-b为后台下载

### curl [-O] url

-O 用于文件下载



### 环境变量 env

$符号被用于取变量的值

echo $PATH  就可以取得PATH这个环境变量的值

echo ${PATH}ABC 就可以在后面拼接上ABC字符串

#### 自行设置环境变量

临时设置：export 变量名=变量值

永久生效：针对当前用户 ～/.bashrc      针对所有用户 /etc/profile     然后source 配置文件，进行立刻生效

export PATH=$PATH:/root/software 这样这个目录下的可执行文件就可以直接在其他目录也可以执行

### rz、sz 上传、下载

安装lrzsz包

### tar

.tar tarball 归档文件 仅仅是简单的封装

.gz 也常见为.tar.gz，gzip格式压缩文件 使用gzip压缩算法将文件压缩到一个文件内

```
tar [-c -v -x -f -z -C] 参数1 参数2 ... 参数N

-c 压缩
-v 展示压缩解压缩过程
-x 解压
-f 要创建的文件或要解压的文件，**这个选项必须在选项的最后一个**
-z gzip模式，若不使用就是普通的tarball格式
-C 选择解压的目的地 这个选项单独使用
```

eg：

```
tar -cvf test.tar 1.txt 2.txt 3.txt
将这三个txt压缩到test.tar
tar -zcvf test.tar.gz 1.txt 2.txt 3.txt
将这三个txt压缩到test.tar.gz

tar -xvf test.tar
tar -xvf test.tar -C /home/test
tar -zxvf test.tar.gz -C /home/test 
```

### zip/unzip

```
zip [-r] 参数1 参数2 ... 参数N
-r，被压缩的包含文件夹时

zip test.zip 1.txt 2.txt 3.txt
将这三个txt压缩到test.zip
zip -r test.zip test 2.txt 3.txt
将这test文件夹和2个txt压缩到test.zip

unzip [-d] 参数
-d 指定要解压取的位置
unzip test.zip
unzip test.zip -d /home/test
```

