"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
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
    user_tags: List[str] = []
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


class AnalyzeRequest(BaseModel):
    """Schema for analyze request."""

    force: bool = False  # Force re-analyze even if already analyzed
    api_url: str = Field("", description="AI API URL（Claude 兼容端点）")
    api_key: Optional[str] = Field(None, description="AI API Key")
    model: str = Field("glm-4-flash", description="AI 模型")


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


class TestModelRequest(BaseModel):
    """测试模型连接请求"""

    api_url: str
    api_key: str
    model: str
    api_type: str = "claude"  # 只支持 claude


class TestModelResponse(BaseModel):
    """测试模型连接响应"""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None


class AISearchRequest(BaseModel):
    """AI 智能搜索请求"""

    query: str = Field(..., description="搜索查询", min_length=1, max_length=500)
    use_cache: bool = Field(True, description="是否使用缓存")
    api_url: str = Field("", description="AI API URL（Claude 兼容端点）")
    api_key: Optional[str] = Field(None, description="AI API Key")
    model: str = Field("glm-4-flash", description="AI 模型")


class AISearchResponse(BaseModel):
    """AI 智能搜索响应"""

    query: str
    projects: List[ProjectResponse]
    detected_categories: List[str]
    search_summary: str
    from_cache: bool
    total_matches: int


class UnanalyzedProjectsResponse(BaseModel):
    """未分析项目列表响应"""

    projects: List[ProjectResponse]
    total: int


class BatchAnalyzeRequest(BaseModel):
    """批量分析请求"""

    project_ids: Optional[List[int]] = None  # 指定项目ID列表，为空则分析所有未分析项目
    limit: int = Field(10, ge=1, le=50, description="最多分析项目数量")
    api_key: Optional[str] = None  # AI API Key
    api_url: str = Field("", description="AI API URL（Claude 兼容端点）")
    model: str = Field("glm-4-flash", description="AI 模型")


class BatchAnalyzeProgress(BaseModel):
    """批量分析进度"""

    total: int
    analyzed: int
    success: int
    failed: int
    current_project: Optional[str] = None


class BatchAnalyzeResponse(BaseModel):
    """批量分析响应"""

    success: bool
    message: str
    total: int
    analyzed: int
    success_count: int
    failed_count: int
    failed_projects: List[Dict[str, Any]] = []