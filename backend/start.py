#!/usr/bin/env python
"""
Start script for GitHub Project Recommendation System.

This script:
1. Checks if MongoDB is running
2. Creates necessary directories
3. Starts the FastAPI server

Usage:
    python start.py                  # Start with default settings
    python start.py --port 8080      # Start on custom port
    python start.py --no-reload      # Start without auto-reload
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import uvicorn


def check_mongodb(url: str = "mongodb://localhost:27017") -> bool:
    """Check if MongoDB is running."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio

        async def _check():
            client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=2000)
            await client.admin.command('ping')
            client.close()
            return True

        return asyncio.run(_check())
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ['fastapi', 'uvicorn', 'motor', 'pydantic', 'playwright']
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
    parser.add_argument(
        "--skip-db-check",
        action="store_true",
        help="Skip MongoDB connection check"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("GitHub Project Recommendation System")
    print("=" * 50)

    # Check dependencies
    print("\n[1/4] Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("  All dependencies installed.")

    # Check .env file
    print("\n[2/4] Checking configuration...")
    check_env_file()
    print("  Configuration ready.")

    # Check MongoDB
    print("\n[3/4] Checking MongoDB connection...")
    if not args.skip_db_check:
        if not check_mongodb():
            print("\n  MongoDB is not running!")
            print("  Please start MongoDB first:")
            print("    - Docker: docker compose up -d mongodb")
            print("    - Or install MongoDB locally")
            print("\n  Use --skip-db-check to bypass this check.")
            sys.exit(1)
        print("  MongoDB connected successfully.")
    else:
        print("  Skipping MongoDB check.")

    # Start server
    print("\n[4/4] Starting server...")
    reload = args.reload and not args.no_reload

    print(f"""
  Server starting at:
    - Local:   http://localhost:{args.port}
    - Network: http://{args.host}:{args.port}
    - API Docs: http://localhost:{args.port}/docs

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