"""Project API routes using SQLAlchemy."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session, init_db
from ..models.project import Project, ProjectSource, CATEGORIES
from ..schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    AnalyzeRequest,
    AnalyzeResult,
    CategoryResponse,
    ReadmeResponse,
    SourceInfoSchema,
    AIAnalysisSchema,
    TestModelRequest,
    TestModelResponse,
    AISearchRequest,
    AISearchResponse,
    UnanalyzedProjectsResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
)
from ..services.ai_analyzer import AIAnalyzer
from ..services.github_service import get_readme
from ..services.update_service import UpdateService
from ..services.ai_search_service import AISearchService
from ..logger import log
from ..scripts.migrate_projects import run_migration

router = APIRouter(prefix="/projects", tags=["projects"])


class CrawlRequest(BaseModel):
    """爬取请求"""
    api_url: str
    api_key: str
    model: str


class CrawlResponse(BaseModel):
    """爬取响应"""
    success: bool
    message: str
    has_new: bool = False
    xuanli_count: int = 0
    itcoffee_count: int = 0
    total_count: int = 0
    ai_analyzed_count: int = 0
    ai_failed_count: int = 0
    new_episodes: dict = {}


def project_to_response(project: Project) -> dict:
    """Convert Project model to response dict."""
    sources = [
        SourceInfoSchema(
            bilibili_url=s.bilibili_url,
            up_name=s.up_name,
            video_title=s.video_title,
            publish_date=s.publish_date,
        )
        for s in project.sources
    ]

    ai_analysis = None
    if project.ai_summary or project.ai_tags:
        ai_analysis = AIAnalysisSchema(
            summary=project.ai_summary,
            suggested_tags=project.get_ai_tags_list(),
            confidence=project.ai_confidence,
            analyzed_at=project.ai_analyzed_at,
        )

    return {
        "_id": str(project.id),
        "name": project.name,
        "github_url": project.github_url,
        "description": project.description,
        "category": project.category,
        "ai_analysis": ai_analysis,
        "recommend_reason": project.recommend_reason,
        "sources": sources if sources else None,
        "tags": project.get_tags_list(),
        "user_tags": project.get_user_tags_list(),
        "stars": project.stars,
        "needs_url": project.needs_url,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    needs_url: Optional[bool] = Query(None, description="Filter projects that need URL"),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated list of projects."""
    # Build query
    query = select(Project)

    if category:
        query = query.where(Project.category == category)
    if needs_url is not None:
        query = query.where(Project.needs_url == needs_url)
    if tag:
        # Search in both AI tags and user tags (JSON arrays)
        tag_pattern = f'%"{tag}"%'
        query = query.where(
            or_(
                Project.tags.ilike(tag_pattern),
                Project.user_tags.ilike(tag_pattern),
            )
        )
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Project.name.ilike(search_term),
                Project.description.ilike(search_term),
                Project.recommend_reason.ilike(search_term),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get paginated results
    query = query.order_by(Project.created_at.desc())
    query = query.options(selectinload(Project.sources))  # 预加载 sources 关系
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    projects = result.scalars().all()

    # Convert to response
    projects_data = [project_to_response(p) for p in projects]

    return ProjectListResponse(
        projects=projects_data,
        total=total or 0,
        page=page,
        page_size=page_size,
        has_more=((page - 1) * page_size + len(projects)) < (total or 0),
    )


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(session: AsyncSession = Depends(get_session)):
    """Get list of all categories with counts."""
    categories = []
    for cat in CATEGORIES:
        count = await session.scalar(
            select(func.count()).where(Project.category == cat["id"])
        )
        categories.append(CategoryResponse(
            id=cat["id"],
            name=cat["name"],
            description=cat["description"],
            count=count or 0
        ))

    return categories


@router.post("/test-model", response_model=TestModelResponse)
async def test_model_connection(request: TestModelRequest):
    """测试 AI 模型连接（只支持 Claude 兼容 API）"""
    from ..services.ai_provider_service import AIProviderService, AIProviderConfig, AIProviderType

    log.info(f"测试模型连接: api_url={request.api_url}, model={request.model}, api_type={request.api_type}")

    # 验证 API 类型
    if request.api_type != "claude":
        return TestModelResponse(
            success=False,
            message=f"不支持的 API 类型: {request.api_type}，当前只支持 Claude 兼容 API"
        )

    # 构建配置
    config = AIProviderConfig(
        api_url=request.api_url,
        api_key=request.api_key,
        model=request.model,
        provider_type=AIProviderType.CLAUDE
    )

    # 执行测试
    service = AIProviderService()
    result = await service.test_connection(config)

    log.info(f"测试结果: success={result.success}, message={result.message}")

    return TestModelResponse(
        success=result.success,
        message=result.message,
        details=result.details,
        response_time_ms=result.response_time_ms
    )


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_new_projects(
    request: CrawlRequest,
    session: AsyncSession = Depends(get_session),
):
    """检查并更新新项目

    检查玄离199和IT咖啡馆是否有新视频，如有则爬取并保存到统一的 projects 表。
    使用用户配置的 AI 模型进行分析。
    """
    log.info(f"收到爬取请求: model={request.model}")

    ai_config = {
        'api_url': request.api_url,
        'api_key': request.api_key,
        'model': request.model,
    }

    update_service = UpdateService()

    try:
        result = await update_service.crawl_and_save(session, ai_config)

        return CrawlResponse(
            success=True,
            message=result.message,
            has_new=result.has_new,
            xuanli_count=result.xuanli_count,
            itcoffee_count=result.itcoffee_count,
            total_count=result.total_count,
            ai_analyzed_count=result.ai_analyzed_count,
            ai_failed_count=result.ai_failed_count,
            new_episodes=result.new_episodes,
        )
    except Exception as e:
        log.error(f"爬取失败: {e}")
        return CrawlResponse(
            success=False,
            message=f"爬取失败: {str(e)}",
        )
    finally:
        await update_service.close()


@router.get("/unanalyzed", response_model=UnanalyzedProjectsResponse)
async def get_unanalyzed_projects(
    limit: int = Query(50, ge=1, le=100, description="返回项目数量"),
    session: AsyncSession = Depends(get_session),
):
    """获取未分析的项目列表

    返回描述为空或"暂无描述"的项目列表。
    """
    # 查询未分析的项目（描述为空或"暂无描述"）
    result = await session.execute(
        select(Project)
        .where(
            or_(
                Project.description.is_(None),
                Project.description == "",
                Project.description == "暂无描述",
            )
        )
        .options(selectinload(Project.sources))
        .order_by(Project.id.desc())
        .limit(limit)
    )
    projects = result.scalars().all()

    # 获取总数
    count_result = await session.execute(
        select(func.count(Project.id)).where(
            or_(
                Project.description.is_(None),
                Project.description == "",
                Project.description == "暂无描述",
            )
        )
    )
    total = count_result.scalar()

    projects_data = [project_to_response(p) for p in projects]

    return UnanalyzedProjectsResponse(
        projects=projects_data,
        total=total
    )


@router.post("/batch-analyze", response_model=BatchAnalyzeResponse)
async def batch_analyze_projects(
    request: BatchAnalyzeRequest,
    session: AsyncSession = Depends(get_session),
):
    """批量分析未分析的项目

    使用 AI 为描述为空的项目生成描述和分类。
    """
    # 获取 AI 配置（优先使用请求中的配置）
    api_key = request.api_key
    model = request.model or "glm-4-flash"

    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 AI API Key，请先在设置中配置")

    # 查询未分析的项目
    if request.project_ids:
        result = await session.execute(
            select(Project)
            .where(Project.id.in_(request.project_ids))
            .options(selectinload(Project.sources))
            .limit(request.limit)
        )
    else:
        result = await session.execute(
            select(Project)
            .where(
                or_(
                    Project.description.is_(None),
                    Project.description == "",
                    Project.description == "暂无描述",
                )
            )
            .options(selectinload(Project.sources))
            .order_by(Project.id.asc())
            .limit(request.limit)
        )

    projects = result.scalars().all()

    if not projects:
        return BatchAnalyzeResponse(
            success=True,
            message="没有需要分析的项目",
            total=0,
            analyzed=0,
            success_count=0,
            failed_count=0
        )

    update_service = UpdateService()
    ai_config = {
        'api_url': request.api_url,
        'api_key': api_key,
        'model': model
    }

    success_count = 0
    failed_count = 0
    failed_projects = []

    for project in projects:
        try:
            log.info(f"正在分析项目: {project.name}")

            ai_summary, ai_tags, ai_category = await update_service.analyze_project_with_config(
                name=project.name,
                github_url=project.github_url,
                description=None,
                ai_config=ai_config
            )

            if ai_summary or ai_tags:
                project.description = ai_summary
                if ai_tags:
                    project.set_tags_list(ai_tags[:3])
                project.category = update_service._determine_category(ai_category, ai_tags)

                success_count += 1
                log.info(f"项目分析成功: {project.name}")
            else:
                failed_count += 1
                failed_projects.append({
                    "id": project.id,
                    "name": project.name,
                    "reason": "AI 返回空结果"
                })

        except Exception as e:
            failed_count += 1
            failed_projects.append({
                "id": project.id,
                "name": project.name,
                "reason": str(e)
            })
            log.error(f"项目分析异常: {project.name}, {e}")

    await session.commit()

    message = f"批量分析完成：成功 {success_count} 个，失败 {failed_count} 个"

    return BatchAnalyzeResponse(
        success=True,
        message=message,
        total=len(projects),
        analyzed=len(projects),
        success_count=success_count,
        failed_count=failed_count,
        failed_projects=failed_projects
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single project by ID."""
    # 使用 selectinload 预加载 sources 关系，避免异步上下文中的延迟加载问题
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.sources))
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project_to_response(project)


@router.get("/{project_id}/readme", response_model=ReadmeResponse)
async def get_project_readme(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get README content for a project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    github_url = project.github_url
    if not github_url:
        raise HTTPException(status_code=400, detail="Project has no GitHub URL")

    # Check if we have cached README
    if project.readme_cache:
        return ReadmeResponse(
            project_id=str(project_id),
            name=project.name,
            readme=project.readme_cache,
            github_url=github_url
        )

    # Fetch README from GitHub
    try:
        readme = await get_readme(github_url)
        if readme:
            project.readme_cache = readme
            project.updated_at = datetime.utcnow()
            await session.commit()
        return ReadmeResponse(
            project_id=str(project_id),
            name=project.name,
            readme=readme,
            github_url=github_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch README: {str(e)}")


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new project manually."""
    # Check if project with same GitHub URL already exists
    if project.github_url:
        existing = await session.scalar(
            select(Project).where(Project.github_url == project.github_url)
        )
        if existing:
            raise HTTPException(status_code=409, detail="Project with this GitHub URL already exists")

    # Check if project with same name already exists
    existing = await session.scalar(
        select(Project).where(Project.name == project.name)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Project with this name already exists")

    # Create project
    new_project = Project(
        name=project.name,
        github_url=project.github_url,
        description=project.description,
        category=project.category,
        recommend_reason=project.recommend_reason,
        stars=project.stars,
        needs_url=project.needs_url,
    )
    new_project.set_tags_list(project.tags)

    # Add source if provided
    if project.source:
        source = ProjectSource(
            bilibili_url=project.source.bilibili_url,
            up_name=project.source.up_name,
            video_title=project.source.video_title,
            publish_date=project.source.publish_date,
        )
        new_project.sources.append(source)

    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)

    return project_to_response(new_project)


@router.post("/{project_id}/analyze", response_model=AnalyzeResult)
async def analyze_project(
    project_id: int,
    request: AnalyzeRequest = AnalyzeRequest(),
    session: AsyncSession = Depends(get_session),
):
    """Trigger AI analysis for a project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already analyzed
    if project.ai_summary and not request.force:
        return AnalyzeResult(
            success=True,
            message="Project already analyzed. Use force=true to re-analyze.",
            project_id=str(project_id),
            category=project.category,
            summary=project.ai_summary
        )

    try:
        analyzer = AIAnalyzer()
        analysis = await analyzer.analyze_project(
            name=project.name,
            github_url=project.github_url,
            existing_description=project.description
        )

        # Update project
        project.ai_summary = analysis.summary
        project.set_ai_tags_list(analysis.suggested_tags)
        project.ai_confidence = analysis.confidence
        project.ai_analyzed_at = analysis.analyzed_at
        project.category = analysis.suggested_tags[0] if analysis.suggested_tags else "其他工具"
        project.updated_at = datetime.utcnow()

        await session.commit()

        return AnalyzeResult(
            success=True,
            message="Analysis completed successfully",
            project_id=str(project_id),
            category=project.category,
            summary=analysis.summary
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a project by ID."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await session.delete(project)
    await session.commit()

    return None


@router.post("/migrate-all")
async def migrate_all_projects():
    """
    迁移所有项目到统一表

    将 IT咖啡馆 和 玄离199 的项目迁移到统一的 projects 表。
    相同 GitHub URL 的项目会合并来源信息。
    """
    log.info("收到迁移请求")

    result = await run_migration()

    return {
        "success": result.success,
        "message": result.message,
        "stats": result.stats
    }


# 用户标签相关API
class UserTagsRequest(BaseModel):
    """用户标签请求"""
    tags: List[str]


@router.get("/{project_id}/user-tags")
async def get_user_tags(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """获取项目的用户标签"""
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.sources))
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"tags": project.get_user_tags_list()}


@router.post("/{project_id}/user-tags")
async def add_user_tag(
    project_id: int,
    request: UserTagsRequest,
    session: AsyncSession = Depends(get_session),
):
    """添加用户标签（追加）"""
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.sources))
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 获取现有标签
    current_tags = project.get_user_tags_list()

    # 添加新标签（去重）
    for tag in request.tags:
        if tag and tag not in current_tags:
            current_tags.append(tag)

    project.set_user_tags_list(current_tags)
    project.updated_at = datetime.utcnow()
    await session.commit()

    return {"success": True, "tags": current_tags}


@router.put("/{project_id}/user-tags")
async def set_user_tags(
    project_id: int,
    request: UserTagsRequest,
    session: AsyncSession = Depends(get_session),
):
    """设置用户标签（覆盖）"""
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.sources))
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.set_user_tags_list(request.tags)
    project.updated_at = datetime.utcnow()
    await session.commit()

    return {"success": True, "tags": request.tags}


@router.delete("/{project_id}/user-tags/{tag}")
async def remove_user_tag(
    project_id: int,
    tag: str,
    session: AsyncSession = Depends(get_session),
):
    """删除单个用户标签"""
    query = select(Project).where(Project.id == project_id).options(selectinload(Project.sources))
    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    current_tags = project.get_user_tags_list()
    if tag in current_tags:
        current_tags.remove(tag)
        project.set_user_tags_list(current_tags)
        project.updated_at = datetime.utcnow()
        await session.commit()

    return {"success": True, "tags": current_tags}


@router.get("/tags/popular")
async def get_popular_tags(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """获取热门标签"""
    from collections import Counter

    # 获取所有项目的标签
    result = await session.execute(select(Project.tags, Project.user_tags))
    rows = result.all()

    tag_counter = Counter()

    for tags, user_tags in rows:
        if tags:
            try:
                import json
                tag_list = json.loads(tags)
                tag_counter.update(tag_list)
            except:
                pass
        if user_tags:
            try:
                import json
                tag_list = json.loads(user_tags)
                tag_counter.update(tag_list)
            except:
                pass

    popular = tag_counter.most_common(limit)

    return {"tags": [{"name": tag, "count": count} for tag, count in popular]}


@router.post("/ai-search", response_model=AISearchResponse)
async def ai_search(
    request: AISearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """AI 智能搜索

    使用 AI 进行两阶段搜索：
    1. 识别最相关的 3 个分类
    2. 在这些分类中找到最匹配的 3 个项目

    支持缓存以提高响应速度。
    """
    try:
        search_service = AISearchService(
            api_url=request.api_url,
            api_key=request.api_key or "",
            model=request.model,
        )
        result = await search_service.intelligent_search(
            query=request.query,
            session=session,
            use_cache=request.use_cache
        )

        # Preload sources for all projects
        for project in result.projects:
            await session.refresh(project, attribute_names=['sources'])

        projects_data = [project_to_response(p) for p in result.projects]

        return AISearchResponse(
            query=request.query,
            projects=projects_data,
            detected_categories=result.detected_categories,
            search_summary=result.search_summary,
            from_cache=result.from_cache,
            total_matches=len(result.projects)
        )

    except Exception as e:
        log.error(f"AI search failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI 搜索失败: {str(e)}")