"""Bilibili crawler for GitHub project recommendations.

This module provides a unified interface for crawling GitHub project recommendations
from multiple Bilibili UP owners who create weekly GitHub trending videos.
"""

import asyncio
from datetime import datetime
from typing import Optional

from .base import BaseCrawler
from .xuanli import XuanliCrawler
from .it_cafe import ITCafeCrawler
from ..config import get_settings

settings = get_settings()


class BilibiliCrawler:
    """Unified crawler for multiple Bilibili UP owners."""

    def __init__(self, sources: Optional[list[str]] = None):
        """Initialize the unified crawler.

        Args:
            sources: List of source names to crawl. Options: 'xuanli', 'it_cafe'.
                     If None, crawls all sources.
        """
        self.sources = sources or ['xuanli', 'it_cafe']
        self.crawlers: dict[str, BaseCrawler] = {
            'xuanli': XuanliCrawler(),
            'it_cafe': ITCafeCrawler(),
        }

    async def crawl(self, max_videos_per_source: int = 10) -> list[dict]:
        """Crawl GitHub projects from all configured sources.

        Args:
            max_videos_per_source: Maximum videos to crawl per source.

        Returns:
            List of project dictionaries ready for database insertion.
        """
        all_projects = []

        for source_name in self.sources:
            if source_name not in self.crawlers:
                print(f"Unknown source: {source_name}")
                continue

            print(f"\n{'='*50}")
            print(f"Crawling source: {source_name}")
            print(f"{'='*50}")

            crawler = self.crawlers[source_name]
            try:
                projects = await crawler.crawl(max_videos=max_videos_per_source)
                all_projects.extend(projects)
                print(f"Found {len(projects)} projects from {source_name}")
            except Exception as e:
                print(f"Error crawling {source_name}: {e}")
                continue

        return all_projects

    def merge_sources(self, projects: list[dict]) -> list[dict]:
        """Merge projects with same GitHub URL from different sources.

        Args:
            projects: List of project dictionaries.

        Returns:
            List of merged project dictionaries.
        """
        # Group by github_url or name
        url_map: dict[str, dict] = {}

        for project in projects:
            # Use github_url as key if available, otherwise use name
            key = project.get('github_url') or project.get('name')

            if not key:
                continue

            if key in url_map:
                # Merge sources
                existing = url_map[key]
                if not existing.get('sources'):
                    existing['sources'] = [existing.get('source')]
                existing['sources'].append(project.get('source'))
                del existing['source']
            else:
                url_map[key] = project.copy()

        return list(url_map.values())


async def crawl_all() -> list[dict]:
    """Convenience function to crawl all sources.

    Returns:
        List of project dictionaries.
    """
    crawler = BilibiliCrawler()
    projects = await crawler.crawl()
    return crawler.merge_sources(projects)


# For backward compatibility
__all__ = ['BilibiliCrawler', 'crawl_all', 'XuanliCrawler', 'ITCafeCrawler']