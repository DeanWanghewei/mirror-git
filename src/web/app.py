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
from .. import __version__

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
WEB_ROOT = PROJECT_ROOT / "src" / "web"
STATIC_DIR = WEB_ROOT / "static"
TEMPLATES_DIR = WEB_ROOT / "templates"

# Create FastAPI app
app = FastAPI(
    title="GitHub Mirror Sync",
    description="Web UI for GitHub to Gitea repository synchronization",
    version=__version__
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
templates = None
if TEMPLATES_DIR.exists():
    try:
        templates = Jinja2Templates(directory=TEMPLATES_DIR)
    except (ImportError, AssertionError):
        # jinja2 not installed, use fallback HTML
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
        print(f"✓ Configuration loaded")

        # Initialize logging
        init_default_logger(_config.log)
        print(f"✓ Logging initialized (level: {_config.log.level})")

        # Create log directory if needed
        log_dir = Path(_config.log.file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        # Use sync.db for backward compatibility with older versions
        db_url = os.getenv("DATABASE_URL", "sqlite:///app/data/sync.db")
        print(f"ℹ Database URL: {db_url.split('@')[0] if '@' in db_url else db_url}")  # Hide password

        # Check for data migration from old database file
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url[len("sqlite:///"):])
            old_db_path = db_path.parent / "mirror_sync.db"

            # If using default path and old database exists but new doesn't, inform user
            if not db_path.exists() and old_db_path.exists() and "sync.db" in str(db_path):
                print(f"\n⚠️  Warning: Found old database at {old_db_path}")
                print(f"   Current database: {db_path}")
                print(f"   Your data is in the old database file.")
                print(f"\n   To use your existing data, set environment variable:")
                print(f"   DATABASE_URL=sqlite:///{old_db_path}")
                print(f"\n   Or rename {old_db_path.name} to {db_path.name}")
                print()

        # Ensure SQLite URL has proper format and create directory
        if db_url.startswith("sqlite:///"):
            # Extract path from sqlite:///path/to/db.db
            # Keep absolute path if it starts with /
            db_path_str = db_url[len("sqlite:///"):]

            # Ensure absolute path in container
            if not db_path_str.startswith('/'):
                db_path_str = '/' + db_path_str

            db_path = Path(db_path_str)

            # Create directory for SQLite database if it doesn't exist
            db_dir = db_path.parent
            db_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ SQLite database directory created: {db_dir}")
            print(f"✓ Database file path: {db_path}")
        elif db_url.startswith("./") or db_url.startswith("/"):
            db_path = db_url.lstrip("./")
            db_url = f"sqlite:///{db_path}"
            # Create directory for SQLite database if it doesn't exist
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ SQLite database directory created: {db_dir}")
        elif not db_url.startswith("sqlite://") and not db_url.startswith("postgresql") and not db_url.startswith("mysql"):
            db_path = db_url
            db_url = f"sqlite:///{db_url}"
            # Create directory for SQLite database if it doesn't exist
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ SQLite database directory created: {db_dir}")

        try:
            _db = init_database(db_url)
            print(f"✓ Database initialized successfully")
        except Exception as db_error:
            error_msg = str(db_error)
            print(f"✗ Database initialization failed: {error_msg}")

            # Provide helpful error messages
            if "Can't connect to MySQL server" in error_msg or "Connection refused" in error_msg:
                print("\n" + "="*60)
                print("❌ MySQL Connection Failed")
                print("="*60)
                print("\nPossible causes:")
                print("1. MySQL container is not running")
                print("2. Incorrect DATABASE_URL configuration")
                print("3. Network connectivity issues")
                print("\nSolutions:")
                print("━" * 60)
                print("\n📌 Option 1: Use SQLite (Recommended for simple deployments)")
                print("   Set environment variable:")
                print("   DATABASE_URL=sqlite:///app/data/mirror_sync.db")
                print("\n📌 Option 2: Fix MySQL connection")
                print("   a) Check if MySQL container is running:")
                print("      docker ps | grep mysql")
                print("   b) Verify both containers are on the same network:")
                print("      docker network inspect mirror-net")
                print("   c) Use correct DATABASE_URL format:")
                print("      mysql+pymysql://user:password@container_name:3306/database")
                print("\n📌 Option 3: Start MySQL container")
                print("   docker run -d --name mirror-git-mysql \\")
                print("     --network mirror-net \\")
                print("     -e MYSQL_ROOT_PASSWORD=root123456 \\")
                print("     -e MYSQL_DATABASE=mirror_git \\")
                print("     -e MYSQL_USER=mirror_user \\")
                print("     -e MYSQL_PASSWORD=mirror123456 \\")
                print("     mysql:8.0")
                print("\n" + "="*60)

            elif "No such file or directory" in error_msg and "sqlite" in db_url.lower():
                print("\n❌ SQLite database directory does not exist")
                print("Solution: Ensure the directory is mounted correctly")
                print("  -v $(pwd)/data:/app/data")

            raise RuntimeError(
                f"Database initialization failed. Please check the error messages above and "
                f"ensure your database is properly configured. "
                f"For simple deployments, we recommend using SQLite: "
                f"DATABASE_URL=sqlite:///app/data/mirror_sync.db"
            ) from db_error

        # Create local repository storage directory
        local_repo_dir = Path(_config.sync.local_path)
        local_repo_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Local repository storage: {_config.sync.local_path}")

        # Initialize scheduler
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

        # Start the scheduler
        _scheduler.start()
        print("✓ Task scheduler started")

        # Schedule automatic sync task
        sync_interval = _config.sync.interval if _config.sync.interval else 3600
        try:
            job_id = _scheduler.schedule_sync(interval_seconds=sync_interval)
            print(f"✓ Scheduled automatic sync every {sync_interval} seconds (job_id: {job_id})")
        except Exception as e:
            print(f"⚠ Could not schedule automatic sync: {e}")
            print(f"  You can manually schedule sync via API: POST /api/tasks/sync/schedule")

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
        "version": __version__
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
        "version": __version__,
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
