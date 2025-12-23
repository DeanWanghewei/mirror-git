#!/bin/bash
#
# GitHub Mirror Sync - Docker 快速启动脚本
# 适用于不使用 docker-compose 的用户
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo_error "Docker 未安装，请先安装 Docker"
    exit 1
fi

echo_info "Docker 版本: $(docker --version)"

# 项目配置
IMAGE_NAME="mirror-git"
IMAGE_TAG="1.2.0"
CONTAINER_NAME="mirror-git-app"
NETWORK_NAME="mirror-net"
PORT="8000"

# 检查环境变量文件
ENV_FILE="docker.env"
if [ ! -f "$ENV_FILE" ]; then
    echo_warn "环境变量文件 $ENV_FILE 不存在"
    echo_info "创建示例环境变量文件..."
    cat > "$ENV_FILE" << 'ENVEOF'
# GitHub 配置 (可选 - 仅私有仓库需要)
GITHUB_TOKEN=
GITHUB_API_URL=https://api.github.com

# Gitea 配置 (必需)
GITEA_URL=https://gitea.example.com
GITEA_TOKEN=your_gitea_api_token_here
GITEA_USERNAME=mirror_user
GITEA_PASSWORD=your_password

# 同步配置
LOCAL_REPO_PATH=/app/data/repos
SYNC_INTERVAL=3600
SYNC_TIMEOUT=1800
SYNC_RETRY_COUNT=3
SYNC_CONCURRENT=3

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/app/logs/sync.log
LOG_MAX_SIZE=100
LOG_BACKUP_COUNT=10

# 数据库配置（默认使用 SQLite）
DATABASE_URL=sqlite:///app/data/mirror_sync.db

# 时区配置
TZ=Asia/Shanghai
ENVEOF
    echo_info "已创建 $ENV_FILE 文件，请编辑并填入您的配置"
    echo_warn "请至少配置以下必需项："
    echo "  - GITEA_URL"
    echo "  - GITEA_TOKEN"
    echo "  - GITEA_USERNAME"
    echo "  - GITEA_PASSWORD"
    echo ""
    echo_info "可选配置（仅私有仓库需要）："
    echo "  - GITHUB_TOKEN"
    echo ""
    read -p "配置完成后按回车继续..."
fi

# 显示菜单
show_menu() {
    echo ""
    echo "========================================="
    echo "   GitHub Mirror Sync - Docker 管理"
    echo "========================================="
    echo "1. 构建镜像"
    echo "2. 启动应用 (SQLite)"
    echo "3. 启动应用 (MySQL)"
    echo "4. 停止应用"
    echo "5. 重启应用"
    echo "6. 查看日志"
    echo "7. 查看容器状态"
    echo "8. 进入容器"
    echo "9. 删除容器"
    echo "0. 退出"
    echo "========================================="
    read -p "请选择操作 [0-9]: " choice
}

# 构建镜像
build_image() {
    echo_info "开始构建镜像 $IMAGE_NAME:$IMAGE_TAG ..."
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
    echo_info "镜像构建完成"
}

# 创建网络
ensure_network() {
    if ! docker network ls | grep -q "$NETWORK_NAME"; then
        echo_info "创建 Docker 网络: $NETWORK_NAME"
        docker network create "$NETWORK_NAME"
    fi
}

# 启动应用 - SQLite
start_app_sqlite() {
    echo_info "启动应用 (使用 SQLite 数据库)..."
    
    # 停止已存在的容器
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        echo_warn "容器已存在，正在停止并删除..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
    fi
    
    # 创建数据目录
    mkdir -p data logs
    
    # 启动容器
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$PORT:8000" \
        --env-file "$ENV_FILE" \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        --restart unless-stopped \
        "$IMAGE_NAME:$IMAGE_TAG"
    
    echo_info "应用启动成功"
    echo_info "Web 界面: http://localhost:$PORT"
    echo_info "API 文档: http://localhost:$PORT/docs"
    echo ""
    echo_info "查看日志: docker logs -f $CONTAINER_NAME"
}

# 启动应用 - MySQL
start_app_mysql() {
    echo_info "启动应用 (使用 MySQL 数据库)..."
    
    ensure_network
    
    # 启动 MySQL
    if ! docker ps | grep -q "mirror-git-mysql"; then
        echo_info "启动 MySQL 容器..."
        docker run -d \
            --name mirror-git-mysql \
            --network "$NETWORK_NAME" \
            -e MYSQL_ROOT_PASSWORD=root123456 \
            -e MYSQL_DATABASE=mirror_git \
            -e MYSQL_USER=mirror_user \
            -e MYSQL_PASSWORD=mirror123456 \
            -e TZ=Asia/Shanghai \
            -p 3306:3306 \
            -v mirror_data:/var/lib/mysql \
            --restart unless-stopped \
            mysql:8.0 \
            --default-authentication-plugin=mysql_native_password \
            --character-set-server=utf8mb4 \
            --collation-server=utf8mb4_unicode_ci
        
        echo_info "等待 MySQL 启动..."
        sleep 10
    fi
    
    # 停止已存在的应用容器
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        echo_warn "容器已存在，正在停止并删除..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
    fi
    
    # 创建数据目录
    mkdir -p data logs
    
    # 更新 DATABASE_URL
    export DATABASE_URL="mysql+pymysql://mirror_user:mirror123456@mirror-git-mysql:3306/mirror_git?charset=utf8mb4"
    
    # 启动应用容器
    docker run -d \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK_NAME" \
        -p "$PORT:8000" \
        --env-file "$ENV_FILE" \
        -e DATABASE_URL="$DATABASE_URL" \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        --restart unless-stopped \
        "$IMAGE_NAME:$IMAGE_TAG"
    
    echo_info "应用启动成功"
    echo_info "Web 界面: http://localhost:$PORT"
    echo_info "API 文档: http://localhost:$PORT/docs"
    echo ""
    echo_info "查看日志: docker logs -f $CONTAINER_NAME"
}

# 停止应用
stop_app() {
    echo_info "停止应用..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || echo_warn "容器未运行"
    echo_info "应用已停止"
}

# 重启应用
restart_app() {
    echo_info "重启应用..."
    docker restart "$CONTAINER_NAME" 2>/dev/null || echo_error "容器不存在"
    echo_info "应用已重启"
}

# 查看日志
view_logs() {
    echo_info "查看实时日志 (Ctrl+C 退出)..."
    docker logs -f "$CONTAINER_NAME"
}

# 查看状态
view_status() {
    echo_info "容器状态:"
    docker ps -a | grep "$CONTAINER_NAME" || echo_warn "容器不存在"
    echo ""
    echo_info "容器详情:"
    docker inspect "$CONTAINER_NAME" 2>/dev/null | grep -E "Status|Running|StartedAt" || echo_warn "容器不存在"
}

# 进入容器
enter_container() {
    echo_info "进入容器 (输入 exit 退出)..."
    docker exec -it "$CONTAINER_NAME" bash
}

# 删除容器
remove_container() {
    read -p "确认删除容器 $CONTAINER_NAME ? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo_info "删除容器..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        echo_info "容器已删除"
    else
        echo_info "取消删除"
    fi
}

# 主循环
while true; do
    show_menu
    case $choice in
        1)
            build_image
            ;;
        2)
            start_app_sqlite
            ;;
        3)
            start_app_mysql
            ;;
        4)
            stop_app
            ;;
        5)
            restart_app
            ;;
        6)
            view_logs
            ;;
        7)
            view_status
            ;;
        8)
            enter_container
            ;;
        9)
            remove_container
            ;;
        0)
            echo_info "退出"
            exit 0
            ;;
        *)
            echo_error "无效选择"
            ;;
    esac
    
    read -p "按回车继续..."
done
