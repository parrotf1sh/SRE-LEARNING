# 在项目根目录执行，打包项目构建镜像
```
docker build -t task-api:版本 -f docker/task-api/Dockerfile task-api/
```



# Nginx 配置更新

```
# 进入容器执行 reload 命令
docker exec nginx nginx -s reload
# 验证配置
docker compose logs -f nginx
```



# Task-API 更新

```
# 1. 只重新构建并启动 task-api（其他服务不受影响）
docker compose up -d --build task-api

# 2. 查看新容器的日志
docker compose logs -f task-api

# 3. 验证服务正常
curl http://localhost/health

# 开发阶段：代码改动后快速更新
docker compose up -d --build task-api

# 生产环境：使用预构建的镜像
docker pull your-registry/task-api:v1.2.3
docker compose up -d task-api

# 回滚到上一个版本
docker pull your-registry/task-api:v1.2.2
docker compose up -d task-api
```

