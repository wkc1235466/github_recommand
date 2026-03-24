"""Project data models for SQLite using SQLAlchemy 1.4."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from dataclasses import dataclass
import json

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Column, Float
from sqlalchemy.orm import relationship

from ..database import Base


class ProjectCategory(str, Enum):
    """Project categories."""

    AI_ML = "AI/机器学习"
    DEV_TOOLS = "开发工具"
    DEVOPS = "系统运维"
    SECURITY = "安全工具"
    MEDIA = "媒体处理"
    PRODUCTIVITY = "效率工具"
    DESKTOP = "桌面应用"
    GAME = "游戏娱乐"
    OTHER = "其他"


@dataclass
class AIAnalysis:
    """AI analysis result for a project."""

    summary: Optional[str] = None
    suggested_tags: List[str] = None
    confidence: Optional[float] = None
    analyzed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.suggested_tags is None:
            self.suggested_tags = []


class Project(Base):
    """SQLAlchemy model for a GitHub project."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), index=True, nullable=False)
    github_url = Column(String(500), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)

    # AI analysis stored as JSON string
    ai_summary = Column(Text, nullable=True)
    ai_tags = Column(Text, nullable=True)  # JSON list
    ai_confidence = Column(Float, nullable=True)
    ai_analyzed_at = Column(DateTime, nullable=True)

    recommend_reason = Column(Text, nullable=True)

    tags = Column(Text, nullable=True)  # JSON list (AI generated tags, max 3)
    user_tags = Column(Text, nullable=True)  # JSON list (user added tags, unlimited)
    stars = Column(Integer, nullable=True)
    readme_cache = Column(Text, nullable=True)

    needs_url = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to sources
    sources = relationship("ProjectSource", back_populates="project", cascade="all, delete-orphan")

    def get_tags_list(self) -> List[str]:
        """Get tags as list."""
        if self.tags:
            return json.loads(self.tags)
        return []

    def set_tags_list(self, tags: List[str]):
        """Set tags from list."""
        self.tags = json.dumps(tags) if tags else None

    def get_ai_tags_list(self) -> List[str]:
        """Get AI suggested tags as list."""
        if self.ai_tags:
            return json.loads(self.ai_tags)
        return []

    def set_ai_tags_list(self, tags: List[str]):
        """Set AI tags from list."""
        self.ai_tags = json.dumps(tags) if tags else None

    def get_user_tags_list(self) -> List[str]:
        """Get user added tags as list."""
        if self.user_tags:
            return json.loads(self.user_tags)
        return []

    def set_user_tags_list(self, tags: List[str]):
        """Set user tags from list."""
        self.user_tags = json.dumps(tags) if tags else None


class ProjectSource(Base):
    """SQLAlchemy model for project sources (from Bilibili)."""

    __tablename__ = "project_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)

    bilibili_url = Column(String(500), nullable=True)
    up_name = Column(String(100), nullable=True)
    video_title = Column(String(500), nullable=True)
    publish_date = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    project = relationship("Project", back_populates="sources")


# Predefined categories for frontend
CATEGORIES = [
    {"id": "AI/机器学习", "name": "AI/机器学习", "description": "LLM、AI工具、Agent、机器学习框架、语音/图像/视频生成"},
    {"id": "开发工具", "name": "开发工具", "description": "开发框架、库、CLI工具、IDE插件、API工具"},
    {"id": "系统运维", "name": "系统运维", "description": "DevOps、监控、部署工具、Docker、数据库"},
    {"id": "安全工具", "name": "安全工具", "description": "渗透测试、安全检测、漏洞分析"},
    {"id": "媒体处理", "name": "媒体处理", "description": "视频、音频、图片处理工具"},
    {"id": "效率工具", "name": "效率工具", "description": "笔记、文档、翻译、下载工具"},
    {"id": "桌面应用", "name": "桌面应用", "description": "系统增强、桌面工具、远程工具"},
    {"id": "游戏娱乐", "name": "游戏娱乐", "description": "游戏、娱乐相关"},
    {"id": "其他", "name": "其他", "description": "不属于以上分类的项目"},
]