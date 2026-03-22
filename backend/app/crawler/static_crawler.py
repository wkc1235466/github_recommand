"""静态爬虫 - 使用 httpx 爬取 B站评论获取 GitHub 项目

核心功能：
1. 从视频 BV号获取 aid (oid)
2. 获取置顶评论
3. 获取二级评论
4. 从 UP主评论中提取 GitHub 链接

不需要 Playwright，纯 API 爬取，速度快。
"""

import re
import json
import asyncio
import hashlib
import time
import urllib.parse
from typing import Optional, List
from dataclasses import dataclass

import httpx

try:
    from ..logger import log
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from app.logger import log, setup_logging
    setup_logging(debug=True)


# B站 wbi 签名密钥
WBI_MIXIN_KEY = "ea1db124af3c7062474693fa704f4ff8"


@dataclass
class VideoInfo:
    """视频信息"""
    bvid: str
    aid: int
    title: str
    description: str


@dataclass
class GitHubProject:
    """GitHub 项目信息"""
    name: str
    url: str
    video_title: str
    video_url: str


class BilibiliStaticCrawler:
    """B站静态爬虫 - 爬取评论区 GitHub 项目"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    def _generate_wbi_sign(self, params: dict) -> dict:
        """生成 wbi 签名

        Args:
            params: 请求参数（不含 w_rid 和 wts）

        Returns:
            添加了 w_rid 和 wts 的参数
        """
        wts = int(time.time())
        params["wts"] = wts

        # 参数按 key 字母排序后拼接
        sorted_params = sorted(params.items())
        query = "&".join([f"{k}={v}" for k, v in sorted_params])

        # MD5 加密
        sign_str = query + WBI_MIXIN_KEY
        w_rid = hashlib.md5(sign_str.encode()).hexdigest()

        params["w_rid"] = w_rid
        return params

    async def get_video_info(self, video_url: str) -> Optional[VideoInfo]:
        """获取视频信息（提取 aid 和标题）

        Args:
            video_url: 视频URL，如 https://www.bilibili.com/video/BV1bZAczVEuK/

        Returns:
            VideoInfo 或 None
        """
        # 提取BV号
        match = re.search(r"video/(BV[a-zA-Z0-9]+)", video_url)
        if not match:
            log.error(f"无效的视频URL: {video_url}")
            return None

        bvid = match.group(1)

        try:
            response = await self.client.get(video_url)
            response.raise_for_status()

            html = response.text

            # 提取 aid
            aid_match = re.search(r'"aid":(\d+)', html)
            if not aid_match:
                log.error(f"未找到 aid: {video_url}")
                return None

            aid = int(aid_match.group(1))

            # 提取标题
            title_match = re.search(r"<title>([^<]+)</title>", html)
            title = title_match.group(1).split(" - ")[0] if title_match else "Unknown"

            # 提取简介
            desc_match = re.search(r'"desc":"([^"]+)"', html)
            desc = desc_match.group(1) if desc_match else ""

            return VideoInfo(
                bvid=bvid,
                aid=aid,
                title=title,
                description=desc
            )

        except Exception as e:
            log.error(f"获取视频信息失败: {e}")
            return None

    async def get_top_comments(self, oid: int) -> dict:
        """获取置顶评论

        Args:
            oid: 视频 aid

        Returns:
            置顶评论数据 {"upper": {...}, "admin": {...}, ...}
        """
        # 构造请求参数
        params = {
            "oid": oid,
            "type": 1,
            "mode": 3,  # 热门评论
            "pagination_str": '{"offset":""}',
            "plat": 1,
            "seek_rpid": "",
            "web_location": 1315875,
        }

        # 添加签名
        params = self._generate_wbi_sign(params)

        # URL 编码 pagination_str
        params["pagination_str"] = urllib.parse.quote(params["pagination_str"], safe=":")

        url = "https://api.bilibili.com/x/v2/reply/wbi/main"

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                log.error(f"API 错误: {data.get('message')}")
                return {}

            return data.get("data", {}).get("top", {})

        except Exception as e:
            log.error(f"获取置顶评论失败: {e}")
            return {}

    async def get_second_comments(self, oid: int, root_id: int) -> List[dict]:
        """获取二级评论

        Args:
            oid: 视频 aid
            root_id: 一级评论的 rpid

        Returns:
            二级评论列表
        """
        url = "https://api.bilibili.com/x/v2/reply/reply"
        params = {
            "oid": oid,
            "type": 1,
            "root": root_id,
            "ps": 30,  # 每页数量
            "pn": 1,   # 页码
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                log.error(f"获取二级评论失败: {data.get('message')}")
                return []

            return data.get("data", {}).get("replies", []) or []

        except Exception as e:
            log.error(f"获取二级评论失败: {e}")
            return []

    async def get_github_projects_from_video(
        self,
        video_url: str,
        up_name: str = "玄离199"
    ) -> List[GitHubProject]:
        """从单个视频的评论区提取 GitHub 项目

        流程：
        1. 获取视频 aid
        2. 获取置顶评论
        3. 获取置顶评论的二级评论
        4. 在 UP主的二级评论中提取 GitHub 链接

        Args:
            video_url: 视频URL
            up_name: UP主名称

        Returns:
            GitHub项目列表
        """
        projects = []

        # 1. 获取视频信息
        video_info = await self.get_video_info(video_url)
        if not video_info:
            return projects

        log.info(f"视频: {video_info.title}")
        log.info(f"aid: {video_info.aid}")

        # 2. 获取置顶评论
        top_comments = await self.get_top_comments(video_info.aid)

        if not top_comments:
            log.warning("未找到置顶评论")
            return projects

        # 3. 遍历所有置顶评论，获取二级评论
        github_pattern = r'https?://github\.com/[\w\-]+/[\w\-\.]+'

        for top_type, top_reply in top_comments.items():
            if not top_reply:
                continue

            root_id = top_reply.get("rpid")
            root_name = top_reply.get("member", {}).get("uname", "")

            log.info(f"置顶评论 [{root_name}]: {top_reply.get('content', {}).get('message', '')[:50]}...")

            # 获取二级评论
            second_comments = await self.get_second_comments(video_info.aid, root_id)

            log.info(f"二级评论数: {len(second_comments)}")

            # 4. 查找 UP主的二级评论
            for comment in second_comments:
                member = comment.get("member", {})
                name = member.get("uname", "")

                if up_name in name:
                    content = comment.get("content", {}).get("message", "")
                    log.info(f"找到 UP主 [{name}] 的二级评论")

                    # 提取 GitHub 链接
                    urls = re.findall(github_pattern, content)

                    for url in urls:
                        # 清理 URL
                        clean_url = url.split("?")[0].rstrip("/")

                        # 提取项目名
                        match = re.search(r"github\.com/([\w\-]+/[\w\-\.]+)", clean_url)
                        if match:
                            project_name = match.group(1)

                            project = GitHubProject(
                                name=project_name,
                                url=clean_url,
                                video_title=video_info.title,
                                video_url=video_url
                            )
                            projects.append(project)
                            log.info(f"  找到项目: {project_name}")

        return projects

    async def crawl_videos(
        self,
        video_urls: List[str],
        up_name: str = "玄离199"
    ) -> List[GitHubProject]:
        """爬取多个视频的 GitHub 项目

        Args:
            video_urls: 视频URL列表
            up_name: UP主名称

        Returns:
            所有 GitHub 项目列表
        """
        all_projects = []

        for i, video_url in enumerate(video_urls):
            log.info(f"\n[{i+1}/{len(video_urls)}] 爬取视频: {video_url}")

            try:
                projects = await self.get_github_projects_from_video(video_url, up_name)
                all_projects.extend(projects)

                # 避免请求过快
                await asyncio.sleep(1)

            except Exception as e:
                log.error(f"爬取视频失败: {e}")

        # 去重
        seen = set()
        unique_projects = []
        for p in all_projects:
            if p.url not in seen:
                seen.add(p.url)
                unique_projects.append(p)

        log.info(f"\n总计找到 {len(unique_projects)} 个不重复的 GitHub 项目")
        return unique_projects


async def test_crawler():
    """测试爬虫"""
    crawler = BilibiliStaticCrawler()

    try:
        # 测试单个视频
        video_url = "https://www.bilibili.com/video/BV1bZAczVEuK/"

        print(f"测试视频: {video_url}")
        print("=" * 60)

        projects = await crawler.get_github_projects_from_video(video_url)

        print(f"\n找到 {len(projects)} 个 GitHub 项目:")
        for p in projects:
            print(f"  {p.name}")
            print(f"    URL: {p.url}")
            print(f"    来源: {p.video_title}")

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(test_crawler())