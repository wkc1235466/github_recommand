"""玄离199 GitHub推荐项目数据模型

存储从B站「科技补全」系列视频中提取的GitHub项目
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Index, Column

from ..database import Base


class Xuanli199Project(Base):
    """玄离199推荐的GitHub项目"""

    __tablename__ = "xuanli199"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # GitHub项目信息
    github_url = Column(String(500), unique=True)
    project_name = Column(String(255))  # owner/repo

    # 来源信息
    bilibili_url = Column(String(500))
    video_title = Column(String(500), nullable=True)
    video_publish_time = Column(DateTime, nullable=True)
    up_name = Column(String(100), default="玄离199")  # UP主名字

    # 期数（从视频标题提取，如「科技补全94」）
    episode_number = Column(Integer, nullable=True)

    # 时间戳
    crawled_at = Column(DateTime, default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index('ix_xuanli199_github_url', 'github_url'),
        Index('ix_xuanli199_project_name', 'project_name'),
        Index('ix_xuanli199_bilibili_url', 'bilibili_url'),
        Index('ix_xuanli199_episode', 'episode_number'),
        Index('ix_xuanli199_up_name', 'up_name'),
        Index('ix_xuanli199_crawled', 'crawled_at'),
    )

    def __repr__(self):
        return f"<Xuanli199Project({self.project_name}, ep={self.episode_number}, up={self.up_name})>"