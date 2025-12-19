# Docker 部署指南

## 概述

本项目支持通过 Docker 和 Docker Compose 进行部署，包括：
- x86/amd64 架构支持
- MySQL 数据库集成
- 完整的环境配置管理

## 前置要求

- Docker 版本 20.10+
- Docker Compose 版本 1.29+
- 至少 2GB 可用磁盘空间

## 快速开始

### 1. 克隆或进入项目目录

```bash
cd /path/to/mirror-git
```

### 2. 配置环境变量

创建 `.env` 文件（基于 `.env.example`）：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键信息：

```env
# GitHub 配置
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_OWNER=your_username

# Gitea 配置
GITEA_URL=https://gitea.example.com
GITEA_TOKEN=your_gitea_api_token_here
GITEA_USERNAME=mirror_user
GITEA_PASSWORD=your_gitea_password_or_token

# MySQL 数据库配置
MYSQL_ROOT_PASSWORD=root123456
MYSQL_DATABASE=mirror_git
MYSQL_USER=mirror_user
MYSQL_PASSWORD=mirror123456
MYSQL_PORT=3306

# 应用配置
APP_PORT=8000
LOG_LEVEL=INFO
SYNC_INTERVAL=3600
```

### 3. 启动服务

```bash
# 构建镜像并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 查看MySQL日志
docker-compose logs -f mysql
```

### 4. 验证服务状态

```bash
# 检查所有容器状态
docker-compose ps

# 检查应用健康状态
curl http://localhost:8000/api/health

# 检查API文档
# 浏览器访问: http://localhost:8000/docs
```

## 详细配置说明

### GitHub 配置

| 环境变量 | 说明 | 必需 |
|--------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | 是 |
| `GITHUB_API_URL` | GitHub API 地址（默认官方）| 否 |
| `GITHUB_OWNER` | GitHub 用户名或组织名 | 否 |

获取 Token：https://github.com/settings/tokens

### Gitea 配置

| 环境变量 | 说明 | 必需 |
|--------|------|------|
| `GITEA_URL` | Gitea 服务器地址 | 是 |
| `GITEA_TOKEN` | Gitea API Token | 是 |
| `GITEA_USERNAME` | Gitea 用户名 | 是 |
| `GITEA_PASSWORD` | Gitea 密码或 Token | 是 |

### MySQL 数据库配置

| 环境变量 | 说明 | 默认值 |
|--------|------|-------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | root123456 |
| `MYSQL_DATABASE` | 数据库名称 | mirror_git |
| `MYSQL_USER` | 数据库用户名 | mirror_user |
| `MYSQL_PASSWORD` | 数据库用户密码 | mirror123456 |
| `MYSQL_PORT` | MySQL 端口 | 3306 |

**重要**：生产环境中请修改默认密码！

### 应用同步配置

| 环境变量 | 说明 | 默认值 |
|--------|------|-------|
| `SYNC_INTERVAL` | 同步间隔（秒） | 3600 |
| `SYNC_TIMEOUT` | 同步超时（秒） | 1800 |
| `MAX_RETRIES` | 最大重试次数 | 3 |
| `CONCURRENT_SYNC` | 并发同步数 | 3 |
| `LOG_LEVEL` | 日志级别 | INFO |

### 存储和日志配置

| 环境变量 | 说明 | 默认值 |
|--------|------|-------|
| `LOCAL_REPO_PATH` | 本地仓库路径 | /app/data/repos |
| `LOG_FILE` | 日志文件路径 | /app/logs/sync.log |
| `LOG_MAX_SIZE` | 单个日志文件最大大小(MB) | 100 |
| `LOG_BACKUP_COUNT` | 保留日志文件数 | 10 |

## 常见操作

### 查看日志

```bash
# 查看应用日志（最后100行）
docker-compose logs -n 100 app

# 实时查看应用日志
docker-compose logs -f app

# 查看MySQL日志
docker-compose logs -f mysql

# 查看特定时间范围的日志
docker-compose logs --since 2024-01-01 app
```

### 进入容器

```bash
# 进入应用容器
docker-compose exec app bash

# 进入MySQL容器
docker-compose exec mysql bash

# 执行MySQL命令
docker-compose exec mysql mysql -u mirror_user -pmirror123456 mirror_git
```

### 数据库管理

```bash
# 连接到数据库
docker-compose exec mysql mysql -u mirror_user -pmirror123456 -D mirror_git

# 查看数据库表
SHOW TABLES;

# 查看仓库信息
SELECT * FROM repositories;

# 查看同步历史
SELECT * FROM sync_history ORDER BY id DESC LIMIT 10;
```

### 停止和移除服务

```bash
# 停止所有服务（保留数据）
docker-compose stop

# 移除所有容器（保留数据）
docker-compose down

# 完全清理（包括数据）
docker-compose down -v

# 重启服务
docker-compose restart

# 重启特定服务
docker-compose restart app
```

### 更新应用

```bash
# 重新构建镜像
docker-compose build --no-cache

# 重新启动服务
docker-compose up -d
```

## 数据持久化

本项目使用 Docker Volumes 确保数据持久化：

- **mysql_data**: MySQL 数据库数据
- **./data**: 本地仓库存储
- **./logs**: 应用日志文件

这些数据在容器移除后仍会保留。

### 备份数据库

```bash
# 备份 MySQL 数据库
docker-compose exec mysql mysqldump -u mirror_user -pmirror123456 mirror_git > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker-compose exec -T mysql mysql -u mirror_user -pmirror123456 mirror_git < backup_20240101_120000.sql
```

## 架构设计

### x86 架构支持

- Dockerfile 和 docker-compose.yml 均明确指定 `platform: linux/amd64`
- 使用官方 Python 和 MySQL 镜像，默认支持 x86 架构
- 多阶段构建优化镜像大小

### 网络配置

- 使用自定义 Docker 网络 `mirror-net`
- MySQL 和应用容器在同一网络中通信
- MySQL 地址：`mysql:3306`

### 健康检查

- 应用：HTTP 健康检查 `/api/health`
- MySQL：使用 `mysqladmin ping` 检查
- 应用依赖 MySQL 的健康检查

## 生产环境建议

### 1. 环境变量安全

不要在 `.env` 文件中存储敏感信息，考虑使用：
- Docker Secrets（Docker Swarm）
- Kubernetes Secrets（K8s）
- 环境变量管理工具（HashiCorp Vault）

### 2. 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  mysql:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 3. 日志收集

配置容器日志驱动将日志发送到集中式日志系统：

```yaml
services:
  app:
    logging:
      driver: "splunk"
      options:
        splunk-token: "${SPLUNK_TOKEN}"
        splunk-url: "https://your-splunk-instance:8088"
```

### 4. 备份策略

定期备份数据库和仓库数据：

```bash
# 每日备份脚本
#!/bin/bash
BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份数据库
docker-compose exec -T mysql mysqldump -u mirror_user -pmirror123456 mirror_git | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# 备份仓库
tar -czf "$BACKUP_DIR/repos_$TIMESTAMP.tar.gz" ./data/repos

# 删除7天前的备份
find "$BACKUP_DIR" -type f -mtime +7 -delete
```

### 5. 监控和告警

使用 Prometheus + Grafana 或其他监控方案：

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

## 故障排除

### 应用无法连接 MySQL

```bash
# 检查网络连接
docker-compose exec app ping mysql

# 检查 MySQL 状态
docker-compose exec mysql mysql -u mirror_user -pmirror123456 -e "SELECT 1"

# 查看应用日志中的数据库连接错误
docker-compose logs app | grep -i database
```

### 磁盘空间不足

```bash
# 检查磁盘使用情况
docker system df

# 清理未使用的 Docker 资源
docker system prune -a --volumes
```

### 权限问题

```bash
# 修复挂载目录权限
sudo chown -R 1000:1000 ./data ./logs
```

### 内存不足

```bash
# 监控容器资源使用
docker stats

# 增加 Docker 内存限制或减少并发同步数
# 在 .env 中修改: CONCURRENT_SYNC=2
```

## API 端点

启动后可访问以下 API 端点：

- **Web UI**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **API 文档**: http://localhost:8000/redoc (ReDoc)
- **健康检查**: http://localhost:8000/api/health
- **配置状态**: http://localhost:8000/api/config/status

## 获取帮助

如有问题，请：

1. 检查日志：`docker-compose logs app`
2. 查看项目文档：[项目 README](README.md)
3. 提交问题：项目 GitHub Issues

## 许可证

[项目许可证信息]
