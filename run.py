#!/usr/bin/env python3
"""
GitHub Mirror Sync - Web UI Launcher

只启动 Web UI 服务，所有配置通过环境变量设置。
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

if __name__ == "__main__":
    # 从环境变量读取配置，提供默认值
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))
    workers = int(os.getenv("WEB_WORKERS", "1"))
    log_level = os.getenv("WEB_LOG_LEVEL", "info")

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      🚀 GitHub Mirror Sync - Web UI                         ║
║                                                              ║
║  📌 访问方式:                                               ║
║     主页:     http://{host}:{port}
║     API文档:  http://{host}:{port}/docs
║     ReDoc:    http://{host}:{port}/redoc
║                                                              ║
║  ⚙️  当前配置:                                               ║
║     监听地址: {host:<45} ║
║     监听端口: {port:<45} ║
║     工作进程: {workers:<45} ║
║     日志级别: {log_level:<45} ║
║                                                              ║
║  💡 提示: 按 Ctrl+C 停止服务                                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        uvicorn.run(
            "src.web.app:app",
            host=host,
            port=port,
            workers=workers,
            log_level=log_level
        )
    except KeyboardInterrupt:
        print("\n✓ 服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 启动失败: {e}")
        sys.exit(1)
