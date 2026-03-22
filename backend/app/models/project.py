"""Project data models for SQLite using SQLAlchemy."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from dataclasses import dataclass
import json

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ProjectCategory(str, Enum):
    """Project categories."""

    AI_ML = "AI/机器学习"
    DEV_TOOLS = "开发工具"
    DEVOPS = "系统运维"
    OTHER = "其他工具"


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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), unique=True, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # AI analysis stored as JSON string
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    ai_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    ai_analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    recommend_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    stars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    readme_cache: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    needs_url: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to sources
    sources: Mapped[List["ProjectSource"]] = relationship(back_populates="project", cascade="all, delete-orphan")

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


class ProjectSource(Base):
    """SQLAlchemy model for project sources (from Bilibili)."""

    __tablename__ = "project_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    bilibili_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    up_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    video_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    publish_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    project: Mapped["Project"] = relationship(back_populates="sources")


# Predefined categories for frontend
CATEGORIES = [
    {"id": "AI/机器学习", "name": "AI/机器学习", "description": "LLM、AI工具、机器学习框架"},
    {"id": "开发工具", "name": "开发工具", "description": "开发框架、库、CLI工具"},
    {"id": "系统运维", "name": "系统运维", "description": "DevOps、监控、部署工具"},
    {"id": "其他工具", "name": "其他工具", "description": "不属于以上分类的项目"},
]