#!/usr/bin/env python3
"""
GitHub Repositories Mirror Sync System - Main Entry Point

Usage:
    python src/main.py --sync-now      # Sync immediately
    python src/main.py --daemon        # Run as daemon
    python src/main.py --help          # Show help
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 添加项目路径到 sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """设置日志系统。

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)

    Returns:
        配置后的日志记录器
    """
    logger = logging.getLogger("mirror_sync")
    logger.setLevel(log_level)

    # 创建日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（稍后实现）
    # log_file = PROJECT_ROOT / "logs" / "sync.log"
    # file_handler = logging.FileHandler(log_file)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    return logger


def main(args: Optional[list] = None) -> int:
    """主函数。

    Args:
        args: 命令行参数列表

    Returns:
        退出代码 (0=成功, 1=失败)
    """
    parser = argparse.ArgumentParser(
        description="GitHub Repositories Mirror Sync System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --sync-now      Sync repositories immediately
  %(prog)s --daemon        Run as daemon with scheduled syncs
  %(prog)s --help          Show this help message
        """
    )

    parser.add_argument(
        "--sync-now",
        action="store_true",
        help="Sync all repositories immediately"
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon with periodic synchronization"
    )

    parser.add_argument(
        "--config",
        type=str,
        default=".env",
        help="Configuration file path (default: .env)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0-planning"
    )

    parsed_args = parser.parse_args(args)

    # 设置日志
    logger = setup_logger(parsed_args.log_level)
    logger.info("GitHub Repositories Mirror Sync System v1.0.0-planning")

    # 验证至少选择了一个操作
    if not (parsed_args.sync_now or parsed_args.daemon):
        parser.print_help()
        logger.warning("No action specified. Use --sync-now or --daemon")
        return 1

    try:
        # TODO: 导入配置系统
        logger.debug(f"Loading config from: {parsed_args.config}")
        # config = load_config(parsed_args.config)

        # TODO: 导入同步引擎
        logger.debug("Initializing sync engine")
        # engine = SyncEngine(config)

        if parsed_args.sync_now:
            logger.info("Starting immediate synchronization...")
            # TODO: 执行单次同步
            # result = engine.sync_all()
            # logger.info(f"Sync completed: {result['success']} success, {result['failed']} failed")
            logger.info("✓ Sync completed (feature not yet implemented)")

        elif parsed_args.daemon:
            logger.info("Starting daemon mode (background synchronization)...")
            # TODO: 启动定时调度
            # scheduler = TaskScheduler(config)
            # scheduler.schedule_sync(interval=config.get("sync_interval", 3600))
            # scheduler.start()
            logger.info("✓ Daemon started (feature not yet implemented)")

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
