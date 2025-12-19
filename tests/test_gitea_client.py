"""
Tests for Gitea API client.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import httpx

from src.config.config import GiteaConfig
from src.clients.gitea_client import GiteaClient, validate_gitea_token


@pytest.fixture
def gitea_config():
    """Create a test Gitea configuration."""
    return GiteaConfig(
        url="https://gitea.example.com",
        username="testuser",
        token="test_token_456"
    )


@pytest.fixture
def gitea_client(gitea_config):
    """Create a test Gitea client."""
    with patch('httpx.Client') as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        client = GiteaClient(gitea_config)
        client.session = mock_client_instance
        yield client


def test_gitea_client_initialization(gitea_config):
    """Test GiteaClient initialization."""
    with patch('httpx.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        client = GiteaClient(gitea_config)

        assert client.config == gitea_config
        assert client.session is not None

        # Verify client was created with correct parameters
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs['base_url'] == "https://gitea.example.com"
        assert 'Authorization' in call_kwargs['headers']
        assert 'token test_token_456' in call_kwargs['headers']['Authorization']
        assert call_kwargs['timeout'] == 30.0


def test_gitea_client_url_trailing_slash():
    """Test that trailing slash is removed from Gitea URL."""
    config = GiteaConfig(
        url="https://gitea.example.com/",
        username="testuser",
        token="test_token"
    )

    with patch('httpx.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        client = GiteaClient(config)

        # URL should not have trailing slash
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs['base_url'] == "https://gitea.example.com"


def test_get_user(gitea_client):
    """Test getting user information."""
    user_data = {
        "login": "testuser",
        "id": 123,
        "full_name": "Test User"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = user_data
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.get_user()

    assert result == user_data
    gitea_client.session.get.assert_called_once_with("/api/v1/user")


def test_get_user_request_error(gitea_client):
    """Test handling of request errors in get_user."""
    gitea_client.session.get.side_effect = httpx.RequestError("Connection failed")

    with pytest.raises(httpx.RequestError):
        gitea_client.get_user()


def test_get_repositories(gitea_client):
    """Test getting user repositories."""
    repos_data = [
        {
            "id": 1,
            "name": "repo1",
            "owner": {"login": "testuser"}
        },
        {
            "id": 2,
            "name": "repo2",
            "owner": {"login": "testuser"}
        }
    ]

    mock_response = MagicMock()
    mock_response.json.return_value = repos_data
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.get_repositories(page=1, limit=50)

    assert len(result) == 2
    assert result[0]["name"] == "repo1"

    # Verify correct parameters
    call_args = gitea_client.session.get.call_args
    assert call_args[0][0] == "/api/v1/user/repos"
    assert call_args[1]['params']['page'] == 1
    assert call_args[1]['params']['limit'] == 50


def test_repository_exists_true(gitea_client):
    """Test checking if repository exists (positive case)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "name": "test-repo"}
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.repository_exists("testuser", "test-repo")

    assert result is True


def test_repository_exists_false(gitea_client):
    """Test checking if repository exists (negative case)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.repository_exists("testuser", "nonexistent")

    assert result is False


def test_repository_exists_error(gitea_client):
    """Test handling of errors when checking repository existence."""
    gitea_client.session.get.side_effect = Exception("Connection error")

    result = gitea_client.repository_exists("testuser", "test-repo")

    assert result is False


def test_create_repository(gitea_client):
    """Test creating a new repository."""
    repo_data = {
        "id": 1,
        "name": "new-repo",
        "description": "A new test repository"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    gitea_client.session.post.return_value = mock_response

    result = gitea_client.create_repository(
        name="new-repo",
        description="A new test repository",
        private=False,
        auto_init=False
    )

    assert result == repo_data

    # Verify correct parameters
    call_args = gitea_client.session.post.call_args
    assert call_args[0][0] == "/api/v1/user/repos"
    assert call_args[1]['json']['name'] == "new-repo"
    assert call_args[1]['json']['description'] == "A new test repository"


def test_create_repository_already_exists(gitea_client):
    """Test creating repository that already exists."""
    mock_response = MagicMock()
    mock_response.status_code = 422
    gitea_client.session.post.side_effect = httpx.HTTPStatusError(
        "Unprocessable Entity",
        request=MagicMock(),
        response=mock_response
    )

    with pytest.raises(ValueError, match="Repository already exists"):
        gitea_client.create_repository(name="existing-repo")


def test_get_repository(gitea_client):
    """Test getting repository information."""
    repo_data = {
        "id": 1,
        "name": "test-repo",
        "owner": {"login": "testuser"},
        "clone_url": "https://gitea.example.com/testuser/test-repo.git"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.get_repository("testuser", "test-repo")

    assert result == repo_data
    gitea_client.session.get.assert_called_once_with("/api/v1/repos/testuser/test-repo")


def test_get_repository_not_found(gitea_client):
    """Test getting non-existent repository."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    gitea_client.session.get.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=mock_response
    )

    with pytest.raises(ValueError, match="Repository not found"):
        gitea_client.get_repository("testuser", "nonexistent")


def test_update_repository(gitea_client):
    """Test updating repository settings."""
    updated_repo = {
        "id": 1,
        "name": "test-repo",
        "description": "Updated description"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = updated_repo
    gitea_client.session.patch.return_value = mock_response

    result = gitea_client.update_repository(
        "testuser",
        "test-repo",
        description="Updated description"
    )

    assert result == updated_repo

    # Verify correct parameters
    call_args = gitea_client.session.patch.call_args
    assert call_args[0][0] == "/api/v1/repos/testuser/test-repo"
    assert call_args[1]['json']['description'] == "Updated description"


def test_update_repository_multiple_fields(gitea_client):
    """Test updating multiple repository fields."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    gitea_client.session.patch.return_value = mock_response

    gitea_client.update_repository(
        "testuser",
        "test-repo",
        description="New description",
        private=True,
        name="new-name"
    )

    call_args = gitea_client.session.patch.call_args
    assert call_args[1]['json']['description'] == "New description"
    assert call_args[1]['json']['private'] is True
    assert call_args[1]['json']['name'] == "new-name"


def test_delete_repository(gitea_client):
    """Test deleting a repository."""
    mock_response = MagicMock()
    gitea_client.session.delete.return_value = mock_response

    result = gitea_client.delete_repository("testuser", "test-repo")

    assert result is True
    gitea_client.session.delete.assert_called_once_with("/api/v1/repos/testuser/test-repo")


def test_delete_repository_not_found(gitea_client):
    """Test deleting non-existent repository."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    gitea_client.session.delete.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=mock_response
    )

    result = gitea_client.delete_repository("testuser", "nonexistent")

    assert result is False


def test_create_webhook(gitea_client):
    """Test creating a webhook."""
    webhook_data = {
        "id": 1,
        "url": "https://example.com/webhook"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = webhook_data
    gitea_client.session.post.return_value = mock_response

    result = gitea_client.create_webhook(
        "testuser",
        "test-repo",
        url="https://example.com/webhook"
    )

    assert result == webhook_data

    # Verify correct parameters
    call_args = gitea_client.session.post.call_args
    assert call_args[0][0] == "/api/v1/repos/testuser/test-repo/hooks"
    assert call_args[1]['json']['config']['url'] == "https://example.com/webhook"
    assert call_args[1]['json']['events'] == ["push", "pull_request"]


def test_create_webhook_custom_events(gitea_client):
    """Test creating webhook with custom events."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1}
    gitea_client.session.post.return_value = mock_response

    gitea_client.create_webhook(
        "testuser",
        "test-repo",
        url="https://example.com/webhook",
        events=["push", "release"]
    )

    call_args = gitea_client.session.post.call_args
    assert call_args[1]['json']['events'] == ["push", "release"]


def test_push_to_repository(gitea_client):
    """Test simulating push to repository."""
    repo_data = {
        "id": 1,
        "name": "test-repo",
        "clone_url": "https://gitea.example.com/testuser/test-repo.git"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.push_to_repository("testuser", "test-repo")

    assert result is True


def test_push_to_repository_no_clone_url(gitea_client):
    """Test push to repository with no clone URL."""
    repo_data = {
        "id": 1,
        "name": "test-repo"
        # No clone_url field
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.push_to_repository("testuser", "test-repo")

    assert result is False


def test_validate_token_valid(gitea_client):
    """Test token validation with valid token."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"login": "testuser"}
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.validate_token()

    assert result is True


def test_validate_token_invalid(gitea_client):
    """Test token validation with invalid token."""
    gitea_client.session.get.side_effect = httpx.RequestError("Unauthorized")

    result = gitea_client.validate_token()

    assert result is False


def test_get_server_version(gitea_client):
    """Test getting Gitea server version."""
    version_data = {
        "version": "1.19.0"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = version_data
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.get_server_version()

    assert result == "1.19.0"
    gitea_client.session.get.assert_called_once_with("/api/v1/version")


def test_get_server_version_unknown(gitea_client):
    """Test getting server version when field is missing."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    gitea_client.session.get.return_value = mock_response

    result = gitea_client.get_server_version()

    assert result == "unknown"


def test_get_server_version_error(gitea_client):
    """Test handling error when getting server version."""
    gitea_client.session.get.side_effect = httpx.RequestError("Connection failed")

    with pytest.raises(httpx.RequestError):
        gitea_client.get_server_version()


def test_close(gitea_client):
    """Test closing the client."""
    gitea_client.close()

    gitea_client.session.close.assert_called_once()


def test_close_with_error(gitea_client):
    """Test closing client when session close fails."""
    gitea_client.session.close.side_effect = Exception("Close failed")

    # Should not raise exception
    gitea_client.close()


def test_multiple_api_calls(gitea_client):
    """Test multiple API calls in sequence."""
    user_response = MagicMock()
    user_response.json.return_value = {"login": "testuser"}

    repos_response = MagicMock()
    repos_response.json.return_value = [{"name": "repo1"}]

    gitea_client.session.get.side_effect = [user_response, repos_response]

    user = gitea_client.get_user()
    repos = gitea_client.get_repositories()

    assert user["login"] == "testuser"
    assert len(repos) == 1


def test_repository_crud_operations(gitea_client):
    """Test complete CRUD operations."""
    # Create
    create_response = MagicMock()
    create_response.json.return_value = {"id": 1, "name": "test-repo"}
    gitea_client.session.post.return_value = create_response

    result = gitea_client.create_repository(name="test-repo")
    assert result["name"] == "test-repo"

    # Get
    get_response = MagicMock()
    get_response.json.return_value = {"id": 1, "name": "test-repo"}
    gitea_client.session.get.return_value = get_response

    result = gitea_client.get_repository("testuser", "test-repo")
    assert result["name"] == "test-repo"

    # Update
    update_response = MagicMock()
    update_response.json.return_value = {"id": 1, "name": "test-repo", "private": True}
    gitea_client.session.patch.return_value = update_response

    result = gitea_client.update_repository("testuser", "test-repo", private=True)
    assert result["private"] is True

    # Delete
    gitea_client.session.delete.return_value = MagicMock()
    result = gitea_client.delete_repository("testuser", "test-repo")
    assert result is True


def test_gitea_config_attributes(gitea_config):
    """Test Gitea config has required attributes."""
    assert hasattr(gitea_config, 'url')
    assert hasattr(gitea_config, 'token')
    assert hasattr(gitea_config, 'username')
    assert gitea_config.url == "https://gitea.example.com"
    assert gitea_config.username == "testuser"
    assert gitea_config.token == "test_token_456"


def test_validate_gitea_token_async():
    """Test async token validation helper."""
    import asyncio

    with patch('src.clients.gitea_client.GiteaClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.validate_token.return_value = True
        mock_client_class.return_value = mock_client

        config = GiteaConfig(
            url="https://gitea.example.com",
            username="testuser",
            token="test_token"
        )

        # Run async version for testing
        from src.clients.gitea_client import validate_gitea_token
        result = asyncio.run(validate_gitea_token(config))

        assert result is True
        mock_client.close.assert_called_once()


def test_webhook_payload_structure(gitea_client):
    """Test webhook payload has correct structure."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1}
    gitea_client.session.post.return_value = mock_response

    gitea_client.create_webhook(
        "testuser",
        "test-repo",
        url="https://example.com/webhook",
        active=False
    )

    call_args = gitea_client.session.post.call_args
    payload = call_args[1]['json']

    assert payload['type'] == 'gitea'
    assert payload['active'] is False
    assert payload['config']['url'] == "https://example.com/webhook"
    assert payload['config']['http_method'] == "POST"
    assert payload['config']['content_type'] == "json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
