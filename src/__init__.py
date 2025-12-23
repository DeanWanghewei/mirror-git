"""
GitHub Repositories Mirror Sync System
A tool to mirror GitHub repositories to self-hosted Gitea server
"""

__version__ = "2.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

import logging

# 配置项目级别的日志
logger = logging.getLogger(__name__)

__all__ = [
    "logger",
    "__version__",
    "__author__",
    "__email__",
]
