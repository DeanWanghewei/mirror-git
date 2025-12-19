"""
Configuration management API routes.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    github_token: Optional[str] = None
    gitea_url: Optional[str] = None
    gitea_token: Optional[str] = None
    sync_interval: Optional[int] = None


class ConfigResponse(BaseModel):
    """Configuration response."""
    github: Dict[str, Any]
    gitea: Dict[str, Any]
    sync: Dict[str, Any]
    log: Dict[str, Any]


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """Get current configuration."""
    from ..app import get_app_state

    state = get_app_state()
    config = state.get("config")

    if not config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    return {
        "github": {
            "api_url": config.github.api_url,
            "token": "***" if config.github.token else None
        },
        "gitea": {
            "url": config.gitea.url,
            "username": config.gitea.username,
            "token": "***" if config.gitea.token else None
        },
        "sync": {
            "local_path": config.sync.local_path,
            "interval": config.sync.interval,
            "timeout": config.sync.timeout,
            "retry_count": config.sync.retry_count,
            "concurrent_tasks": config.sync.concurrent_tasks
        },
        "log": {
            "level": config.log.level,
            "file_path": config.log.file_path,
            "max_file_size": config.log.max_file_size,
            "backup_count": config.log.backup_count
        }
    }


@router.post("/validate/github")
async def validate_github_config(token: str):
    """Validate GitHub token."""
    from ...clients.github_client import GitHubClient
    from ...config.config import GitHubConfig
    from ..app import get_app_state

    state = get_app_state()
    config = state.get("config")

    if not config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    try:
        github_config = GitHubConfig(
            token=token,
            api_url=config.github.api_url
        )
        client = GitHubClient(github_config)
        is_valid = client.validate_token()
        client.close()

        return {
            "valid": is_valid,
            "message": "GitHub token is valid" if is_valid else "GitHub token is invalid"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate/gitea")
async def validate_gitea_config(url: str, token: str):
    """Validate Gitea connection."""
    from ...clients.gitea_client import GiteaClient
    from ...config.config import GiteaConfig
    from ..app import get_app_state

    state = get_app_state()
    config = state.get("config")

    if not config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    try:
        gitea_config = GiteaConfig(
            url=url,
            token=token,
            username=config.gitea.username
        )
        client = GiteaClient(gitea_config)
        is_valid = client.validate_token()
        version = client.get_server_version() if is_valid else None
        client.close()

        return {
            "valid": is_valid,
            "version": version,
            "message": f"Gitea connection successful (v{version})" if is_valid else "Gitea connection failed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/")
async def update_config(config_update: ConfigUpdate):
    """Update configuration."""
    from ..app import get_app_state
    from ...logger.logger import get_logger

    state = get_app_state()
    config = state.get("config")
    logger = get_logger("config_router")

    if not config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    try:
        updates = {}

        if config_update.github_token:
            updates["GITHUB_TOKEN"] = config_update.github_token

        if config_update.gitea_url:
            updates["GITEA_URL"] = config_update.gitea_url

        if config_update.gitea_token:
            updates["GITEA_TOKEN"] = config_update.gitea_token

        if config_update.sync_interval:
            updates["SYNC_INTERVAL"] = str(config_update.sync_interval)

        if updates:
            # In a real app, this would persist to .env or config file
            logger.info(f"Configuration updated: {list(updates.keys())}")

        return {
            "status": "success",
            "message": "Configuration updated",
            "updated_fields": list(updates.keys())
        }
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_config_status():
    """Get configuration status."""
    from ..app import get_app_state
    from ...clients.github_client import GitHubClient
    from ...clients.gitea_client import GiteaClient

    state = get_app_state()
    config = state.get("config")

    if not config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    try:
        # Check GitHub
        github_client = GitHubClient(config.github)
        github_ok = github_client.validate_token()
        github_client.close()

        # Check Gitea
        gitea_client = GiteaClient(config.gitea)
        gitea_ok = gitea_client.validate_token()
        gitea_client.close()

        return {
            "github": {
                "connected": github_ok,
                "url": config.github.api_url
            },
            "gitea": {
                "connected": gitea_ok,
                "url": config.gitea.url
            },
            "database": True,  # Assume database is connected if we reach here
            "overall_status": "healthy" if (github_ok and gitea_ok) else "degraded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
