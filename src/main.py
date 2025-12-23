#!/usr/bin/env python3
"""
GitHub Repositories Mirror Sync System - Web UI Entry Point

Usage:
    python src/main.py

访问 Web UI: http://localhost:8000
"""

import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 添加项目路径到 sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """启动 Web UI 服务器"""
    try:
        import uvicorn
        from src.web.app import app

        print("=" * 60)
        print("🚀 GitHub Mirror Sync - Web UI Starting...")
        print("=" * 60)
        print()
        print("📌 访问方式:")
        print("   主页:     http://localhost:8000")
        print("   API文档:  http://localhost:8000/docs")
        print("   ReDoc:    http://localhost:8000/redoc")
        print()
        print("💡 提示: 按 Ctrl+C 停止服务")
        print("=" * 60)
        print()

        # 启动 Web 服务器
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )

        return 0

    except KeyboardInterrupt:
        print("\n✓ 服务已停止")
        return 0
    except ImportError as e:
        print(f"✗ 导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
