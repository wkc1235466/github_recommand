"""AI-powered intelligent search service."""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from ..models.project import Project, SearchCache, CATEGORIES
from ..logger import log


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
    """AI-powered intelligent search service.

    Uses Claude compatible API (httpx) for all AI calls.
    """

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        model: str = "glm-4-flash"
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    async def _call_ai(self, prompt: str, max_tokens: int = 512) -> Optional[str]:
        """Call Claude compatible API.

        Returns the text content from the response, or None on failure.
        """
        if not self.api_key:
            log.warning("AI search: no API key configured")
            return None

        # Ensure URL ends with /v1/messages
        api_url = self.api_url
        if not api_url.endswith('/v1/messages'):
            if api_url.endswith('/'):
                api_url = api_url + 'v1/messages'
            else:
                api_url = api_url + '/v1/messages'

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    api_url,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                )

            if response.status_code != 200:
                log.error(f"AI search API error: HTTP {response.status_code}")
                return None

            response_data = response.json()
            content_blocks = response_data.get("content", [])
            content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")

            return content.strip() if content else None

        except httpx.TimeoutException:
            log.error("AI search request timed out")
            return None
        except Exception as e:
            log.error(f"AI search call failed: {e}")
            return None

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
                cached.hit_count += 1
                cached.updated_at = datetime.utcnow()
                await session.commit()

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

        # If no projects found in detected categories, try keyword fallback
        if not category_projects:
            category_projects = await self._search_by_keywords(query, session)
            log.info(f"Keyword fallback found {len(category_projects)} projects")

        if not category_projects:
            # Last resort: search across all categories
            category_projects = await self._fetch_projects_by_categories(
                [c["id"] for c in CATEGORIES], session, limit=50
            )

        # Stage 2: Rank projects using AI
        ranked_projects = await self._rank_projects(query, category_projects)
        top_projects = ranked_projects[:3]

        # Generate search summary
        search_summary = self._generate_search_summary(
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

        content = await self._call_ai(prompt)
        if content:
            categories = [c.strip() for c in content.split(",") if c.strip()]
            valid_categories = [c["id"] for c in CATEGORIES]
            detected = [c for c in categories if c in valid_categories]
            if detected:
                return detected[:3]

        # Fallback: try keyword matching against category names/descriptions
        query_lower = query.lower()
        keyword_matched = []
        for c in CATEGORIES:
            if c["id"].lower() in query_lower or any(
                kw in query_lower for kw in c["description"].split("、")
            ):
                keyword_matched.append(c["id"])

        if keyword_matched:
            return keyword_matched[:3]

        # Last resort: return all categories so the search is broader
        return [c["id"] for c in CATEGORIES]

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
            ).order_by(Project.id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def _search_by_keywords(
        self,
        query: str,
        session: AsyncSession,
        limit: int = 50
    ) -> List[Project]:
        """Fallback keyword search when category-based search returns nothing."""
        search_term = f"%{query}%"
        result = await session.execute(
            select(Project).where(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term),
                    Project.recommend_reason.ilike(search_term),
                )
            ).order_by(Project.id.desc()).limit(limit)
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

        content = await self._call_ai(prompt)

        if content:
            ranked_ids = []
            for part in content.split(","):
                part = part.strip()
                if part.isdigit():
                    ranked_ids.append(int(part))

            id_to_project = {p.id: p for p in projects}

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

        # Fallback: keyword-based ranking
        log.warning("AI ranking failed, using keyword fallback")
        return self._keyword_rank_projects(query, projects)

    def _keyword_rank_projects(
        self,
        query: str,
        projects: List[Project]
    ) -> List[Project]:
        """Simple keyword-based ranking as fallback."""
        query_lower = query.lower()
        query_words = query_lower.split()

        scored = []
        for p in projects:
            score = 0
            name = (p.name or "").lower()
            desc = (p.description or "").lower()
            reason = (p.recommend_reason or "").lower()
            tags = " ".join(p.get_tags_list() or []).lower()

            for word in query_words:
                if word in name:
                    score += 10
                if word in desc:
                    score += 3
                if word in reason:
                    score += 2
                if word in tags:
                    score += 5

            scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def _generate_search_summary(
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
