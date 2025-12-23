"""
Configuration management system for GitHub Mirror Sync.

Handles loading and validating configuration from .env and JSON files.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class GitHubConfig(BaseModel):
    """GitHub API configuration."""
    token: Optional[str] = Field(default=None, description="GitHub personal access token (optional for public repos)")
    api_url: str = Field(default="https://api.github.com", description="GitHub API URL")

    @validator("token")
    def token_validation(cls, v: Optional[str]) -> Optional[str]:
        """Validate token - allow None or empty for public repos."""
        if v is not None and v.strip() == "":
            # Convert empty string to None
            return None
        return v


class GiteaConfig(BaseModel):
    """Gitea server configuration."""
    url: str = Field(..., description="Gitea server URL")
    token: str = Field(..., description="Gitea API token")
    username: str = Field(..., description="Gitea username for mirror operations")
    password: Optional[str] = Field(default=None, description="Gitea password (if needed)")

    @validator("url")
    def url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Gitea URL cannot be empty")
        return v


class SyncConfig(BaseModel):
    """Repository synchronization configuration."""
    local_path: str = Field(default="./data/repos", description="Local repository storage path")
    interval: int = Field(default=3600, description="Sync interval in seconds")
    timeout: int = Field(default=1800, description="Sync timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retries on failure")
    concurrent_tasks: int = Field(default=3, description="Number of concurrent sync tasks")

    @validator("interval")
    def interval_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Sync interval must be positive")
        return v

    @validator("timeout")
    def timeout_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v


class ProxyConfig(BaseModel):
    """Proxy configuration for network requests."""
    enabled: bool = Field(default=False, description="Enable proxy")
    url: Optional[str] = Field(default=None, description="Proxy URL (e.g., http://127.0.0.1:7890)")
    username: Optional[str] = Field(default=None, description="Proxy username")
    password: Optional[str] = Field(default=None, description="Proxy password")


class LogConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    file_path: str = Field(default="./logs/sync.log", description="Log file path")
    max_file_size: int = Field(default=100, description="Max log file size in MB")
    backup_count: int = Field(default=10, description="Number of backup log files to keep")

    @validator("level")
    def level_valid(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class NotificationConfig(BaseModel):
    """Notification configuration."""
    email_enabled: bool = Field(default=False, description="Enable email notifications")
    smtp_server: Optional[str] = Field(default=None, description="SMTP server address")
    smtp_port: int = Field(default=587, description="SMTP server port")
    sender_email: Optional[str] = Field(default=None, description="Sender email address")
    sender_password: Optional[str] = Field(default=None, description="Sender email password")
    recipient_emails: Optional[str] = Field(default=None, description="Recipient emails (comma separated)")

    webhook_enabled: bool = Field(default=False, description="Enable webhook notifications")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")


class SystemConfig(BaseModel):
    """System-wide configuration."""
    github: GitHubConfig
    gitea: GiteaConfig
    sync: SyncConfig
    proxy: ProxyConfig
    log: LogConfig
    notification: NotificationConfig


class ConfigManager:
    """Manages application configuration from .env and JSON files."""

    def __init__(self, env_file: str = ".env", repo_config_file: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            env_file: Path to .env configuration file
            repo_config_file: Path to repositories.json configuration file
        """
        self.env_file = Path(env_file)
        self.repo_config_file = Path(repo_config_file) if repo_config_file else Path("src/config/repositories.json")
        self.config: Optional[SystemConfig] = None
        self.repositories: Dict[str, Any] = {}

    def load(self) -> SystemConfig:
        """Load and parse configuration from environment variables.

        Configuration can be loaded from:
        1. .env file (if exists) - will be loaded first
        2. System environment variables - always checked

        Returns:
            Parsed SystemConfig object

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Load environment variables from .env file if it exists
        # In Docker/production, environment variables are set directly
        if self.env_file.exists():
            load_dotenv(self.env_file)
            print(f"✓ Loaded configuration from {self.env_file}")
        else:
            print(f"ℹ .env file not found, using environment variables directly")

        # Parse configuration from environment variables
        # GitHub token is optional - only needed for private repos
        github_token = self._get_env("GITHUB_TOKEN", required=False)
        if github_token and github_token.strip():
            github_token = github_token.strip()
        else:
            github_token = None
            print("ℹ GitHub token not provided - only public repositories will be accessible")

        github_config = GitHubConfig(
            token=github_token,
            api_url=self._get_env("GITHUB_API_URL", default="https://api.github.com")
        )

        # Load Gitea configuration and print for debugging
        gitea_url = self._get_env("GITEA_URL", required=True)
        gitea_token = self._get_env("GITEA_TOKEN", required=True)
        gitea_username = self._get_env("GITEA_USERNAME", required=True)
        gitea_password = self._get_env("GITEA_PASSWORD")

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Gitea 配置信息                                             ║
╠══════════════════════════════════════════════════════════════╣
║  URL:      {gitea_url:<49} ║
║  Username: {gitea_username:<49} ║
║  Token:    {('*' * 8 + gitea_token[-4:] if gitea_token and len(gitea_token) > 8 else '***'):<49} ║
║  Password: {('已设置' if gitea_password else '未设置'):<49} ║
╚══════════════════════════════════════════════════════════════╝
        """)

        gitea_config = GiteaConfig(
            url=gitea_url,
            token=gitea_token,
            username=gitea_username,
            password=gitea_password
        )

        sync_config = SyncConfig(
            local_path=self._get_env("LOCAL_REPO_PATH", default="./data/repos"),
            interval=int(self._get_env("SYNC_INTERVAL", default="3600")),
            timeout=int(self._get_env("SYNC_TIMEOUT", default="1800")),
            retry_count=int(self._get_env("SYNC_RETRY_COUNT", default="3")),
            concurrent_tasks=int(self._get_env("SYNC_CONCURRENT", default="3"))
        )

        proxy_config = ProxyConfig(
            enabled=self._get_env("USE_PROXY", default="false").lower() == "true",
            url=self._get_env("PROXY_URL"),
            username=self._get_env("PROXY_USERNAME"),
            password=self._get_env("PROXY_PASSWORD")
        )

        log_config = LogConfig(
            level=self._get_env("LOG_LEVEL", default="INFO"),
            file_path=self._get_env("LOG_FILE", default="./logs/sync.log"),
            max_file_size=int(self._get_env("LOG_MAX_SIZE", default="100")),
            backup_count=int(self._get_env("LOG_BACKUP_COUNT", default="10"))
        )

        notification_config = NotificationConfig(
            email_enabled=self._get_env("NOTIFICATION_EMAIL_ENABLED", default="false").lower() == "true",
            smtp_server=self._get_env("SMTP_SERVER"),
            smtp_port=int(self._get_env("SMTP_PORT", default="587")),
            sender_email=self._get_env("SENDER_EMAIL"),
            sender_password=self._get_env("SENDER_PASSWORD"),
            recipient_emails=self._get_env("RECIPIENT_EMAILS"),
            webhook_enabled=self._get_env("NOTIFICATION_WEBHOOK_ENABLED", default="false").lower() == "true",
            webhook_url=self._get_env("WEBHOOK_URL")
        )

        self.config = SystemConfig(
            github=github_config,
            gitea=gitea_config,
            sync=sync_config,
            proxy=proxy_config,
            log=log_config,
            notification=notification_config
        )

        # Load repositories configuration
        self._load_repositories()

        return self.config

    def _load_repositories(self) -> None:
        """Load repositories from JSON configuration file."""
        if self.repo_config_file.exists():
            try:
                with open(self.repo_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.repositories = {repo["name"]: repo for repo in data.get("repositories", [])}
            except (json.JSONDecodeError, KeyError) as e:
                raise ValueError(f"Invalid repositories configuration: {e}")

    def save_repositories(self, repositories: list) -> None:
        """Save repositories to JSON configuration file.

        Args:
            repositories: List of repository configurations
        """
        self.repo_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.repo_config_file, "w", encoding="utf-8") as f:
            json.dump({
                "description": "GitHub 仓库镜像列表配置",
                "version": "1.2",
                "repositories": repositories
            }, f, indent=2, ensure_ascii=False)
        self.repositories = {repo["name"]: repo for repo in repositories}

    def validate(self) -> bool:
        """Validate current configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
        return True

    def get(self) -> SystemConfig:
        """Get current configuration.

        Returns:
            Current SystemConfig object

        Raises:
            RuntimeError: If configuration not loaded
        """
        if not self.config:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self.config

    def get_repositories(self) -> Dict[str, Any]:
        """Get all configured repositories.

        Returns:
            Dictionary of repositories keyed by name
        """
        return self.repositories.copy()

    def update_config(self, **kwargs) -> SystemConfig:
        """Update configuration values.

        Args:
            **kwargs: Configuration items to update

        Returns:
            Updated SystemConfig object
        """
        if not self.config:
            raise RuntimeError("Configuration not loaded. Call load() first.")

        # Update environment variables
        for key, value in kwargs.items():
            os.environ[key] = str(value)

        # Reload configuration
        return self.load()

    @staticmethod
    def _get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
        """Get environment variable with optional default and validation.

        Args:
            key: Environment variable name
            default: Default value if not found
            required: Whether the variable is required

        Returns:
            Environment variable value

        Raises:
            ValueError: If required variable is not found
        """
        value = os.getenv(key, default)
        if required and not value:
            raise ValueError(
                f"Required configuration not found: {key}\n"
                f"Please set the {key} environment variable or add it to your .env file"
            )
        return value or ""


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(env_file: str = ".env") -> ConfigManager:
    """Get or create global configuration manager.

    Args:
        env_file: Path to .env configuration file

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(env_file=env_file)
    return _config_manager


def load_config(env_file: str = ".env") -> SystemConfig:
    """Load configuration from .env file.

    Args:
        env_file: Path to .env configuration file

    Returns:
        Parsed SystemConfig object
    """
    manager = get_config_manager(env_file)
    return manager.load()
