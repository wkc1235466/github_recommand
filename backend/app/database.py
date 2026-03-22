"""SQLite database connection management using SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from pathlib import Path

from .config import get_settings
from .logger import log

settings = get_settings()

# Database file path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "github_recommend.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Async engine
engine = None
async_session_maker = None


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


async def init_db():
    """初始化数据库并创建表"""
    global engine, async_session_maker

    log.info(f"正在初始化数据库: {DB_PATH}")

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        echo=settings.debug,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    log.info(f"数据库初始化完成: {DB_PATH}")


async def close_db():
    """关闭数据库连接"""
    global engine
    if engine:
        await engine.dispose()
        log.info("数据库连接已关闭")


async def get_session() -> AsyncSession:
    """获取异步数据库会话"""
    if async_session_maker is None:
        await init_db()
    async with async_session_maker() as session:
        yield session