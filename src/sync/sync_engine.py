"""
Synchronization engine for mirroring GitHub repositories to Gitea.

Handles cloning, pulling, and pushing repository updates.
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from git import Repo, GitCommandError
from sqlalchemy.orm import Session

from ..clients.github_client import GitHubClient
from ..clients.gitea_client import GiteaClient
from ..config.config import GitHubConfig, GiteaConfig, SyncConfig, ProxyConfig
from ..logger.logger import get_logger
from ..models import Database, Repository, SyncHistory


class SyncEngine:
    """Engine for synchronizing GitHub repositories to Gitea."""

    def __init__(
        self,
        github_config: GitHubConfig,
        gitea_config: GiteaConfig,
        sync_config: SyncConfig,
        db: Database,
        log_config=None,
        proxy_config: Optional[ProxyConfig] = None
    ):
        """Initialize sync engine.

        Args:
            github_config: GitHub API configuration
            gitea_config: Gitea server configuration
            sync_config: Synchronization configuration
            db: Database instance
            log_config: Optional logging configuration
            proxy_config: Optional proxy configuration
        """
        self.github_config = github_config
        self.gitea_config = gitea_config
        self.sync_config = sync_config
        self.db = db
        self.proxy_config = proxy_config
        self.logger = get_logger("sync_engine", log_config)

        self.github_client = GitHubClient(github_config, log_config, proxy_config)
        self.gitea_client = GiteaClient(gitea_config, log_config, proxy_config)

        # Create local repo path
        self.local_repo_path = Path(sync_config.local_path)
        self.local_repo_path.mkdir(parents=True, exist_ok=True)

    def _get_git_env(self) -> Dict[str, str]:
        """Build Git environment variables with proxy configuration.

        Returns:
            Dictionary of environment variables for Git operations
        """
        git_env = {
            'GIT_HTTP_LOW_SPEED_LIMIT': '1000',  # 1KB/s minimum
            'GIT_HTTP_LOW_SPEED_TIME': '60',     # for 60 seconds
            # Increase HTTP POST buffer to handle large repos (500MB)
            'GIT_HTTP_POST_BUFFER': str(500 * 1024 * 1024),
        }

        # Add proxy configuration if enabled
        if self.proxy_config and self.proxy_config.enabled and self.proxy_config.url:
            git_env['http_proxy'] = self.proxy_config.url
            git_env['https_proxy'] = self.proxy_config.url
            git_env['HTTP_PROXY'] = self.proxy_config.url
            git_env['HTTPS_PROXY'] = self.proxy_config.url

        return git_env

    def sync_repository(
        self,
        repo_name: str,
        github_url: str,
        gitea_owner: str = None,
        gitea_org: str = None
    ) -> Dict[str, Any]:
        """Synchronize a single repository.

        Args:
            repo_name: Repository name
            github_url: GitHub repository URL
            gitea_owner: Gitea owner username (defaults to gitea username)
            gitea_org: Optional Gitea organization to create repo in

        Returns:
            Sync result dictionary with status and details

        Raises:
            Exception: If sync fails
        """
        if gitea_owner is None:
            gitea_owner = self.gitea_config.username

        session = self.db.get_session()
        start_time = datetime.utcnow()

        try:
            self.logger.info(f"Starting sync for repository: {repo_name}")

            # Normalize GitHub URL to ensure it ends with .git
            github_url = self._normalize_github_url(github_url)
            self.logger.debug(f"Normalized GitHub URL: {github_url}")

            # Get or extract repository owner and name from GitHub URL
            github_owner, github_repo_name = self._extract_owner_and_repo(github_url)

            # Check if repository exists in Gitea, create if not
            repo_exists = False
            if gitea_org:
                repo_exists = self.gitea_client.repository_exists(gitea_org, repo_name)
            else:
                repo_exists = self.gitea_client.repository_exists(gitea_owner, repo_name)

            if not repo_exists:
                self.logger.info(
                    f"Repository does not exist in Gitea, creating: {gitea_org or gitea_owner}/{repo_name}"
                )
                try:
                    self.gitea_client.create_repository(
                        name=repo_name,
                        description=f"Mirror of {github_url}",
                        private=False,
                        org=gitea_org
                    )
                except PermissionError as e:
                    # If org creation fails due to permissions, try user namespace
                    if gitea_org:
                        self.logger.warning(
                            f"Failed to create in organization {gitea_org}, trying user namespace: {e}"
                        )
                        try:
                            self.gitea_client.create_repository(
                                name=repo_name,
                                description=f"Mirror of {github_url}",
                                private=False,
                                org=None
                            )
                            self.logger.info(
                                f"Repository created in user namespace (fallback from org {gitea_org})"
                            )
                        except PermissionError as fallback_error:
                            error_msg = (
                                f"Failed to create repository in both organization '{gitea_org}' "
                                f"and user namespace. Token permissions issue: {fallback_error}. "
                                f"See GITEA_TOKEN_PERMISSIONS.md for required permissions."
                            )
                            self.logger.error(error_msg)
                            raise Exception(error_msg)
                    else:
                        raise

            # Get local repository path
            local_path = self.local_repo_path / repo_name

            # Clone or update repository
            if local_path.exists():
                self.logger.debug(f"Repository exists locally, updating: {repo_name}")
                status, log_output = self._update_repository(local_path, github_url)
                operation_type = "update"
            else:
                self.logger.debug(f"Cloning repository: {repo_name}")
                status, log_output = self._clone_repository(github_url, local_path)
                operation_type = "clone"

            if status != "success":
                raise Exception(f"Failed to {operation_type} repository: {log_output}")

            # Push to Gitea
            # Determine where repo was created
            push_owner = gitea_org if gitea_org else gitea_owner
            self.logger.debug(f"Pushing to Gitea: {push_owner}/{repo_name}")
            push_status, push_log = self._push_to_gitea(
                local_path,
                push_owner,
                repo_name
            )

            if push_status != "success":
                raise Exception(f"Failed to push to Gitea: {push_log}")

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = {
                "status": "success",
                "repository": repo_name,
                "operation_type": operation_type,
                "duration_seconds": duration,
                "message": f"Successfully synchronized {repo_name}"
            }

            # Record sync history
            self._record_sync_history(
                session, repo_name, operation_type, "success", duration
            )

            self.logger.info(f"Successfully synchronized repository: {repo_name}")
            return result

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            error_message = str(e)
            self.logger.error(f"Failed to synchronize repository {repo_name}: {error_message}")

            # Record failed sync
            self._record_sync_history(
                session, repo_name, "sync", "failed", duration, error_message
            )

            return {
                "status": "failed",
                "repository": repo_name,
                "error": error_message,
                "duration_seconds": duration
            }

        finally:
            session.close()

    def _clone_repository(
        self,
        github_url: str,
        local_path: Path,
        max_retries: int = 3
    ) -> Tuple[str, str]:
        """Clone repository from GitHub with retry mechanism.

        Args:
            github_url: GitHub repository URL
            local_path: Local path to clone to
            max_retries: Maximum number of retry attempts for transient errors

        Returns:
            Tuple of (status, log_output)
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Cloning from {github_url} to {local_path} (attempt {attempt + 1}/{max_retries})")

                # Configure git for better HTTP/2 handling and proxy support
                repo = Repo.clone_from(
                    github_url,
                    local_path,
                    mirror=False,
                    depth=None,
                    env=self._get_git_env()
                )

                self.logger.debug(f"Successfully cloned repository to {local_path}")
                return "success", ""

            except GitCommandError as e:
                error_msg = str(e)
                last_error = error_msg

                # Check if it's a transient error (HTTP/2 framing layer, timeout, etc)
                if any(x in error_msg for x in [
                    "HTTP2 framing layer",
                    "Connection timed out",
                    "Temporary failure",
                    "Network is unreachable",
                    "No address associated",
                    "Connection reset by peer",
                    "timeout"
                ]):
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s
                        self.logger.warning(
                            f"Transient network error, retrying in {wait_time}s: {error_msg}"
                        )
                        time.sleep(wait_time)
                        continue

                # For non-transient errors, fail immediately
                full_error = f"Git command error: {error_msg}"
                self.logger.error(full_error)
                return "failed", full_error

            except Exception as e:
                error_msg = str(e)
                last_error = error_msg

                # Check for transient network errors
                if any(x in error_msg for x in [
                    "timeout",
                    "temporary",
                    "reset",
                    "connection",
                    "network"
                ]):
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        self.logger.warning(
                            f"Network error, retrying in {wait_time}s: {error_msg}"
                        )
                        time.sleep(wait_time)
                        continue

                full_error = f"Clone failed: {error_msg}"
                self.logger.error(full_error)
                return "failed", full_error

        # All retries exhausted
        full_error = f"Failed to clone after {max_retries} attempts. Last error: {last_error}"
        self.logger.error(full_error)
        return "failed", full_error

    def _update_repository(
        self,
        local_path: Path,
        github_url: str,
        max_retries: int = 3
    ) -> Tuple[str, str]:
        """Update existing repository with retry mechanism.

        Args:
            local_path: Local repository path
            github_url: GitHub repository URL
            max_retries: Maximum number of retry attempts

        Returns:
            Tuple of (status, log_output)
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Updating repository at {local_path} (attempt {attempt + 1}/{max_retries})")

                repo = Repo(local_path)

                # Ensure remote is set correctly
                if "origin" not in repo.remotes:
                    repo.create_remote("origin", github_url)
                else:
                    repo.remotes.origin.set_url(github_url)

                # Detach HEAD to allow fetching into all branches (including the current branch)
                # This is necessary because Git refuses to fetch into a branch that's currently checked out
                try:
                    repo.git.checkout("--detach", "HEAD")
                    self.logger.debug("Detached HEAD for safe branch updates")
                except GitCommandError:
                    # If detach fails, log but continue - fetch might still work
                    self.logger.debug("Could not detach HEAD, attempting fetch anyway")

                # Fetch all branches and tags from GitHub with Git environment config
                try:
                    repo.remotes.origin.fetch(
                        "+refs/heads/*:refs/heads/*",
                        env=self._get_git_env()
                    )
                    repo.remotes.origin.fetch(
                        "refs/tags/*:refs/tags/*",
                        env=self._get_git_env()
                    )
                except GitCommandError as fetch_error:
                    # Retry fetch on transient errors and recoverable errors
                    error_str = str(fetch_error)
                    if any(x in error_str for x in [
                        "HTTP2 framing layer",
                        "Connection timed out",
                        "timeout",
                        "reset",
                        "Temporary",
                        "refusing to fetch",  # Branch checkout conflict
                        "remote unpack failed"  # Network/remote issues
                    ]) and attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        self.logger.warning(
                            f"Transient fetch error, retrying in {wait_time}s: {fetch_error}"
                        )
                        time.sleep(wait_time)
                        continue
                    raise

                self.logger.debug(f"Successfully updated repository at {local_path}")
                return "success", ""

            except GitCommandError as e:
                error_msg = str(e)
                last_error = error_msg

                # Check if it's a transient or recoverable error
                if any(x in error_msg for x in [
                    "HTTP2 framing layer",
                    "Connection timed out",
                    "timeout",
                    "reset",
                    "Temporary failure",
                    "Network",
                    "refusing to fetch",
                    "remote unpack failed"
                ]) and attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    self.logger.warning(
                        f"Transient network error, retrying in {wait_time}s: {error_msg}"
                    )
                    time.sleep(wait_time)
                    continue

                full_error = f"Git command error: {error_msg}"
                self.logger.error(full_error)
                return "failed", full_error

            except Exception as e:
                error_msg = str(e)
                last_error = error_msg

                if any(x in error_msg for x in [
                    "timeout",
                    "connection",
                    "reset",
                    "temporary"
                ]) and attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    self.logger.warning(
                        f"Network error, retrying in {wait_time}s: {error_msg}"
                    )
                    time.sleep(wait_time)
                    continue

                full_error = f"Update failed: {error_msg}"
                self.logger.error(full_error)
                return "failed", full_error

        # All retries exhausted
        full_error = f"Failed to update after {max_retries} attempts. Last error: {last_error}"
        self.logger.error(full_error)
        return "failed", full_error

    def _push_to_gitea(
        self,
        local_path: Path,
        gitea_owner: str,
        repo_name: str
    ) -> Tuple[str, str]:
        """Push repository to Gitea.

        Args:
            local_path: Local repository path
            gitea_owner: Gitea owner username
            repo_name: Repository name in Gitea

        Returns:
            Tuple of (status, log_output)
        """
        try:
            self.logger.debug(f"Pushing to Gitea: {gitea_owner}/{repo_name}")

            repo = Repo(local_path)

            # Configure git for large repo pushes
            try:
                # Set larger HTTP POST buffer (500MB) to handle large repositories
                repo.git.config("http.postBuffer", str(500 * 1024 * 1024))
                # Set compression level to balance speed and size
                repo.git.config("core.compression", "1")
                # Allow pushing refs/tags
                repo.git.config("push.followTags", "true")
                self.logger.debug("Git configuration updated for large repo handling")
            except GitCommandError as config_error:
                self.logger.warning(f"Failed to configure git: {config_error}")
                # Continue anyway, environment variables will still help

            # Construct Gitea push URL
            gitea_url = (
                f"{self.gitea_config.url.rstrip('/')}"
                f"/{gitea_owner}/{repo_name}.git"
            )

            # Ensure gitea remote exists
            if "gitea" not in repo.remotes:
                repo.create_remote("gitea", gitea_url)
            else:
                repo.remotes.gitea.set_url(gitea_url)

            # Push all branches and tags to Gitea
            try:
                self.logger.debug(f"Starting push of all branches and tags to {gitea_owner}/{repo_name}")
                repo.remotes.gitea.push(
                    "+refs/heads/*:refs/heads/*",
                    tags=True,
                    force=True,
                    env=self._get_git_env()
                )
                self.logger.debug(f"Successfully pushed to Gitea: {gitea_owner}/{repo_name}")
            except GitCommandError as push_error:
                error_str = str(push_error)

                # Check for HTTP 413 (Entity Too Large) error
                if "413" in error_str or "Entity Too Large" in error_str:
                    self.logger.warning(
                        f"HTTP 413 error during mirror push. Attempting fallback strategy "
                        f"(pushing branches individually)..."
                    )

                    # Fallback: Push branches individually
                    try:
                        # Get all branches
                        branches = [ref.remote_head for ref in repo.remotes.origin.refs]
                        self.logger.info(f"Pushing {len(branches)} branches individually")

                        for branch in branches:
                            try:
                                self.logger.debug(f"Pushing branch {branch}")
                                repo.remotes.gitea.push(
                                    branch,
                                    force=True,
                                    env=self._get_git_env()
                                )
                            except GitCommandError as branch_error:
                                # Log but continue with other branches
                                self.logger.warning(f"Failed to push branch {branch}: {branch_error}")

                        # Push tags separately
                        try:
                            self.logger.debug("Pushing tags")
                            repo.remotes.gitea.push(
                                tags=True,
                                env=self._get_git_env()
                            )
                        except GitCommandError as tag_error:
                            self.logger.warning(f"Failed to push tags: {tag_error}")

                        self.logger.info(f"Successfully pushed {gitea_owner}/{repo_name} using individual branch push")
                        return "success", ""
                    except Exception as fallback_error:
                        raise GitCommandError(
                            f"Failed to push using individual branch strategy: {fallback_error}",
                            error_str
                        )

                # For other errors, check if it's a "No refs to push" situation
                if "No refs to push" in error_str:
                    self.logger.debug("No refs to push (repository is empty)")
                    return "success", ""

                # Re-raise for other errors
                raise

            return "success", ""

        except GitCommandError as e:
            error_msg = f"Git command error during push: {e}"
            self.logger.error(error_msg)
            return "failed", error_msg
        except Exception as e:
            error_msg = f"Push failed: {e}"
            self.logger.error(error_msg)
            return "failed", error_msg

    def sync_all(self, repositories: list = None) -> Dict[str, Any]:
        """Synchronize all repositories.

        Args:
            repositories: Optional list of repositories to sync

        Returns:
            Summary of sync results
        """
        if repositories is None:
            # Get repositories from database
            session = self.db.get_session()
            try:
                repositories = session.query(Repository).filter(
                    Repository.enabled == True
                ).all()
                repositories = [r.to_dict() for r in repositories]
            finally:
                session.close()

        self.logger.info(f"Starting sync of {len(repositories)} repositories")

        results = {
            "total": len(repositories),
            "success": 0,
            "failed": 0,
            "repositories": []
        }

        for repo in repositories:
            try:
                result = self.sync_repository(
                    repo["name"],
                    repo["url"]
                )
                results["repositories"].append(result)

                if result["status"] == "success":
                    results["success"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                self.logger.error(f"Error syncing {repo.get('name')}: {e}")
                results["failed"] += 1
                results["repositories"].append({
                    "status": "failed",
                    "repository": repo.get("name"),
                    "error": str(e)
                })

        self.logger.info(
            f"Sync complete: {results['success']} success, {results['failed']} failed"
        )
        return results

    def _record_sync_history(
        self,
        session: Session,
        repo_name: str,
        operation_type: str,
        status: str,
        duration_seconds: float,
        error_message: str = None
    ) -> None:
        """Record sync operation in database.

        Args:
            session: Database session
            repo_name: Repository name
            operation_type: Operation type (clone, update, push)
            status: Operation status (success, failed)
            duration_seconds: Operation duration
            error_message: Error message if failed
        """
        try:
            history = SyncHistory(
                repository_id=0,  # Will be updated if repo exists
                repository_name=repo_name,
                operation_type=operation_type,
                status=status,
                error_message=error_message,
                start_time=datetime.utcnow(),
                duration_seconds=duration_seconds
            )
            session.add(history)
            session.commit()
        except Exception as e:
            self.logger.error(f"Failed to record sync history: {e}")

    @staticmethod
    def _normalize_github_url(github_url: str) -> str:
        """Normalize GitHub URL to ensure it ends with .git.

        Args:
            github_url: GitHub repository URL (with or without .git suffix)

        Returns:
            Normalized URL with .git suffix
        """
        # Remove trailing whitespace
        github_url = github_url.strip()

        # Ensure URL ends with .git for consistency with Git operations
        if not github_url.endswith(".git"):
            # SSH format: git@github.com:owner/repo
            if github_url.startswith("git@github.com:"):
                github_url = github_url + ".git"
            # HTTPS format: https://github.com/owner/repo or https://github.com/owner/repo/
            elif "github.com/" in github_url:
                # Remove trailing slash if present
                github_url = github_url.rstrip("/")
                github_url = github_url + ".git"

        return github_url

    @staticmethod
    def _extract_owner_and_repo(github_url: str) -> Tuple[str, str]:
        """Extract owner and repo name from GitHub URL.

        Args:
            github_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            ValueError: If URL format is invalid
        """
        # Handle both https and ssh URLs
        if github_url.endswith(".git"):
            github_url = github_url[:-4]

        if github_url.startswith("git@github.com:"):
            # SSH format: git@github.com:owner/repo
            path = github_url.split(":")[-1]
        elif "github.com/" in github_url:
            # HTTPS format: https://github.com/owner/repo
            path = github_url.split("github.com/")[-1]
        else:
            raise ValueError(f"Invalid GitHub URL: {github_url}")

        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL format: {github_url}")

        return parts[0], parts[1]

    def close(self) -> None:
        """Close client connections."""
        try:
            self.github_client.close()
            self.gitea_client.close()
            self.logger.debug("Sync engine closed")
        except Exception as e:
            self.logger.error(f"Error closing sync engine: {e}")
