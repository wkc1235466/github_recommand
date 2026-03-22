"""Base crawler class for Bilibili crawlers."""

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page

from ..config import get_settings

settings = get_settings()


class BaseCrawler(ABC):
    """Abstract base class for Bilibili crawlers."""

    def __init__(self, collection_url: str, up_name: str):
        """Initialize the crawler.

        Args:
            collection_url: URL of the Bilibili video collection.
            up_name: Name of the UP owner.
        """
        self.collection_url = collection_url
        self.up_name = up_name
        self.browser: Optional[Browser] = None

    async def crawl(self, max_videos: int = 10) -> list[dict]:
        """Crawl GitHub projects from Bilibili videos.

        Args:
            max_videos: Maximum number of videos to crawl.

        Returns:
            List of project dictionaries ready for database insertion.
        """
        projects = []

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(
                headless=settings.crawler_headless,
                channel="chrome"
            )

            try:
                # Get video links from collection page
                video_links = await self._get_video_links(max_videos)

                # Crawl each video
                for video_url in video_links:
                    try:
                        video_projects = await self._crawl_video(video_url)
                        projects.extend(video_projects)
                    except Exception as e:
                        print(f"Error crawling video {video_url}: {e}")
                        continue

            finally:
                await self.browser.close()

        return projects

    async def _get_video_links(self, max_videos: int) -> list[str]:
        """Extract video links from collection page.

        Args:
            max_videos: Maximum number of videos to return.

        Returns:
            List of video URLs.
        """
        page = await self.browser.new_page()
        video_links = []

        try:
            print(f"Navigating to collection: {self.collection_url}")
            await page.goto(self.collection_url, timeout=settings.crawler_timeout)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # Extract video links
            video_links = await page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href*="video/BV"]').forEach(a => {
                        const href = a.href;
                        // Normalize URL
                        const match = href.match(/bilibili\.com\/video\/(BV[a-zA-Z0-9]+)/);
                        if (match && !links.some(l => l.includes(match[1]))) {
                            links.push('https://www.bilibili.com/video/' + match[1] + '/');
                        }
                    });
                    return links;
                }
            """)

            print(f"Found {len(video_links)} videos in collection")
            return video_links[:max_videos]

        finally:
            await page.close()

    @abstractmethod
    async def _crawl_video(self, video_url: str) -> list[dict]:
        """Crawl GitHub projects from a single video.

        Args:
            video_url: Bilibili video URL.

        Returns:
            List of project dictionaries.
        """
        pass

    async def _get_video_info(self, page: Page) -> dict:
        """Get basic video information.

        Args:
            page: Playwright page object on video page.

        Returns:
            Dictionary with video title and other info.
        """
        info = {
            "title": "Unknown",
            "up_name": self.up_name,
        }

        try:
            # Get video title from page title
            title = await page.title()
            # Clean up title (remove " - 哔哩哔哩" suffix)
            info["title"] = title.split(" - ")[0]
        except Exception:
            pass

        return info

    def _extract_github_urls(self, text: str) -> list[str]:
        """Extract GitHub repository URLs from text.

        Args:
            text: Text to search for GitHub URLs.

        Returns:
            List of GitHub repository URLs.
        """
        # Match GitHub repository URLs
        pattern = r'https?://github\.com/[\w\-]+/[\w\-\.]+'
        urls = re.findall(pattern, text)

        # Remove duplicates and filter
        valid_urls = set()
        for url in urls:
            # Normalize URL (remove trailing slashes and query params)
            url = url.split('?')[0].rstrip('/')
            # Filter out URLs that are too long
            if len(url) < 100:
                valid_urls.add(url)

        return list(valid_urls)

    def _extract_repo_name(self, github_url: str) -> str:
        """Extract repository name from GitHub URL.

        Args:
            github_url: GitHub repository URL.

        Returns:
            Repository name (owner/repo format).
        """
        match = re.search(r'github\.com/([\w\-]+/[\w\-\.]+)', github_url)
        if match:
            return match.group(1)
        return github_url.split("/")[-1]