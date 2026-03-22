#!/usr/bin/env python
"""
Start script for GitHub Project Recommendation System.

This script:
1. Checks dependencies
2. Creates necessary directories
3. Starts the FastAPI server

Usage:
    python start.py                  # Start with default settings
    python start.py --port 8080      # Start on custom port
    python start.py --no-reload      # Start without auto-reload
"""

import argparse
import sys
from pathlib import Path

import uvicorn


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ['fastapi', 'uvicorn', 'sqlalchemy', 'aiosqlite', 'pydantic', 'playwright']
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Run: uv sync")
        return False

    return True


def check_env_file():
    """Check if .env file exists, create from example if not."""
    env_file = Path(__file__).parent.parent / ".env"
    env_example = Path(__file__).parent.parent / ".env.example"

    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        import shutil
        shutil.copy(env_example, env_file)
        print("Please edit .env file with your configuration.")
    elif not env_file.exists():
        print("Warning: No .env file found. Using default settings.")


def create_data_dir():
    """Create data directory for SQLite database."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Start GitHub Project Recommendation System"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
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
        default=True,
        help="Enable auto-reload (default: True)"
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("GitHub Project Recommendation System")
    print("=" * 50)

    # Check dependencies
    print("\n[1/3] Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("  All dependencies installed.")

    # Check .env file
    print("\n[2/3] Checking configuration...")
    check_env_file()
    create_data_dir()
    print("  Configuration ready.")

    # Start server
    print("\n[3/3] Starting server...")
    reload = args.reload and not args.no_reload

    print(f"""
  Server starting at:
    - Local:   http://localhost:{args.port}
    - Network: http://{args.host}:{args.port}
    - API Docs: http://localhost:{args.port}/docs

  Database: SQLite (data/github_recommend.db)

  Press Ctrl+C to stop.
""")

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=reload,
    )


if __name__ == "__main__":
    main()