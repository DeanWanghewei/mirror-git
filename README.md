# GitHub Repositories 镜像同步系统

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

![监控面板](./doc/dashbord.png)
![仓库挂历](./doc/manager.png)


### 🚀 快速开始


### ⚠️ Gitea Token 权限配置（重要）

Gitea Token 需要根据使用场景配置不同的权限：

#### 最小权限配置（仅个人命名空间）

如果只需要在个人用户命名空间下创建镜像仓库：

| 权限                   | 说明             | 必需   |
| ---------------------- | ---------------- | ------ |
| `read:user`            | 用户信息读取权限   | ✅ 必需 |
| `write:repository`     | 仓库读写权限       | ✅ 必需 |

#### 完整权限配置（推荐 - 支持组织）

如果需要在组织中创建镜像仓库（更常见的使用场景）：

| 权限                   | 说明                     | 必需   |
| ---------------------- | ------------------------ | ------ |
| `read:user`            | 用户信息读取权限          | ✅ 必需 |
| `write:repository`     | 仓库读写权限（含 Webhook）| ✅ 必需 |
| `write:organization`   | 组织仓库创建权限          | ✅ 必需 |

**权限说明**：
- `read:user` - 用于验证 Token 和获取用户信息
- `write:repository` - 用于创建、更新、删除仓库，以及管理 Webhook
- `write:organization` - 仅在需要将仓库镜像到组织命名空间时需要

**如何创建 Token**：
1. 登录 Gitea: `{GITEA_URL}`
2. 进入：`设置` → `应用` → `管理访问令牌`
3. 点击 `生成新令牌`，选择上述权限范围
4. 复制生成的 Token 并配置到环境变量 `GITEA_TOKEN`

## 方式一：🐳 Docker 部署（推荐）

### 前置要求
- Docker 20.10+
- Docker Compose 1.29+
- 至少 2GB 可用磁盘空间
- 自建 Gitea 服务器
- GitHub 账号 (用于获取 Token,非必须)

### 3 步快速启动

#### 方案 A: 使用 SQLite（最简单）

```bash
docker run -d \
  --name mirror-git-app \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e GITEA_URL=http://your-gitea-server:3000 \
  -e GITEA_TOKEN=your_gitea_token \
  -e GITEA_USERNAME=your_username \
  -e DATABASE_URL='sqlite:///data/mirror_sync.db' \
  -e TIMEZONE=Asia/Shanghai \
  -e LOG_LEVEL=INFO \
  deanwang/mirror-git:latest

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
  -e TIMEZONE=Asia/Shanghai \
  -e LOG_LEVEL=INFO \
  deanwang/mirror-git:latest

# 7. 访问 Web UI
# http://localhost:8000
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


1. **访问 Web UI**
```
浏览器打开: http://localhost:8000
```

1. **通过 Web UI 进行操作**
- 📋 查看仓库列表
- ➕ 添加新的同步仓库
- 🔄 手动触发同步
- 📊 查看同步历史和状态
- ⚙️ 配置定时同步
- 📈 监控同步统计

1. **API 接口调用**（可选）

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

### 常见问题

**Q: 如何添加新的仓库进行同步?**
A: 访问 Web UI (http://localhost:8000)，在仓库管理页面添加新仓库。

**Q: 如何查看同步日志?**
A: 在 Web UI 的同步历史页面查看，或查看 `logs/sync.log` 文件。

**Q: 如何触发手动同步?**
A: 在 Web UI 的仓库列表中，点击对应仓库的"同步"按钮。

**Q: 支持代理吗?**
A: 支持。在 `.env` 文件中配置代理相关参数即可。

### 安全建议

- 🔐 使用 GitHub Personal Access Token，而不是账号密码
- 🔐 使用 Gitea API Token 进行认证
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

- 📧 Email: deanwanghewei@gmail.com
---

**Last Updated**: 2025-12-23
**Version**: v2.0.0
