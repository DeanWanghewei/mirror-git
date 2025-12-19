"""
Repository management API routes.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
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
async def delete_repository(repo_id: int):
    """Delete a repository."""
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

            session.delete(repo)
            session.commit()

            return {"status": "success", "message": "Repository deleted"}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{repo_id}/sync")
async def sync_repository(repo_id: int):
    """Synchronize a specific repository."""
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

            # Create sync engine and sync repository
            engine = SyncEngine(
                config.github,
                config.gitea,
                config.sync,
                db,
                config.log,
                config.proxy
            )

            result = engine.sync_repository(
                repo.name,
                repo.url,
                gitea_owner=None,  # Use default from config
                gitea_org=repo.gitea_owner  # Use stored organization/namespace if specified
            )
            engine.close()

            return result
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
