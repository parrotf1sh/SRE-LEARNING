# 基本配置

```
#设置
git config --global user.name "fishbone"
git config --global user.email "fishbone@gmail.com"

#查看
git config --global user.name
git config --global user.email

~/.bashrc
# 用于输出git提交日志
alias git-log='git log --pretty=oneline --all --graph --abbrev-commit'
# 用于输出当前目录所有文件及基本信息
alias ll='ls -al'

source ~/.bashrc
```

# 本地仓库

```
# 初始化当前目录为git仓库
git init

git add		(工作区 => 暂存区)
git commit		(暂存区 => 本地仓库)

======>
git add .
git commit -m "注释"

# 查看修改的状态
git status
#查看提交日志
git log
	--all	显示所有分支
	--pretty=oneline	将提交信息显示为1行
	--abbrev-commit	使输出的commitid更简短
	--graph	以图的形式显示
	
# 版本回退
git reset --hard commitID
# 主要是找ID然后控制版本
git reflog
```

# 分支

```
# 查看本地分支
git branch
# 创建本地分支
git branch 分支名
# 切换分支
git checkout 分支名
## 创建并切换
git checkout -b 分支名
# 合并分支
git merge 另一个分支名   #把另一个分支合并到当前分支
# 删除分支
git branch -d 分支名
git branch -D 分支名			#强制删除
```

### 规范

master（生产）分支

======>线上分支，主分支，中小规模项目作为线上运行的应用对应的分支

develop（开发）分支

======>是从master创建的分支，值班作为开发部门的主要开发分支，如果没有其他并行开发不同期上线要求，都可以在此版本进行开发，阶段开发完成后，需要合并到master分支，准备上线

feature/xxx分支

======>由develop创建的分支，一般是同期并行开发，但不同期上线时创建的分支，分支上的人研发任务完成后合并到develop分支

hotfix/xxx分支

======>由master派生的分支，一般作为线上bug修复使用，修复完成后需要合并到master、test、develop分支

test（测试）、pre（预上线）

# 远程仓库

```
git remote add origin SSH
# origin 通用远端名称

# 推送
git push [-f] [--set-upstream] [远端名称 [本地分支名][:远端分支名]]
	# 如果远程分支名和本地分支名相同，可以只写本地分支
	git push origin master
	# --set-upstream 推送到远端的同时并且建立起和远端分支的关联关系
	git push --set-upstream origin master
	# 如果当前分支已经和远端分支关联，则可以省略分支名和远端名
	git push
	
# 查看关联关系
git branch -vv

# 抓取
# 将仓库里的更新都抓取到本地，不进行合并
# 若不指定远端名称和分支名，则抓取所有分支
git fetch [remote name] [branch name]

# 拉取
# 将远端仓库的修改拉到本地并自动进行合并，等同于fetch+merge
# 若不指定远端名称和分支名，则抓取所有并更新当前分支
git pull [remote name] [branch name]
```



**切换分支前先提交本地的修改**