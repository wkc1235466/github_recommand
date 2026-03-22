"""Crawler for 玄离199's GitHub recommendation videos.

玄离199的视频结构：
- 项目信息在置顶评论的回复中
- 需要找到用户"玄离199"的回复
- 回复中包含项目名称和GitHub地址
"""

import asyncio
import re
from typing import Optional
from playwright.async_api import Page

from .base import BaseCrawler
from ..config import get_settings
from ..logger import log

settings = get_settings()


class XuanliCrawler(BaseCrawler):
    """Crawler for 玄离199's Bilibili GitHub recommendation videos."""

    def __init__(self):
        """Initialize the crawler for 玄离199."""
        super().__init__(
            collection_url="https://space.bilibili.com/67079745/lists/3173076?type=season",
            up_name="玄离199"
        )

    async def _crawl_video(self, video_url: str) -> list[dict]:
        """Crawl GitHub projects from a single video."""
        projects = []
        page = await self.browser.new_page()

        try:
            log.info(f"  爬取视频: {video_url}")
            await page.goto(video_url, timeout=settings.crawler_timeout)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)

            # Get video info
            video_info = await self._get_video_info(page)
            log.info(f"  视频标题: {video_info['title']}")

            # Scroll to load comments
            log.debug("  滚动到评论区...")
            for i in range(3):
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)*0.3})")
                await asyncio.sleep(1)

            # Wait for comments to load
            await asyncio.sleep(2)

            # Extract projects from comments
            project_info = await self._extract_projects_from_comments(page)

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
                log.info(f"    发现项目: {name} - {github_url}")

        except Exception as e:
            log.error(f"  爬取视频失败: {e}")

        finally:
            await page.close()

        return projects

    async def _extract_projects_from_comments(self, page: Page) -> list[tuple[str, str]]:
        """Extract project names and GitHub URLs from comments."""
        projects = []

        try:
            # 方法1: 直接从页面文本中提取所有GitHub链接
            log.debug("  方法1: 从页面提取GitHub链接...")
            page_text = await page.evaluate("() => document.body.innerText")

            github_pattern = r'https?://github\.com/[\w\-]+/[\w\-\.]+'
            all_urls = re.findall(github_pattern, page_text)

            # 去重
            unique_urls = list(set(all_urls))
            log.debug(f"  页面中找到 {len(unique_urls)} 个GitHub链接")

            for url in unique_urls:
                url = url.split('?')[0].rstrip('/')
                # 从URL提取项目名
                match = re.search(r'github\.com/([\w\-]+/[\w\-\.]+)', url)
                if match:
                    name = match.group(1)
                    projects.append((name, url))

            # 方法2: 查找置顶评论
            if not projects:
                log.debug("  方法2: 查找置顶评论...")

                # 尝试多种选择器
                selectors = [
                    ".reply-item",
                    ".comment-item",
                    "[class*='reply']",
                    "[class*='comment']"
                ]

                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        log.debug(f"    找到 {len(elements)} 个元素: {selector}")

                        for el in elements[:5]:  # 只检查前5个
                            text = await el.inner_text()
                            if 'github.com' in text.lower() or '玄离' in text:
                                log.debug(f"    相关内容: {text[:100]}...")
                                urls = re.findall(github_pattern, text)
                                for url in urls:
                                    url = url.split('?')[0].rstrip('/')
                                    match = re.search(r'github\.com/([\w\-]+/[\w\-\.]+)', url)
                                    if match:
                                        name = match.group(1)
                                        if (name, url) not in projects:
                                            projects.append((name, url))

            # 方法3: 检查视频简介
            if not projects:
                log.debug("  方法3: 检查视频简介...")
                desc = await page.evaluate("""
                    () => {
                        const selectors = [
                            '.basic-desc-info',
                            '.desc-info-text',
                            '[class*="desc"]'
                        ];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el) return el.innerText;
                        }
                        return null;
                    }
                """)
                if desc:
                    log.debug(f"    简介内容: {desc[:200]}...")
                    urls = re.findall(github_pattern, desc)
                    for url in urls:
                        url = url.split('?')[0].rstrip('/')
                        match = re.search(r'github\.com/([\w\-]+/[\w\-\.]+)', url)
                        if match:
                            name = match.group(1)
                            if (name, url) not in projects:
                                projects.append((name, url))

        except Exception as e:
            log.error(f"  提取项目失败: {e}")

        return projects

    async def _get_video_info(self, page: Page) -> dict:
        """Get basic video information."""
        info = {
            "title": "Unknown",
            "up_name": self.up_name,
        }

        try:
            title = await page.title()
            info["title"] = title.split(" - ")[0]
        except Exception:
            pass

        return info