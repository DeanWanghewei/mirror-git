#!/bin/bash
# 测试定时任务调度器功能

echo "======================================"
echo "定时任务调度器测试脚本"
echo "======================================"
echo ""

API_BASE="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查服务是否运行
echo "1️⃣  检查服务状态..."
if curl -s "${API_BASE}/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 服务正常运行"
else
    echo -e "${RED}✗${NC} 服务未运行，请先启动应用"
    exit 1
fi
echo ""

# 查看所有定时任务
echo "2️⃣  查看当前定时任务..."
TASKS=$(curl -s "${API_BASE}/api/tasks/")
echo "$TASKS" | python3 -m json.tool 2>/dev/null || echo "$TASKS"
echo ""

# 检查是否有 sync_all_repositories 任务
if echo "$TASKS" | grep -q "sync_all_repositories"; then
    echo -e "${GREEN}✓${NC} 找到自动同步任务 (sync_all_repositories)"

    # 提取下次运行时间
    NEXT_RUN=$(echo "$TASKS" | python3 -c "import sys, json; tasks = json.load(sys.stdin); print([t['next_run_time'] for t in tasks if t['id'] == 'sync_all_repositories'][0] if tasks else 'N/A')" 2>/dev/null)
    if [ "$NEXT_RUN" != "null" ] && [ "$NEXT_RUN" != "N/A" ]; then
        echo -e "   下次运行时间: ${YELLOW}${NEXT_RUN}${NC}"
    else
        echo -e "${YELLOW}⚠${NC}  任务已添加但未调度（调度器可能未启动）"
    fi
else
    echo -e "${RED}✗${NC} 未找到自动同步任务"
    echo -e "${YELLOW}提示:${NC} 任务可能未添加，请检查应用启动日志"
fi
echo ""

# 查看同步历史
echo "3️⃣  查看最近的同步历史..."
HISTORY=$(curl -s "${API_BASE}/api/sync/history?limit=5")
if [ ! -z "$HISTORY" ]; then
    echo "$HISTORY" | python3 -m json.tool 2>/dev/null || echo "$HISTORY"
else
    echo -e "${YELLOW}⚠${NC}  暂无同步历史记录"
fi
echo ""

# 手动触发一次同步测试
echo "4️⃣  是否要手动触发一次同步测试？(y/n)"
read -r CONFIRM

if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
    echo "正在触发同步..."
    RESULT=$(curl -s -X POST "${API_BASE}/api/tasks/sync/now")
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
    echo ""
    echo -e "${GREEN}✓${NC} 同步已触发，请检查日志文件: logs/sync.log"
else
    echo "跳过手动测试"
fi
echo ""

echo "======================================"
echo "测试完成"
echo "======================================"
echo ""
echo "📝 日志文件位置:"
echo "   - 应用日志: logs/app.log"
echo "   - 同步日志: logs/sync.log"
echo ""
echo "🔍 有用的 API 端点:"
echo "   - 查看所有任务: GET  ${API_BASE}/api/tasks/"
echo "   - 手动触发同步: POST ${API_BASE}/api/tasks/sync/now"
echo "   - 同步历史:     GET  ${API_BASE}/api/sync/history"
echo "   - 仓库列表:     GET  ${API_BASE}/api/repositories"
echo ""
