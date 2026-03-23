"""ITcoffee API 路由

提供增量更新、完整爬取、统计信息等接口
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models.itcoffee import ITcoffeeProject
from ..itcoffee import ITcoffeeService
from ..logger import log

router = APIRouter(prefix="/itcoffee", tags=["ITcoffee"])


# ========== Pydantic Schemas ==========

class ITcoffeeProjectResponse(BaseModel):
    """项目响应模型"""
    id: int
    project_name: str
    description: Optional[str]
    github_url: Optional[str]
    bilibili_url: str
    video_title: Optional[str]
    video_publish_time: Optional[datetime]
    episode_number: Optional[int]
    up_name: str
    url_verified: bool
    crawled_at: datetime

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """统计信息响应"""
    total_projects: int
    crawled_episodes: int
    max_episode: int
    episode_list: List[int]
    latest_crawled: Optional[datetime]
    verified_count: int


class UpdateResponse(BaseModel):
    """更新响应"""
    success: bool
    message: str
    new_projects: int
    new_episodes: List[int] = []


class CrawlStatus(BaseModel):
    """爬取状态"""
    is_crawling: bool
    last_update: Optional[datetime]
    message: str = ""


class UrlFillResponse(BaseModel):
    """URL 补全响应"""
    success: bool
    message: str
    filled_count: int = 0
    failed_count: int = 0


# ========== 全局状态 ==========

_crawling_status = {"is_crawling": False, "message": "", "last_update": None}
_url_fill_status = {"is_filling": False, "message": "", "last_update": None}


# ========== API Endpoints ==========

@router.get("/stats", response_model=StatsResponse)
async def get_stats(session: AsyncSession = Depends(get_session)):
    """获取统计信息"""
    # 总项目数
    result = await session.execute(
        select(func.count(ITcoffeeProject.id))
    )
    total = result.scalar()

    # 已爬取的期数
    result = await session.execute(
        select(ITcoffeeProject.episode_number)
        .distinct()
        .where(ITcoffeeProject.episode_number.isnot(None))
    )
    episodes = sorted([row[0] for row in result.fetchall()])

    # 最大期数
    max_episode = max(episodes) if episodes else 0

    # 最新爬取时间
    result = await session.execute(
        select(func.max(ITcoffeeProject.crawled_at))
    )
    latest_crawled = result.scalar()

    # URL已验证的项目数
    result = await session.execute(
        select(func.count(ITcoffeeProject.id))
        .where(ITcoffeeProject.url_verified == True)
    )
    verified_count = result.scalar()

    return StatsResponse(
        total_projects=total or 0,
        crawled_episodes=len(episodes),
        max_episode=max_episode,
        episode_list=episodes,
        latest_crawled=latest_crawled,
        verified_count=verified_count or 0,
    )


@router.get("/projects", response_model=List[ITcoffeeProjectResponse])
async def list_projects(
    episode: Optional[int] = None,
    needs_url: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """获取项目列表

    Args:
        episode: 指定期数筛选
        needs_url: 筛选需要补全URL的项目
        limit: 每页数量
        offset: 偏移量
    """
    query = select(ITcoffeeProject).order_by(desc(ITcoffeeProject.episode_number))

    if episode:
        query = query.where(ITcoffeeProject.episode_number == episode)

    if needs_url is not None:
        if needs_url:
            query = query.where(
                (ITcoffeeProject.github_url.is_(None)) |
                (ITcoffeeProject.url_verified == False)
            )
        else:
            query = query.where(ITcoffeeProject.url_verified == True)

    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    projects = result.scalars().all()

    return [ITcoffeeProjectResponse.model_validate(p) for p in projects]


@router.get("/status", response_model=CrawlStatus)
async def get_crawl_status():
    """获取爬取状态"""
    return CrawlStatus(
        is_crawling=_crawling_status["is_crawling"],
        last_update=_crawling_status.get("last_update"),
        message=_crawling_status.get("message", ""),
    )


async def run_crawl_update():
    """后台任务：增量更新"""
    global _crawling_status

    _crawling_status["is_crawling"] = True
    _crawling_status["message"] = "正在爬取..."

    service = ITcoffeeService()

    try:
        saved_count, new_episodes = await service.crawl_new_episodes()

        _crawling_status["message"] = f"爬取完成，新增 {saved_count} 个项目"
        _crawling_status["last_update"] = datetime.utcnow()

        log.info(f"增量更新完成: 新增 {saved_count} 个项目, 新期数 {new_episodes}")

    except Exception as e:
        _crawling_status["message"] = f"爬取失败: {str(e)}"
        log.error(f"增量更新失败: {e}")

    finally:
        _crawling_status["is_crawling"] = False
        await service.close()


@router.post("/update", response_model=UpdateResponse)
async def trigger_update(background_tasks: BackgroundTasks):
    """触发增量更新"""
    if _crawling_status["is_crawling"]:
        return UpdateResponse(
            success=False,
            message="正在爬取中，请稍后再试",
            new_projects=0,
        )

    background_tasks.add_task(run_crawl_update)

    return UpdateResponse(
        success=True,
        message="已开始增量更新",
        new_projects=0,
    )


async def run_full_crawl():
    """后台任务：完整爬取"""
    global _crawling_status

    _crawling_status["is_crawling"] = True
    _crawling_status["message"] = "正在完整爬取所有视频..."

    service = ITcoffeeService()

    try:
        saved_count = await service.crawl_full()

        _crawling_status["message"] = f"完整爬取完成，新增 {saved_count} 个项目"
        _crawling_status["last_update"] = datetime.utcnow()

        log.info(f"完整爬取完成: 新增 {saved_count} 个项目")

    except Exception as e:
        _crawling_status["message"] = f"爬取失败: {str(e)}"
        log.error(f"完整爬取失败: {e}")

    finally:
        _crawling_status["is_crawling"] = False
        await service.close()


@router.post("/crawl-full", response_model=UpdateResponse)
async def trigger_full_crawl(background_tasks: BackgroundTasks):
    """触发完整爬取"""
    if _crawling_status["is_crawling"]:
        return UpdateResponse(
            success=False,
            message="正在爬取中，请稍后再试",
            new_projects=0,
        )

    background_tasks.add_task(run_full_crawl)

    return UpdateResponse(
        success=True,
        message="已开始完整爬取，这可能需要几分钟",
        new_projects=0,
    )


@router.patch("/projects/{project_id}/url")
async def update_project_url(
    project_id: int,
    github_url: str,
    session: AsyncSession = Depends(get_session),
):
    """更新项目的GitHub URL（AI补全后使用）"""
    result = await session.execute(
        select(ITcoffeeProject).where(ITcoffeeProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.github_url = github_url
    project.url_verified = True
    await session.commit()

    return {"success": True, "message": "URL已更新"}


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """删除单个项目"""
    result = await session.execute(
        select(ITcoffeeProject).where(ITcoffeeProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await session.delete(project)
    await session.commit()

    return {"success": True, "message": "删除成功"}


# ========== GitHub URL 补全接口 ==========

@router.get("/url-fill/status")
async def get_url_fill_status():
    """获取 URL 补全状态"""
    return {
        "is_filling": _url_fill_status["is_filling"],
        "message": _url_fill_status.get("message", ""),
        "last_update": _url_fill_status.get("last_update"),
    }


async def run_url_fill():
    """后台任务：补全所有项目的 GitHub URL"""
    global _url_fill_status

    _url_fill_status["is_filling"] = True
    _url_fill_status["message"] = "正在补全 GitHub URL..."

    service = ITcoffeeService()

    try:
        success_count, fail_count = await service.fill_github_urls()

        _url_fill_status["message"] = f"补全完成: 成功 {success_count}, 失败 {fail_count}"
        _url_fill_status["last_update"] = datetime.utcnow()

        log.info(f"URL 补全完成: 成功 {success_count}, 失败 {fail_count}")

    except Exception as e:
        _url_fill_status["message"] = f"补全失败: {str(e)}"
        log.error(f"URL 补全失败: {e}")

    finally:
        _url_fill_status["is_filling"] = False
        await service.close()


@router.post("/url-fill", response_model=UrlFillResponse)
async def trigger_url_fill(background_tasks: BackgroundTasks):
    """触发批量补全 GitHub URL

    使用 GitHub API 搜索所有未验证的项目，自动补全 URL
    """
    if _url_fill_status["is_filling"]:
        return UrlFillResponse(
            success=False,
            message="正在补全中，请稍后再试",
        )

    if _crawling_status["is_crawling"]:
        return UrlFillResponse(
            success=False,
            message="正在爬取中，请稍后再试",
        )

    background_tasks.add_task(run_url_fill)

    return UrlFillResponse(
        success=True,
        message="已开始批量补全 GitHub URL",
    )


@router.post("/projects/{project_id}/fill-url", response_model=UrlFillResponse)
async def fill_single_url(project_id: int):
    """补全单个项目的 GitHub URL

    使用 GitHub API 搜索指定项目并补全 URL
    """
    if _url_fill_status["is_filling"]:
        return UrlFillResponse(
            success=False,
            message="正在批量补全中，请稍后再试",
        )

    service = ITcoffeeService()

    try:
        success = await service.fill_single_project_url(project_id)

        if success:
            return UrlFillResponse(
                success=True,
                message="URL 补全成功",
                filled_count=1,
            )
        else:
            return UrlFillResponse(
                success=False,
                message="未找到对应的 GitHub 项目",
                failed_count=1,
            )

    finally:
        await service.close()


class SpecificProjectsRequest(BaseModel):
    """指定项目名称请求"""
    project_names: List[str]


@router.get("/projects/unverified")
async def get_unverified_projects():
    """获取所有未验证URL的项目列表"""
    service = ITcoffeeService()

    try:
        projects = await service.get_unverified_projects()
        return {"count": len(projects), "projects": projects}
    finally:
        await service.close()


@router.post("/url-fill/specific")
async def fill_specific_projects(
    request: SpecificProjectsRequest,
    background_tasks: BackgroundTasks,
):
    """补全指定项目的 GitHub URL

    Args:
        request: 包含 project_names 列表的请求体
    """
    if _url_fill_status["is_filling"]:
        return {
            "success": False,
            "message": "正在批量补全中，请稍后再试",
        }

    async def run_specific_fill():
        global _url_fill_status

        _url_fill_status["is_filling"] = True
        _url_fill_status["message"] = f"正在补全 {len(request.project_names)} 个指定项目..."

        service = ITcoffeeService()

        try:
            success_count, fail_count, failed = await service.fill_specific_projects(request.project_names)

            _url_fill_status["message"] = f"补全完成: 成功 {success_count}, 失败 {fail_count}"
            _url_fill_status["last_update"] = datetime.utcnow()

        except Exception as e:
            _url_fill_status["message"] = f"补全失败: {str(e)}"
            log.error(f"指定项目 URL 补全失败: {e}")

        finally:
            _url_fill_status["is_filling"] = False
            await service.close()

    background_tasks.add_task(run_specific_fill)

    return {
        "success": True,
        "message": f"已开始补全 {len(request.project_names)} 个指定项目",
    }