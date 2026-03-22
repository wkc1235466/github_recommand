"""Crawler for 玄离199's GitHub recommendation videos.

玄离199的视频结构：
- 项目信息在置顶评论的回复中
- 需要找到用户"玄离199"的回复
- 回复中包含项目名称和GitHub地址
"""

import asyncio
from typing import Optional
from playwright.async_api import Page

from .base import BaseCrawler


class XuanliCrawler(BaseCrawler):
    """Crawler for 玄离199's Bilibili GitHub recommendation videos."""

    def __init__(self):
        """Initialize the crawler for 玄离199."""
        super().__init__(
            collection_url="https://space.bilibili.com/67079745/lists/3173076?type=season",
            up_name="玄离199"
        )

    async def _crawl_video(self, video_url: str) -> list[dict]:
        """Crawl GitHub projects from a single video.

        玄离199的视频特点：
        1. 项目信息在置顶评论的回复中
        2. 需要找到用户"玄离199"的回复
        3. 回复中包含项目名称和GitHub地址

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

            # Scroll to comments section
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
            await asyncio.sleep(2)

            # Find the pinned comment and get replies from 玄离199
            project_info = await self._extract_projects_from_pinned_reply(page)

            for name, github_url in project_info:
                project = {
                    "name": name,
                    "github_url": github_url,
                    "description": None,
                    "recommend_reason": f"推荐自B站视频: {video_info['title']}",
                    "source": {
                        "bilibili_url": video_url,
                        "up_name": self.up_name,
                        "video_title": video_info["title"],
                    },
                    "tags": [],
                    "stars": None,
                }
                projects.append(project)
                print(f"    Found project: {name} - {github_url}")

        except Exception as e:
            print(f"  Error crawling video: {e}")

        finally:
            await page.close()

        return projects

    async def _extract_projects_from_pinned_reply(self, page: Page) -> list[tuple[str, str]]:
        """Extract project names and GitHub URLs from pinned comment replies.

        玄离199通常会在置顶评论的回复中列出项目信息。

        Args:
            page: Playwright page object.

        Returns:
            List of (project_name, github_url) tuples.
        """
        projects = []

        try:
            # Method 1: Try to find replies from 玄离199 in the pinned comment
            # B站评论区结构较为复杂，需要多层查找

            # First, try to click "查看更多回复" if exists
            try:
                view_more_btn = await page.query_selector(".reply-item .view-more-btn")
                if view_more_btn:
                    await view_more_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # Get all reply content from 玄离199
            # The structure is: comment -> replies -> each reply has user name and content
            reply_data = await page.evaluate("""
                () => {
                    const projects = [];

                    // Find all reply items
                    const replyItems = document.querySelectorAll('.reply-item, .sub-reply-item');

                    replyItems.forEach(item => {
                        // Check if this is from 玄离199
                        const userEl = item.querySelector('.reply-user-name, .sub-reply-name');
                        const contentEl = item.querySelector('.reply-content, .sub-reply-content');

                        if (userEl && contentEl) {
                            const userName = userEl.textContent.trim();
                            const content = contentEl.textContent.trim();

                            // Check if user is 玄离199 or contains github link
                            if (userName.includes('玄离') || content.includes('github.com')) {
                                // Extract github URLs
                                const githubPattern = /https?:\\/\\/github\\.com\\/[\\w\\-]+\\/[\\w\\-\\.]+/g;
                                const matches = content.match(githubPattern) || [];

                                matches.forEach(url => {
                                    // Try to extract project name from content
                                    // Format is usually: "1. project-name: url" or similar
                                    const beforeUrl = content.split(url)[0];
                                    const lines = beforeUrl.split(/[\\n,，、]/);
                                    let name = lines[lines.length - 1].trim();
                                    // Clean up name (remove numbers, dots, etc.)
                                    name = name.replace(/^[\\d.\\-\\s]+/, '').replace(/[:：]$/, '').trim();

                                    if (!name || name.length < 2) {
                                        // Extract from URL
                                        const urlMatch = url.match(/github\\.com\\/([\\w\\-]+\\/([\\w\\-\\.]+))/);
                                        if (urlMatch) {
                                            name = urlMatch[1]; // owner/repo format
                                        }
                                    }

                                    projects.push([name, url]);
                                });
                            }
                        }
                    });

                    return projects;
                }
            """)

            if reply_data:
                # Deduplicate
                seen = set()
                for name, url in reply_data:
                    # Normalize URL
                    url = url.split('?')[0].rstrip('/')
                    if url not in seen:
                        seen.add(url)
                        projects.append((name, url))

            # Method 2: If no projects found, search entire page for GitHub URLs
            if not projects:
                print("    No projects found in comments, searching entire page...")
                page_content = await page.content()
                github_urls = self._extract_github_urls(page_content)

                for url in github_urls:
                    name = self._extract_repo_name(url)
                    projects.append((name, url))

        except Exception as e:
            print(f"    Error extracting projects: {e}")

        return projects


# Import settings at module level for use in methods
from ..config import get_settings
settings = get_settings()