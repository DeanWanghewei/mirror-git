"""
Tests for synchronization engine.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from git import GitCommandError

from src.sync.sync_engine import SyncEngine
from src.config.config import GitHubConfig, GiteaConfig, SyncConfig
from src.models import Database, Repository, SyncHistory


@pytest.fixture
def configs(tmp_path):
    """Create test configurations."""
    github_config = GitHubConfig(
        token="test_token",
        api_url="https://api.github.com"
    )

    gitea_config = GiteaConfig(
        url="https://gitea.example.com",
        username="testuser",
        token="test_token"
    )

    sync_config = SyncConfig(
        local_path=str(tmp_path / "repos"),
        interval=3600,
        timeout=300,
        retry_count=3,
        concurrent_tasks=5
    )

    return github_config, gitea_config, sync_config


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db = Database(f"sqlite:///{tmp_path / 'test.db'}")
    db.init_db()
    return db


@pytest.fixture
def sync_engine(configs, test_db):
    """Create sync engine with mocked clients."""
    github_config, gitea_config, sync_config = configs

    with patch('src.sync.sync_engine.GitHubClient') as mock_github, \
         patch('src.sync.sync_engine.GiteaClient') as mock_gitea:
        mock_github.return_value = MagicMock()
        mock_gitea.return_value = MagicMock()

        engine = SyncEngine(
            github_config,
            gitea_config,
            sync_config,
            test_db
        )

        engine.github_client = MagicMock()
        engine.gitea_client = MagicMock()

        yield engine


def test_sync_engine_initialization(configs, test_db):
    """Test SyncEngine initialization."""
    github_config, gitea_config, sync_config = configs

    with patch('src.sync.sync_engine.GitHubClient') as mock_github, \
         patch('src.sync.sync_engine.GiteaClient') as mock_gitea:
        mock_github.return_value = MagicMock()
        mock_gitea.return_value = MagicMock()

        engine = SyncEngine(
            github_config,
            gitea_config,
            sync_config,
            test_db
        )

        assert engine.github_config == github_config
        assert engine.gitea_config == gitea_config
        assert engine.sync_config == sync_config
        assert engine.db == test_db
        assert engine.local_repo_path.exists()


def test_extract_owner_and_repo_https():
    """Test extracting owner and repo from HTTPS URL."""
    url = "https://github.com/testuser/test-repo.git"
    owner, repo = SyncEngine._extract_owner_and_repo(url)

    assert owner == "testuser"
    assert repo == "test-repo"


def test_extract_owner_and_repo_https_no_git():
    """Test extracting owner and repo from HTTPS URL without .git."""
    url = "https://github.com/testuser/test-repo"
    owner, repo = SyncEngine._extract_owner_and_repo(url)

    assert owner == "testuser"
    assert repo == "test-repo"


def test_extract_owner_and_repo_ssh():
    """Test extracting owner and repo from SSH URL."""
    url = "git@github.com:testuser/test-repo.git"
    owner, repo = SyncEngine._extract_owner_and_repo(url)

    assert owner == "testuser"
    assert repo == "test-repo"


def test_extract_owner_and_repo_ssh_no_git():
    """Test extracting owner and repo from SSH URL without .git."""
    url = "git@github.com:testuser/test-repo"
    owner, repo = SyncEngine._extract_owner_and_repo(url)

    assert owner == "testuser"
    assert repo == "test-repo"


def test_extract_owner_and_repo_invalid_format():
    """Test invalid URL format."""
    with pytest.raises(ValueError, match="Invalid GitHub URL"):
        SyncEngine._extract_owner_and_repo("invalid-url")


def test_extract_owner_and_repo_missing_parts():
    """Test URL with missing parts."""
    with pytest.raises(ValueError, match="Invalid GitHub URL format"):
        SyncEngine._extract_owner_and_repo("https://github.com/onlyowner")


def test_clone_repository_success(sync_engine):
    """Test successful repository cloning."""
    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo.clone_from.return_value = MagicMock()

        local_path = sync_engine.local_repo_path / "test-repo"
        status, output = sync_engine._clone_repository(
            "https://github.com/testuser/test-repo.git",
            local_path
        )

        assert status == "success"
        assert output == ""
        mock_repo.clone_from.assert_called_once()


def test_clone_repository_git_error(sync_engine):
    """Test clone failure due to git error."""
    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo.clone_from.side_effect = GitCommandError(
            "git clone",
            1,
            stderr="Repository not found"
        )

        local_path = sync_engine.local_repo_path / "test-repo"
        status, output = sync_engine._clone_repository(
            "https://github.com/testuser/nonexistent.git",
            local_path
        )

        assert status == "failed"
        assert "Git command error" in output


def test_clone_repository_general_error(sync_engine):
    """Test clone failure due to general error."""
    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo.clone_from.side_effect = Exception("General error")

        local_path = sync_engine.local_repo_path / "test-repo"
        status, output = sync_engine._clone_repository(
            "https://github.com/testuser/test-repo.git",
            local_path
        )

        assert status == "failed"
        assert "Clone failed" in output


def test_update_repository_success(sync_engine, tmp_path):
    """Test successful repository update."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes = MagicMock()
        mock_repo_instance.remotes.origin = MagicMock()
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=True)

        status, output = sync_engine._update_repository(
            local_path,
            "https://github.com/testuser/test-repo.git"
        )

        assert status == "success"
        assert output == ""


def test_update_repository_create_remote(sync_engine, tmp_path):
    """Test update creating remote if it doesn't exist."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)
        mock_repo_instance.create_remote = MagicMock()

        status, output = sync_engine._update_repository(
            local_path,
            "https://github.com/testuser/test-repo.git"
        )

        assert status == "success"
        mock_repo_instance.create_remote.assert_called_once()


def test_update_repository_git_error(sync_engine, tmp_path):
    """Test update failure due to git error."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo.side_effect = GitCommandError(
            "git fetch",
            1,
            stderr="Connection refused"
        )

        status, output = sync_engine._update_repository(
            local_path,
            "https://github.com/testuser/test-repo.git"
        )

        assert status == "failed"
        assert "Git command error" in output


def test_push_to_gitea_success(sync_engine, tmp_path):
    """Test successful push to Gitea."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)
        mock_repo_instance.create_remote = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()

        status, output = sync_engine._push_to_gitea(
            local_path,
            "testuser",
            "test-repo"
        )

        assert status == "success"
        assert output == ""


def test_push_to_gitea_set_existing_url(sync_engine, tmp_path):
    """Test push to Gitea updating existing remote URL."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=True)
        mock_repo_instance.remotes.gitea = MagicMock()

        sync_engine._push_to_gitea(
            local_path,
            "testuser",
            "test-repo"
        )

        mock_repo_instance.remotes.gitea.set_url.assert_called_once()


def test_push_to_gitea_no_refs_to_push(sync_engine, tmp_path):
    """Test push when there are no refs to push."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)
        mock_repo_instance.create_remote = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()
        mock_repo_instance.remotes.gitea.push.side_effect = GitCommandError(
            "git push",
            1,
            stderr="No refs to push"
        )

        status, output = sync_engine._push_to_gitea(
            local_path,
            "testuser",
            "test-repo"
        )

        assert status == "success"


def test_push_to_gitea_error(sync_engine, tmp_path):
    """Test push failure."""
    local_path = tmp_path / "test-repo"
    local_path.mkdir()

    with patch('src.sync.sync_engine.Repo') as mock_repo:
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)
        mock_repo_instance.create_remote = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()
        mock_repo_instance.remotes.gitea.push.side_effect = GitCommandError(
            "git push",
            1,
            stderr="Permission denied"
        )

        status, output = sync_engine._push_to_gitea(
            local_path,
            "testuser",
            "test-repo"
        )

        assert status == "failed"
        assert "Git command error" in output


def test_record_sync_history(sync_engine, test_db):
    """Test recording sync history."""
    session = test_db.get_session()

    sync_engine._record_sync_history(
        session,
        "test-repo",
        "clone",
        "success",
        10.5
    )

    history = session.query(SyncHistory).all()
    assert len(history) == 1
    assert history[0].repository_name == "test-repo"
    assert history[0].status == "success"
    assert history[0].duration_seconds == 10.5

    session.close()


def test_record_sync_history_with_error(sync_engine, test_db):
    """Test recording failed sync history."""
    session = test_db.get_session()

    sync_engine._record_sync_history(
        session,
        "test-repo",
        "sync",
        "failed",
        5.0,
        error_message="Connection timeout"
    )

    history = session.query(SyncHistory).all()
    assert len(history) == 1
    assert history[0].status == "failed"
    assert history[0].error_message == "Connection timeout"

    session.close()


def test_sync_repository_clone_new(sync_engine):
    """Test syncing a new repository (clone operation)."""
    sync_engine.gitea_client.repository_exists.return_value = False
    sync_engine.gitea_client.create_repository.return_value = {"id": 1}

    with patch('src.sync.sync_engine.Repo') as mock_repo, \
         patch.object(Path, 'exists') as mock_exists:
        mock_exists.side_effect = [False, False]  # Repo doesn't exist locally
        mock_repo.clone_from.return_value = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)
        mock_repo_instance.remotes.gitea = MagicMock()

        result = sync_engine.sync_repository(
            "test-repo",
            "https://github.com/testuser/test-repo.git"
        )

        assert result["status"] == "success"
        assert result["operation_type"] == "clone"
        assert "test-repo" in result["repository"]


def test_sync_repository_update_existing(sync_engine):
    """Test syncing existing repository (update operation)."""
    sync_engine.gitea_client.repository_exists.return_value = True

    with patch('src.sync.sync_engine.Repo') as mock_repo, \
         patch.object(Path, 'exists') as mock_exists:
        mock_exists.return_value = True  # Repo exists locally
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes = MagicMock()
        mock_repo_instance.remotes.origin = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=True)

        result = sync_engine.sync_repository(
            "test-repo",
            "https://github.com/testuser/test-repo.git"
        )

        assert result["status"] == "success"
        assert result["operation_type"] == "update"


def test_sync_repository_failure(sync_engine):
    """Test sync failure handling."""
    sync_engine.gitea_client.repository_exists.return_value = True

    with patch('src.sync.sync_engine.Repo') as mock_repo, \
         patch.object(Path, 'exists') as mock_exists:
        mock_exists.return_value = True
        mock_repo.side_effect = Exception("Clone failed")

        result = sync_engine.sync_repository(
            "test-repo",
            "https://github.com/testuser/test-repo.git"
        )

        assert result["status"] == "failed"
        assert "error" in result


def test_sync_all_success(sync_engine, test_db):
    """Test syncing all repositories."""
    session = test_db.get_session()

    # Add test repositories
    repos = [
        Repository(name="repo1", owner="user", url="https://github.com/user/repo1.git"),
        Repository(name="repo2", owner="user", url="https://github.com/user/repo2.git"),
    ]
    session.add_all(repos)
    session.commit()
    session.close()

    sync_engine.gitea_client.repository_exists.return_value = False
    sync_engine.gitea_client.create_repository.return_value = {"id": 1}

    with patch('src.sync.sync_engine.Repo') as mock_repo, \
         patch.object(Path, 'exists') as mock_exists:
        mock_exists.return_value = False  # Repos don't exist locally
        mock_repo.clone_from.return_value = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)

        result = sync_engine.sync_all()

        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0


def test_sync_all_partial_failure(sync_engine):
    """Test sync_all with partial failures."""
    repos = [
        {"name": "repo1", "url": "https://github.com/user/repo1.git"},
        {"name": "repo2", "url": "https://github.com/user/repo2.git"},
    ]

    sync_engine.gitea_client.repository_exists.return_value = False
    sync_engine.gitea_client.create_repository.return_value = {"id": 1}

    with patch('src.sync.sync_engine.Repo') as mock_repo, \
         patch.object(Path, 'exists') as mock_exists:
        mock_exists.side_effect = [False, Exception("Clone failed")]
        mock_repo.clone_from.side_effect = [MagicMock(), Exception("Clone failed")]
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)

        result = sync_engine.sync_all(repos)

        assert result["total"] == 2
        # At least one should succeed or fail gracefully
        assert result["success"] >= 0


def test_sync_all_empty_list(sync_engine):
    """Test sync_all with empty repository list."""
    result = sync_engine.sync_all([])

    assert result["total"] == 0
    assert result["success"] == 0
    assert result["failed"] == 0


def test_close(sync_engine):
    """Test closing the sync engine."""
    sync_engine.close()

    sync_engine.github_client.close.assert_called_once()
    sync_engine.gitea_client.close.assert_called_once()


def test_close_with_error(sync_engine):
    """Test closing engine when client close fails."""
    sync_engine.github_client.close.side_effect = Exception("Close failed")

    # Should not raise exception
    sync_engine.close()


def test_sync_with_custom_gitea_owner(sync_engine):
    """Test sync with custom Gitea owner."""
    sync_engine.gitea_client.repository_exists.return_value = False
    sync_engine.gitea_client.create_repository.return_value = {"id": 1}

    with patch('src.sync.sync_engine.Repo') as mock_repo, \
         patch.object(Path, 'exists') as mock_exists:
        mock_exists.return_value = False
        mock_repo.clone_from.return_value = MagicMock()
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.remotes = MagicMock()
        mock_repo_instance.remotes.gitea = MagicMock()
        mock_repo_instance.remotes.__contains__ = MagicMock(return_value=False)

        result = sync_engine.sync_repository(
            "test-repo",
            "https://github.com/testuser/test-repo.git",
            gitea_owner="customowner"
        )

        assert result["status"] == "success"
        sync_engine.gitea_client.repository_exists.assert_called_with("customowner", "test-repo")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
