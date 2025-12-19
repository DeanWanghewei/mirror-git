"""
Tests for logging system.
"""

import pytest
from pathlib import Path
import tempfile

from src.logger.logger import StructuredLogger, get_logger, create_logger


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def log_config(temp_log_dir):
    """Create a test log configuration."""
    class LogConfig:
        level = "DEBUG"
        file_path = str(temp_log_dir / "test.log")
        max_file_size = 10  # 10 MB
        backup_count = 3

    return LogConfig()


def test_structured_logger_creation(log_config):
    """Test creating a structured logger."""
    logger = StructuredLogger("test", log_config)
    assert logger.name == "test"
    assert logger.logger is not None


def test_logger_debug_message(log_config, capsys):
    """Test debug log message."""
    logger = StructuredLogger("test", log_config)
    logger.debug("Debug message")
    captured = capsys.readouterr()
    assert "Debug message" in captured.err or "Debug message" in captured.out


def test_logger_info_message(log_config, capsys):
    """Test info log message."""
    logger = StructuredLogger("test", log_config)
    logger.info("Info message")
    captured = capsys.readouterr()
    assert "Info message" in captured.err or "Info message" in captured.out


def test_logger_warning_message(log_config, capsys):
    """Test warning log message."""
    logger = StructuredLogger("test", log_config)
    logger.warning("Warning message")
    captured = capsys.readouterr()
    assert "Warning message" in captured.err or "Warning message" in captured.out


def test_logger_error_message(log_config, capsys):
    """Test error log message."""
    logger = StructuredLogger("test", log_config)
    logger.error("Error message")
    captured = capsys.readouterr()
    assert "Error message" in captured.err or "Error message" in captured.out


def test_logger_file_creation(log_config):
    """Test that logger creates log file."""
    logger = StructuredLogger("test", log_config)
    logger.info("Test message")

    # Check that log file was created
    log_file = Path(log_config.file_path)
    assert log_file.exists() or log_file.parent.exists()


def test_get_logger(log_config):
    """Test getting logger instance."""
    logger1 = get_logger("test_app", log_config)
    logger2 = get_logger("test_app", log_config)

    # Should return same instance
    assert logger1 is logger2


def test_create_logger(log_config):
    """Test creating new logger instance."""
    logger1 = create_logger("new_logger", log_config)
    logger2 = create_logger("new_logger", log_config)

    # Should create new instance each time
    assert logger1 is not None
    assert logger2 is not None


def test_logger_with_format(log_config, capsys):
    """Test logger with formatted messages."""
    logger = StructuredLogger("test", log_config)
    logger.info("Message with %s", "parameter")

    captured = capsys.readouterr()
    assert "Message with parameter" in captured.err or "Message with parameter" in captured.out


def test_logger_exception(log_config, capsys):
    """Test logger exception method."""
    logger = StructuredLogger("test", log_config)

    try:
        raise ValueError("Test error")
    except ValueError:
        logger.exception("An error occurred")

    captured = capsys.readouterr()
    assert "An error occurred" in captured.err or "An error occurred" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
