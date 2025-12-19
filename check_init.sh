#!/bin/bash
# 项目初始化完成检查脚本

echo "===================="
echo "项目文件结构检查"
echo "===================="
echo ""

# 定义颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查文件
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${YELLOW}✗${NC} $1 (missing)"
        return 1
    fi
}

# 检查目录
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${YELLOW}✗${NC} $1/ (missing)"
        return 1
    fi
}

echo -e "${BLUE}文档文件:${NC}"
check_file "PROJECT_PLAN.md"
check_file "README.md"
check_file "INIT_INFO.md"
check_file "DEVELOPER_GUIDE.md"
check_file "QUICK_START.md"

echo ""
echo -e "${BLUE}配置文件:${NC}"
check_file ".env.example"
check_file ".gitignore"
check_file "requirements.txt"

echo ""
echo -e "${BLUE}源代码目录:${NC}"
check_dir "src"
check_dir "src/config"
check_dir "src/clients"
check_dir "src/sync"
check_dir "src/scheduler"
check_dir "src/logger"
check_dir "tests"

echo ""
echo -e "${BLUE}源代码文件:${NC}"
check_file "src/__init__.py"
check_file "src/main.py"
check_file "src/config/__init__.py"
check_file "src/config/repositories.json"
check_file "src/clients/__init__.py"
check_file "src/sync/__init__.py"
check_file "src/scheduler/__init__.py"
check_file "src/logger/__init__.py"
check_file "tests/__init__.py"

echo ""
echo -e "${BLUE}数据目录:${NC}"
check_dir "data"
check_dir "logs"

echo ""
echo "===================="
echo "初始化完成！"
echo "===================="
