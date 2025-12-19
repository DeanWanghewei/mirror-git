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

### 快速开始

#### 前置要求
- Python 3.8+
- Git
- 自建 Gitea 服务器
- GitHub 账号 (用于获取 Token)

#### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourname/mirror-git.git
cd mirror-git
```

2. **创建虚拟环境**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境**
```bash
cp .env.example .env
# 编辑 .env 文件，填入配置信息
```

5. **运行程序**
```bash
python src/main.py
```

### 配置说明

编辑 `.env` 文件配置以下项目:

```env
# GitHub 配置
GITHUB_TOKEN=your_github_token_here
GITHUB_API_URL=https://api.github.com

# Gitea 配置
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

### 项目结构

```
mirror-git/
├── README.md                         # 本文件
├── INITIAL_SETUP.md                  # ⭐ 初始配置指南（必读）
├── GITEA_TOKEN_PERMISSIONS.md        # ⭐ Gitea Token 权限详细文档
├── GITEA_TOKEN_QUICK_FIX.md          # ⭐ Token 权限快速修复
├── QUICK_START.md                    # 快速开始指南
├── QUICK_START_PUBLIC_REPOS.md       # 公共仓库快速开始
├── PUBLIC_REPOS_GUIDE.md             # 公共仓库完整指南
├── PUBLIC_REPOS_IMPLEMENTATION.md    # 公共仓库实现细节
├── PROJECT_PLAN.md                   # 项目规划
├── TEST_REPORT.md                    # 测试报告
├── API_ERROR_FIX.md                  # API 错误修复
├── requirements.txt                  # Python 依赖列表
├── .env.example                      # 环境变量示例
├── run.py                            # Web UI 启动脚本
├── src/
│   ├── main.py                       # CLI 入口
│   ├── config/                       # 配置管理
│   │   └── config.py
│   ├── clients/                      # API 客户端
│   │   ├── github_client.py
│   │   └── gitea_client.py
│   ├── sync/                         # 同步引擎
│   │   └── sync_engine.py
│   ├── scheduler/                    # 定时调度
│   │   └── task_scheduler.py
│   ├── logger/                       # 日志系统
│   │   └── logger.py
│   ├── models/                       # 数据库模型
│   │   └── __init__.py
│   └── web/                          # Web UI
│       ├── app.py
│       ├── routes/
│       │   ├── config.py
│       │   ├── repositories.py
│       │   ├── sync.py
│       │   ├── monitor.py
│       │   └── tasks.py
│       ├── templates/
│       │   └── index.html
│       └── static/
├── tests/                            # 测试用例
│   ├── test_config.py
│   ├── test_logger.py
│   ├── test_models.py
│   ├── test_github_client.py
│   ├── test_gitea_client.py
│   └── test_sync_engine.py
├── scripts/                          # 工具脚本
│   ├── migrate_db.py                 # 数据库迁移
│   └── test_public_repos.py          # 公共仓库测试
└── data/
    └── repos/                        # 本地仓库存储
```

### 使用示例

#### 基本使用

```python
from src.config.config import load_config
from src.sync.sync_engine import SyncEngine

# 加载配置
config = load_config()

# 创建同步引擎
engine = SyncEngine(config)

# 执行同步
result = engine.sync_all()
print(f"成功: {result['success']}, 失败: {result['failed']}")
```

#### 定时同步

```python
from src.scheduler.task_scheduler import TaskScheduler

scheduler = TaskScheduler(config)
scheduler.schedule_sync(interval=3600)  # 每小时同步一次
scheduler.start()
```

### 文档

- [详细的项目计划](./PROJECT_PLAN.md) - 包含完整的系统设计和开发计划
- [API 文档](#) - 即将推出

### 常见问题

**Q: 如何添加新的仓库进行同步?**
A: 编辑 `src/config/repositories.json` 文件，添加仓库信息。

**Q: 如何查看同步日志?**
A: 查看 `logs/sync.log` 文件，或设置 `LOG_LEVEL=DEBUG` 查看详细日志。

**Q: 支持代理吗?**
A: 将在后续版本中支持，敬请期待。

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

### Configuration

Edit the `.env` file to configure the following:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_API_URL=https://api.github.com

# Gitea Configuration
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

### Project Structure

```
mirror-git/
├── README.md                 # This file
├── PROJECT_PLAN.md          # Detailed project plan
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables example
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

**Last Updated**: 2024-01-15
**Version**: v1.0.0-planning
