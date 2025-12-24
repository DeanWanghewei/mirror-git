"""
Task scheduling API routes.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TaskSchedule(BaseModel):
    """Task schedule request."""
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None


@router.get("/")
async def list_tasks():
    """List all scheduled tasks."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        jobs = scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/schedule")
async def schedule_sync(schedule: TaskSchedule):
    """Schedule automatic synchronization."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        job_id = scheduler.schedule_sync(
            interval_seconds=schedule.interval_seconds,
            cron_expression=schedule.cron_expression
        )
        return {
            "status": "scheduled",
            "job_id": job_id,
            "message": "Synchronization scheduled successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/now")
async def execute_sync_now():
    """Execute synchronization immediately."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        result = scheduler.execute_sync_now()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_task_status(job_id: str):
    """Get task status."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        status = scheduler.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler():
    """Start the scheduler."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        scheduler.start()
        return {
            "status": "started",
            "message": "Scheduler started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """Stop the scheduler."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        scheduler.stop()
        return {
            "status": "stopped",
            "message": "Scheduler stopped successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/pause")
async def pause_task(job_id: str):
    """Pause a scheduled task."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        success = scheduler.pause_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "status": "paused",
            "job_id": job_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/resume")
async def resume_task(job_id: str):
    """Resume a paused task."""
    from ..app import get_app_state

    state = get_app_state()
    scheduler = state.get("scheduler")

    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        success = scheduler.resume_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "status": "resumed",
            "job_id": job_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
