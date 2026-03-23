"""ITcoffee GitHub推荐项目数据模型

存储从B站「GitHub一周热点」系列视频中提取的GitHub项目名称
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ITcoffeeProject(Base):
    """ITcoffee推荐的GitHub项目"""

    __tablename__ = "itcoffee"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 项目信息（只有名称，URL需要后续AI补全）
    project_name: Mapped[str] = mapped_column(String(255))  # 项目名称
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 项目描述
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # AI补全后的URL

    # 来源信息
    bilibili_url: Mapped[str] = mapped_column(String(500))
    video_title: Mapped[str] = mapped_column(String(500), nullable=True)
    video_publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    up_name: Mapped[str] = mapped_column(String(100), default="IT咖啡馆")

    # 期数（从视频标题提取，如「GitHub一周热点107期」）
    episode_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 状态
    url_verified: Mapped[bool] = mapped_column(default=False)  # URL是否已验证

    # 时间戳
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index('ix_itcoffee_project_name', 'project_name'),
        Index('ix_itcoffee_bilibili_url', 'bilibili_url'),
        Index('ix_itcoffee_episode', 'episode_number'),
        Index('ix_itcoffee_up_name', 'up_name'),
        Index('ix_itcoffee_crawled', 'crawled_at'),
    )

    def __repr__(self):
        return f"<ITcoffeeProject({self.project_name}, ep={self.episode_number})>"