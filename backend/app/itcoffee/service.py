"""ITcoffee 爬虫服务

提供爬取、保存、增量更新、GitHub URL补全功能
"""

import re
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

import httpx
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.itcoffee import ITcoffeeProject
from ..logger import log


def get_session_maker():
    """获取数据库会话工厂（延迟导入以避免循环依赖）"""
    from ..database import async_session_maker
    return async_session_maker


@dataclass
class VideoProject:
    """视频中的GitHub项目"""
    project_name: str
    description: Optional[str]
    bilibili_url: str
    video_title: str
    video_publish_time: Optional[datetime]
    episode_number: Optional[int]
    up_name: str = "IT咖啡馆"


class ITcoffeeService:
    """ITcoffee 爬虫服务"""

    # 合集中任意一个视频的URL（用于提取合集视频列表）
    COLLECTION_URL = "https://www.bilibili.com/video/BV1ekwfz2EhS/"

    # 请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=self.HEADERS,
            follow_redirects=True,
            timeout=30.0
        )

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    def _extract_episode_number(self, title: str) -> Optional[int]:
        """从视频标题提取期数

        Args:
            title: 视频标题，如「GitHub一周热点107期」

        Returns:
            期数，如 107
        """
        # 匹配「热点107期」或「热点 107 期」
        match = re.search(r'热点\s*(\d+)\s*期', title)
        if match:
            return int(match.group(1))

        # 匹配「第107期」
        match = re.search(r'第\s*(\d+)\s*期', title)
        if match:
            return int(match.group(1))

        return None

    async def get_collection_videos(self, video_url: str) -> List[str]:
        """从合集视频页面提取所有视频URL

        通过访问合集中的一个视频页面，提取该合集的所有视频BV号。
        使用标题过滤确保只提取合集内的视频，排除推荐视频等干扰。

        Args:
            video_url: 合集中任意视频的URL

        Returns:
            视频URL列表
        """
        try:
            response = await self.client.get(video_url)
            response.raise_for_status()
            html = response.text

            # 提取包含关键词的视频
            # 使用标题过滤确保只提取合集内的视频
            pattern = r'"bvid":"(BV[a-zA-Z0-9]+)"[^}]*?"title":"([^"]+)"'
            matches = re.findall(pattern, html)

            collection_videos = []
            seen = set()

            for bvid, title in matches:
                # 过滤包含 GitHub/Github/热点 关键词的视频
                if bvid not in seen and ('Github' in title or 'GitHub' in title or '热点' in title):
                    seen.add(bvid)
                    collection_videos.append(bvid)

            # 构造视频URL列表
            video_urls = [f"https://www.bilibili.com/video/{bv}/" for bv in collection_videos]

            log.info(f"从合集页面提取到 {len(video_urls)} 个视频")
            return video_urls

        except Exception as e:
            log.error(f"获取合集视频列表失败: {e}")
            return []

    async def get_video_list_from_page(self, page_url: str) -> List[str]:
        """从视频页面获取合集所有视频URL（兼容旧接口）

        Args:
            page_url: 合集中任意视频的URL

        Returns:
            视频URL列表
        """
        return await self.get_collection_videos(page_url)

    async def get_video_info(self, video_url: str) -> Optional[dict]:
        """获取视频信息

        Args:
            video_url: 视频URL

        Returns:
            视频信息字典
        """
        try:
            response = await self.client.get(video_url)
            response.raise_for_status()
            html = response.text

            # 提取 __INITIAL_STATE__
            match = re.search(r'__INITIAL_STATE__\s*=\s*(\{.+\})\s*;', html, re.DOTALL)
            if not match:
                return None

            data = json.loads(match.group(1))
            video_data = data.get('videoData', {})

            # 提取发布时间
            pubdate = video_data.get('pubdate')
            publish_time = datetime.fromtimestamp(pubdate) if pubdate else None

            return {
                'bvid': video_data.get('bvid'),
                'aid': video_data.get('aid'),
                'title': video_data.get('title'),
                'desc': video_data.get('desc', ''),
                'owner': video_data.get('owner', {}).get('name', 'IT咖啡馆'),
                'publish_time': publish_time,
            }

        except Exception as e:
            log.error(f"获取视频信息失败: {video_url}, {e}")
            return None

    def _parse_project_names(self, description: str) -> List[Tuple[str, Optional[str]]]:
        """从简介中解析项目名称

        简介格式示例:
        1、项目名称：Everything Claude Code – Claude Code完全优化版
        GitHub 链接：https://github.com/xxx
        2、项目名称：promptfoo – AI安全工具

        Args:
            description: 视频简介

        Returns:
            [(项目名称, 项目描述), ...]
        """
        projects = []

        # 模式1: 数字、项目名称：xxx – xxx（支持项目名称含空格）
        # 匹配: 1、项目名称：Everything Claude Code – Claude Code完全优化版
        # 使用 [^–\-—]+ 匹配项目名称（到分隔符为止）
        pattern1 = r'\d+[、.．]\s*项目名称[：:]\s*([^–\-—\n]+?)\s*[–\-—]\s*(.+)'

        matches = re.findall(pattern1, description)
        for name, desc in matches:
            name = name.strip()
            desc = desc.strip()
            if name and len(name) > 1:
                projects.append((name, desc))

        # 如果模式1匹配到了，直接返回
        if projects:
            return projects

        # 模式2: 数字. 名称 – 描述（备用）
        pattern2 = r'\d+[、.．]\s*([^–\-—\n]+?)\s*[–\-—]\s*(.+)'
        matches = re.findall(pattern2, description)
        for name, desc in matches:
            name = name.strip()
            desc = desc.strip()
            # 过滤掉非项目名称
            if name and len(name) > 1 and not name.startswith('http'):
                projects.append((name, desc))

        return projects

    async def crawl_all_videos(self) -> List[VideoProject]:
        """爬取所有视频的项目

        Returns:
            所有项目列表
        """
        log.info("开始爬取所有视频...")

        # 1. 获取视频列表
        video_urls = await self.get_video_list_from_page(self.COLLECTION_URL)

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
                video_info = await self.get_video_info(video_url)
                if not video_info:
                    log.warning(f"获取视频信息失败")
                    continue

                # 解析项目名称
                projects = self._parse_project_names(video_info['desc'])

                # 提取期数
                episode_number = self._extract_episode_number(video_info['title'])

                for name, desc in projects:
                    project = VideoProject(
                        project_name=name,
                        description=desc,
                        bilibili_url=video_url,
                        video_title=video_info['title'],
                        video_publish_time=video_info['publish_time'],
                        episode_number=episode_number,
                        up_name=video_info['owner'],
                    )
                    all_projects.append(project)
                    log.info(f"  找到项目: {name}")

                # 避免请求过快
                await asyncio.sleep(0.5)

            except Exception as e:
                log.error(f"爬取视频失败: {e}")

        log.info(f"爬取完成，共找到 {len(all_projects)} 个项目")
        return all_projects

    async def get_crawled_episodes(self, session: AsyncSession) -> List[int]:
        """获取已爬取的期数列表"""
        result = await session.execute(
            select(ITcoffeeProject.episode_number)
            .distinct()
            .where(ITcoffeeProject.episode_number.isnot(None))
        )
        episodes = [row[0] for row in result.fetchall()]
        return sorted(episodes)

    async def get_max_crawled_episode(self, session: AsyncSession) -> Optional[int]:
        """获取已爬取的最大期数"""
        result = await session.execute(
            select(func.max(ITcoffeeProject.episode_number))
        )
        return result.scalar()

    async def save_projects(self, projects: List[VideoProject]) -> int:
        """保存项目到数据库

        使用 (project_name, bilibili_url) 组合去重
        """
        async with get_session_maker()() as session:
            saved_count = 0

            for project in projects:
                # 检查是否已存在（同一视频中的同名项目）
                result = await session.execute(
                    select(ITcoffeeProject).where(
                        ITcoffeeProject.project_name == project.project_name,
                        ITcoffeeProject.bilibili_url == project.bilibili_url,
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    continue

                # 创建新记录
                db_project = ITcoffeeProject(
                    project_name=project.project_name,
                    description=project.description,
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

    async def get_video_list_with_episodes(self) -> List[Tuple[str, str, Optional[int]]]:
        """获取视频列表及其期数（快速，只获取列表不爬取内容）

        Returns:
            [(视频URL, 视频标题, 期数), ...]
        """
        try:
            response = await self.client.get(self.COLLECTION_URL)
            response.raise_for_status()
            html = response.text

            # 提取视频BV号和标题
            pattern = r'"bvid":"(BV[a-zA-Z0-9]+)"[^}]*?"title":"([^"]+)"'
            matches = re.findall(pattern, html)

            videos = []
            seen = set()

            for bvid, title in matches:
                # 过滤包含 GitHub/Github/热点 关键词的视频
                if bvid not in seen and ('Github' in title or 'GitHub' in title or '热点' in title):
                    seen.add(bvid)
                    episode_number = self._extract_episode_number(title)
                    videos.append((f"https://www.bilibili.com/video/{bvid}/", title, episode_number))

            log.info(f"[IT咖啡馆] 从合集页面提取到 {len(videos)} 个视频")
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

        log.info(f"[IT咖啡馆] 已爬取的最大期数: {max_crawled}")

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
            log.info(f"[IT咖啡馆] 没有发现新视频")
            return [], []

        log.info(f"[IT咖啡馆] 发现 {len(new_videos)} 个新视频，新期数: {new_episodes}")

        # 3. 只爬取新视频
        all_projects = []

        for i, (video_url, video_title, episode_number) in enumerate(new_videos, 1):
            log.info(f"[IT咖啡馆] [{i}/{len(new_videos)}] 爬取: {video_url} (第{episode_number}期)")

            try:
                video_info = await self.get_video_info(video_url)
                if not video_info:
                    log.warning(f"获取视频信息失败")
                    continue

                projects = self._parse_project_names(video_info['desc'])

                for name, desc in projects:
                    project = VideoProject(
                        project_name=name,
                        description=desc,
                        bilibili_url=video_url,
                        video_title=video_info['title'],
                        video_publish_time=video_info['publish_time'],
                        episode_number=episode_number,
                        up_name=video_info['owner'],
                    )
                    all_projects.append(project)
                    log.info(f"  找到项目: {name}")

                await asyncio.sleep(0.5)

            except Exception as e:
                log.error(f"爬取视频失败: {e}")

        log.info(f"[IT咖啡馆] 爬取完成，找到 {len(all_projects)} 个新项目")
        return all_projects, new_episodes

    async def crawl_full(self) -> int:
        """完整爬取（爬取所有视频）"""
        log.info("开始完整爬取...")

        all_projects = await self.crawl_all_videos()

        if not all_projects:
            return 0

        saved_count = await self.save_projects(all_projects)

        log.info(f"完整爬取完成，新增 {saved_count} 个项目")
        return saved_count

    async def get_stats(self) -> dict:
        """获取统计信息"""
        async with get_session_maker()() as session:
            # 总项目数
            total_result = await session.execute(
                select(func.count(ITcoffeeProject.id))
            )
            total = total_result.scalar()

            # 已爬取的期数
            episodes = await self.get_crawled_episodes(session)

            # 最大期数
            max_episode = max(episodes) if episodes else 0

            # 最新爬取时间
            latest_result = await session.execute(
                select(func.max(ITcoffeeProject.crawled_at))
            )
            latest_crawled = latest_result.scalar()

            # URL已验证的项目数
            verified_result = await session.execute(
                select(func.count(ITcoffeeProject.id))
                .where(ITcoffeeProject.url_verified == True)
            )
            verified_count = verified_result.scalar()

            return {
                "total_projects": total,
                "crawled_episodes": len(episodes),
                "max_episode": max_episode,
                "episode_list": episodes,
                "latest_crawled": latest_crawled,
                "verified_count": verified_count,
            }

    async def search_github_repo(self, project_name: str, description: str = None) -> Optional[Dict]:
        """使用 GitHub API 搜索项目

        直接搜索项目名称，按星标排序，取第一个结果。

        Args:
            project_name: 项目名称
            description: 项目描述（未使用，保留兼容性）

        Returns:
            搜索结果字典，包含 url, full_name, stars, description 等
        """
        try:
            # 直接搜索项目名称，按星标排序
            url = f"https://api.github.com/search/repositories?q={project_name}&sort=stars&order=desc&per_page=1"

            headers = {
                'User-Agent': 'GitHub-Project-Recommender/1.0',
                'Accept': 'application/vnd.github.v3+json',
            }

            response = await self.client.get(url, headers=headers, timeout=30.0)

            if response.status_code != 200:
                log.warning(f"GitHub API 返回 {response.status_code}")
                return None

            data = response.json()
            items = data.get('items', [])

            if not items:
                log.warning(f"未找到项目: {project_name}")
                return None

            # 直接取第一个结果（星标最高）
            first_item = items[0]

            return {
                'url': first_item['html_url'],
                'full_name': first_item['full_name'],
                'stars': first_item['stargazers_count'],
                'description': first_item.get('description', ''),
                'language': first_item.get('language', ''),
            }

        except Exception as e:
            log.error(f"GitHub 搜索失败 [{project_name}]: {e}")
            return None

    async def fill_github_urls(self, batch_size: int = 50, max_retries: int = 3) -> Tuple[int, int, List[Dict]]:
        """补全所有未验证项目的 GitHub URL

        Args:
            batch_size: 每批处理的项目数量
            max_retries: 每个项目的最大重试次数

        Returns:
            (成功补全数量, 失败数量, 失败项目列表)
        """
        log.info("开始补全 GitHub URL...")

        success_count = 0
        fail_count = 0
        failed_projects = []  # 记录失败的项目

        async with get_session_maker()() as session:
            # 获取所有未验证的项目
            result = await session.execute(
                select(ITcoffeeProject)
                .where(or_(
                    ITcoffeeProject.github_url.is_(None),
                    ITcoffeeProject.url_verified == False
                ))
                .order_by(ITcoffeeProject.id)
            )
            projects = result.scalars().all()

            total = len(projects)
            log.info(f"找到 {total} 个需要补全 URL 的项目")

            for i, project in enumerate(projects, 1):
                log.info(f"[{i}/{total}] 搜索: {project.project_name}")

                # 重试逻辑
                search_result = None
                for attempt in range(1, max_retries + 1):
                    search_result = await self.search_github_repo(project.project_name, project.description)

                    if search_result:
                        break

                    if attempt < max_retries:
                        log.warning(f"  第 {attempt} 次失败，等待后重试...")
                        await asyncio.sleep(2)  # 重试前等待更长时间

                if search_result:
                    project.github_url = search_result['url']
                    project.url_verified = True
                    success_count += 1
                    log.info(f"  找到: {search_result['full_name']} ({search_result['stars']} stars)")
                else:
                    fail_count += 1
                    # 记录失败项目
                    failed_projects.append({
                        'id': project.id,
                        'project_name': project.project_name,
                        'description': project.description,
                        'episode_number': project.episode_number,
                        'video_title': project.video_title,
                    })
                    log.warning(f"  {max_retries} 次重试后仍未找到")

                # 每处理 batch_size 个提交一次
                if i % batch_size == 0:
                    await session.commit()
                    log.info(f"已提交 {i} 个项目")

                # 避免 GitHub API 限流
                await asyncio.sleep(1)

            # 提交剩余的
            await session.commit()

        log.info(f"URL 补全完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count, fail_count, failed_projects

    async def fill_single_project_url(self, project_id: int) -> bool:
        """补全单个项目的 GitHub URL

        Args:
            project_id: 项目 ID

        Returns:
            是否成功
        """
        async with get_session_maker()() as session:
            result = await session.execute(
                select(ITcoffeeProject).where(ITcoffeeProject.id == project_id)
            )
            project = result.scalar_one_or_none()

            if not project:
                log.error(f"项目不存在: {project_id}")
                return False

            log.info(f"搜索项目: {project.project_name}")

            # 搜索 GitHub
            search_result = await self.search_github_repo(project.project_name, project.description)

            if search_result:
                project.github_url = search_result['url']
                project.url_verified = True
                await session.commit()
                log.info(f"找到: {search_result['full_name']}")
                return True
            else:
                log.warning(f"未找到: {project.project_name}")
                return False

    async def fill_specific_projects(self, project_names: List[str]) -> Tuple[int, int, List[Dict]]:
        """补全指定项目名称的 GitHub URL

        Args:
            project_names: 需要补全的项目名称列表

        Returns:
            (成功补全数量, 失败数量, 失败项目列表)
        """
        log.info(f"开始补全 {len(project_names)} 个指定项目的 URL...")

        success_count = 0
        fail_count = 0
        failed_projects = []

        async with get_session_maker()() as session:
            for name in project_names:
                # 查找项目
                result = await session.execute(
                    select(ITcoffeeProject).where(
                        ITcoffeeProject.project_name == name,
                        or_(
                            ITcoffeeProject.github_url.is_(None),
                            ITcoffeeProject.url_verified == False
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    log.warning(f"项目不存在或已验证: {name}")
                    continue

                log.info(f"搜索项目: {project.project_name} - {project.description}")

                # 搜索 GitHub
                search_result = await self.search_github_repo(project.project_name, project.description)

                if search_result:
                    project.github_url = search_result['url']
                    project.url_verified = True
                    success_count += 1
                    log.info(f"  找到: {search_result['full_name']} ({search_result['stars']} stars)")
                else:
                    fail_count += 1
                    failed_projects.append({
                        'id': project.id,
                        'project_name': project.project_name,
                        'description': project.description,
                        'episode_number': project.episode_number,
                    })
                    log.warning(f"  未找到: {project.project_name}")

                # 避免 GitHub API 限流
                await asyncio.sleep(1.5)

            await session.commit()

        log.info(f"URL 补全完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count, fail_count, failed_projects

    async def get_unverified_projects(self) -> List[Dict]:
        """获取所有未验证URL的项目

        Returns:
            未验证项目列表
        """
        async with get_session_maker()() as session:
            result = await session.execute(
                select(ITcoffeeProject)
                .where(or_(
                    ITcoffeeProject.github_url.is_(None),
                    ITcoffeeProject.url_verified == False
                ))
                .order_by(ITcoffeeProject.episode_number.desc())
            )
            projects = result.scalars().all()

            return [{
                'id': p.id,
                'project_name': p.project_name,
                'description': p.description,
                'episode_number': p.episode_number,
                'video_title': p.video_title,
            } for p in projects]


async def test_service():
    """测试服务"""
    from ..database import init_db
    await init_db()

    service = ITcoffeeService()

    try:
        # 获取统计信息
        stats = await service.get_stats()
        print("当前统计:")
        print(f"  总项目数: {stats['total_projects']}")
        print(f"  已爬取期数: {stats['crawled_episodes']}")
        print(f"  最大期数: {stats['max_episode']}")
        print(f"  已验证URL: {stats['verified_count']}")

        # 爬取一个测试视频
        print("\n测试爬取单个视频...")
        video_info = await service.get_video_info("https://www.bilibili.com/video/BV1ekwfz2EhS")
        if video_info:
            print(f"  标题: {video_info['title']}")
            print(f"  简介: {video_info['desc'][:200]}...")

            projects = service._parse_project_names(video_info['desc'])
            print(f"  解析到 {len(projects)} 个项目:")
            for name, desc in projects:
                print(f"    - {name}: {desc}")

    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(test_service())