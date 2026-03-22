"""Project data model for MongoDB."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ProjectCategory(str, Enum):
    """Project categories."""

    AI_ML = "AI/机器学习"
    DEV_TOOLS = "开发工具"
    DEVOPS = "系统运维"
    OTHER = "其他工具"


class SourceInfo(BaseModel):
    """Source information from Bilibili."""

    bilibili_url: Optional[str] = None
    up_name: Optional[str] = None
    video_title: Optional[str] = None
    publish_date: Optional[str] = None


class AIAnalysis(BaseModel):
    """AI analysis result for a project."""

    summary: Optional[str] = None  # AI生成的项目简介
    suggested_tags: List[str] = []  # AI建议的标签
    confidence: Optional[float] = None  # 分类置信度
    analyzed_at: Optional[datetime] = None


class ProjectModel(BaseModel):
    """MongoDB document model for a GitHub project."""

    id: Optional[str] = Field(None, alias="_id")
    name: str
    github_url: Optional[str] = None  # 可能为空（IT咖啡馆只有名称）
    description: Optional[str] = None
    category: Optional[str] = None  # 项目分类
    ai_analysis: Optional[AIAnalysis] = None  # AI分析结果

    recommend_reason: Optional[str] = None

    # Support both single source and multiple sources
    source: Optional[SourceInfo] = None  # 单个来源（向后兼容）
    sources: Optional[List[SourceInfo]] = None  # 多个来源

    tags: List[str] = []
    stars: Optional[int] = None
    readme_cache: Optional[str] = None  # README内容缓存

    needs_url: bool = False  # 是否需要补全GitHub地址

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def get_all_sources(self) -> List[SourceInfo]:
        """Get all sources as a list."""
        if self.sources:
            return self.sources
        if self.source:
            return [self.source]
        return []

    def add_source(self, source: SourceInfo) -> None:
        """Add a new source to the project."""
        if self.sources is None:
            self.sources = []
            if self.source:
                self.sources.append(self.source)
                self.source = None
        self.sources.append(source)


# Predefined categories for frontend
CATEGORIES = [
    {"id": "AI/机器学习", "name": "AI/机器学习", "description": "LLM、AI工具、机器学习框架"},
    {"id": "开发工具", "name": "开发工具", "description": "开发框架、库、CLI工具"},
    {"id": "系统运维", "name": "系统运维", "description": "DevOps、监控、部署工具"},
    {"id": "其他工具", "name": "其他工具", "description": "不属于以上分类的项目"},
]