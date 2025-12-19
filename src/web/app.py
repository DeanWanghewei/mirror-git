"""
FastAPI application for GitHub Mirror Sync Web UI.

Main entry point for the web application.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..config.config import load_config
from ..logger.logger import init_default_logger
from ..models import init_database

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
WEB_ROOT = PROJECT_ROOT / "src" / "web"
STATIC_DIR = WEB_ROOT / "static"
TEMPLATES_DIR = WEB_ROOT / "templates"

# Create FastAPI app
app = FastAPI(
    title="GitHub Mirror Sync",
    description="Web UI for GitHub to Gitea repository synchronization",
    version="1.0.0"
)

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
if TEMPLATES_DIR.exists():
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
else:
    templates = None

# Global state
_config = None
_db = None
_scheduler = None


def get_app_state():
    """Get application state."""
    return {
        "config": _config,
        "db": _db,
        "scheduler": _scheduler
    }


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global _config, _db, _scheduler

    try:
        # Load configuration
        env_file = os.getenv("CONFIG_FILE", ".env")
        _config = load_config(env_file)
        print(f"✓ Configuration loaded from {env_file}")

        # Initialize logging
        init_default_logger(_config.log)
        print(f"✓ Logging initialized (level: {_config.log.level})")

        # Create log directory if needed
        log_dir = Path(_config.log.file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db_url = os.getenv("DATABASE_URL", "sqlite:///mirror_sync.db")
        # Ensure SQLite URL has proper format
        if db_url.startswith("./") or db_url.startswith("/"):
            db_path = db_url.lstrip("./")
            db_url = f"sqlite:///{db_path}"
            # Create directory for SQLite database if it doesn't exist
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        elif not db_url.startswith("sqlite://") and not db_url.startswith("postgresql") and not db_url.startswith("mysql"):
            db_path = db_url
            db_url = f"sqlite:///{db_url}"
            # Create directory for SQLite database if it doesn't exist
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        _db = init_database(db_url)
        print(f"✓ Database initialized: {db_url}")

        # Create local repository storage directory
        local_repo_dir = Path(_config.sync.local_path)
        local_repo_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Local repository storage: {_config.sync.local_path}")

        # Initialize scheduler (but don't start it yet)
        from ..scheduler.task_scheduler import TaskScheduler
        _scheduler = TaskScheduler(
            _config.github,
            _config.gitea,
            _config.sync,
            _db,
            _config.log,
            _config.proxy
        )
        print("✓ Task scheduler initialized")

        # Validate configurations
        if _config.github:
            print(f"✓ GitHub API: {_config.github.api_url}")
        if _config.gitea:
            print(f"✓ Gitea Server: {_config.gitea.url}")

        print("\n🚀 GitHub Mirror Sync Web UI Started")
        print(f"   Access at: http://localhost:8000")
        print(f"   API Docs: http://localhost:8000/docs")
        print(f"   ReDoc: http://localhost:8000/redoc")

    except Exception as e:
        print(f"✗ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _scheduler

    try:
        if _scheduler:
            _scheduler.close()
            print("✓ Scheduler closed")
    except Exception as e:
        print(f"✗ Shutdown error: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main page."""
    if templates:
        return templates.TemplateResponse("index.html", {"request": {}})
    return """
    <html>
        <head>
            <title>GitHub Mirror Sync</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                h1 { color: #333; }
                .info {
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>🚀 GitHub Mirror Sync - Web UI</h1>
            <div class="info">
                <p>Welcome to GitHub Mirror Sync!</p>
                <p>API Documentation: <a href="/docs">Swagger UI</a></p>
                <p>Alternative Docs: <a href="/redoc">ReDoc</a></p>
                <p>Status: <strong>Running</strong> ✓</p>
            </div>
        </body>
    </html>
    """


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "GitHub Mirror Sync",
        "version": "1.0.0"
    }


@app.get("/api/config/status")
async def config_status():
    """Get configuration status."""
    state = get_app_state()
    config = state["config"]

    if not config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    return {
        "github_configured": bool(config.github),
        "gitea_configured": bool(config.gitea),
        "database_configured": bool(state["db"]),
        "sync_enabled": True
    }


@app.get("/api/version")
async def get_version():
    """Get application version."""
    return {
        "name": "GitHub Mirror Sync",
        "version": "1.0.0",
        "api_version": "v1"
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


# Import and include API routers
def setup_routes():
    """Setup API routes."""
    try:
        # Import route modules
        from .routes import config, repositories, sync, monitor, tasks

        # Include routers
        app.include_router(config.router, prefix="/api/config", tags=["config"])
        app.include_router(repositories.router, prefix="/api/repositories", tags=["repositories"])
        app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
        app.include_router(monitor.router, prefix="/api/monitor", tags=["monitor"])
        app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])

        print("✓ API routes loaded")
    except ImportError as e:
        print(f"⚠ Could not load all routes: {e}")


# Setup routes
setup_routes()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
