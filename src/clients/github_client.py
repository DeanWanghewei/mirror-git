"""
GitHub API client for interacting with GitHub repositories.

Provides methods for fetching repository information and managing mirrors.
"""

from typing import Any, Dict, List, Optional

import httpx

from ..config.config import GitHubConfig, ProxyConfig
from ..logger.logger import get_logger


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, config: GitHubConfig, log_config=None, proxy_config: Optional[ProxyConfig] = None):
        """Initialize GitHub client.

        Args:
            config: GitHubConfig instance
            log_config: Optional LogConfig for logging
            proxy_config: Optional ProxyConfig for proxy settings
        """
        self.config = config
        self.logger = get_logger("github_client", log_config)

        # Build httpx client with optional proxy
        client_kwargs = {
            "base_url": config.api_url,
            "headers": {
                "Authorization": f"token {config.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Mirror-Git/1.0"
            },
            "timeout": 30.0
        }

        if proxy_config and proxy_config.enabled and proxy_config.url:
            # Format proxy URL with authentication if provided
            proxy_url = proxy_config.url
            if proxy_config.username and proxy_config.password:
                proxy_url = proxy_url.replace(
                    "://",
                    f"://{proxy_config.username}:{proxy_config.password}@"
                )
            client_kwargs["proxy"] = proxy_url
            self.logger.debug(f"Using proxy: {proxy_config.url}")

        self.session = httpx.Client(**client_kwargs)

    def __del__(self):
        """Close session on cleanup."""
        try:
            self.session.close()
        except Exception:
            pass

    def get_user(self) -> Dict[str, Any]:
        """Get authenticated user information.

        Returns:
            User information dictionary

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.session.get("/user")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get user information: {e}")
            raise

    def get_user_repositories(self, per_page: int = 30, page: int = 1) -> List[Dict[str, Any]]:
        """Get all repositories for authenticated user.

        Args:
            per_page: Number of repositories per page (max 100)
            page: Page number (1-indexed)

        Returns:
            List of repository dictionaries

        Raises:
            Exception: If API call fails
        """
        per_page = min(per_page, 100)  # GitHub max is 100

        try:
            response = self.session.get(
                "/user/repos",
                params={"per_page": per_page, "page": page, "type": "all"}
            )
            response.raise_for_status()
            repos = response.json()

            # Parse GitHub pagination link header if needed
            link_header = response.headers.get("link", "")
            has_next = "rel=\"next\"" in link_header

            self.logger.debug(
                f"Retrieved {len(repos)} repositories from page {page} "
                f"(has_next: {has_next})"
            )
            return repos
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get user repositories: {e}")
            raise

    def get_all_user_repositories(self) -> List[Dict[str, Any]]:
        """Get all repositories for authenticated user (paginated).

        Returns:
            List of all repository dictionaries

        Raises:
            Exception: If API call fails
        """
        all_repos = []
        page = 1

        while True:
            repos = self.get_user_repositories(per_page=100, page=page)
            if not repos:
                break

            all_repos.extend(repos)
            page += 1

            self.logger.debug(f"Retrieved {len(all_repos)} total repositories so far...")

        self.logger.info(f"Successfully retrieved {len(all_repos)} total repositories")
        return all_repos

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository information dictionary

        Raises:
            Exception: If API call fails or repository not found
        """
        try:
            response = self.session.get(f"/repos/{owner}/{repo}")
            response.raise_for_status()
            repo_data = response.json()
            self.logger.debug(f"Retrieved repository {owner}/{repo}")
            return repo_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"Repository not found: {owner}/{repo}")
                raise ValueError(f"Repository not found: {owner}/{repo}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get repository {owner}/{repo}: {e}")
            raise

    def repository_exists(self, owner: str, repo: str) -> bool:
        """Check if repository exists.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            True if repository exists, False otherwise
        """
        try:
            self.get_repository(owner, repo)
            return True
        except ValueError:
            return False
        except Exception as e:
            self.logger.error(f"Error checking if repository exists: {e}")
            return False

    def get_repository_clone_url(self, owner: str, repo: str, protocol: str = "https") -> str:
        """Get clone URL for a repository.

        Args:
            owner: Repository owner username
            repo: Repository name
            protocol: Clone protocol ('https' or 'ssh')

        Returns:
            Clone URL string

        Raises:
            ValueError: If protocol is invalid
        """
        if protocol not in ("https", "ssh"):
            raise ValueError(f"Invalid protocol: {protocol}")

        try:
            repo_data = self.get_repository(owner, repo)

            if protocol == "https":
                clone_url = repo_data.get("clone_url")
            else:  # ssh
                clone_url = repo_data.get("ssh_url")

            if not clone_url:
                raise ValueError(f"Clone URL not available for {owner}/{repo}")

            return clone_url
        except Exception as e:
            self.logger.error(f"Failed to get clone URL for {owner}/{repo}: {e}")
            raise

    def validate_token(self) -> bool:
        """Validate GitHub token by attempting to get user info.

        Returns:
            True if token is valid, False otherwise
        """
        try:
            self.get_user()
            self.logger.info("GitHub token validated successfully")
            return True
        except Exception as e:
            self.logger.error(f"GitHub token validation failed: {e}")
            return False

    def search_repositories(self, query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        """Search for repositories on GitHub.

        Args:
            query: Search query string
            per_page: Results per page (max 100)

        Returns:
            List of repository dictionaries

        Raises:
            Exception: If search fails
        """
        per_page = min(per_page, 100)

        try:
            response = self.session.get(
                "/search/repositories",
                params={"q": query, "per_page": per_page, "sort": "stars"}
            )
            response.raise_for_status()
            data = response.json()
            repos = data.get("items", [])
            self.logger.debug(f"Found {len(repos)} repositories matching query: {query}")
            return repos
        except httpx.RequestError as e:
            self.logger.error(f"Repository search failed: {e}")
            raise

    def get_repository_size(self, owner: str, repo: str) -> int:
        """Get repository size in kilobytes.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository size in kilobytes

        Raises:
            Exception: If API call fails
        """
        try:
            repo_data = self.get_repository(owner, repo)
            size_kb = repo_data.get("size", 0)
            self.logger.debug(f"Repository {owner}/{repo} size: {size_kb} KB")
            return size_kb
        except Exception as e:
            self.logger.error(f"Failed to get repository size: {e}")
            raise

    def close(self) -> None:
        """Close the HTTP session."""
        try:
            self.session.close()
            self.logger.debug("GitHub client session closed")
        except Exception as e:
            self.logger.error(f"Error closing GitHub client: {e}")


async def validate_github_token(config: GitHubConfig) -> bool:
    """Async helper to validate GitHub token.

    Args:
        config: GitHubConfig instance

    Returns:
        True if token is valid
    """
    client = GitHubClient(config)
    try:
        return client.validate_token()
    finally:
        client.close()
