#!/usr/bin/env python3
"""
GitHub Mirror Sync - Web UI Launcher

Starts the FastAPI web application for repository synchronization.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GitHub Mirror Sync - Web UI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                           # Run on localhost:8000
  python run.py --host 0.0.0.0 --port 8080  # Run on all interfaces:8080
  python run.py --reload                  # Enable auto-reload for development
        """
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )

    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level (default: info)"
    )

    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      🚀 GitHub Mirror Sync - Web UI                         ║
║                                                              ║
║  Starting application...                                    ║
║  Host: {args.host:<48} ║
║  Port: {args.port:<48} ║
║  Reload: {'Enabled' if args.reload else 'Disabled':<44} ║
║                                                              ║
║  📖 Access the application:                                 ║
║     Web UI: http://{args.host}:{args.port}                 ║
║     API Docs: http://{args.host}:{args.port}/docs          ║
║     ReDoc: http://{args.host}:{args.port}/redoc            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        uvicorn.run(
            "src.web.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            log_level=args.log_level
        )
    except KeyboardInterrupt:
        print("\n\n✓ Application stopped")
        sys.exit(0)
