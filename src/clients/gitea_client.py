"""
Gitea API client for interacting with Gitea server.

Provides methods for creating and managing repositories in Gitea.
"""

from typing import Any, Dict, List, Optional

import httpx

from ..config.config import GiteaConfig, ProxyConfig
from ..logger.logger import get_logger


class GiteaClient:
    """Client for interacting with Gitea API."""

    def __init__(self, config: GiteaConfig, log_config=None, proxy_config: Optional[ProxyConfig] = None):
        """Initialize Gitea client.

        Args:
            config: GiteaConfig instance
            log_config: Optional LogConfig for logging
            proxy_config: Optional ProxyConfig for proxy settings
        """
        self.config = config
        self.logger = get_logger("gitea_client", log_config)

        # Ensure base_url doesn't have trailing slash
        base_url = config.url.rstrip("/")

        # Build httpx client with optional proxy
        client_kwargs = {
            "base_url": base_url,
            "headers": {
                "Authorization": f"token {config.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
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
            response = self.session.get("/api/v1/user")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get user information: {e}")
            raise

    def get_repositories(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get user repositories.

        Args:
            page: Page number (1-indexed)
            limit: Number of repositories per page

        Returns:
            Response dictionary with repositories and pagination info

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.session.get(
                "/api/v1/user/repos",
                params={"page": page, "limit": limit}
            )
            response.raise_for_status()
            repos = response.json()
            self.logger.debug(f"Retrieved {len(repos)} repositories from page {page}")
            return repos
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get repositories: {e}")
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
            response = self.session.get(f"/api/v1/repos/{owner}/{repo}")
            return response.status_code == 200
        except Exception as e:
            self.logger.debug(f"Error checking repository existence: {e}")
            return False

    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = False,
        issue_labels: Optional[str] = None,
        org: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new repository.

        Args:
            name: Repository name
            description: Repository description
            private: Whether repository is private
            auto_init: Initialize with README
            issue_labels: Issue labels configuration
            org: Optional organization name to create repo in (defaults to current user)

        Returns:
            Created repository information

        Raises:
            Exception: If API call fails
        """
        payload = {
            "name": name,
            "description": description or "",
            "private": private,
            "auto_init": auto_init,
        }

        if issue_labels:
            payload["issue_labels"] = issue_labels

        # Use organization endpoint if org is specified, otherwise use user endpoint
        if org:
            api_endpoint = f"/api/v1/orgs/{org}/repos"
            location = f"{org}/{name}"
        else:
            api_endpoint = "/api/v1/user/repos"
            location = name

        try:
            response = self.session.post(api_endpoint, json=payload)
            response.raise_for_status()
            repo = response.json()
            self.logger.info(f"Repository created successfully: {location}")
            return repo
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:  # Unprocessable Entity
                self.logger.warning(f"Repository already exists: {location}")
                raise ValueError(f"Repository already exists: {location}")
            elif e.response.status_code == 403:  # Forbidden
                error_msg = (
                    f"Permission denied creating repository {location}. "
                    f"Ensure your Gitea token has these permissions: "
                    f"'repo', 'admin:repo_hook', 'admin:org' (for organizations). "
                    f"See GITEA_TOKEN_PERMISSIONS.md for details."
                )
                self.logger.warning(error_msg)
                raise PermissionError(error_msg)
            elif e.response.status_code == 404:  # Not Found
                error_msg = (
                    f"Organization or repository endpoint not found: {location}. "
                    f"Ensure the organization exists and the URL is correct."
                )
                self.logger.warning(error_msg)
                raise ValueError(error_msg)
            self.logger.error(f"Failed to create repository {location}: {e}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {e}")
            raise

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository information dictionary

        Raises:
            Exception: If repository not found or API call fails
        """
        try:
            response = self.session.get(f"/api/v1/repos/{owner}/{repo}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"Repository not found: {owner}/{repo}")
                raise ValueError(f"Repository not found: {owner}/{repo}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get repository {owner}/{repo}: {e}")
            raise

    def update_repository(
        self,
        owner: str,
        repo: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update repository settings.

        Args:
            owner: Repository owner username
            repo: Repository name
            **kwargs: Fields to update (name, description, private, etc.)

        Returns:
            Updated repository information

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.session.patch(
                f"/api/v1/repos/{owner}/{repo}",
                json=kwargs
            )
            response.raise_for_status()
            self.logger.info(f"Repository updated: {owner}/{repo}")
            return response.json()
        except httpx.RequestError as e:
            self.logger.error(f"Failed to update repository {owner}/{repo}: {e}")
            raise

    def delete_repository(self, owner: str, repo: str) -> bool:
        """Delete a repository.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            True if deletion was successful

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.session.delete(f"/api/v1/repos/{owner}/{repo}")
            response.raise_for_status()
            self.logger.info(f"Repository deleted: {owner}/{repo}")
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"Repository not found: {owner}/{repo}")
                return False
            raise
        except httpx.RequestError as e:
            self.logger.error(f"Failed to delete repository {owner}/{repo}: {e}")
            raise

    def create_webhook(
        self,
        owner: str,
        repo: str,
        url: str,
        events: Optional[List[str]] = None,
        active: bool = True
    ) -> Dict[str, Any]:
        """Create a webhook for a repository.

        Args:
            owner: Repository owner username
            repo: Repository name
            url: Webhook callback URL
            events: List of events to trigger webhook
            active: Whether webhook is active

        Returns:
            Created webhook information

        Raises:
            Exception: If API call fails
        """
        if events is None:
            events = ["push", "pull_request"]

        payload = {
            "type": "gitea",
            "config": {
                "url": url,
                "http_method": "POST",
                "content_type": "json",
                "secret": ""
            },
            "events": events,
            "active": active
        }

        try:
            response = self.session.post(
                f"/api/v1/repos/{owner}/{repo}/hooks",
                json=payload
            )
            response.raise_for_status()
            webhook = response.json()
            self.logger.info(f"Webhook created for {owner}/{repo}")
            return webhook
        except httpx.RequestError as e:
            self.logger.error(f"Failed to create webhook: {e}")
            raise

    def push_to_repository(
        self,
        owner: str,
        repo: str,
        force: bool = False
    ) -> bool:
        """Simulate a push to a repository (for API purposes).

        Note: This is a placeholder as actual Git operations happen via Git command.

        Args:
            owner: Repository owner username
            repo: Repository name
            force: Force push flag (not actually used in API)

        Returns:
            True if push information is valid
        """
        try:
            repo_info = self.get_repository(owner, repo)
            clone_url = repo_info.get("clone_url")
            if not clone_url:
                raise ValueError("Clone URL not available")
            self.logger.info(f"Repository {owner}/{repo} is ready for push")
            return True
        except Exception as e:
            self.logger.error(f"Failed to verify repository for push: {e}")
            return False

    def validate_token(self) -> bool:
        """Validate Gitea token by attempting to get user info.

        Returns:
            True if token is valid, False otherwise
        """
        try:
            self.get_user()
            self.logger.info("Gitea token validated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Gitea token validation failed: {e}")
            return False

    def get_server_version(self) -> str:
        """Get Gitea server version.

        Returns:
            Version string

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.session.get("/api/v1/version")
            response.raise_for_status()
            data = response.json()
            version = data.get("version", "unknown")
            self.logger.debug(f"Gitea server version: {version}")
            return version
        except httpx.RequestError as e:
            self.logger.error(f"Failed to get server version: {e}")
            raise

    def close(self) -> None:
        """Close the HTTP session."""
        try:
            self.session.close()
            self.logger.debug("Gitea client session closed")
        except Exception as e:
            self.logger.error(f"Error closing Gitea client: {e}")


async def validate_gitea_token(config: GiteaConfig) -> bool:
    """Async helper to validate Gitea token.

    Args:
        config: GiteaConfig instance

    Returns:
        True if token is valid
    """
    client = GiteaClient(config)
    try:
        return client.validate_token()
    finally:
        client.close()
