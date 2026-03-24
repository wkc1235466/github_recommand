"""玄离199 爬虫服务

提供爬取、保存、增量更新功能
"""

import re
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..crawler.static_crawler import BilibiliStaticCrawler, GitHubProject
from ..models.xuanli199 import Xuanli199Project
from ..logger import log


def get_session_maker():
    """获取数据库会话工厂（延迟导入以避免循环依赖）"""
    from ..database import async_session_maker
    return async_session_maker


@dataclass
class VideoProject:
    """视频中的GitHub项目"""
    github_url: str
    project_name: str
    bilibili_url: str
    video_title: str
    video_publish_time: Optional[datetime]
    episode_number: Optional[int]
    up_name: str = "玄离199"


class Xuanli199Service:
    """玄离199 爬虫服务"""

    # 合集视频URL（任意一个视频都可以提取合集列表）
    COLLECTION_URL = "https://www.bilibili.com/video/BV1srwxzMEdn/"

    def __init__(self):
        self.crawler = BilibiliStaticCrawler()

    async def close(self):
        """关闭爬虫"""
        await self.crawler.close()

    def _extract_episode_number(self, title: str) -> Optional[int]:
        """从视频标题提取期数

        Args:
            title: 视频标题，如「【科技补全94】...」

        Returns:
            期数，如 94
        """
        # 匹配「科技补全94」或「科技补全 94」
        match = re.search(r'科技补全\s*(\d+)', title)
        if match:
            return int(match.group(1))
        return None

    async def get_video_publish_time(self, video_url: str) -> Optional[datetime]:
        """获取视频发布时间

        Args:
            video_url: 视频URL

        Returns:
            发布时间
        """
        try:
            response = await self.crawler.client.get(video_url)
            response.raise_for_status()
            html = response.text

            # 提取发布时间戳
            match = re.search(r'"pubdate":(\d+)', html)
            if match:
                timestamp = int(match.group(1))
                return datetime.fromtimestamp(timestamp)
        except Exception as e:
            log.warning(f"获取视频发布时间失败: {e}")

        return None

    async def crawl_all_videos(self) -> List[VideoProject]:
        """爬取所有视频的GitHub项目

        Returns:
            所有GitHub项目列表
        """
        log.info("开始爬取所有视频...")

        # 1. 获取视频列表
        video_urls = await self.crawler.get_collection_videos(self.COLLECTION_URL)

        if not video_urls:
            log.error("未获取到视频列表")
            return []

        log.info(f"找到 {len(video_urls)} 个视频")

        # 2. 爬取每个视频
        all_projects = []

        for i, video_url in enumerate(video_urls, 1):
            log.info(f"[{i}/{len(video_urls)}] 爬取: {video_url}")

            try:
                # 获取视频信息
                video_info = await self.crawler.get_video_info(video_url)
                if not video_info:
                    continue

                # 获取置顶评论
                top_comments = await self.crawler.get_top_comments(video_info.aid)
                if not top_comments:
                    log.warning(f"未找到置顶评论")
                    continue

                # 获取发布时间
                publish_time = await self.get_video_publish_time(video_url)

                # 提取期数
                episode_number = self._extract_episode_number(video_info.title)

                # 提取GitHub项目
                github_pattern = r'https?://github\.com/[\w\-]+/[\w\-\.]+'

                for top_type, top_reply in top_comments.items():
                    if not top_reply:
                        continue

                    root_id = top_reply.get("rpid")

                    # 获取二级评论
                    second_comments = await self.crawler.get_second_comments(video_info.aid, root_id)

                    for comment in second_comments:
                        member = comment.get("member", {})
                        name = member.get("uname", "")

                        if "玄离" in name:
                            content = comment.get("content", {}).get("message", "")

                            # 提取GitHub链接
                            urls = re.findall(github_pattern, content)

                            for url in urls:
                                clean_url = url.split("?")[0].rstrip("/")

                                # 提取项目名
                                match = re.search(r"github\.com/([\w\-]+/[\w\-\.]+)", clean_url)
                                if match:
                                    project_name = match.group(1)

                                    project = VideoProject(
                                        github_url=clean_url,
                                        project_name=project_name,
                                        bilibili_url=video_url,
                                        video_title=video_info.title,
                                        video_publish_time=publish_time,
                                        episode_number=episode_number,
                                        up_name=name,
                                    )
                                    all_projects.append(project)
                                    log.info(f"  找到项目: {project_name}")

                # 避免请求过快
                await asyncio.sleep(1)

            except Exception as e:
                log.error(f"爬取视频失败: {e}")

        log.info(f"爬取完成，共找到 {len(all_projects)} 个项目")
        return all_projects

    async def get_video_list_with_episodes(self) -> List[Tuple[str, str, Optional[int]]]:
        """获取视频列表及其期数（快速，只获取列表不爬取内容）

        Returns:
            [(视频URL, 视频标题, 期数), ...]
        """
        try:
            response = await self.crawler.client.get(self.COLLECTION_URL)
            response.raise_for_status()
            html = response.text

            # 提取视频BV号和标题
            pattern = r'"bvid":"(BV[a-zA-Z0-9]+)"[^}]*?"title":"([^"]+)"'
            matches = re.findall(pattern, html)

            videos = []
            seen = set()

            for bvid, title in matches:
                # 过滤包含「科技补全」的视频
                if bvid not in seen and "科技补全" in title:
                    seen.add(bvid)
                    episode_number = self._extract_episode_number(title)
                    videos.append((f"https://www.bilibili.com/video/{bvid}/", title, episode_number))

            log.info(f"[玄离199] 从合集页面提取到 {len(videos)} 个视频")
            return videos

        except Exception as e:
            log.error(f"获取视频列表失败: {e}")
            return []

    async def fetch_new_projects(self) -> Tuple[List[VideoProject], List[int]]:
        """获取新项目但不保存，返回数据供统一服务处理

        优化：只爬取期数大于已爬取最大期数的视频，避免爬取所有视频。

        Returns:
            (新项目列表, 新期数列表)
        """
        async with get_session_maker()() as session:
            max_crawled = await self.get_max_crawled_episode(session)

        log.info(f"[玄离199] 已爬取的最大期数: {max_crawled}")

        # 1. 快速获取视频列表和期数
        video_list = await self.get_video_list_with_episodes()

        if not video_list:
            return [], []

        # 2. 筛选新视频（期数大于已爬取的最大期数）
        if max_crawled:
            new_videos = [
                (url, title, ep) for url, title, ep in video_list
                if ep and ep > max_crawled
            ]
        else:
            new_videos = video_list

        new_episodes = sorted(set(ep for _, _, ep in new_videos if ep))

        if not new_videos:
            log.info(f"[玄离199] 没有发现新视频")
            return [], []

        log.info(f"[玄离199] 发现 {len(new_videos)} 个新视频，新期数: {new_episodes}")

        # 3. 只爬取新视频
        all_projects = []

        for i, (video_url, video_title, episode_number) in enumerate(new_videos, 1):
            log.info(f"[玄离199] [{i}/{len(new_videos)}] 爬取: {video_url} (第{episode_number}期)")

            try:
                video_info = await self.crawler.get_video_info(video_url)
                if not video_info:
                    log.warning(f"获取视频信息失败")
                    continue

                top_comments = await self.crawler.get_top_comments(video_info.aid)
                if not top_comments:
                    log.warning(f"未找到置顶评论")
                    continue

                publish_time = await self.get_video_publish_time(video_url)

                github_pattern = r'https?://github\.com/[\w\-]+/[\w\-\.]+'

                for top_type, top_reply in top_comments.items():
                    if not top_reply:
                        continue

                    root_id = top_reply.get("rpid")
                    second_comments = await self.crawler.get_second_comments(video_info.aid, root_id)

                    for comment in second_comments:
                        member = comment.get("member", {})
                        name = member.get("uname", "")

                        if "玄离" in name:
                            content = comment.get("content", {}).get("message", "")
                            urls = re.findall(github_pattern, content)

                            for url in urls:
                                clean_url = url.split("?")[0].rstrip("/")
                                match = re.search(r"github\.com/([\w\-]+/[\w\-\.]+)", clean_url)
                                if match:
                                    project_name = match.group(1)

                                    project = VideoProject(
                                        github_url=clean_url,
                                        project_name=project_name,
                                        bilibili_url=video_url,
                                        video_title=video_info.title,
                                        video_publish_time=publish_time,
                                        episode_number=episode_number,
                                        up_name=name,
                                    )
                                    all_projects.append(project)
                                    log.info(f"  找到项目: {project_name}")

                await asyncio.sleep(1)

            except Exception as e:
                log.error(f"爬取视频失败: {e}")

        log.info(f"[玄离199] 爬取完成，找到 {len(all_projects)} 个新项目")
        return all_projects, new_episodes

    async def get_crawled_episodes(self, session: AsyncSession) -> List[int]:
        """获取已爬取的期数列表

        Args:
            session: 数据库会话

        Returns:
            已爬取的期数列表
        """
        result = await session.execute(
            select(Xuanli199Project.episode_number)
            .distinct()
            .where(Xuanli199Project.episode_number.isnot(None))
        )
        episodes = [row[0] for row in result.fetchall()]
        return sorted(episodes)

    async def get_max_crawled_episode(self, session: AsyncSession) -> Optional[int]:
        """获取已爬取的最大期数

        Args:
            session: 数据库会话

        Returns:
            最大期数，如果没有则返回None
        """
        result = await session.execute(
            select(func.max(Xuanli199Project.episode_number))
        )
        max_episode = result.scalar()
        return max_episode

    async def save_projects(self, projects: List[VideoProject]) -> int:
        """保存项目到数据库

        Args:
            projects: 项目列表

        Returns:
            新增的项目数量
        """
        async with get_session_maker()() as session:
            saved_count = 0

            for project in projects:
                # 检查是否已存在
                result = await session.execute(
                    select(Xuanli199Project).where(
                        Xuanli199Project.github_url == project.github_url
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    continue

                # 创建新记录
                db_project = Xuanli199Project(
                    github_url=project.github_url,
                    project_name=project.project_name,
                    bilibili_url=project.bilibili_url,
                    video_title=project.video_title,
                    video_publish_time=project.video_publish_time,
                    episode_number=project.episode_number,
                    up_name=project.up_name,
                )
                session.add(db_project)
                saved_count += 1

            await session.commit()
            log.info(f"保存了 {saved_count} 个新项目")
            return saved_count

    async def crawl_new_episodes(self) -> Tuple[int, List[int]]:
        """增量爬取新期数

        Returns:
            (新增项目数量, 新爬取的期数列表)
        """
        async with get_session_maker()() as session:
            # 获取已爬取的最大期数
            max_crawled = await self.get_max_crawled_episode(session)

        log.info(f"已爬取的最大期数: {max_crawled}")

        # 爬取所有视频
        all_projects = await self.crawl_all_videos()

        if not all_projects:
            return 0, []

        # 筛选新期数的项目
        if max_crawled:
            new_projects = [
                p for p in all_projects
                if p.episode_number and p.episode_number > max_crawled
            ]
            new_episodes = sorted(set(
                p.episode_number for p in new_projects
                if p.episode_number
            ))
        else:
            new_projects = all_projects
            new_episodes = sorted(set(
                p.episode_number for p in all_projects
                if p.episode_number
            ))

        # 保存到数据库
        saved_count = await self.save_projects(new_projects)

        return saved_count, new_episodes

    async def crawl_full(self) -> int:
        """完整爬取（爬取所有视频）

        Returns:
            新增项目数量
        """
        log.info("开始完整爬取...")

        # 爬取所有视频
        all_projects = await self.crawl_all_videos()

        if not all_projects:
            return 0

        # 保存到数据库
        saved_count = await self.save_projects(all_projects)

        log.info(f"完整爬取完成，新增 {saved_count} 个项目")
        return saved_count

    async def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        async with get_session_maker()() as session:
            # 总项目数
            total_result = await session.execute(
                select(func.count(Xuanli199Project.id))
            )
            total = total_result.scalar()

            # 已爬取的期数
            episodes = await self.get_crawled_episodes(session)

            # 最大期数
            max_episode = max(episodes) if episodes else 0

            # 最新爬取时间
            latest_result = await session.execute(
                select(func.max(Xuanli199Project.crawled_at))
            )
            latest_crawled = latest_result.scalar()

            return {
                "total_projects": total,
                "crawled_episodes": len(episodes),
                "max_episode": max_episode,
                "episode_list": episodes,
                "latest_crawled": latest_crawled,
            }


async def test_service():
    """测试服务"""
    # 初始化数据库
    from ..database import init_db
    await init_db()

    service = Xuanli199Service()

    try:
        # 获取统计信息
        stats = await service.get_stats()
        print("当前统计:")
        print(f"  总项目数: {stats['total_projects']}")
        print(f"  已爬取期数: {stats['crawled_episodes']}")
        print(f"  最大期数: {stats['max_episode']}")
        print(f"  最新爬取: {stats['latest_crawled']}")

        # 增量更新
        print("\n开始增量更新...")
        saved_count, new_episodes = await service.crawl_new_episodes()
        print(f"新增 {saved_count} 个项目")
        print(f"新爬取的期数: {new_episodes}")

        # 再次获取统计
        stats = await service.get_stats()
        print("\n更新后统计:")
        print(f"  总项目数: {stats['total_projects']}")
        print(f"  已爬取期数: {stats['crawled_episodes']}")

    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_service())