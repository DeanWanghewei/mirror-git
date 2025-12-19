"""
Monitoring and logging API routes.
"""

from typing import List

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """Get monitoring dashboard data."""
    from ..app import get_app_state
    from ...models import Repository, SyncHistory

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            # Repository statistics
            repos = session.query(Repository).all()
            total_repos = len(repos)
            enabled_repos = sum(1 for r in repos if r.enabled)
            total_size = sum(r.size_mb for r in repos if r.size_mb is not None)

            # Sync statistics
            history = session.query(SyncHistory).order_by(
                SyncHistory.created_at.desc()
            ).limit(100).all()

            success_count = sum(1 for h in history if h.status == "success")
            failed_count = sum(1 for h in history if h.status == "failed")

            return {
                "repositories": {
                    "total": total_repos,
                    "enabled": enabled_repos,
                    "total_size_mb": total_size
                },
                "sync": {
                    "total_operations": len(history),
                    "success": success_count,
                    "failed": failed_count,
                    "success_rate": (success_count / len(history) * 100) if history else 0
                }
            }
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_logs(skip: int = 0, limit: int = 100, level: str = "ALL"):
    """Get application logs."""
    from ..app import get_app_state
    from ...models import SyncLog

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            query = session.query(SyncLog)

            if level != "ALL":
                query = query.filter(SyncLog.level == level.upper())

            logs = query.order_by(
                SyncLog.created_at.desc()
            ).offset(skip).limit(limit).all()

            return [l.to_dict() for l in logs]
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs/export")
async def export_logs(format: str = "json"):
    """Export logs to file."""
    from datetime import datetime
    from ..app import get_app_state
    from ...models import SyncLog
    import json

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            logs = session.query(SyncLog).order_by(SyncLog.created_at.desc()).all()

            if format == "json":
                data = [l.to_dict() for l in logs]
                return {
                    "format": "json",
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_records": len(logs),
                    "data": data
                }
            elif format == "csv":
                # Simple CSV format
                lines = ["timestamp,level,message"]
                for log in logs:
                    lines.append(f"{log.timestamp},{log.level},{log.message}")
                return {
                    "format": "csv",
                    "content": "\\n".join(lines)
                }
            else:
                raise ValueError("Unsupported format")
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics():
    """Get system statistics."""
    from ..app import get_app_state
    from ...models import Repository, SyncHistory

    state = get_app_state()
    db = state.get("db")

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session = db.get_session()
        try:
            # Get all time statistics
            total_syncs = session.query(SyncHistory).count()
            successful_syncs = session.query(SyncHistory).filter(
                SyncHistory.status == "success"
            ).count()

            repos = session.query(Repository).all()
            avg_repo_size = sum(r.size_mb for r in repos) / len(repos) if repos else 0

            return {
                "total_syncs": total_syncs,
                "successful_syncs": successful_syncs,
                "failed_syncs": total_syncs - successful_syncs,
                "success_rate": (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0,
                "total_repositories": len(repos),
                "average_repository_size_mb": avg_repo_size
            }
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
