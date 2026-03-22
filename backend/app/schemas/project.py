"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SourceInfoSchema(BaseModel):
    """Source information schema."""

    bilibili_url: Optional[str] = None
    up_name: Optional[str] = None
    video_title: Optional[str] = None
    publish_date: Optional[str] = None


class AIAnalysisSchema(BaseModel):
    """AI analysis result schema."""

    summary: Optional[str] = None
    suggested_tags: List[str] = []
    confidence: Optional[float] = None
    analyzed_at: Optional[datetime] = None


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str
    github_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    recommend_reason: Optional[str] = None
    source: Optional[SourceInfoSchema] = None
    tags: List[str] = []
    stars: Optional[int] = None
    needs_url: bool = False


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str = Field(..., alias="_id")
    name: str
    github_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    ai_analysis: Optional[AIAnalysisSchema] = None
    recommend_reason: Optional[str] = None
    source: Optional[SourceInfoSchema] = None
    sources: Optional[List[SourceInfoSchema]] = None
    tags: List[str] = []
    stars: Optional[int] = None
    needs_url: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectListResponse(BaseModel):
    """Schema for paginated project list response."""

    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CrawlResult(BaseModel):
    """Schema for crawl result."""

    success: bool
    message: str
    projects_added: int = 0
    projects_updated: int = 0
    projects_need_url: int = 0  # Projects without GitHub URL


class AnalyzeRequest(BaseModel):
    """Schema for analyze request."""

    force: bool = False  # Force re-analyze even if already analyzed


class AnalyzeResult(BaseModel):
    """Schema for analyze result."""

    success: bool
    message: str
    project_id: str
    category: Optional[str] = None
    summary: Optional[str] = None


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: str
    name: str
    description: str
    count: int = 0


class ReadmeResponse(BaseModel):
    """Schema for README response."""

    project_id: str
    name: str
    readme: Optional[str] = None
    github_url: Optional[str] = None