# Web UI 纯界面操作模式

## 📌 更新说明

本项目已完全移除命令行操作方式，改为纯 Web UI 操作。所有功能都可以通过浏览器界面完成。

## 🚀 启动方式

### 方式一：直接启动

```bash
python run.py
```

### 方式二：Docker 启动（推荐）

```bash
docker-compose up -d
```

### 方式三：使用 src/main.py

```bash
python src/main.py
```

## 🌐 访问 Web UI

启动后，在浏览器中访问：
- **主页**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## ⚙️ 配置选项

所有配置通过环境变量设置，无需命令行参数：

### Web UI 配置
- `WEB_HOST`: Web 服务监听地址（默认: 0.0.0.0）
- `WEB_PORT`: Web 服务端口（默认: 8000）
- `WEB_WORKERS`: Worker 进程数（默认: 1）
- `WEB_LOG_LEVEL`: 日志级别（默认: info）

### 应用配置
- `GITHUB_TOKEN`: GitHub 访问令牌
- `GITEA_URL`: Gitea 服务器地址
- `GITEA_TOKEN`: Gitea 访问令牌
- `GITEA_USERNAME`: Gitea 用户名
- `SYNC_INTERVAL`: 同步间隔（秒）
- `LOG_LEVEL`: 应用日志级别

详细配置请参考 `.env.example` 或 `.env.docker.example`

## 📋 主要功能

通过 Web UI 可以完成以下操作：

1. **仓库管理**
   - 查看所有同步仓库
   - 添加新仓库
   - 编辑仓库配置
   - 删除仓库

2. **同步操作**
   - 手动触发单个仓库同步
   - 批量同步所有仓库
   - 配置自动定时同步
   - 查看同步进度

3. **监控与日志**
   - 查看同步历史
   - 查看同步状态
   - 查看错误日志
   - 统计信息展示

4. **配置管理**
   - GitHub 配置
   - Gitea 配置
   - 同步策略配置
   - 通知配置

## 🔧 环境变量配置示例

### 在 .env 文件中配置：

```env
# GitHub 配置
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_API_URL=https://api.github.com

# Gitea 配置
GITEA_URL=http://192.168.9.101:8418
GITEA_TOKEN=your_gitea_token_here
GITEA_USERNAME=your_username

# 同步配置
SYNC_INTERVAL=3600
LOCAL_REPO_PATH=/app/data/repos
SYNC_TIMEOUT=1800

# Web UI 配置（可选）
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_WORKERS=1
WEB_LOG_LEVEL=info

# 数据库配置
# SQLite URL 格式说明：
#   sqlite:////app/data/xxx.db  (4个斜杠 = 绝对路径 /app/data/xxx.db)
#   sqlite:///data/xxx.db       (3个斜杠 = 相对路径，工作目录 /app + data/xxx.db)
DATABASE_URL=sqlite:////app/data/mirror_sync.db
```

### 在 docker-compose.yml 中配置：

已默认配置好所有必要的环境变量，只需在 `.env` 文件中设置具体值即可。

## 📖 API 使用

如需通过 API 进行自动化操作，可以使用 REST API：

### 获取仓库列表
```bash
curl http://localhost:8000/api/repositories
```

### 触发同步
```bash
curl -X POST http://localhost:8000/api/sync/repository \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-repo",
    "url": "https://github.com/user/my-repo.git"
  }'
```

### 查看同步历史
```bash
curl http://localhost:8000/api/sync/history?limit=10
```

完整 API 文档: http://localhost:8000/docs

## ✅ 改动清单

### 已移除
- ❌ 所有命令行参数（`--sync-now`, `--daemon`, `--config` 等）
- ❌ 命令行操作方式
- ❌ argparse 参数解析
- ❌ CLI 模式

### 已保留
- ✅ Web UI 完整功能
- ✅ REST API 接口
- ✅ 环境变量配置
- ✅ Docker 部署方式
- ✅ 所有核心同步功能

### 已简化
- 📝 `src/main.py` - 只启动 Web UI
- 📝 `run.py` - 移除命令行参数，改用环境变量
- 📝 `Dockerfile` - 简化 CMD 命令
- 📝 `README.md` - 更新使用说明

## 🎯 使用建议

1. **开发环境**: 使用 `python run.py` 直接启动
2. **生产环境**: 使用 `docker-compose up -d` 部署
3. **所有操作**: 通过 Web UI (http://localhost:8000) 完成
4. **自动化需求**: 使用 REST API 接口

## 📞 需要帮助？

- 查看 API 文档: http://localhost:8000/docs
- 查看 README.md: 详细使用说明
- 查看 TROUBLESHOOTING.md: 常见问题解决

---

**注意**: 本项目不再支持命令行操作方式，所有功能请通过 Web UI 访问。
