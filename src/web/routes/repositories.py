"""
Repository management API routes.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class RepositoryCreate(BaseModel):
    """Create repository request."""
    name: str
    owner: str
    url: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: bool = True
    gitea_owner: Optional[str] = None  # Optional Gitea organization or custom namespace


class RepositoryUpdate(BaseModel):
    """Update repository request."""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None
    sync_interval: Optional[int] = None
    gitea_owner: Optional[str] = None  # Optional Gitea organization or custom namespace


class RepositoryResponse(BaseModel):
    """Repository response."""
    id: int
    name: str
    owner: str
    url: str
    description: Optional[str]
    enabled: bool
    size_mb: float
    last_sync_time: Optional[str]
    last_sync_status: str
    gitea_owner: Optional[str]


@router.get("/", response_model=List[RepositoryResponse])
async def list_repositories(skip: int = 0, limit: int = 100):
    """List all repositories."""
    from ..app import get_app_state
    from ...models import Repository

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            repos = session.query(Repository).offset(skip).limit(limit).all()
            return [r.to_dict() for r in repos]
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: int):
    """Get repository details."""
    from ..app import get_app_state
    from ...models import Repository

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            repo = session.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                raise HTTPException(status_code=404, detail="Repository not found")
            return repo.to_dict()
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate):
    """Create a new repository."""
    from ..app import get_app_state
    from ...models import Repository
    from ...sync.sync_engine import SyncEngine

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            # Check if repository already exists
            existing = session.query(Repository).filter(
                Repository.name == repo.name
            ).first()

            if existing:
                raise HTTPException(status_code=409, detail="Repository already exists")

            # Normalize the GitHub URL to ensure it ends with .git
            normalized_url = SyncEngine._normalize_github_url(repo.url)

            # Create new repository
            db_repo = Repository(
                name=repo.name,
                owner=repo.owner,
                url=normalized_url,
                description=repo.description,
                tags=",".join(repo.tags) if repo.tags else None,
                enabled=repo.enabled,
                gitea_owner=repo.gitea_owner
            )
            session.add(db_repo)
            session.commit()
            session.refresh(db_repo)

            return db_repo.to_dict()
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(repo_id: int, repo_update: RepositoryUpdate):
    """Update repository settings."""
    from ..app import get_app_state
    from ...models import Repository

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            repo = session.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                raise HTTPException(status_code=404, detail="Repository not found")

            # Update fields
            if repo_update.description is not None:
                repo.description = repo_update.description

            if repo_update.tags is not None:
                repo.tags = ",".join(repo_update.tags)

            if repo_update.enabled is not None:
                repo.enabled = repo_update.enabled

            if repo_update.sync_interval is not None:
                repo.sync_interval = repo_update.sync_interval

            if repo_update.gitea_owner is not None:
                repo.gitea_owner = repo_update.gitea_owner

            session.commit()
            session.refresh(repo)

            return repo.to_dict()
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: int,
    delete_local: bool = False,
    delete_gitea: bool = False,
    delete_history: bool = True
):
    """
    Delete a repository.

    Args:
        repo_id: Repository ID
        delete_local: Whether to delete local clone directory (default: False)
        delete_gitea: Whether to delete repository from Gitea (default: False)
        delete_history: Whether to delete sync history records (default: True)

    Returns:
        Status message with details of what was deleted
    """
    import shutil
    from pathlib import Path
    from ..app import get_app_state
    from ...models import Repository, SyncHistory
    from ...clients.gitea_client import GiteaClient

    state = get_app_state()
    db = state.get("db")
    config = state.get("config")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    deleted_items = []
    errors = []

    try:
        session = db.get_session()
        try:
            # Find repository
            repo = session.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                raise HTTPException(status_code=404, detail="Repository not found")

            repo_name = repo.name
            repo_url = repo.url
            local_path = repo.local_path
            gitea_owner = repo.gitea_owner

            # Delete local files if requested
            if delete_local and local_path:
                try:
                    local_dir = Path(local_path)
                    if local_dir.exists():
                        shutil.rmtree(local_dir)
                        deleted_items.append(f"local files at {local_path}")
                    else:
                        deleted_items.append(f"local path (already removed): {local_path}")
                except Exception as e:
                    errors.append(f"Failed to delete local files: {str(e)}")

            # Delete from Gitea if requested
            if delete_gitea and config:
                try:
                    gitea_client = GiteaClient(
                        config.gitea,
                        config.log,
                        config.proxy
                    )

                    # Determine the owner (organization or user)
                    owner = gitea_owner if gitea_owner else config.gitea.owner

                    # Try to delete the repository
                    if gitea_client.delete_repository(owner, repo_name):
                        deleted_items.append(f"Gitea repository: {owner}/{repo_name}")
                    else:
                        errors.append(f"Failed to delete Gitea repository {owner}/{repo_name} (may not exist)")

                    gitea_client.close()
                except Exception as e:
                    errors.append(f"Failed to delete from Gitea: {str(e)}")

            # Delete sync history if requested
            if delete_history:
                try:
                    history_count = session.query(SyncHistory).filter(
                        SyncHistory.repository_id == repo_id
                    ).delete()
                    if history_count > 0:
                        deleted_items.append(f"{history_count} sync history record(s)")
                except Exception as e:
                    errors.append(f"Failed to delete sync history: {str(e)}")

            # Delete repository from database
            session.delete(repo)
            session.commit()
            deleted_items.append(f"database record for repository '{repo_name}'")

            return {
                "status": "success",
                "message": f"Repository '{repo_name}' deleted",
                "deleted": deleted_items,
                "errors": errors if errors else None
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{repo_id}/sync")
async def sync_repository(repo_id: int, background_tasks: BackgroundTasks):
    """Synchronize a specific repository asynchronously in the background."""
    from ..app import get_app_state
    from ...models import Repository
    from ...sync.sync_engine import SyncEngine

    state = get_app_state()
    db = state.get("db")
    config = state.get("config")

    if not db or not config:
        raise HTTPException(status_code=503, detail="System not ready")

    try:
        session = db.get_session()
        try:
            repo = session.query(Repository).filter(Repository.id == repo_id).first()
            if not repo:
                raise HTTPException(status_code=404, detail="Repository not found")

            repo_name = repo.name
            repo_url = repo.url
            gitea_owner = repo.gitea_owner

            # Update status to syncing immediately
            repo.last_sync_status = "syncing"
            session.commit()

            # Define background task function
            def run_sync():
                """Background task to sync repository."""
                try:
                    engine = SyncEngine(
                        config.github,
                        config.gitea,
                        config.sync,
                        db,
                        config.log,
                        config.proxy
                    )

                    # If gitea_owner is set in database, treat it as organization
                    # Otherwise, repo will be pushed to user namespace
                    engine.sync_repository(
                        repo_name,
                        repo_url,
                        gitea_owner=config.gitea.username if gitea_owner else None,
                        gitea_org=gitea_owner  # Pass gitea_owner as organization parameter
                    )
                    engine.close()
                except Exception as e:
                    # Log error but don't crash
                    import logging
                    logging.error(f"Background sync failed for {repo_name}: {e}")

            # Add task to background
            background_tasks.add_task(run_sync)

            return {
                "status": "started",
                "repository": repo_name,
                "message": f"同步任务已启动，正在后台执行"
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/history")
async def get_repository_history(repo_id: int, limit: int = 10):
    """Get sync history for a repository."""
    from ..app import get_app_state
    from ...models import SyncHistory

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            history = session.query(SyncHistory).filter(
                SyncHistory.repository_id == repo_id
            ).order_by(SyncHistory.created_at.desc()).limit(limit).all()

            return [h.to_dict() for h in history]
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
