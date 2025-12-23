# SQLite 数据库路径配置说明

## 问题说明

在配置 SQLite 数据库时，很多用户会遇到数据库文件创建在错误位置的问题。例如：

❌ **错误示例**：设置 `DATABASE_URL=sqlite:///app/data/mirror_sync.db`，但数据库却创建在 `/app/app/data/mirror_sync.db`

这是因为对 SQLite URL 格式理解不正确导致的。

## SQLite URL 格式详解

SQLite URL 的斜杠数量决定了路径是相对路径还是绝对路径：

### 格式 1：绝对路径（4个斜杠）✅ 推荐

```
sqlite:////app/data/mirror_sync.db
       ↑   ↑
       |   |
       |   +-- 绝对路径的开头（Linux 下路径以 / 开头）
       |
       +------ SQLite 协议固定的 3 个斜杠
```

**解释**：
- 前3个斜杠 `sqlite:///` 是 SQLite URL 的固定格式
- 第4个斜杠 `/` 是 Linux 绝对路径的开头
- 最终路径：`/app/data/mirror_sync.db`（绝对路径）

**示例**：
```bash
DATABASE_URL='sqlite:////app/data/mirror_sync.db'
# 数据库文件位置：/app/data/mirror_sync.db
```

### 格式 2：相对路径（3个斜杠）

```
sqlite:///data/mirror_sync.db
       ↑  ↑
       |  |
       |  +-- 相对路径（不以 / 开头）
       |
       +------ SQLite 协议固定的 3 个斜杠
```

**解释**：
- 前3个斜杠 `sqlite:///` 是 SQLite URL 的固定格式
- `data/mirror_sync.db` 是相对路径
- 相对于当前工作目录（在 Docker 容器中是 `/app`）
- 最终路径：`/app` + `data/mirror_sync.db` = `/app/data/mirror_sync.db`

**示例**：
```bash
DATABASE_URL='sqlite:///data/mirror_sync.db'
# 容器工作目录：/app
# 数据库文件位置：/app/data/mirror_sync.db
```

## 常见错误案例

### 案例 1：多余的路径前缀

❌ **错误配置**：
```bash
DATABASE_URL='sqlite:///app/data/mirror_sync.db'
```

**问题分析**：
- SQLite URL：`sqlite:///app/data/mirror_sync.db`（3个斜杠）
- 这被解释为相对路径：`app/data/mirror_sync.db`
- 容器工作目录：`/app`
- 实际路径：`/app` + `app/data/mirror_sync.db` = `/app/app/data/mirror_sync.db` ❌

**验证方法**：
```bash
# 进入容器
docker exec -it mirror-git-app bash

# 查找数据库文件
find / -name "mirror_sync.db" 2>/dev/null

# 会发现文件在 /app/app/data/mirror_sync.db
ls -lh /app/app/data/
```

✅ **正确配置**：
```bash
# 方案 A：使用绝对路径（4个斜杠）
DATABASE_URL='sqlite:////app/data/mirror_sync.db'

# 方案 B：使用相对路径（3个斜杠，但去掉 app）
DATABASE_URL='sqlite:///data/mirror_sync.db'
```

### 案例 2：Windows 风格路径

❌ **错误配置**：
```bash
DATABASE_URL='sqlite:///C:/app/data/mirror_sync.db'
```

这是 Windows 风格路径，在 Linux Docker 容器中不适用。

✅ **正确配置**：
```bash
DATABASE_URL='sqlite:////app/data/mirror_sync.db'
```

## 推荐配置

### Docker 部署（推荐使用绝对路径）

```bash
docker run -d \
  --name mirror-git-app \
  -p 8000:8000 \
  -e DATABASE_URL='sqlite:////app/data/mirror_sync.db' \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  mirror-git:latest
```

**优点**：
- ✅ 明确指定绝对路径，不依赖工作目录
- ✅ 不容易出错
- ✅ 一看就知道文件在哪里

### 本地开发（可以使用相对路径）

```bash
# .env 文件
DATABASE_URL=sqlite:///data/mirror_sync.db

# 等价于
DATABASE_URL=sqlite:////app/data/mirror_sync.db
```

## 验证配置是否正确

### 方法 1：查看启动日志

```bash
docker logs mirror-git-app | grep -i "database"
```

应该看到类似输出：
```
✓ Database URL: sqlite:////app/data/mirror_sync.db
✓ SQLite database directory created: /app/data
✓ Database file path: /app/data/mirror_sync.db
✓ Database initialized successfully
```

### 方法 2：进入容器检查文件

```bash
# 进入容器
docker exec -it mirror-git-app bash

# 查看数据库文件
ls -lh /app/data/*.db

# 应该看到
# -rw-r--r-- 1 root root 12K Jan 1 12:00 /app/data/mirror_sync.db
```

### 方法 3：查找所有数据库文件

```bash
docker exec mirror-git-app find / -name "*.db" -type f 2>/dev/null
```

如果发现文件在 `/app/app/data/` 下，说明配置错误。

## 快速修复指南

如果发现数据库在错误位置：

```bash
# 1. 停止容器
docker stop mirror-git-app

# 2. 进入容器（不启动应用）
docker exec -it mirror-git-app bash

# 3. 移动数据库到正确位置
mv /app/app/data/mirror_sync.db /app/data/mirror_sync.db

# 4. 退出容器
exit

# 5. 使用正确的配置重启
docker rm mirror-git-app
docker run -d \
  --name mirror-git-app \
  -p 8000:8000 \
  -e DATABASE_URL='sqlite:////app/data/mirror_sync.db' \
  -v $(pwd)/data:/app/data \
  mirror-git:latest
```

## 总结

| 配置 | 含义 | 实际路径 | 推荐 |
|------|------|----------|------|
| `sqlite:////app/data/sync.db` | 绝对路径 | `/app/data/sync.db` | ✅ 推荐 |
| `sqlite:///data/sync.db` | 相对路径 | `/app/data/sync.db` | ✅ 可用 |
| `sqlite:///app/data/sync.db` | 相对路径 | `/app/app/data/sync.db` | ❌ 错误 |

**记住**：
- 在 Docker 容器中，**4个斜杠 = 绝对路径**
- **3个斜杠 = 相对于工作目录**（容器工作目录是 `/app`）
- 推荐使用 **4个斜杠的绝对路径**，避免混淆

## 相关文档

- [数据恢复指南](./DATA_RECOVERY.md)
- [故障排查指南](./TROUBLESHOOTING.md)
- [MySQL 配置指南](./MYSQL_CONFIG.md)
