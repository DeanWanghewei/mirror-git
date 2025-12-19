"""
Logging system for GitHub Mirror Sync.

Provides structured logging with file rotation and color output.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

import colorlog


class StructuredLogger:
    """Structured logging system with file rotation and color output."""

    def __init__(self, name: str, log_config):
        """Initialize logger.

        Args:
            name: Logger name
            log_config: LogConfig instance with logging configuration
        """
        self.name = name
        self.log_config = log_config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with handlers.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_config.level)

        # Clear existing handlers
        logger.handlers.clear()

        # Create log directory if needed
        log_file = Path(self.log_config.file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Console handler with colors
        console_handler = self._create_console_handler()
        logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = self._create_file_handler()
        logger.addHandler(file_handler)

        return logger

    def _create_console_handler(self) -> logging.StreamHandler:
        """Create console handler with color output.

        Returns:
            Configured console handler
        """
        handler = colorlog.StreamHandler()
        handler.setLevel(self.log_config.level)

        formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s]%(reset)s %(levelname)-8s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            }
        )
        handler.setFormatter(formatter)
        return handler

    def _create_file_handler(self) -> logging.Handler:
        """Create file handler with rotation.

        Returns:
            Configured file handler
        """
        log_file = self.log_config.file_path
        max_bytes = self.log_config.max_file_size * 1024 * 1024  # Convert MB to bytes
        backup_count = self.log_config.backup_count

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        handler.setLevel(self.log_config.level)

        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        return handler

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, exc_info=False, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """Log exception message."""
        self.logger.exception(message, *args, **kwargs)


# Global logger instances
_loggers: dict = {}


def get_logger(name: str, log_config=None) -> StructuredLogger:
    """Get or create a logger instance.

    Args:
        name: Logger name
        log_config: Optional LogConfig instance (uses default if not provided)

    Returns:
        StructuredLogger instance
    """
    global _loggers

    if name not in _loggers:
        if log_config is None:
            # Create default log config dynamically
            class DefaultLogConfig:
                level = "INFO"
                file_path = "./logs/sync.log"
                max_file_size = 100
                backup_count = 10

            log_config = DefaultLogConfig()

        _loggers[name] = StructuredLogger(name, log_config)

    return _loggers[name]


def create_logger(name: str, log_config) -> StructuredLogger:
    """Create a new logger instance (overwriting if exists).

    Args:
        name: Logger name
        log_config: LogConfig instance

    Returns:
        StructuredLogger instance
    """
    global _loggers
    _loggers[name] = StructuredLogger(name, log_config)
    return _loggers[name]


# Module-level logger
_default_logger: Optional[StructuredLogger] = None


def init_default_logger(log_config) -> None:
    """Initialize default logger for the module.

    Args:
        log_config: LogConfig instance
    """
    global _default_logger
    _default_logger = create_logger("mirror_sync", log_config)


def debug(message: str, *args, **kwargs) -> None:
    """Log debug message using default logger."""
    if _default_logger:
        _default_logger.debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs) -> None:
    """Log info message using default logger."""
    if _default_logger:
        _default_logger.info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs) -> None:
    """Log warning message using default logger."""
    if _default_logger:
        _default_logger.warning(message, *args, **kwargs)


def error(message: str, *args, exc_info=False, **kwargs) -> None:
    """Log error message using default logger."""
    if _default_logger:
        _default_logger.error(message, *args, exc_info=exc_info, **kwargs)


def critical(message: str, *args, **kwargs) -> None:
    """Log critical message using default logger."""
    if _default_logger:
        _default_logger.critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs) -> None:
    """Log exception message using default logger."""
    if _default_logger:
        _default_logger.exception(message, *args, **kwargs)
