"""Crawler for IT咖啡馆's GitHub recommendation videos.

IT咖啡馆的视频结构：
- 视频简介中有项目名称列表
- 通常没有GitHub地址，需要后续补全
- 项目名称格式通常是：1. project-name 或类似
"""

import asyncio
import re
from playwright.async_api import Page

from .base import BaseCrawler


class ITCafeCrawler(BaseCrawler):
    """Crawler for IT咖啡馆's Bilibili GitHub recommendation videos."""

    def __init__(self):
        """Initialize the crawler for IT咖啡馆."""
        super().__init__(
            collection_url="https://space.bilibili.com/65564239/lists/1982929?type=season",
            up_name="IT咖啡馆"
        )

    async def _crawl_video(self, video_url: str) -> list[dict]:
        """Crawl GitHub projects from a single video.

        IT咖啡馆的视频特点：
        1. 项目名称在视频简介中
        2. 通常没有GitHub地址
        3. 需要后续通过AI或GitHub搜索补全

        Args:
            video_url: Bilibili video URL.

        Returns:
            List of project dictionaries.
        """
        projects = []
        page = await self.browser.new_page()

        try:
            print(f"  Crawling video: {video_url}")
            await page.goto(video_url, timeout=settings.crawler_timeout)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # Get video info
            video_info = await self._get_video_info(page)

            # Extract project names from description
            project_names = await self._extract_project_names_from_description(page)

            for name in project_names:
                # For IT咖啡馆, we don't have GitHub URLs
                # These will need to be filled by AI analysis or manual search later
                project = {
                    "name": name,
                    "github_url": None,  # Will be filled by AI/GitHub search
                    "description": None,
                    "recommend_reason": f"推荐自B站视频: {video_info['title']}",
                    "source": {
                        "bilibili_url": video_url,
                        "up_name": self.up_name,
                        "video_title": video_info["title"],
                    },
                    "tags": [],
                    "stars": None,
                    "needs_url": True,  # Flag to indicate URL needs to be filled
                }
                projects.append(project)
                print(f"    Found project: {name}")

        except Exception as e:
            print(f"  Error crawling video: {e}")

        finally:
            await page.close()

        return projects

    async def _extract_project_names_from_description(self, page: Page) -> list[str]:
        """Extract project names from video description.

        IT咖啡馆的视频简介通常包含：
        - 编号的列表如 "1. project-name"
        - 或者 "项目名：xxx" 格式
        - 有时也会有GitHub链接

        Args:
            page: Playwright page object.

        Returns:
            List of project names.
        """
        project_names = []

        try:
            # Try to expand description if needed
            try:
                expand_btn = await page.query_selector(".desc-btn, [class*='expand']")
                if expand_btn:
                    await expand_btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            # Get description text
            description_data = await page.evaluate("""
                () => {
                    // Try multiple selectors for description
                    const selectors = [
                        '.basic-desc-info',
                        '.desc-info-text',
                        '.video-desc .text',
                        '[class*="desc-content"]',
                        '.right-info .desc'
                    ];

                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            return el.innerText;
                        }
                    }

                    // Fallback: get all text from video info section
                    const videoInfo = document.querySelector('.video-info');
                    if (videoInfo) {
                        return videoInfo.innerText;
                    }

                    return null;
                }
            """)

            if description_data:
                print(f"    Description found: {description_data[:200]}...")

                # Extract project names from description
                # Pattern 1: Numbered list (1. xxx, 2. xxx, etc.)
                # Pattern 2: GitHub URLs (extract repo name)
                # Pattern 3: Lines with project-like names

                lines = description_data.split('\n')
                for line in lines:
                    line = line.strip()

                    # Skip empty lines
                    if not line or len(line) < 2:
                        continue

                    # Check for GitHub URL
                    if 'github.com' in line.lower():
                        urls = self._extract_github_urls(line)
                        for url in urls:
                            name = self._extract_repo_name(url)
                            if name not in project_names:
                                project_names.append(name)
                        continue

                    # Check for numbered list pattern
                    numbered_match = re.match(r'^[\d]+[.、\s]+(.+)$', line)
                    if numbered_match:
                        name = numbered_match.group(1).strip()
                        # Clean up the name
                        name = re.sub(r'[:：].*$', '', name)  # Remove text after colon
                        name = re.sub(r'\s+', ' ', name).strip()
                        if len(name) > 1 and len(name) < 100:
                            if name not in project_names:
                                project_names.append(name)
                        continue

                    # Check for "项目名：" pattern
                    colon_match = re.match(r'^[^:：]+[:：](.+)$', line)
                    if colon_match:
                        name = colon_match.group(1).strip()
                        if len(name) > 1 and len(name) < 100:
                            if name not in project_names:
                                project_names.append(name)

            # Also check comments for GitHub URLs (sometimes they add links there)
            if not project_names:
                print("    No projects in description, checking comments...")
                comments_data = await page.evaluate("""
                    () => {
                        const comments = document.querySelectorAll('.reply-content, .sub-reply-content');
                        const texts = [];
                        comments.forEach(c => texts.push(c.innerText));
                        return texts.join('\\n');
                    }
                """)

                if comments_data:
                    urls = self._extract_github_urls(comments_data)
                    for url in urls:
                        name = self._extract_repo_name(url)
                        if name not in project_names:
                            project_names.append(name)

        except Exception as e:
            print(f"    Error extracting project names: {e}")

        return project_names


# Import settings at module level for use in methods
from ..config import get_settings
settings = get_settings()