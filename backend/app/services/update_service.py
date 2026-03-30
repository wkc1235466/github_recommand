"""统一更新服务

提供检查新视频、爬取新项目、AI分析并保存到统一 projects 表的功能
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project import Project, ProjectSource
from ..xuanli199.service import Xuanli199Service, VideoProject as XuanliVideoProject
from ..itcoffee.service import ITcoffeeService, VideoProject as ITcoffeeVideoProject
from ..logger import log


@dataclass
class CrawlResult:
    """爬取结果"""
    has_new: bool
    message: str
    xuanli_count: int = 0
    itcoffee_count: int = 0
    total_count: int = 0
    ai_analyzed_count: int = 0
    ai_failed_count: int = 0
    new_episodes: Dict[str, List[int]] = None

    def __post_init__(self):
        if self.new_episodes is None:
            self.new_episodes = {}


class UpdateService:
    """统一更新服务"""

    def __init__(self):
        self.xuanli_service = Xuanli199Service()
        self.itcoffee_service = ITcoffeeService()

    async def close(self):
        """关闭服务"""
        await self.xuanli_service.close()
        await self.itcoffee_service.close()

    async def check_for_new_videos(self) -> Tuple[bool, bool]:
        """检查两个UP主是否有新视频

        Returns:
            (玄离199是否有新视频, IT咖啡馆是否有新视频)
        """
        log.info("开始检查新视频...")

        # 并行获取两个服务的新项目（不保存）
        xuanli_task = self.xuanli_service.fetch_new_projects()
        itcoffee_task = self.itcoffee_service.fetch_new_projects()

        xuanli_result, itcoffee_result = await asyncio.gather(
            xuanli_task, itcoffee_task
        )

        xuanli_projects, xuanli_episodes = xuanli_result
        itcoffee_projects, itcoffee_episodes = itcoffee_result

        xuanli_has_new = len(xuanli_projects) > 0
        itcoffee_has_new = len(itcoffee_projects) > 0

        log.info(f"检查完成: 玄离199 有 {len(xuanli_projects)} 个新项目, IT咖啡馆 有 {len(itcoffee_projects)} 个新项目")

        return xuanli_has_new, itcoffee_has_new, xuanli_projects, itcoffee_projects

    async def analyze_project_with_config(
        self,
        name: str,
        github_url: Optional[str],
        description: Optional[str],
        ai_config: Dict[str, str]
    ) -> Tuple[Optional[str], List[str], Optional[str]]:
        """使用用户配置的 AI 模型分析项目（通过 Claude 兼容 API）

        Args:
            name: 项目名称
            github_url: GitHub URL
            description: 现有描述
            ai_config: AI 配置 (api_url, api_key, model)

        Returns:
            (AI 生成的描述, AI 生成的标签列表, AI 生成的分类)
        """
        api_url = ai_config.get('api_url', '')
        api_key = ai_config.get('api_key', '')
        model = ai_config.get('model', 'glm-4-flash')

        if not api_key:
            log.warning(f"AI 配置不完整，跳过分析: {name}")
            return None, [], None

        try:
            # 确保 URL 以 /v1/messages 结尾
            if not api_url.endswith('/v1/messages'):
                if api_url.endswith('/'):
                    api_url = api_url + 'v1/messages'
                else:
                    api_url = api_url + '/v1/messages'

            # 构建分析 prompt
            prompt = self._build_analysis_prompt(name, github_url, description)

            # 使用 httpx 调用 Claude 兼容 API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    api_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": model,
                        "max_tokens": 1024,
                        "messages": [
                            {"role": "user", "content": self._get_system_prompt() + "\n\n" + prompt}
                        ],
                        "temperature": 0.3,
                    },
                )

            # 解析响应
            response_data = response.json()

            if response.status_code != 200:
                error_msg = response_data.get("error", {})
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get("message", str(response_data))
                log.error(f"AI API 返回错误 [{name}]: HTTP {response.status_code} - {error_msg}")
                return None, [], None

            # 提取 content 文本
            content_blocks = response_data.get("content", [])
            content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")

            if not content:
                log.error(f"AI 返回空内容 [{name}]")
                return None, [], None

            return self._parse_ai_response(content)

        except httpx.TimeoutException:
            log.error(f"AI 分析超时 [{name}]")
            return None, [], None
        except httpx.ConnectError as e:
            log.error(f"AI 连接失败 [{name}]: {e}")
            return None, [], None
        except Exception as e:
            log.error(f"AI 分析异常 [{name}]: {e}")
            return None, [], None

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        from ..models.project import CATEGORIES
        categories = ", ".join([c["id"] for c in CATEGORIES])
        return f"""你是一个GitHub项目分析专家。你的任务是分析GitHub项目并生成简洁的描述和分类。

你需要返回JSON格式的结果，包含以下字段：
- summary: 项目简介（50-100字）
- category: 项目分类，必须是以下之一: {categories}
- tags: 建议的标签（2-3个）

只返回JSON，不要有其他内容。"""

    def _build_analysis_prompt(
        self,
        name: str,
        github_url: Optional[str],
        description: Optional[str]
    ) -> str:
        """构建 AI 分析 prompt"""
        from ..models.project import CATEGORIES

        categories = ", ".join([c["id"] for c in CATEGORIES])

        parts = [
            f"请分析以下 GitHub 项目并返回 JSON 格式的结果：\n",
            f"项目名称: {name}",
        ]

        if github_url:
            parts.append(f"GitHub 地址: {github_url}")

        if description:
            parts.append(f"现有描述: {description}")

        parts.extend([
            "",
            "请返回以下 JSON 格式（只返回 JSON，不要其他内容）：",
            "{",
            '  "summary": "项目简介（50-100字）",',
            f'  "category": "项目分类（必须是以下之一: {categories}）",',
            '  "tags": ["标签1", "标签2", "标签3"]',
            "}"
        ])

        return "\n".join(parts)

    def _parse_ai_response(self, content: str) -> Tuple[Optional[str], List[str], Optional[str]]:
        """解析 AI 响应

        Returns:
            (summary, tags, category)
        """
        from ..models.project import CATEGORIES
        valid_categories = [c["id"] for c in CATEGORIES]

        try:
            # 尝试提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            summary = data.get("summary", "") or None
            tags = data.get("tags", []) or []
            category = data.get("category", "")

            # 校验分类合法性
            if category not in valid_categories:
                category = None

            return summary, tags, category

        except json.JSONDecodeError:
            # 如果解析失败，返回原始内容作为描述
            return content[:200] if content else None, [], None

    def _determine_category(self, ai_category: Optional[str], ai_tags: List[str]) -> str:
        """确定项目分类

        优先使用 AI 返回的 category，其次尝试从 tags 中匹配合法分类，最后回退到"其他"。

        Args:
            ai_category: AI 返回的分类（已通过合法性校验）
            ai_tags: AI 返回的标签列表

        Returns:
            合法的分类字符串
        """
        from ..models.project import CATEGORIES
        valid_categories = [c["id"] for c in CATEGORIES]

        # 优先使用 AI 返回的 category
        if ai_category and ai_category in valid_categories:
            return ai_category

        # 尝试从 tags 中匹配合法分类
        for tag in ai_tags:
            if tag in valid_categories:
                return tag

        return "其他"

    async def save_project_to_db(
        self,
        session: AsyncSession,
        project_data: Dict[str, Any],
        source_info: Optional[Dict[str, Any]] = None
    ) -> Optional[Project]:
        """保存项目到数据库

        Args:
            session: 数据库会话
            project_data: 项目数据
            source_info: 来源信息

        Returns:
            保存的 Project 对象，如果已存在则返回 None
        """
        github_url = project_data.get('github_url')

        # 检查是否已存在（按 GitHub URL 或名称）
        if github_url:
            existing = await session.scalar(
                select(Project).where(Project.github_url == github_url)
            )
            if existing:
                log.debug(f"项目已存在（按 URL）: {github_url}")
                return None

        # 创建新项目
        new_project = Project(
            name=project_data.get('name', ''),
            github_url=github_url,
            description=project_data.get('description'),
            category=project_data.get('category'),
            recommend_reason=project_data.get('recommend_reason'),
            stars=project_data.get('stars'),
        )

        # 设置 AI 生成的标签
        tags = project_data.get('tags', [])
        if tags:
            new_project.set_tags_list(tags[:3])  # 最多 3 个标签

        session.add(new_project)
        await session.flush()  # 获取 ID

        # 添加来源信息
        if source_info:
            source = ProjectSource(
                project_id=new_project.id,
                bilibili_url=source_info.get('bilibili_url'),
                up_name=source_info.get('up_name'),
                video_title=source_info.get('video_title'),
                publish_date=source_info.get('publish_date'),
            )
            session.add(source)

        return new_project

    async def crawl_and_save(
        self,
        session: AsyncSession,
        ai_config: Dict[str, str]
    ) -> CrawlResult:
        """爬取新项目并保存到 projects 表

        Args:
            session: 数据库会话
            ai_config: AI 配置 (api_url, api_key, model)

        Returns:
            CrawlResult: 爬取结果
        """
        log.info("开始爬取并保存新项目...")

        # 1. 检查并获取新项目
        xuanli_has_new, itcoffee_has_new, xuanli_projects, itcoffee_projects = \
            await self.check_for_new_videos()

        if not xuanli_has_new and not itcoffee_has_new:
            return CrawlResult(
                has_new=False,
                message="数据已是最新的，没有发现新视频"
            )

        # 2. 处理玄离199的项目
        xuanli_count = 0
        ai_analyzed = 0
        ai_failed = 0
        new_episodes = {}

        for project in xuanli_projects:
            # AI 分析
            ai_summary, ai_tags, ai_category = await self.analyze_project_with_config(
                name=project.project_name,
                github_url=project.github_url,
                description=None,
                ai_config=ai_config
            )

            if ai_summary or ai_tags:
                ai_analyzed += 1
            else:
                ai_failed += 1

            # 确定分类：优先使用 AI 返回的 category
            category = self._determine_category(ai_category, ai_tags)

            # 保存到数据库
            saved = await self.save_project_to_db(
                session,
                project_data={
                    'name': project.project_name,
                    'github_url': project.github_url,
                    'description': ai_summary,
                    'category': category,
                    'tags': ai_tags,
                },
                source_info={
                    'bilibili_url': project.bilibili_url,
                    'up_name': project.up_name,
                    'video_title': project.video_title,
                    'publish_date': project.video_publish_time.isoformat() if project.video_publish_time else None,
                }
            )

            if saved:
                xuanli_count += 1

        if xuanli_projects:
            new_episodes['xuanli199'] = sorted(set(
                p.episode_number for p in xuanli_projects if p.episode_number
            ))

        # 3. 处理 IT咖啡馆的项目
        itcoffee_count = 0

        for project in itcoffee_projects:
            # IT 咖啡馆没有直接的 GitHub URL，需要搜索
            # 先用 AI 分析
            ai_summary, ai_tags, ai_category = await self.analyze_project_with_config(
                name=project.project_name,
                github_url=None,
                description=project.description,
                ai_config=ai_config
            )

            if ai_summary or ai_tags:
                ai_analyzed += 1
            else:
                ai_failed += 1

            # 确定分类：优先使用 AI 返回的 category
            category = self._determine_category(ai_category, ai_tags)

            # 尝试搜索 GitHub URL
            github_url = None
            try:
                search_result = await self.itcoffee_service.search_github_repo(
                    project.project_name,
                    project.description
                )
                if search_result:
                    github_url = search_result.get('url')
            except Exception as e:
                log.warning(f"搜索 GitHub URL 失败 [{project.project_name}]: {e}")

            # 保存到数据库
            saved = await self.save_project_to_db(
                session,
                project_data={
                    'name': project.project_name,
                    'github_url': github_url,
                    'description': ai_summary or project.description,
                    'category': category,
                    'tags': ai_tags,
                    'needs_url': github_url is None,  # 没有 URL 标记为需要补全
                },
                source_info={
                    'bilibili_url': project.bilibili_url,
                    'up_name': project.up_name,
                    'video_title': project.video_title,
                    'publish_date': project.video_publish_time.isoformat() if project.video_publish_time else None,
                }
            )

            if saved:
                itcoffee_count += 1

        if itcoffee_projects:
            new_episodes['itcoffee'] = sorted(set(
                p.episode_number for p in itcoffee_projects if p.episode_number
            ))

        # 提交事务
        await session.commit()

        total_count = xuanli_count + itcoffee_count

        # 构建消息
        message_parts = []
        if xuanli_count > 0:
            message_parts.append(f"玄离199 新增 {xuanli_count} 个项目")
        if itcoffee_count > 0:
            message_parts.append(f"IT咖啡馆 新增 {itcoffee_count} 个项目")

        message = "，".join(message_parts) if message_parts else "没有新增项目"
        if ai_analyzed > 0:
            message += f"，AI 分析成功 {ai_analyzed} 个"
        if ai_failed > 0:
            message += f"，AI 分析失败 {ai_failed} 个"

        log.info(f"爬取完成: {message}")

        return CrawlResult(
            has_new=True,
            message=message,
            xuanli_count=xuanli_count,
            itcoffee_count=itcoffee_count,
            total_count=total_count,
            ai_analyzed_count=ai_analyzed,
            ai_failed_count=ai_failed,
            new_episodes=new_episodes
        )