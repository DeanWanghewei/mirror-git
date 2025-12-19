"""
Tests for GitHub API client.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import httpx

from src.config.config import GitHubConfig
from src.clients.github_client import GitHubClient, validate_github_token


@pytest.fixture
def github_config():
    """Create a test GitHub configuration."""
    return GitHubConfig(
        token="test_token_123",
        api_url="https://api.github.com"
    )


@pytest.fixture
def github_client(github_config):
    """Create a test GitHub client."""
    with patch('httpx.Client') as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        client = GitHubClient(github_config)
        client.session = mock_client_instance
        yield client


def test_github_client_initialization(github_config):
    """Test GitHubClient initialization."""
    with patch('httpx.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        client = GitHubClient(github_config)

        assert client.config == github_config
        assert client.session is not None

        # Verify client was created with correct parameters
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        assert call_kwargs['base_url'] == "https://api.github.com"
        assert 'Authorization' in call_kwargs['headers']
        assert 'token test_token_123' in call_kwargs['headers']['Authorization']
        assert call_kwargs['timeout'] == 30.0


def test_get_user(github_client):
    """Test getting user information."""
    user_data = {
        "login": "testuser",
        "id": 12345,
        "name": "Test User"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = user_data
    github_client.session.get.return_value = mock_response

    result = github_client.get_user()

    assert result == user_data
    github_client.session.get.assert_called_once_with("/user")


def test_get_user_request_error(github_client):
    """Test handling of request errors in get_user."""
    github_client.session.get.side_effect = httpx.RequestError("Connection failed")

    with pytest.raises(httpx.RequestError):
        github_client.get_user()


def test_get_user_repositories(github_client):
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
    mock_response.headers.get.return_value = ""  # No next page
    github_client.session.get.return_value = mock_response

    result = github_client.get_user_repositories(per_page=30, page=1)

    assert len(result) == 2
    assert result[0]["name"] == "repo1"
    assert result[1]["name"] == "repo2"

    # Verify correct parameters
    github_client.session.get.assert_called_once()
    call_args = github_client.session.get.call_args
    assert call_args[0][0] == "/user/repos"
    assert call_args[1]['params']['per_page'] == 30
    assert call_args[1]['params']['page'] == 1


def test_get_user_repositories_per_page_limit(github_client):
    """Test per_page parameter is limited to 100."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.headers.get.return_value = ""
    github_client.session.get.return_value = mock_response

    github_client.get_user_repositories(per_page=200)

    call_args = github_client.session.get.call_args
    assert call_args[1]['params']['per_page'] == 100


def test_get_all_user_repositories(github_client):
    """Test getting all user repositories with pagination."""
    page1_data = [{"id": i, "name": f"repo{i}"} for i in range(1, 101)]
    page2_data = [{"id": i, "name": f"repo{i}"} for i in range(101, 121)]

    mock_response = MagicMock()
    mock_response.headers.get.return_value = ""
    mock_response.json.side_effect = [page1_data, page2_data, []]

    github_client.session.get.return_value = mock_response

    result = github_client.get_all_user_repositories()

    assert len(result) == 120
    assert result[0]["name"] == "repo1"
    assert result[100]["name"] == "repo101"


def test_get_repository(github_client):
    """Test getting repository information."""
    repo_data = {
        "id": 1,
        "name": "test-repo",
        "owner": {"login": "testuser"},
        "url": "https://github.com/testuser/test-repo"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    github_client.session.get.return_value = mock_response

    result = github_client.get_repository("testuser", "test-repo")

    assert result == repo_data
    github_client.session.get.assert_called_once_with("/repos/testuser/test-repo")


def test_get_repository_not_found(github_client):
    """Test handling of 404 errors when getting repository."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    github_client.session.get.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=mock_response
    )

    with pytest.raises(ValueError, match="Repository not found"):
        github_client.get_repository("testuser", "nonexistent")


def test_repository_exists_true(github_client):
    """Test checking if repository exists (positive case)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "name": "test-repo"}
    github_client.session.get.return_value = mock_response

    result = github_client.repository_exists("testuser", "test-repo")

    assert result is True


def test_repository_exists_false(github_client):
    """Test checking if repository exists (negative case)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    github_client.session.get.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=mock_response
    )

    result = github_client.repository_exists("testuser", "nonexistent")

    assert result is False


def test_get_repository_clone_url_https(github_client):
    """Test getting clone URL with HTTPS protocol."""
    repo_data = {
        "clone_url": "https://github.com/testuser/test-repo.git",
        "ssh_url": "git@github.com:testuser/test-repo.git"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    github_client.session.get.return_value = mock_response

    result = github_client.get_repository_clone_url("testuser", "test-repo", protocol="https")

    assert result == "https://github.com/testuser/test-repo.git"


def test_get_repository_clone_url_ssh(github_client):
    """Test getting clone URL with SSH protocol."""
    repo_data = {
        "clone_url": "https://github.com/testuser/test-repo.git",
        "ssh_url": "git@github.com:testuser/test-repo.git"
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    github_client.session.get.return_value = mock_response

    result = github_client.get_repository_clone_url("testuser", "test-repo", protocol="ssh")

    assert result == "git@github.com:testuser/test-repo.git"


def test_get_repository_clone_url_invalid_protocol(github_client):
    """Test invalid protocol raises ValueError."""
    with pytest.raises(ValueError, match="Invalid protocol"):
        github_client.get_repository_clone_url("testuser", "test-repo", protocol="ftp")


def test_validate_token_valid(github_client):
    """Test token validation with valid token."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"login": "testuser"}
    github_client.session.get.return_value = mock_response

    result = github_client.validate_token()

    assert result is True


def test_validate_token_invalid(github_client):
    """Test token validation with invalid token."""
    github_client.session.get.side_effect = httpx.RequestError("Unauthorized")

    result = github_client.validate_token()

    assert result is False


def test_search_repositories(github_client):
    """Test searching for repositories."""
    search_results = {
        "items": [
            {"id": 1, "name": "result1", "stars": 100},
            {"id": 2, "name": "result2", "stars": 50}
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = search_results
    github_client.session.get.return_value = mock_response

    result = github_client.search_repositories("python", per_page=10)

    assert len(result) == 2
    assert result[0]["name"] == "result1"

    # Verify search parameters
    call_args = github_client.session.get.call_args
    assert call_args[0][0] == "/search/repositories"
    assert call_args[1]['params']['q'] == "python"
    assert call_args[1]['params']['sort'] == "stars"


def test_search_repositories_per_page_limit(github_client):
    """Test per_page parameter is limited to 100."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    github_client.session.get.return_value = mock_response

    github_client.search_repositories("python", per_page=200)

    call_args = github_client.session.get.call_args
    assert call_args[1]['params']['per_page'] == 100


def test_search_repositories_empty_results(github_client):
    """Test search with no results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    github_client.session.get.return_value = mock_response

    result = github_client.search_repositories("nonexistentlanguage")

    assert result == []


def test_get_repository_size(github_client):
    """Test getting repository size."""
    repo_data = {
        "id": 1,
        "name": "test-repo",
        "size": 1024  # in KB
    }

    mock_response = MagicMock()
    mock_response.json.return_value = repo_data
    github_client.session.get.return_value = mock_response

    result = github_client.get_repository_size("testuser", "test-repo")

    assert result == 1024


def test_get_repository_size_zero(github_client):
    """Test getting size of empty repository."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"size": 0}
    github_client.session.get.return_value = mock_response

    result = github_client.get_repository_size("testuser", "empty-repo")

    assert result == 0


def test_close(github_client):
    """Test closing the client."""
    github_client.close()

    github_client.session.close.assert_called_once()


def test_close_with_error(github_client):
    """Test closing client when session close fails."""
    github_client.session.close.side_effect = Exception("Close failed")

    # Should not raise exception
    github_client.close()


def test_context_manager_cleanup():
    """Test that client properly cleans up on deletion."""
    with patch('httpx.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        config = GitHubConfig(token="test_token", api_url="https://api.github.com")
        client = GitHubClient(config)

        # Delete should close session
        del client


def test_multiple_api_calls(github_client):
    """Test multiple API calls in sequence."""
    user_response = MagicMock()
    user_response.json.return_value = {"login": "testuser"}

    repos_response = MagicMock()
    repos_response.json.return_value = [{"name": "repo1"}]
    repos_response.headers.get.return_value = ""

    github_client.session.get.side_effect = [user_response, repos_response]

    user = github_client.get_user()
    repos = github_client.get_user_repositories()

    assert user["login"] == "testuser"
    assert len(repos) == 1


def test_pagination_logic(github_client):
    """Test pagination through multiple pages."""
    # Simulate 3 pages of results
    page_responses = []
    for page_num in range(3):
        repos = [{"id": i, "name": f"repo{i}"} for i in range(page_num * 50, (page_num + 1) * 50)]
        mock_response = MagicMock()
        mock_response.json.return_value = repos
        mock_response.headers.get.return_value = 'rel="next"' if page_num < 2 else ""
        page_responses.append(mock_response)

    github_client.session.get.side_effect = page_responses

    # Only 2 calls should actually happen (third call returns empty list)
    mock_response_empty = MagicMock()
    mock_response_empty.json.return_value = []
    mock_response_empty.headers.get.return_value = ""
    github_client.session.get.side_effect = [page_responses[0], page_responses[1], mock_response_empty]

    result = github_client.get_all_user_repositories()

    assert len(result) == 100  # 50 + 50


def test_github_config_attributes(github_config):
    """Test GitHub config has required attributes."""
    assert hasattr(github_config, 'token')
    assert hasattr(github_config, 'api_url')
    assert github_config.token == "test_token_123"
    assert github_config.api_url == "https://api.github.com"


def test_validate_github_token_async():
    """Test async token validation helper."""
    import asyncio

    with patch('src.clients.github_client.GitHubClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.validate_token.return_value = True
        mock_client_class.return_value = mock_client

        config = GitHubConfig(token="test_token", api_url="https://api.github.com")

        # Run async version for testing
        from src.clients.github_client import validate_github_token
        result = asyncio.run(validate_github_token(config))

        assert result is True
        mock_client.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
