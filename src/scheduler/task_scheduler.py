"""
Task scheduler for automated repository synchronization.

Uses APScheduler to manage periodic sync tasks.
"""

import asyncio
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config.config import GitHubConfig, GiteaConfig, SyncConfig, ProxyConfig
from ..logger.logger import get_logger
from ..models import Database
from ..sync.sync_engine import SyncEngine


class TaskScheduler:
    """Task scheduler for automated synchronization."""

    def __init__(
        self,
        github_config: GitHubConfig,
        gitea_config: GiteaConfig,
        sync_config: SyncConfig,
        db: Database,
        log_config=None,
        proxy_config: Optional[ProxyConfig] = None
    ):
        """Initialize task scheduler.

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
        self.logger = get_logger("task_scheduler", log_config)

        self.scheduler = BackgroundScheduler()
        self.sync_engine = SyncEngine(
            github_config, gitea_config, sync_config, db, log_config, proxy_config
        )

        self.is_running = False

    def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return

        try:
            self.scheduler.start()
            self.is_running = True
            self.logger.info("Task scheduler started")
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.shutdown()
            self.is_running = False
            self.logger.info("Task scheduler stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop scheduler: {e}")

    def schedule_sync(
        self,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        job_id: str = "sync_all_repositories"
    ) -> str:
        """Schedule a synchronization task.

        Args:
            interval_seconds: Interval in seconds (if using interval trigger)
            cron_expression: Cron expression (if using cron trigger)
            job_id: Job identifier

        Returns:
            Job ID

        Raises:
            ValueError: If neither interval nor cron is provided
        """
        if interval_seconds is None and cron_expression is None:
            interval_seconds = self.sync_config.interval

        try:
            if cron_expression:
                trigger = CronTrigger.from_crontab(cron_expression)
                self.logger.info(f"Scheduling sync with cron: {cron_expression}")
            else:
                trigger = IntervalTrigger(seconds=interval_seconds)
                self.logger.info(f"Scheduling sync every {interval_seconds} seconds")

            job = self.scheduler.add_job(
                self._sync_task,
                trigger=trigger,
                id=job_id,
                name="Repository Synchronization",
                replace_existing=True
            )

            self.logger.info(f"Sync job scheduled: {job_id}")
            return job.id

        except Exception as e:
            self.logger.error(f"Failed to schedule sync task: {e}")
            raise

    def schedule_repository_sync(
        self,
        repo_name: str,
        github_url: str,
        interval_seconds: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> str:
        """Schedule synchronization for a specific repository.

        Args:
            repo_name: Repository name
            github_url: GitHub repository URL
            interval_seconds: Sync interval
            job_id: Optional job ID

        Returns:
            Job ID
        """
        if job_id is None:
            job_id = f"sync_{repo_name}"

        if interval_seconds is None:
            interval_seconds = self.sync_config.interval

        try:
            trigger = IntervalTrigger(seconds=interval_seconds)

            job = self.scheduler.add_job(
                self._sync_single_task,
                trigger=trigger,
                id=job_id,
                args=(repo_name, github_url),
                name=f"Repository Sync: {repo_name}",
                replace_existing=True
            )

            self.logger.info(
                f"Repository sync scheduled: {repo_name} (every {interval_seconds}s)"
            )
            return job.id

        except Exception as e:
            self.logger.error(f"Failed to schedule repository sync: {e}")
            raise

    def unschedule_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was removed, False otherwise
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.remove_job(job_id)
                self.logger.info(f"Job removed: {job_id}")
                return True
            else:
                self.logger.warning(f"Job not found: {job_id}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove job: {e}")
            return False

    def get_jobs(self) -> list:
        """Get all scheduled jobs.

        Returns:
            List of scheduled jobs
        """
        return self.scheduler.get_jobs()

    def execute_sync_now(self) -> Dict[str, Any]:
        """Execute synchronization immediately.

        Returns:
            Sync results
        """
        self.logger.info("Executing immediate synchronization...")
        return self._sync_task()

    def _sync_task(self) -> Dict[str, Any]:
        """Internal sync task for scheduler.

        Returns:
            Sync results
        """
        try:
            self.logger.info("Starting scheduled repository synchronization")
            result = self.sync_engine.sync_all()
            return result
        except Exception as e:
            self.logger.error(f"Scheduled sync task failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "total": 0,
                "success": 0,
                "failed": 0
            }

    def _sync_single_task(self, repo_name: str, github_url: str) -> Dict[str, Any]:
        """Internal task for syncing a single repository.

        Args:
            repo_name: Repository name
            github_url: GitHub repository URL

        Returns:
            Sync result
        """
        try:
            self.logger.info(f"Starting scheduled sync for: {repo_name}")
            result = self.sync_engine.sync_repository(repo_name, github_url)
            return result
        except Exception as e:
            self.logger.error(f"Scheduled sync for {repo_name} failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "repository": repo_name,
                "error": str(e)
            }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job.

        Args:
            job_id: Job identifier

        Returns:
            Job information or None if not found
        """
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        return None

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job (remove then re-add with same config).

        Args:
            job_id: Job identifier

        Returns:
            True if successful
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.pause_job(job_id)
                self.logger.info(f"Job paused: {job_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to pause job: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: Job identifier

        Returns:
            True if successful
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.resume_job(job_id)
                self.logger.info(f"Job resumed: {job_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to resume job: {e}")
            return False

    def close(self) -> None:
        """Close the scheduler and cleanup."""
        try:
            if self.is_running:
                self.stop()
            self.sync_engine.close()
            self.logger.debug("Task scheduler closed")
        except Exception as e:
            self.logger.error(f"Error closing scheduler: {e}")
