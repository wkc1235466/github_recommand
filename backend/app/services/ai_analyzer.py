"""AI analysis service using ZhipuAI (智谱AI)."""

import json
from datetime import datetime
from typing import Optional, List

from ..config import get_settings
from ..models.project import AIAnalysis, CATEGORIES

settings = get_settings()


class AIAnalyzer:
    """AI analyzer for project classification and description generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4-flash"
    ):
        """Initialize the AI analyzer.

        Args:
            api_key: ZhipuAI API key. If None, reads from settings.
            model: Model to use. Default is glm-4-flash (fast and cheap).
        """
        self.api_key = api_key or getattr(settings, 'zhipuai_api_key', None)
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load the ZhipuAI client."""
        if self._client is None:
            try:
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "zhipuai package not installed. "
                    "Install it with: pip install zhipuai"
                )
        return self._client

    async def analyze_project(
        self,
        name: str,
        github_url: Optional[str] = None,
        existing_description: Optional[str] = None
    ) -> AIAnalysis:
        """Analyze a project and generate description and category.

        Args:
            name: Project name.
            github_url: GitHub URL if available.
            existing_description: Existing description if available.

        Returns:
            AIAnalysis object with results.
        """
        # Build prompt
        prompt = self._build_analysis_prompt(name, github_url, existing_description)

        try:
            # Call ZhipuAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            # Parse response
            content = response.choices[0].message.content
            return self._parse_analysis_response(content)

        except Exception as e:
            print(f"Error analyzing project {name}: {e}")
            return AIAnalysis(
                summary=f"无法分析项目: {str(e)}",
                suggested_tags=[],
                analyzed_at=datetime.utcnow()
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for project analysis."""
        categories = ", ".join([c["id"] for c in CATEGORIES])
        return f"""你是一个GitHub项目分析专家。你的任务是分析GitHub项目并生成简洁的描述和分类。

你需要返回JSON格式的结果，包含以下字段：
- summary: 项目简介（50-100字）
- category: 项目分类，必须是以下之一: {categories}
- suggested_tags: 建议的标签（2-5个）
- confidence: 分类置信度（0-1之间的数字）

只返回JSON，不要有其他内容。"""

    def _build_analysis_prompt(
        self,
        name: str,
        github_url: Optional[str],
        existing_description: Optional[str]
    ) -> str:
        """Build the analysis prompt."""
        parts = [f"项目名称: {name}"]

        if github_url:
            parts.append(f"GitHub地址: {github_url}")

        if existing_description:
            parts.append(f"现有描述: {existing_description}")

        parts.append("\n请分析这个项目并返回JSON格式的结果。")
        return "\n".join(parts)

    def _parse_analysis_response(self, content: str) -> AIAnalysis:
        """Parse the AI response into AIAnalysis object."""
        try:
            # Try to extract JSON from the response
            # Sometimes AI adds markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            return AIAnalysis(
                summary=data.get("summary", ""),
                suggested_tags=data.get("suggested_tags", []),
                confidence=data.get("confidence"),
                analyzed_at=datetime.utcnow()
            )
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response: {e}")
            return AIAnalysis(
                summary=content[:200] if content else "分析失败",
                suggested_tags=[],
                analyzed_at=datetime.utcnow()
            )



# Convenience function
async def analyze_project(
    name: str,
    github_url: Optional[str] = None,
    existing_description: Optional[str] = None
) -> AIAnalysis:
    """Analyze a project using AI.

    Args:
        name: Project name.
        github_url: GitHub URL if available.
        existing_description: Existing description if available.

    Returns:
        AIAnalysis object with results.
    """
    analyzer = AIAnalyzer()
    return await analyzer.analyze_project(name, github_url, existing_description)