"""
Synchronization control API routes.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/all")
async def sync_all_repositories():
    """Synchronize all repositories."""
    from ..app import get_app_state
    from ...sync.sync_engine import SyncEngine

    state = get_app_state()
    db = state.get("db")
    config = state.get("config")

    if not db or not config:
        raise HTTPException(status_code=503, detail="System not ready")

    try:
        engine = SyncEngine(
            config.github,
            config.gitea,
            config.sync,
            db,
            config.log,
            config.proxy
        )

        result = engine.sync_all()
        engine.close()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_sync_history(skip: int = 0, limit: int = 50):
    """Get synchronization history."""
    from ..app import get_app_state
    from ...models import SyncHistory

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            history = session.query(SyncHistory).order_by(
                SyncHistory.created_at.desc()
            ).offset(skip).limit(limit).all()

            return [h.to_dict() for h in history]
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sync_status():
    """Get current synchronization status."""
    from ..app import get_app_state
    from ...models import Repository

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            repos = session.query(Repository).all()
            total = len(repos)
            synced = sum(1 for r in repos if r.last_sync_status == "success")
            syncing = sum(1 for r in repos if r.last_sync_status == "syncing")
            failed = sum(1 for r in repos if r.last_sync_status == "failed")

            return {
                "total_repositories": total,
                "synced": synced,
                "syncing": syncing,
                "failed": failed,
                "sync_rate": (synced / total * 100) if total > 0 else 0
            }
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
