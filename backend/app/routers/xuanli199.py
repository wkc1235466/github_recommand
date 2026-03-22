"""玄离199 API 路由

提供增量更新、完整爬取、统计信息等接口
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models.xuanli199 import Xuanli199Project
from ..xuanli199 import Xuanli199Service
from ..logger import log

router = APIRouter(prefix="/xuanli199", tags=["玄离199"])


# ========== Pydantic Schemas ==========

class Xuanli199ProjectResponse(BaseModel):
    """项目响应模型"""
    id: int
    github_url: str
    project_name: str
    bilibili_url: str
    video_title: Optional[str]
    video_publish_time: Optional[datetime]
    episode_number: Optional[int]
    up_name: str
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


# ========== 全局状态 ==========

_crawling_status = {"is_crawling": False, "message": "", "last_update": None}


# ========== API Endpoints ==========

@router.get("/stats", response_model=StatsResponse)
async def get_stats(session: AsyncSession = Depends(get_session)):
    """获取统计信息

    Returns:
        总项目数、已爬取期数、最大期数等统计信息
    """
    # 总项目数
    result = await session.execute(
        select(func.count(Xuanli199Project.id))  # type: ignore
    )
    from sqlalchemy import func
    result = await session.execute(
        select(func.count(Xuanli199Project.id))
    )
    total = result.scalar()

    # 已爬取的期数
    result = await session.execute(
        select(Xuanli199Project.episode_number)
        .distinct()
        .where(Xuanli199Project.episode_number.isnot(None))
    )
    episodes = sorted([row[0] for row in result.fetchall()])

    # 最大期数
    max_episode = max(episodes) if episodes else 0

    # 最新爬取时间
    result = await session.execute(
        select(func.max(Xuanli199Project.crawled_at))
    )
    latest_crawled = result.scalar()

    return StatsResponse(
        total_projects=total or 0,
        crawled_episodes=len(episodes),
        max_episode=max_episode,
        episode_list=episodes,
        latest_crawled=latest_crawled,
    )


@router.get("/projects", response_model=List[Xuanli199ProjectResponse])
async def list_projects(
    episode: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """获取项目列表

    Args:
        episode: 指定期数筛选
        limit: 每页数量
        offset: 偏移量

    Returns:
        项目列表
    """
    query = select(Xuanli199Project).order_by(desc(Xuanli199Project.episode_number))

    if episode:
        query = query.where(Xuanli199Project.episode_number == episode)

    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    projects = result.scalars().all()

    return [Xuanli199ProjectResponse.model_validate(p) for p in projects]


@router.get("/status", response_model=CrawlStatus)
async def get_crawl_status():
    """获取爬取状态

    Returns:
        是否正在爬取、上次更新时间等
    """
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

    service = Xuanli199Service()

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
    """触发增量更新

    检查已爬取的最大期数，爬取新发布的视频

    Returns:
        更新结果
    """
    if _crawling_status["is_crawling"]:
        return UpdateResponse(
            success=False,
            message="正在爬取中，请稍后再试",
            new_projects=0,
        )

    # 后台执行爬取
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

    service = Xuanli199Service()

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
    """触发完整爬取

    爬取所有视频的GitHub项目

    Returns:
        更新结果
    """
    if _crawling_status["is_crawling"]:
        return UpdateResponse(
            success=False,
            message="正在爬取中，请稍后再试",
            new_projects=0,
        )

    # 后台执行爬取
    background_tasks.add_task(run_full_crawl)

    return UpdateResponse(
        success=True,
        message="已开始完整爬取，这可能需要几分钟",
        new_projects=0,
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    """删除单个项目

    Args:
        project_id: 项目ID

    Returns:
        删除结果
    """
    result = await session.execute(
        select(Xuanli199Project).where(Xuanli199Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await session.delete(project)
    await session.commit()

    return {"success": True, "message": "删除成功"}