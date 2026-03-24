"""数据迁移脚本：将 IT咖啡馆 和 玄离199 的项目迁移到统一的项目表"""

import asyncio
from typing import Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models.project import Project, ProjectSource
from ..models.itcoffee import ITcoffeeProject
from ..models.xuanli199 import Xuanli199Project
from ..logger import log


class MigrationResult:
    """迁移结果"""
    def __init__(
        self,
        success: bool,
        message: str,
        stats: Dict[str, int] = None
    ):
        self.success = success
        self.message = message
        self.stats = stats or {
            "total_migrated": 0,
            "from_itcoffee": 0,
            "from_xuanli199": 0,
            "duplicates": 0,
            "errors": 0
        }


class ProjectMigrator:
    """项目迁移器"""

    def __init__(self):
        self.stats = {
            "total_migrated": 0,
            "from_itcoffee": 0,
            "from_xuanli199": 0,
            "duplicates": 0,
            "errors": 0
        }

    async def find_project_by_github_url(
        self,
        session: AsyncSession,
        github_url: str
    ) -> Project | None:
        """根据 GitHub URL 查找项目"""
        if not github_url:
            return None

        result = await session.execute(
            select(Project).where(Project.github_url == github_url)
        )
        return result.scalar_one_or_none()

    def create_project_from_itcoffee(
        self,
        itcoffee: ITcoffeeProject
    ) -> Project:
        """从 IT咖啡馆项目创建统一项目"""
        project = Project(
            name=itcoffee.project_name or "",
            github_url=itcoffee.github_url or "",
            description=itcoffee.description or "",
            category="其他工具",  # 默认分类
            stars=0,
            needs_url=False if itcoffee.github_url else True
        )
        project.set_tags_list([])  # 使用方法设置 tags
        return project

    def create_project_from_xuanli199(
        self,
        xuanli: Xuanli199Project
    ) -> Project:
        """从玄离199项目创建统一项目"""
        # 从 github_url 提取项目名称
        name = xuanli.project_name or ""
        if not name and xuanli.github_url:
            # 从 URL 提取 owner/repo
            parts = xuanli.github_url.strip("/").split("/")
            if len(parts) >= 2:
                name = f"{parts[-2]}/{parts[-1]}"

        project = Project(
            name=name,
            github_url=xuanli.github_url or "",
            description="",
            category="其他工具",  # 默认分类
            stars=0,
            needs_url=False
        )
        project.set_tags_list([])  # 使用方法设置 tags
        return project

    def create_source_from_itcoffee(
        self,
        itcoffee: ITcoffeeProject,
        project_id: int
    ) -> ProjectSource:
        """从 IT咖啡馆项目创建来源信息"""
        source = ProjectSource(
            project_id=project_id,
            bilibili_url=itcoffee.bilibili_url or "",
            up_name=itcoffee.up_name or "IT咖啡馆",
            video_title=itcoffee.video_title or "",
            publish_date=itcoffee.video_publish_time.strftime("%Y-%m-%d") if itcoffee.video_publish_time else ""
        )
        return source

    def create_source_from_xuanli199(
        self,
        xuanli: Xuanli199Project,
        project_id: int
    ) -> ProjectSource:
        """从玄离199项目创建来源信息"""
        source = ProjectSource(
            project_id=project_id,
            bilibili_url=xuanli.bilibili_url or "",
            up_name=xuanli.up_name or "玄离199",
            video_title=xuanli.video_title or "",
            publish_date=xuanli.video_publish_time.strftime("%Y-%m-%d") if xuanli.video_publish_time else ""
        )
        return source

    async def migrate_itcoffee_projects(
        self,
        session: AsyncSession
    ) -> int:
        """迁移 IT咖啡馆项目"""
        log.info("开始迁移 IT咖啡馆项目")

        result = await session.execute(select(ITcoffeeProject))
        itcoffee_projects = result.scalars().all()

        migrated_count = 0
        for itc in itcoffee_projects:
            try:
                # 检查是否已存在
                existing = await self.find_project_by_github_url(session, itc.github_url)

                if existing:
                    # 添加来源信息
                    source = self.create_source_from_itcoffee(itc, existing.id)
                    session.add(source)
                    self.stats["duplicates"] += 1
                    log.debug(f"合并 IT咖啡馆项目: {itc.project_name}")
                else:
                    # 创建新项目
                    project = self.create_project_from_itcoffee(itc)
                    session.add(project)
                    await session.flush()  # 获取项目 ID

                    # 添加来源信息
                    source = self.create_source_from_itcoffee(itc, project.id)
                    session.add(source)

                    migrated_count += 1
                    self.stats["from_itcoffee"] += 1
                    log.debug(f"迁移 IT咖啡馆项目: {itc.project_name}")

            except Exception as e:
                log.error(f"迁移 IT咖啡馆项目失败 {itc.project_name}: {e}")
                self.stats["errors"] += 1

        log.info(f"IT咖啡馆项目迁移完成: {migrated_count} 条")
        return migrated_count

    async def migrate_xuanli199_projects(
        self,
        session: AsyncSession
    ) -> int:
        """迁移玄离199项目"""
        log.info("开始迁移玄离199项目")

        result = await session.execute(select(Xuanli199Project))
        xuanli_projects = result.scalars().all()

        migrated_count = 0
        for xuanli in xuanli_projects:
            try:
                # 检查是否已存在
                existing = await self.find_project_by_github_url(session, xuanli.github_url)

                if existing:
                    # 添加来源信息
                    source = self.create_source_from_xuanli199(xuanli, existing.id)
                    session.add(source)
                    self.stats["duplicates"] += 1
                    log.debug(f"合并玄离199项目: {xuanli.project_name}")
                else:
                    # 创建新项目
                    project = self.create_project_from_xuanli199(xuanli)
                    session.add(project)
                    await session.flush()  # 获取项目 ID

                    # 添加来源信息
                    source = self.create_source_from_xuanli199(xuanli, project.id)
                    session.add(source)

                    migrated_count += 1
                    self.stats["from_xuanli199"] += 1
                    log.debug(f"迁移玄离199项目: {xuanli.project_name}")

            except Exception as e:
                log.error(f"迁移玄离199项目失败 {xuanli.project_name}: {e}")
                self.stats["errors"] += 1

        log.info(f"玄离199项目迁移完成: {migrated_count} 条")
        return migrated_count

    async def migrate_all(self) -> MigrationResult:
        """迁移所有项目"""
        log.info("=" * 60)
        log.info("开始数据迁移：IT咖啡馆 + 玄离199 → 统一项目表")
        log.info("=" * 60)

        try:
            from ..database import async_session_maker

            async with async_session_maker() as session:
                # 统计原始数据
                itcoffee_count = await session.scalar(
                    select(func.count()).select_from(ITcoffeeProject)
                )
                xuanli_count = await session.scalar(
                    select(func.count()).select_from(Xuanli199Project)
                )

                log.info(f"IT咖啡馆项目: {itcoffee_count} 条")
                log.info(f"玄离199项目: {xuanli_count} 条")
                log.info(f"总计: {itcoffee_count + xuanli_count} 条")

                # 迁移 IT咖啡馆项目
                await self.migrate_itcoffee_projects(session)

                # 迁移玄离199项目
                await self.migrate_xuanli199_projects(session)

                # 提交事务
                await session.commit()

                # 统计结果
                total_count = await session.scalar(
                    select(func.count()).select_from(Project)
                )

                self.stats["total_migrated"] = total_count

                log.info("=" * 60)
                log.info("数据迁移完成")
                log.info(f"统一项目表总数: {total_count}")
                log.info(f"  - IT咖啡馆: {self.stats['from_itcoffee']} 条")
                log.info(f"  - 玄离199: {self.stats['from_xuanli199']} 条")
                log.info(f"  - 重复合并: {self.stats['duplicates']} 条")
                log.info(f"  - 错误: {self.stats['errors']} 条")
                log.info("=" * 60)

                return MigrationResult(
                    success=True,
                    message="数据迁移完成",
                    stats=self.stats
                )

        except Exception as e:
            log.error(f"数据迁移失败: {e}", exc_info=True)
            return MigrationResult(
                success=False,
                message=f"数据迁移失败: {str(e)}",
                stats=self.stats
            )


async def run_migration() -> MigrationResult:
    """运行迁移任务"""
    migrator = ProjectMigrator()
    return await migrator.migrate_all()


if __name__ == "__main__":
    """直接运行迁移脚本"""
    result = asyncio.run(run_migration())
    print(f"\n迁移结果: {'成功' if result.success else '失败'}")
    print(f"消息: {result.message}")
    if result.stats:
        print(f"统计: {result.stats}")
