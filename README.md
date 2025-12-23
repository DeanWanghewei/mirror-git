# GitHub Repositories 镜像同步系统

[中文](#中文) | [English](#english)

## 中文

### 项目简介

这是一个自动化系统，用于将 GitHub 上的仓库镜像同步到自建 Gitea 服务器。系统会定期自动拉取 GitHub 的最新更新并同步到 Gitea，实现高效的代码仓库管理和备份。

### 核心功能

✨ **主要特性**:
- 🔄 自动镜像 GitHub 仓库到 Gitea
- 📅 定期自动更新同步
- 🛡️ 完善的错误处理和重试机制
- 📊 详细的日志记录和监控
- ⚙️ 灵活的配置管理
- 🚀 支持大规模仓库同步

### 🚀 快速开始

## 方式一：🐳 Docker 部署（推荐）

### 前置要求
- Docker 20.10+
- Docker Compose 1.29+
- 至少 2GB 可用磁盘空间
- 自建 Gitea 服务器
- GitHub 账号 (用于获取 Token)

### 3 步快速启动

**1. 克隆项目**
```bash
git clone https://github.com/yourname/mirror-git.git
cd mirror-git
```

**2. 配置环境变量**
```bash
cp .env.docker.example .env
# 编辑 .env，设置 GitHub Token、Gitea URL 等必要信息
nano .env  # 或使用其他编辑器
```

**3. 启动服务**
```bash
# 构建镜像并启动（包括 MySQL 数据库）
docker-compose up -d

# 查看启动日志
docker-compose logs -f app
```

**4. 验证服务**
```bash
# 查看容器状态
docker-compose ps

# 检查应用健康状态
curl http://localhost:8000/api/health

# 浏览器访问
# Web UI: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

---

### 纯 Docker 命令启动（不使用 docker-compose）

如果你不想使用 docker-compose，可以使用纯 Docker 命令启动：

#### 方案 A: 使用 SQLite（最简单）

```bash
# 1. 构建镜像
docker build -t mirror-git:latest .

# 2. 创建数据目录
mkdir -p data logs

# 3. 启动容器
docker run -d \
  --name mirror-git-app \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e GITEA_URL=http://your-gitea-server:3000 \
  -e GITEA_TOKEN=your_gitea_token \
  -e GITEA_USERNAME=your_username \
  -e DATABASE_URL='sqlite:////app/data/mirror_sync.db' \
  -e LOG_LEVEL=INFO \
  mirror-git:latest

# 💡 SQLite URL 格式说明：
# sqlite:////app/data/xxx.db  (4个斜杠 = 绝对路径 /app/data/xxx.db)
# sqlite:///data/xxx.db       (3个斜杠 = 相对路径 ./data/xxx.db，相对于工作目录 /app)

# 4. 查看日志
docker logs -f mirror-git-app

# 5. 访问 Web UI
# http://localhost:8000
```

#### 方案 B: 使用 MySQL（完整功能）

```bash
# 1. 创建 Docker 网络
docker network create mirror-net

# 2. 启动 MySQL 容器
docker run -d \
  --name mirror-git-mysql \
  --network mirror-net \
  -e MYSQL_ROOT_PASSWORD=root123456 \
  -e MYSQL_DATABASE=mirror_git \
  -e MYSQL_USER=mirror_user \
  -e MYSQL_PASSWORD=mirror123456 \
  -v mirror-git-mysql-data:/var/lib/mysql \
  mysql:8.0 \
  --default-authentication-plugin=mysql_native_password \
  --character-set-server=utf8mb4 \
  --collation-server=utf8mb4_unicode_ci

# 3. 等待 MySQL 启动（约10秒）
sleep 10

# 4. 构建应用镜像
docker build -t mirror-git:latest .

# 5. 启动应用容器
docker run -d \
  --name mirror-git-app \
  --network mirror-net \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e GITHUB_TOKEN=your_github_token \
  -e GITEA_URL=http://your-gitea-server:3000 \
  -e GITEA_TOKEN=your_gitea_token \
  -e GITEA_USERNAME=your_username \
  -e DATABASE_URL=mysql+pymysql://mirror_user:mirror123456@mirror-git-mysql:3306/mirror_git?charset=utf8mb4 \
  -e SYNC_INTERVAL=3600 \
  -e LOG_LEVEL=INFO \
  mirror-git:latest

# 6. 查看应用日志
docker logs -f mirror-git-app

# 7. 访问 Web UI
# http://localhost:8000
```

#### 常用纯 Docker 管理命令

```bash
# 查看运行状态
docker ps

# 查看日志
docker logs -f mirror-git-app
docker logs -f mirror-git-mysql

# 进入容器
docker exec -it mirror-git-app bash
docker exec -it mirror-git-mysql bash

# 重启容器
docker restart mirror-git-app

# 停止容器
docker stop mirror-git-app mirror-git-mysql

# 删除容器
docker rm -f mirror-git-app mirror-git-mysql

# 删除网络
docker network rm mirror-net

# 删除数据卷（⚠️ 会删除所有数据）
docker volume rm mirror-git-mysql-data
```

---

### Docker 特性
- ✅ **一键部署** - 自动配置 MySQL 数据库
- ✅ **x86 架构支持** - 适配 x86/amd64 服务器
- ✅ **完全可配置** - 所有配置通过环境变量控制
- ✅ **数据持久化** - 使用 Docker Volumes 保存数据
- ✅ **健康检查** - 自动监控和恢复

### 📦 数据持久化说明

**重要**：所有数据都保存在宿主机的 `data` 目录中，升级不会丢失数据。

**数据位置**：
```bash
mirror-git/
├── data/                    # 📌 数据目录（持久化）
│   ├── sync.db             # SQLite 数据库（仓库信息、同步历史）
│   └── repos/              # 本地克隆的仓库
└── logs/                    # 日志文件
```

**数据库配置**：
- 默认使用 SQLite: `data/sync.db`
- 也支持 MySQL（通过环境变量配置）
- ⚠️ **重要**：SQLite 路径配置说明请查看 [SQLite 路径配置指南](./SQLITE_PATH_CONFIG.md)

**升级保护**：
```bash
# 升级前备份（推荐）
cp -r data data.backup

# 升级
docker-compose pull
docker-compose up -d

# 如果遇到数据问题，运行恢复脚本
python scripts/restore_database.py
```

**数据恢复**：
如果升级后数据丢失，查看 [数据恢复指南](./DATA_RECOVERY.md)

### 常用 Docker Compose 命令

```bash
# 查看日志
docker-compose logs -f app              # 应用日志
docker-compose logs -f mysql            # MySQL 日志

# 进入容器
docker-compose exec app bash            # 进入应用容器
docker-compose exec mysql bash          # 进入 MySQL 容器

# 数据库操作
docker-compose exec mysql mysql -u mirror_user -pmirror123456 -D mirror_git

# 停止和清理
docker-compose stop                     # 停止服务（保留数据）
docker-compose down -v                  # 删除所有（包括数据）

# 更新应用
docker-compose build --no-cache         # 重新构建镜像
docker-compose up -d                    # 重新启动
```

---

## 方式二：本地 Python 环境部署

### 前置要求
- Python 3.8+
- Git
- 自建 Gitea 服务器
- GitHub 账号 (用于获取 Token)

### 安装步骤

**1. 克隆项目**
```bash
git clone https://github.com/yourname/mirror-git.git
cd mirror-git
```

**2. 创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

**3. 安装依赖**
```bash
pip install -r requirements.txt
```

**4. 配置环境**
```bash
cp .env.example .env
# 编辑 .env 文件，填入配置信息
nano .env  # 或使用其他编辑器
```

**5. 启动 Web UI**
```bash
# 启动 Web 服务
python run.py

# 或使用 uvicorn 直接启动
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

**6. 访问 Web UI**
```
打开浏览器访问: http://localhost:8000
API 文档: http://localhost:8000/docs
```

---

### ⚙️ 配置说明

编辑 `.env` 文件配置以下项目:

```env
# GitHub 配置 (可选 - 仅私有仓库需要)
GITHUB_TOKEN=your_github_token_here  # 公开仓库可留空
GITHUB_API_URL=https://api.github.com

# Gitea 配置 (必需)
GITEA_URL=https://gitea.example.com
GITEA_TOKEN=your_gitea_token_here    # ⚠️ 必须有正确的权限（见下文）
GITEA_USERNAME=mirror_user

# 同步配置
SYNC_INTERVAL=3600          # 同步间隔（秒）
LOCAL_REPO_PATH=./data/repos # 本地仓库路径
SYNC_TIMEOUT=1800           # 同步超时（秒）

# 日志配置
LOG_LEVEL=INFO              # 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_FILE=./logs/sync.log    # 日志文件路径
```

**注意**：`GITHUB_TOKEN` 仅在需要访问私有仓库时必填，访问公开仓库时可以留空。

### ⚠️ Gitea Token 权限配置（重要）

Gitea Token 必须具有以下权限才能正常工作：

| 权限 | 说明 | 必需 |
|------|------|------|
| `repo` | 仓库访问权限 | ✅ 必需 |
| `admin:org` | 组织管理权限 | ✅ 必需 |
| `admin:repo_hook` | Webhook 管理权限 | ✅ 必需 |
| `user` | 用户信息权限 | ✅ 必需 |

**如果遇到 403 Forbidden 错误：**
1. 查看 `INITIAL_SETUP.md` - 初始配置步骤
2. 查看 `GITEA_TOKEN_QUICK_FIX.md` - 快速修复指南
3. 查看 `GITEA_TOKEN_PERMISSIONS.md` - 详细权限文档

### 使用示例

#### Web UI 操作（推荐）

所有操作通过 Web UI 完成，无需命令行：

1. **启动应用**
```bash
# 直接启动
python run.py

# 或使用 Docker
docker-compose up -d
```

2. **访问 Web UI**
```
浏览器打开: http://localhost:8000
```

3. **通过 Web UI 进行操作**
- 📋 查看仓库列表
- ➕ 添加新的同步仓库
- 🔄 手动触发同步
- 📊 查看同步历史和状态
- ⚙️ 配置定时同步
- 📈 监控同步统计

4. **API 接口调用**（可选）

如需自动化脚本，可使用 REST API：

```python
import requests

# 查看仓库列表
response = requests.get("http://localhost:8000/api/repositories")
repositories = response.json()

# 触发单个仓库同步
response = requests.post(
    "http://localhost:8000/api/sync/repository",
    json={
        "name": "my-repo",
        "url": "https://github.com/user/my-repo.git"
    }
)
result = response.json()
```

完整 API 文档: http://localhost:8000/docs

### 文档

- [详细的项目计划](./PROJECT_PLAN.md) - 包含完整的系统设计和开发计划
- [API 文档](#) - 即将推出

### 常见问题

**Q: 如何添加新的仓库进行同步?**
A: 访问 Web UI (http://localhost:8000)，在仓库管理页面添加新仓库。

**Q: 如何查看同步日志?**
A: 在 Web UI 的同步历史页面查看，或查看 `logs/sync.log` 文件。

**Q: 如何触发手动同步?**
A: 在 Web UI 的仓库列表中，点击对应仓库的"同步"按钮。

**Q: 支持代理吗?**
A: 支持。在 `.env` 文件中配置代理相关参数即可。

**Q: 数据库文件创建在了错误的位置怎么办?**
A: 查看 [SQLite 路径配置指南](./SQLITE_PATH_CONFIG.md) 了解正确的配置方法。

**Q: 升级后数据丢失怎么办?**
A: 查看 [数据恢复指南](./DATA_RECOVERY.md) 进行数据恢复。

### 安全建议

- 🔐 使用 GitHub Personal Access Token，而不是账号密码
- 🔐 使用 Gitea API Token 进行认证
- 🔐 将 `.env` 文件加入 `.gitignore`，不要提交到版本控制
- 🔐 定期轮换 Token
- 🔐 在信任的网络环境中运行

### 贡献指南

欢迎贡献！请参考以下流程：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。

### 联系方式

- 📧 Email: your.email@example.com
- 💬 Issues: [GitHub Issues](https://github.com/yourname/mirror-git/issues)

---

## English

### Project Introduction

This is an automation system for mirroring GitHub repositories to a self-hosted Gitea server. The system periodically pulls the latest updates from GitHub and syncs them to Gitea, enabling efficient code repository management and backup.

### Core Features

✨ **Key Features**:
- 🔄 Automatically mirror GitHub repositories to Gitea
- 📅 Periodically auto-sync updates
- 🛡️ Comprehensive error handling and retry mechanism
- 📊 Detailed logging and monitoring
- ⚙️ Flexible configuration management
- 🚀 Support for large-scale repository synchronization

### Quick Start

#### Prerequisites
- Python 3.8+
- Git
- Self-hosted Gitea server
- GitHub account (for token generation)

#### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourname/mirror-git.git
cd mirror-git
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env file with your configuration
```

5. **Run the application**
```bash
python src/main.py
```

### 🐳 Docker Quick Deployment

#### Prerequisites
- Docker 20.10+
- Docker Compose 1.29+
- At least 2GB available disk space

#### 3-Step Quick Start

1. **Configure environment variables**
```bash
cp .env.docker.example .env
# Edit .env file and set GitHub Token, Gitea URL, etc.
```

2. **Start services**
```bash
# Build image and start all services (including MySQL database)
docker-compose up -d

# View startup logs
docker-compose logs -f app
```

3. **Verify services**
```bash
# Check container status
docker-compose ps

# Check application health
curl http://localhost:8000/api/health

# Access via browser
# Web UI: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

#### Docker Features
- ✅ **x86 Architecture Support** - Optimized for x86/amd64 servers
- ✅ **MySQL 8.0 Integration** - Automatic deployment and initialization
- ✅ **Fully Configurable** - All settings via environment variables
- ✅ **Data Persistence** - Data saved using Docker Volumes
- ✅ **Health Checks** - Automatic monitoring and recovery

#### Common Docker Commands

```bash
# View logs
docker-compose logs -f app              # Application logs
docker-compose logs -f mysql            # MySQL logs

# Enter containers
docker-compose exec app bash            # Enter app container
docker-compose exec mysql bash          # Enter MySQL container

# Database operations
docker-compose exec mysql mysql -u mirror_user -pmirror123456 -D mirror_git

# Stop and cleanup
docker-compose stop                     # Stop services (keep data)
docker-compose down -v                  # Remove all (including data)

# Update application
docker-compose build --no-cache         # Rebuild image
docker-compose up -d                    # Restart services
```

#### Detailed Configuration
See [Docker Deployment Guide](./DOCKER_DEPLOYMENT.md) and [Docker Quick Start Guide](./DOCKER_QUICK_START.md)

#### Pure Docker Containers (without docker-compose)
If you prefer not to use docker-compose, see: [Docker Pure Containers Startup Guide](./DOCKER_PURE_CONTAINERS.md)

#### Docker Build Guide for macOS
If you need to build Docker images locally or push to a registry, refer to: [Docker Build and Push Guide](./DOCKER_BUILD_AND_PUSH.md)

#### Docker Build Issues?
If you encounter network timeout or other build issues, see: [Docker Build Problem Quick Fix Guide](./DOCKER_BUILD_FIX.md)

### Configuration

Edit the `.env` file to configure the following:

```env
# GitHub Configuration (Optional - only for private repositories)
GITHUB_TOKEN=your_github_token_here  # Leave empty for public repos
GITHUB_API_URL=https://api.github.com

# Gitea Configuration (Required)
GITEA_URL=https://gitea.example.com
GITEA_TOKEN=your_gitea_token_here
GITEA_USERNAME=mirror_user

# Sync Configuration
SYNC_INTERVAL=3600          # Sync interval in seconds
LOCAL_REPO_PATH=./data/repos # Local repository path
SYNC_TIMEOUT=1800           # Sync timeout in seconds

# Logging Configuration
LOG_LEVEL=INFO              # Log level: DEBUG, INFO, WARNING, ERROR
LOG_FILE=./logs/sync.log    # Log file path
```

**Note**: `GITHUB_TOKEN` is only required for accessing private repositories. For public repositories, you can leave it empty.

### Project Structure

```
mirror-git/
├── README.md                 # This file
├── DOCKER_DEPLOYMENT.md      # ⭐ Complete Docker deployment guide
├── DOCKER_QUICK_START.md     # ⭐ Docker quick start guide
├── Dockerfile                # Docker image build file
├── docker-compose.yml        # Docker Compose orchestration file
├── .dockerignore             # Docker build ignore file
├── docker/
│   └── mysql/
│       └── my.cnf            # MySQL 8.0 configuration
├── PROJECT_PLAN.md          # Detailed project plan
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables example (local)
├── .env.docker.example      # Environment variables example (Docker)
├── run.py                   # Web UI startup script
├── src/
│   ├── main.py             # Main entry point
│   ├── config/             # Configuration management
│   ├── clients/            # GitHub and Gitea clients
│   ├── sync/               # Sync engine
│   ├── scheduler/          # Task scheduler
│   └── logger/             # Logging system
├── tests/                   # Test cases
└── data/
    └── repos/              # Local repository storage
```

### Documentation

- [Detailed Project Plan](./PROJECT_PLAN.md) - Complete system design and development plan
- [API Documentation](#) - Coming soon

### License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) file for details.

---

**Last Updated**: 2025-12-23
**Version**: v2.0.0
