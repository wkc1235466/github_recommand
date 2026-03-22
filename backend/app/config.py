"""Application configuration management."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API settings
    api_prefix: str = "/api"
    app_name: str = "GitHub Project Recommendation System"
    debug: bool = True

    # Database settings (SQLite - no external service needed)
    # Database file will be stored in data/github_recommend.db

    # Crawler settings
    crawler_headless: bool = True
    crawler_timeout: int = 30000  # milliseconds
    crawler_max_videos: int = 10  # max videos per source

    # ZhipuAI settings
    zhipuai_api_key: Optional[str] = None
    zhipuai_model: str = "glm-4-flash"

    # GitHub settings
    github_token: Optional[str] = None  # GitHub personal access token (optional)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()