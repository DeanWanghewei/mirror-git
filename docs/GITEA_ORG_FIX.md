# Gitea 组织推送修复说明

## 问题根源

**错误信息：**
```
remote: Push to create is not enabled for organizations.
fatal: unable to access 'http://192.168.9.101:8418/mirror-github/jimmer.git/': The requested URL returned error: 403
```

**根本原因：**
代码中多处将数据库的 `gitea_owner` 字段（组织名）错误地传递给了 `sync_repository()` 的 `gitea_owner` 参数（应该是用户名），导致：
1. 仓库创建逻辑混乱
2. 推送目标不一致
3. 组织仓库无法正确创建和推送

## 修复的文件

### 1. src/web/routes/repositories.py:347-354

**修复前：**
```python
engine.sync_repository(
    repo_name,
    repo_url,
    gitea_owner=None,        # ← 错误：传 None 会使用默认用户名
    gitea_org=gitea_owner    # ← 传数据库中的组织名
)
```

**修复后：**
```python
# If gitea_owner is set in database, treat it as organization
# Otherwise, repo will be pushed to user namespace
engine.sync_repository(
    repo_name,
    repo_url,
    gitea_owner=config.gitea.username if gitea_owner else None,
    gitea_org=gitea_owner  # Pass gitea_owner as organization parameter
)
```

### 2. src/sync/sync_engine.py:822-833

**修复前：**
```python
result = self.sync_repository(
    repo["name"],
    repo["url"],
    gitea_owner=repo.get("gitea_owner")  # ← 错误：组织名传给了用户名参数
)
```

**修复后：**
```python
# If gitea_owner is set in repo, treat it as organization
# Otherwise, push to user namespace
gitea_org_name = repo.get("gitea_owner")

result = self.sync_repository(
    repo["name"],
    repo["url"],
    gitea_owner=self.gitea_config.username if gitea_org_name else None,
    gitea_org=gitea_org_name
)
```

### 3. src/scheduler/task_scheduler.py:232-276

**修复前：**
```python
def _sync_single_task(self, repo_name: str, github_url: str) -> Dict[str, Any]:
    self.logger.info(f"Starting scheduled sync for: {repo_name}")
    result = self.sync_engine.sync_repository(repo_name, github_url)
    # ← 没有传 gitea_owner/gitea_org，默认推送到用户空间
    return result
```

**修复后：**
```python
def _sync_single_task(self, repo_name: str, github_url: str) -> Dict[str, Any]:
    self.logger.info(f"Starting scheduled sync for: {repo_name}")

    # Get repository from database to get gitea_owner configuration
    from ..models import Repository
    session = self.sync_engine.db.get_session()
    try:
        repo = session.query(Repository).filter(
            Repository.name == repo_name,
            Repository.url == github_url
        ).first()

        if repo:
            # If gitea_owner is set, treat it as organization
            gitea_org_name = repo.gitea_owner
            result = self.sync_engine.sync_repository(
                repo_name,
                github_url,
                gitea_owner=self.sync_engine.gitea_config.username if gitea_org_name else None,
                gitea_org=gitea_org_name
            )
        else:
            # Repository not in database, use default (user namespace)
            result = self.sync_engine.sync_repository(repo_name, github_url)
    finally:
        session.close()

    return result
```

## 参数说明

### sync_repository() 方法参数：

```python
def sync_repository(
    self,
    repo_name: str,
    github_url: str,
    gitea_owner: str = None,  # Gitea 用户名（用于回退），默认使用配置的用户名
    gitea_org: str = None      # Gitea 组织名（如果要推送到组织）
)
```

**正确用法：**

1. **推送到组织：**
   ```python
   sync_repository(
       "jimmer",
       "https://github.com/xxx/jimmer.git",
       gitea_owner="deanwang",      # 用户名（用于 fallback）
       gitea_org="mirror-github"    # 组织名
   )
   ```
   → 仓库创建在：`mirror-github/jimmer`

2. **推送到用户空间：**
   ```python
   sync_repository(
       "jimmer",
       "https://github.com/xxx/jimmer.git",
       gitea_owner=None,  # 使用默认用户名
       gitea_org=None     # 不使用组织
   )
   ```
   → 仓库创建在：`deanwang/jimmer`

## 数据库字段说明

```python
# src/models/__init__.py
class Repository:
    gitea_owner = Column(String(255), nullable=True)
    # Organization or user namespace in Gitea
```

**设计意图：**
- 如果 `gitea_owner` 有值 → 视为**组织名**，仓库推送到该组织
- 如果 `gitea_owner` 为 NULL → 推送到**用户空间**（配置的 GITEA_USERNAME）

## 验证修复

### 1. 重新构建并部署

```bash
# 构建新镜像
docker build -t deanwang/mirror-git:latest .

# 停止旧容器
docker stop mirror-git-app
docker rm mirror-git-app

# 启动新容器
docker run -d \
  --name mirror-git-app \
  -p 8020:8000 \
  -e GITEA_URL=http://192.168.9.101:8418 \
  -e GITEA_TOKEN=<你的新token> \
  -e GITEA_USERNAME=deanwang \
  -e DATABASE_URL='sqlite:///data/mirror_sync.db' \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  deanwang/mirror-git:latest
```

### 2. 查看启动日志

```bash
docker logs mirror-git-app --tail 50
```

应该能看到 Gitea 配置信息打印：
```
╔══════════════════════════════════════════════════════════════╗
║  Gitea 配置信息                                             ║
╠══════════════════════════════════════════════════════════════╣
║  URL:      http://192.168.9.101:8418                        ║
║  Username: deanwang                                          ║
║  Token:    ********e00                                      ║
║  Password: 未设置                                           ║
╚══════════════════════════════════════════════════════════════╝
```

### 3. 触发同步测试

```bash
# 通过 Web UI 或 API 触发同步
curl -X POST http://localhost:8020/api/repositories/<repo_id>/sync
```

### 4. 检查 Gitea 组织中是否创建了仓库

```bash
curl -X GET "http://100.64.0.11:8418/api/v1/orgs/mirror-github/repos" \
  -H "Authorization: token <your_token>"
```

应该能看到 `jimmer` 等仓库。

### 5. 查看同步日志

```bash
docker exec mirror-git-app cat /app/logs/sync.log | tail -100
```

应该看到：
```
[PUSH START] Preparing to push to Gitea: mirror-github/jimmer
[PUSH SUCCESS] Pushed to mirror-github/jimmer in X.Xs
```

## 常见问题

### Q1: 已有数据库中的仓库怎么办？

A: 数据库中 `gitea_owner` 字段的值会被正确解释为组织名，不需要修改。

### Q2: 如果不想使用组织，想推送到用户空间？

A: 清除数据库中的 `gitea_owner` 字段：
```python
from src.models import Database, Repository
db = Database('sqlite:///./data/sync.db')
session = db.get_session()
repos = session.query(Repository).filter(Repository.gitea_owner != None).all()
for repo in repos:
    repo.gitea_owner = None
session.commit()
session.close()
```

### Q3: Token 需要什么权限？

A: Token 需要以下权限：
- ✅ `repo` (仓库读写)
- ✅ `write:user` (创建仓库)
- ✅ `admin:org` (在组织中创建仓库)

### Q4: 组织必须预先创建吗？

A: 是的，组织 `mirror-github` 必须在 Gitea 中预先手动创建。但组织内的仓库会通过 API 自动创建。

## 测试清单

- [ ] 应用启动时打印 Gitea 配置信息
- [ ] 能够在组织中通过 API 创建仓库
- [ ] 推送到组织仓库成功
- [ ] gitea_owner 为 NULL 的仓库推送到用户空间
- [ ] 定时任务能正确同步组织仓库
- [ ] 错误日志清晰明确（403 权限错误时有详细提示）
