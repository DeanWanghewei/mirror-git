# Mirror-Git 远程诊断手册

## 快速诊断命令

如果您的 Docker 容器在远程服务器上，请 SSH 到远程服务器后执行以下命令：

### 步骤 1: 查找容器

```bash
# 查找运行中的容器
docker ps | grep mirror-git

# 或查找所有容器（包括已停止的）
docker ps -a | grep mirror-git

# 记下容器名称，例如：mirror-git-app
```

### 步骤 2: 检查环境变量

```bash
# 将 mirror-git-app 替换为您的容器名称
CONTAINER_NAME="mirror-git-app"

# 检查 Gitea 配置
echo "=== Gitea 配置 ==="
docker exec $CONTAINER_NAME env | grep GITEA

# 应该看到：
# GITEA_URL=http://...
# GITEA_TOKEN=...
# GITEA_USERNAME=...
```

**如果环境变量为空或缺失**，说明 `-e` 参数没有生效，需要重新启动容器。

### 步骤 3: 测试 Gitea Token 权限

```bash
# 获取环境变量
GITEA_URL=$(docker exec $CONTAINER_NAME env | grep "^GITEA_URL=" | cut -d'=' -f2-)
GITEA_TOKEN=$(docker exec $CONTAINER_NAME env | grep "^GITEA_TOKEN=" | cut -d'=' -f2-)

# 测试 API 连接
docker exec $CONTAINER_NAME curl -i -H "Authorization: token $GITEA_TOKEN" \
  $GITEA_URL/api/v1/user

# 检查响应：
# - HTTP/1.1 200 OK  ✅ Token 有效
# - HTTP/1.1 401     ❌ Token 无效或过期
# - HTTP/1.1 403     ❌ Token 权限不足（这就是您的问题！）
```

### 步骤 4: 测试创建仓库权限

```bash
# 测试创建仓库（这个会暴露权限问题）
docker exec $CONTAINER_NAME curl -i -X POST \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"test-repo-temp","private":true}' \
  $GITEA_URL/api/v1/user/repos

# 检查响应：
# - HTTP/1.1 201 Created  ✅ 权限正常
# - HTTP/1.1 403 Forbidden ❌ 权限不足（您的问题）
```

## 常见问题和解决方案

### 问题 1: 环境变量缺失（`docker exec` 看不到环境变量）

**原因**: Docker 启动时 `-e` 参数未生效

**解决方案**:

```bash
# 1. 停止并删除容器
docker stop mirror-git-app
docker rm mirror-git-app

# 2. 重新启动，注意环境变量要用引号
docker run -d \
  --name mirror-git-app \
  -p 8020:8000 \
  -e GITEA_URL='http://192.168.9.101:8418' \
  -e GITEA_TOKEN='82f6ab15a488048ea3524aa797bb4774b8bf8e00' \
  -e GITEA_USERNAME='deanwang' \
  -e DATABASE_URL='sqlite:////app/data/mirror_sync.db' \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  deanwang/mirror-git:v1.9

# 3. 验证环境变量
docker exec mirror-git-app env | grep GITEA
```

### 问题 2: Token 权限不足（HTTP 403）

**症状**:
```
[2025-12-23 01:17:23] WARNING  gitea_client - Permission denied creating repository
```

**原因**: Gitea Token 没有创建仓库的权限

**解决方案**:

1. **登录 Gitea Web 界面**
   ```
   访问: http://192.168.9.101:8418
   ```

2. **进入 Token 管理页面**
   ```
   右上角头像 → 设置 → 应用程序 → 管理访问令牌
   ```

3. **创建新的 Token，确保勾选以下权限**:
   - ✅ `write:repository` - 仓库写入权限
   - ✅ `write:organization` - 组织管理权限（如果使用组织）
   - ✅ `read:user` - 用户信息读取
   - ✅ `write:user` - 用户信息写入

4. **复制新 Token，更新容器**:
   ```bash
   NEW_TOKEN="新生成的token"

   docker stop mirror-git-app
   docker rm mirror-git-app

   docker run -d \
     --name mirror-git-app \
     -p 8020:8000 \
     -e GITEA_URL='http://192.168.9.101:8418' \
     -e GITEA_TOKEN="$NEW_TOKEN" \
     -e GITEA_USERNAME='deanwang' \
     -e DATABASE_URL='sqlite:////app/data/mirror_sync.db' \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/logs:/app/logs \
     deanwang/mirror-git:v1.9
   ```

5. **验证新 Token**:
   ```bash
   docker exec mirror-git-app env | grep GITEA_TOKEN
   ```

### 问题 3: Token 格式错误

**检查 Token 格式**:
```bash
docker exec mirror-git-app env | grep GITEA_TOKEN

# 应该类似：
# GITEA_TOKEN=82f6ab15a488048ea3524aa797bb4774b8bf8e00
# 长度通常是 40 个字符
```

如果 Token 不是 40 个字符，或包含特殊字符，可能格式错误。

## 查看详细日志

```bash
# 查看最近 50 行日志
docker logs mirror-git-app --tail 50

# 实时查看日志
docker logs -f mirror-git-app

# 查看容器内的日志文件
docker exec mirror-git-app tail -100 /app/logs/sync.log
```

## 诊断脚本

我们提供了一键诊断脚本，将脚本上传到服务器后执行：

```bash
# 1. 上传 diagnose_remote.sh 到服务器

# 2. 赋予执行权限
chmod +x diagnose_remote.sh

# 3. 运行诊断
./diagnose_remote.sh
```

## 验证修复

修复后，测试同步：

```bash
# 方法 1: 通过 Web UI
# 访问 http://your-server:8020
# 手动触发一个仓库同步

# 方法 2: 通过 API
curl -X POST http://your-server:8020/api/sync/repository \
  -H "Content-Type: application/json" \
  -d '{"name":"test-repo","url":"https://github.com/user/test-repo"}'

# 方法 3: 查看日志确认
docker logs -f mirror-git-app
```

## 最可能的原因

根据您的错误信息：
```
Permission denied creating repository skills
```

**99% 的可能性是 Gitea Token 权限不足**。

请按照 **问题 2** 的步骤重新生成一个具有完整权限的 Token。

---

如需进一步帮助，请提供：
1. `docker exec mirror-git-app env | grep GITEA` 的输出
2. Token 权限测试的 HTTP 状态码
3. Gitea 版本号
