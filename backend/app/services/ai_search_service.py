"""AI-powered intelligent search service."""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.project import Project, SearchCache, CATEGORIES
from ..logger import log

settings = get_settings()


class AISearchResult:
    """AI search result model."""

    def __init__(
        self,
        projects: List[Project],
        detected_categories: List[str],
        search_summary: str,
        from_cache: bool = False
    ):
        self.projects = projects
        self.detected_categories = detected_categories
        self.search_summary = search_summary
        self.from_cache = from_cache


class AISearchService:
    """AI-powered intelligent search service."""

    def __init__(self, api_key: Optional[str] = None, model: str = "glm-4-flash"):
        """Initialize the AI search service.

        Args:
            api_key: ZhipuAI API key. If None, reads from settings.
            model: Model to use. Default is glm-4-flash.
        """
        self.api_key = api_key or getattr(settings, 'zhipuai_api_key', None)
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load the ZhipuAI client."""
        if self._client is None:
            try:
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "zhipuai package not installed. "
                    "Install it with: pip install zhipuai"
                )
        return self._client

    async def intelligent_search(
        self,
        query: str,
        session: AsyncSession,
        use_cache: bool = True
    ) -> AISearchResult:
        """Perform AI-powered intelligent search.

        Two-stage search process:
        1. AI detects the most relevant categories (top 3)
        2. AI finds the best matching projects from those categories (top 3)

        Args:
            query: User's search query.
            session: Database session.
            use_cache: Whether to use cached results.

        Returns:
            AISearchResult with matched projects and metadata.
        """
        # Check cache first
        if use_cache:
            cached = await self._get_cached_result(query, session)
            if cached:
                log.info(f"AI search cache hit for query: {query}")
                # Increment hit count
                cached.hit_count += 1
                cached.updated_at = datetime.utcnow()
                await session.commit()

                # Fetch projects
                project_ids = cached.get_matched_project_ids()
                projects = await self._fetch_projects_by_ids(project_ids, session)

                return AISearchResult(
                    projects=projects,
                    detected_categories=cached.get_detected_categories(),
                    search_summary=cached.search_summary or "从缓存获取的结果",
                    from_cache=True
                )

        log.info(f"Performing AI search for query: {query}")

        # Stage 1: Detect relevant categories
        detected_categories = await self._detect_categories(query)
        log.info(f"Detected categories: {detected_categories}")

        # Fetch projects from detected categories
        category_projects = await self._fetch_projects_by_categories(
            detected_categories, session
        )
        log.info(f"Found {len(category_projects)} projects in detected categories")

        if not category_projects:
            # Fallback: search across all categories
            category_projects = await self._fetch_projects_by_categories(
                [c["id"] for c in CATEGORIES], session, limit=50
            )

        # Stage 2: Rank projects using AI
        ranked_projects = await self._rank_projects(query, category_projects)
        top_projects = ranked_projects[:3]

        # Generate search summary
        search_summary = await self._generate_search_summary(
            query, detected_categories, top_projects
        )

        # Cache the results
        await self._cache_result(
            query, detected_categories, top_projects, search_summary, session
        )

        return AISearchResult(
            projects=top_projects,
            detected_categories=detected_categories,
            search_summary=search_summary,
            from_cache=False
        )

    async def _get_cached_result(
        self,
        query: str,
        session: AsyncSession
    ) -> Optional[SearchCache]:
        """Get cached search result if available and recent."""
        # Cache expires after 7 days
        expire_date = datetime.utcnow() - timedelta(days=7)

        result = await session.execute(
            select(SearchCache).where(
                SearchCache.query == query,
                SearchCache.created_at > expire_date
            ).order_by(SearchCache.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def _cache_result(
        self,
        query: str,
        categories: List[str],
        projects: List[Project],
        summary: str,
        session: AsyncSession
    ):
        """Cache search result."""
        cache_entry = SearchCache(
            query=query,
            matched_project_ids=json.dumps([p.id for p in projects]),
            search_summary=summary,
            hit_count=1
        )
        cache_entry.set_detected_categories(categories)

        session.add(cache_entry)
        await session.commit()

    async def _detect_categories(self, query: str) -> List[str]:
        """Use AI to detect the most relevant categories for the query.

        Returns top 3 categories.
        """
        categories_list = [f"{c['id']}: {c['description']}" for c in CATEGORIES]
        categories_str = "\n".join(categories_list)

        prompt = f"""用户搜索查询: "{query}"

请分析这个查询，从以下分类中选择最相关的 3 个分类（按相关性排序）:

{categories_str}

请只返回分类ID，用逗号分隔，不要有其他内容。
例如: AI/机器学习,开发工具,效率工具"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()
            categories = [c.strip() for c in content.split(",") if c.strip()]

            # Validate categories
            valid_categories = [c["id"] for c in CATEGORIES]
            detected = [c for c in categories if c in valid_categories]

            # If none valid, return top 3 categories
            if not detected:
                return [c["id"] for c in CATEGORIES[:3]]

            return detected[:3]

        except Exception as e:
            log.error(f"Error detecting categories: {e}")
            # Fallback to top 3 categories
            return [c["id"] for c in CATEGORIES[:3]]

    async def _fetch_projects_by_categories(
        self,
        categories: List[str],
        session: AsyncSession,
        limit: int = 100
    ) -> List[Project]:
        """Fetch projects from specified categories."""
        result = await session.execute(
            select(Project).where(
                Project.category.in_(categories)
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def _fetch_projects_by_ids(
        self,
        project_ids: List[int],
        session: AsyncSession
    ) -> List[Project]:
        """Fetch projects by IDs."""
        if not project_ids:
            return []

        result = await session.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        return list(result.scalars().all())

    async def _rank_projects(
        self,
        query: str,
        projects: List[Project]
    ) -> List[Project]:
        """Use AI to rank projects by relevance to the query.

        Returns sorted list of projects.
        """
        if not projects:
            return []

        # Prepare project summaries for AI
        project_summaries = []
        for i, p in enumerate(projects):
            summary = f"""
项目 {i+1}:
ID: {p.id}
名称: {p.name}
分类: {p.category or '未分类'}
描述: {p.description or '暂无描述'}
推荐原因: {p.recommend_reason or '暂无'}
AI简介: {p.ai_summary or '暂无'}
标签: {', '.join(p.get_tags_list()) or '无'}
"""
            project_summaries.append(summary)

        projects_text = "\n".join(project_summaries)

        prompt = f"""用户搜索查询: "{query}"

以下是候选项目列表:

{projects_text}

请分析这些项目与用户查询的相关性，返回最相关的 3 个项目ID（按相关性排序）。
只返回项目ID，用逗号分隔，不要有其他内容。
例如: 1,5,3"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()

            # Parse project IDs
            ranked_ids = []
            for part in content.split(","):
                part = part.strip()
                if part.isdigit():
                    ranked_ids.append(int(part))

            # Create ID to project mapping
            id_to_project = {p.id: p for p in projects}

            # Sort projects by AI ranking
            ranked_projects = []
            seen_ids = set()

            for pid in ranked_ids:
                if pid in id_to_project and pid not in seen_ids:
                    ranked_projects.append(id_to_project[pid])
                    seen_ids.add(pid)

            # Add remaining projects not in AI ranking
            for p in projects:
                if p.id not in seen_ids:
                    ranked_projects.append(p)

            return ranked_projects

        except Exception as e:
            log.error(f"Error ranking projects: {e}")
            # Return projects as-is
            return projects

    async def _generate_search_summary(
        self,
        query: str,
        categories: List[str],
        projects: List[Project]
    ) -> str:
        """Generate a human-readable search summary."""
        if not projects:
            return f"未找到与「{query}」相关的项目"

        category_names = "、".join(categories)
        project_names = "、".join([p.name for p in projects])

        return f"根据搜索「{query}」，AI 在「{category_names}」分类中为您找到以下最相关的项目：{project_names}"
