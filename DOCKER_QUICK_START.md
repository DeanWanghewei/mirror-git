# Docker 快速启动指南

## 📦 已生成的文件清单

✅ `Dockerfile` - 支持 x86 架构的多阶段构建
✅ `docker-compose.yml` - 完整的 Docker Compose 配置
✅ `.dockerignore` - 构建时排除的文件列表
✅ `docker/mysql/my.cnf` - MySQL 配置文件
✅ `.env.docker.example` - Docker 环境变量示例
✅ `DOCKER_DEPLOYMENT.md` - 详细部署文档
✅ `requirements.txt` - 已添加 PyMySQL 驱动

---

## 🚀 3 步快速启动

### 1️⃣ 配置环境变量

```bash
# 复制示例配置
cp .env.docker.example .env

# 编辑 .env 文件，修改以下关键信息：
# - GITHUB_TOKEN: 你的 GitHub Token
# - GITEA_URL: Gitea 服务器地址
# - GITEA_TOKEN: Gitea API Token
# - MYSQL_PASSWORD: MySQL 密码（生产环境必改）
```

### 2️⃣ 启动服务

```bash
# 构建镜像并启动（第一次会下载基础镜像，需要几分钟）
docker-compose up -d

# 等待 MySQL 完全启动（约 30 秒）
docker-compose logs -f mysql
```

### 3️⃣ 验证服务

```bash
# 查看容器状态（都应为 Up）
docker-compose ps

# 检查应用是否正常运行
curl http://localhost:8000/api/health

# 打开浏览器访问 Web UI
# http://localhost:8000
# http://localhost:8000/docs (API 文档)
```

---

## 📋 关键特性

### ✨ x86 架构支持
- Dockerfile 使用官方 Python 3.11 基础镜像
- docker-compose.yml 明确指定 `platform: linux/amd64`
- 多阶段构建优化镜像大小（约 800MB）

### 🗄️ MySQL 集成
- MySQL 8.0 自动集成
- 完整的数据库初始化
- 数据持久化存储
- 自定义配置文件支持

### 🔧 完全可配置
```env
# 数据库连接自动配置
DATABASE_URL=mysql+pymysql://mirror_user:mirror123456@mysql:3306/mirror_git?charset=utf8mb4

# 所有应用参数都可通过环境变量修改
GITHUB_TOKEN=...
GITEA_URL=...
SYNC_INTERVAL=3600
LOG_LEVEL=INFO
```

---

## 📊 常用命令

```bash
# 查看日志
docker-compose logs -f app          # 应用日志
docker-compose logs -f mysql        # MySQL 日志

# 进入容器
docker-compose exec app bash        # 进入应用容器
docker-compose exec mysql bash      # 进入MySQL容器

# 数据库操作
docker-compose exec mysql mysql -u mirror_user -pmirror123456 -D mirror_git

# 备份数据库
docker-compose exec mysql mysqldump -u mirror_user -pmirror123456 mirror_git > backup.sql

# 停止服务
docker-compose stop                 # 保留数据
docker-compose down -v              # 删除所有（包括数据）

# 更新应用
docker-compose build --no-cache     # 重新构建镜像
docker-compose up -d                # 重新启动
```

---

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|-----|------|------|
| Web UI | http://localhost:8000 | 主应用界面 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| ReDoc | http://localhost:8000/redoc | 备用文档 |
| MySQL | localhost:3306 | 数据库连接 |

---

## 🔐 生产环境建议

### 1. 修改默认密码
```env
MYSQL_ROOT_PASSWORD=your_secure_password_here
MYSQL_PASSWORD=your_secure_password_here
```

### 2. 添加资源限制
在 `docker-compose.yml` 中添加：
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 3. 设置定期备份
```bash
# 备份脚本
docker-compose exec mysql mysqldump -u mirror_user -pmirror123456 mirror_git | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 4. 启用日志持久化
```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## ❓ 故障排除

### MySQL 连接失败
```bash
# 检查 MySQL 是否启动
docker-compose ps mysql

# 查看 MySQL 日志
docker-compose logs mysql

# 检查网络连接
docker-compose exec app ping mysql
```

### 应用无法启动
```bash
# 查看应用启动日志
docker-compose logs app

# 检查数据库配置
docker-compose exec app env | grep DATABASE
```

### 磁盘空间不足
```bash
# 清理未使用的镜像和容器
docker system prune -a --volumes
```

---

## 📚 更多信息

详细的部署文档请参考：[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

## ✅ 检查清单

部署前请确认：

- [ ] 已修改 `.env` 中的所有必要配置
- [ ] GitHub Token 和 Gitea Token 已正确配置
- [ ] MySQL 密码已修改（生产环境）
- [ ] 服务器有足够的磁盘空间（至少 2GB）
- [ ] 8000 和 3306 端口未被占用
- [ ] Docker 和 Docker Compose 已安装

---

**祝你使用愉快！** 如有问题，请查阅详细文档或提交 Issue。
