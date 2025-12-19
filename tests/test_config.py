"""
Tests for configuration system.
"""

import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

from src.config.config import ConfigManager, GitHubConfig, GiteaConfig, load_config


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text("""
# GitHub Configuration
GITHUB_TOKEN=test_token_12345
GITHUB_API_URL=https://api.github.com

# Gitea Configuration
GITEA_URL=https://gitea.example.com
GITEA_TOKEN=test_gitea_token
GITEA_USERNAME=mirror_user
GITEA_PASSWORD=mirror_password

# Sync Configuration
SYNC_INTERVAL=3600
LOCAL_REPO_PATH=./data/repos
SYNC_TIMEOUT=1800
SYNC_RETRY_COUNT=3
SYNC_CONCURRENT=3

# Log Configuration
LOG_LEVEL=INFO
LOG_FILE=./logs/sync.log
LOG_MAX_SIZE=100
LOG_BACKUP_COUNT=10
""")
    return env_file


def test_github_config_validation():
    """Test GitHub configuration validation."""
    config = GitHubConfig(
        token="test_token",
        api_url="https://api.github.com"
    )
    assert config.token == "test_token"
    assert config.api_url == "https://api.github.com"


def test_github_config_empty_token():
    """Test GitHub configuration rejects empty token."""
    with pytest.raises(ValueError):
        GitHubConfig(token="", api_url="https://api.github.com")


def test_gitea_config_validation():
    """Test Gitea configuration validation."""
    config = GiteaConfig(
        url="https://gitea.example.com",
        token="test_token",
        username="test_user"
    )
    assert config.url == "https://gitea.example.com"
    assert config.token == "test_token"
    assert config.username == "test_user"


def test_config_manager_load(temp_env_file):
    """Test config manager loading configuration."""
    manager = ConfigManager(env_file=str(temp_env_file))
    config = manager.load()

    assert config.github.token == "test_token_12345"
    assert config.gitea.url == "https://gitea.example.com"
    assert config.sync.interval == 3600
    assert config.log.level == "INFO"


def test_config_manager_validation(temp_env_file):
    """Test config manager validation."""
    manager = ConfigManager(env_file=str(temp_env_file))
    config = manager.load()

    assert manager.validate() is True


def test_config_manager_get_repositories(temp_env_file, tmp_path):
    """Test getting repositories from config."""
    # Create a test repositories.json
    repo_file = tmp_path / "repositories.json"
    repo_file.write_text("""
{
    "description": "Test repositories",
    "version": "1.0",
    "repositories": [
        {
            "name": "test-repo",
            "owner": "test-owner",
            "url": "https://github.com/test-owner/test-repo",
            "enabled": true
        }
    ]
}
""")

    manager = ConfigManager(
        env_file=str(temp_env_file),
        repo_config_file=str(repo_file)
    )
    manager.load()
    repos = manager.get_repositories()

    assert "test-repo" in repos
    assert repos["test-repo"]["owner"] == "test-owner"


def test_config_manager_save_repositories(temp_env_file, tmp_path):
    """Test saving repositories."""
    repo_file = tmp_path / "repositories.json"

    manager = ConfigManager(
        env_file=str(temp_env_file),
        repo_config_file=str(repo_file)
    )

    repos = [
        {
            "name": "repo1",
            "owner": "owner1",
            "url": "https://github.com/owner1/repo1"
        }
    ]

    manager.save_repositories(repos)
    assert repo_file.exists()

    # Reload and verify
    manager2 = ConfigManager(
        env_file=str(temp_env_file),
        repo_config_file=str(repo_file)
    )
    manager2.load()
    repos_loaded = manager2.get_repositories()

    assert "repo1" in repos_loaded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
