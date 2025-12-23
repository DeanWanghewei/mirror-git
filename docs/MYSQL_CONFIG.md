# 使用 MySQL 数据库配置指南

## 概述

默认情况下，系统使用 SQLite 数据库，适合大多数场景。如果需要更强的并发性能或多实例部署，可以切换到 MySQL。

## 配置步骤

### 1. 启用 MySQL 服务

编辑 `docker-compose.yml`：

**取消注释 MySQL 依赖**：
```yaml
    depends_on:
      mysql:
        condition: service_healthy
```

**设置 MySQL 数据库 URL**：
```yaml
    environment:
      # 注释掉 SQLite 配置
      # DATABASE_URL: ${DATABASE_URL:-sqlite:////app/data/sync.db}

      # 启用 MySQL 配置
      DATABASE_URL: mysql+pymysql://${MYSQL_USER:-mirror_user}:${MYSQL_PASSWORD:-mirror123456}@mysql:3306/${MYSQL_DATABASE:-mirror_git}?charset=utf8mb4
      DATABASE_TYPE: mysql
```

### 2. 配置 MySQL 环境变量

在 `.env` 文件中设置：

```env
# MySQL Configuration
MYSQL_ROOT_PASSWORD=root123456
MYSQL_DATABASE=mirror_git
MYSQL_USER=mirror_user
MYSQL_PASSWORD=mirror123456
MYSQL_PORT=3306
```

### 3. 启动服务

```bash
# 重新构建并启动（包括 MySQL）
docker-compose up -d

# 查看日志
docker-compose logs -f app
docker-compose logs -f mysql

# 验证 MySQL 连接
docker-compose exec mysql mysql -u mirror_user -pmirror123456 -D mirror_git -e "SHOW TABLES;"
```

## SQLite vs MySQL 对比

| 特性 | SQLite | MySQL |
|------|--------|-------|
| **部署复杂度** | ⭐⭐⭐⭐⭐ 简单 | ⭐⭐⭐ 需额外容器 |
| **资源占用** | ⭐⭐⭐⭐⭐ 极低 | ⭐⭐⭐ 中等 |
| **并发性能** | ⭐⭐⭐ 读多写少 | ⭐⭐⭐⭐⭐ 高并发 |
| **数据规模** | ⭐⭐⭐⭐ < 100 仓库 | ⭐⭐⭐⭐⭐ 无限制 |
| **备份迁移** | ⭐⭐⭐⭐⭐ 复制文件 | ⭐⭐⭐ 需导出工具 |
| **多实例** | ❌ 不支持 | ✅ 支持 |
| **推荐场景** | 单机部署 | 高并发/多实例 |

## 数据迁移

### SQLite → MySQL

```bash
# 1. 导出 SQLite 数据（在容器内）
docker-compose exec app bash
sqlite3 /app/data/sync.db .dump > /tmp/dump.sql

# 2. 转换为 MySQL 格式
sed -i 's/AUTOINCREMENT/AUTO_INCREMENT/g' /tmp/dump.sql
sed -i 's/INTEGER PRIMARY KEY/INT PRIMARY KEY AUTO_INCREMENT/g' /tmp/dump.sql

# 3. 导入 MySQL
mysql -u mirror_user -pmirror123456 -D mirror_git < /tmp/dump.sql
```

### MySQL → SQLite

```bash
# 1. 导出 MySQL 数据
docker-compose exec mysql mysqldump -u mirror_user -pmirror123456 mirror_git > backup.sql

# 2. 停止应用，切换到 SQLite
# 编辑 docker-compose.yml，使用 SQLite 配置

# 3. 重启应用（会创建新的 SQLite 数据库结构）
docker-compose restart app

# 4. 手动导入数据（需要根据表结构调整）
```

## 故障排查

### 问题 1: MySQL 连接失败

**错误信息**：
```
Can't connect to MySQL server on 'mysql'
```

**解决方案**：
```bash
# 检查 MySQL 容器状态
docker-compose ps mysql

# 检查网络连接
docker-compose exec app ping mysql

# 查看 MySQL 日志
docker-compose logs mysql

# 重启 MySQL
docker-compose restart mysql
```

### 问题 2: 权限错误

**错误信息**：
```
Access denied for user 'mirror_user'@'%'
```

**解决方案**：
```bash
# 进入 MySQL 容器
docker-compose exec mysql mysql -u root -proot123456

# 创建用户和授权
CREATE USER 'mirror_user'@'%' IDENTIFIED BY 'mirror123456';
GRANT ALL PRIVILEGES ON mirror_git.* TO 'mirror_user'@'%';
FLUSH PRIVILEGES;
```

### 问题 3: 数据库不存在

**错误信息**：
```
Unknown database 'mirror_git'
```

**解决方案**：
```bash
# 创建数据库
docker-compose exec mysql mysql -u root -proot123456 -e "CREATE DATABASE mirror_git CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 重启应用
docker-compose restart app
```

## 性能优化

### MySQL 配置优化

编辑 `docker/mysql/my.cnf`：

```ini
[mysqld]
# 连接数
max_connections = 1000

# 缓冲池大小（根据可用内存调整）
innodb_buffer_pool_size = 1G

# 日志配置
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2

# 查询缓存
query_cache_size = 0
query_cache_type = 0

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

### 索引优化

```sql
-- 为常用查询添加索引
CREATE INDEX idx_repo_url ON repositories(url);
CREATE INDEX idx_repo_status ON repositories(last_sync_status);
CREATE INDEX idx_sync_history_repo ON sync_history(repository_id, created_at);
```

## 备份策略

### 自动备份脚本

```bash
#!/bin/bash
# backup-mysql.sh

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T mysql mysqldump \
  -u mirror_user \
  -pmirror123456 \
  --single-transaction \
  --quick \
  --lock-tables=false \
  mirror_git > "$BACKUP_DIR/mirror_git_$DATE.sql"

# 压缩
gzip "$BACKUP_DIR/mirror_git_$DATE.sql"

# 保留最近7天的备份
find $BACKUP_DIR -name "mirror_git_*.sql.gz" -mtime +7 -delete

echo "Backup completed: mirror_git_$DATE.sql.gz"
```

### 定时任务

```bash
# 添加到 crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/backup-mysql.sh
```

## 推荐配置

### 小型部署（< 50 仓库）
```yaml
# 使用 SQLite
# 💡 格式说明：sqlite:////app/data/xxx.db (4个斜杠 = 绝对路径)
DATABASE_URL: sqlite:////app/data/sync.db
```

### 中型部署（50-200 仓库）
```yaml
# MySQL，基础配置
DATABASE_URL: mysql+pymysql://mirror_user:password@mysql:3306/mirror_git
# MySQL 内存: 1-2GB
```

### 大型部署（200+ 仓库）
```yaml
# MySQL，优化配置
DATABASE_URL: mysql+pymysql://mirror_user:password@mysql:3306/mirror_git
# MySQL 内存: 4GB+
# 启用连接池
# 优化 innodb_buffer_pool_size
```

---

**提示**：如无特殊需求，建议使用默认的 SQLite 配置，简单可靠。
