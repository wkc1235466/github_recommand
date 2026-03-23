"""重新爬取失败项目的GitHub URL

运行方式:
    python backend/app/itcoffee/retry_failed.py
"""

import asyncio
import sys
import os

# 添加项目路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from app.database import init_db
from app.itcoffee import ITcoffeeService


# 需要重新爬取的项目列表
FAILED_PROJECTS = [
    "MiroThinker",
    "icloud_photos_downloader",
    "wechat-article-exporter",
    "vibe-kanban",
    "LaunchNext",
    "NoteDiscovery",
    "nginx-proxy-manager",
    "CnC_Red_Alert",
    "ktransformers",
    "unsloth",
    "data-formulator",
    "hoppscotch",
    "lucide",
    "oumi",
    "ladybird",
    "pydantic-ai",
    "stock",
    "react-scan",
    "go-blueprint",
    "windows",
    "docling",
    "formbricks",
    "localstack",
    "AnythingLLM",
    "Nginx",
    "postiz",
    "PowerToys",
    "shadcn-ui",
    "composio",
    "maestro",
    "awesome",
    "graphrag-accelerator",
    "tiptap",
    "ImHex",
    "marker",
]


async def main():
    """重新爬取失败的项目"""
    await init_db()

    service = ITcoffeeService()

    try:
        print(f"Start retry {len(FAILED_PROJECTS)} failed projects...")
        print("=" * 60)

        success_count, fail_count, failed_projects = await service.fill_specific_projects(FAILED_PROJECTS)

        print("=" * 60)
        print(f"\nResult: success {success_count}, failed {fail_count}")

        if failed_projects:
            print("\nStill failed projects:")
            for p in failed_projects:
                print(f"  - [{p['episode_number']}] {p['project_name']}: {p.get('description', '')}")

    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())