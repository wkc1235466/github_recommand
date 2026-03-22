"""GitHub service for fetching project metadata and README."""

import re
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import get_settings

settings = get_settings()


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize the GitHub service.

        Args:
            token: GitHub personal access token. If None, uses unauthenticated requests.
        """
        self.token = token or getattr(settings, 'github_token', None)
        self.base_url = "https://api.github.com"
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            try:
                import aiohttp
                headers = {"Accept": "application/vnd.github.v3+json"}
                if self.token:
                    headers["Authorization"] = f"token {self.token}"
                self._session = aiohttp.ClientSession(headers=headers)
            except ImportError:
                raise ImportError(
                    "aiohttp package not installed. "
                    "Install it with: pip install aiohttp"
                )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None

    def _extract_owner_repo(self, github_url: str) -> Optional[tuple]:
        """Extract owner and repo name from GitHub URL.

        Args:
            github_url: GitHub repository URL.

        Returns:
            Tuple of (owner, repo) or None.
        """
        match = re.search(r'github\.com/([\w\-]+)/([\w\-\.]+)', github_url)
        if match:
            return match.group(1), match.group(2)
        return None

    async def get_repo_info(self, github_url: str) -> Dict[str, Any]:
        """Get repository information from GitHub API.

        Args:
            github_url: GitHub repository URL.

        Returns:
            Dictionary with repo info (stars, description, topics, etc.).
        """
        result = self._extract_owner_repo(github_url)
        if not result:
            return {}

        owner, repo = result
        api_url = f"{self.base_url}/repos/{owner}/{repo}"

        try:
            session = await self._get_session()
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "stars": data.get("stargazers_count"),
                        "description": data.get("description"),
                        "topics": data.get("topics", []),
                        "language": data.get("language"),
                        "forks": data.get("forks_count"),
                        "open_issues": data.get("open_issues_count"),
                        "license": data.get("license", {}).get("name") if data.get("license") else None,
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "homepage": data.get("homepage"),
                    }
                elif response.status == 404:
                    print(f"Repository not found: {github_url}")
                    return {}
                else:
                    print(f"Error fetching {github_url}: {response.status}")
                    return {}

        except Exception as e:
            print(f"Error fetching repo info: {e}")
            return {}

    async def get_readme(self, github_url: str) -> Optional[str]:
        """Get README content from GitHub.

        Args:
            github_url: GitHub repository URL.

        Returns:
            README content as string or None.
        """
        result = self._extract_owner_repo(github_url)
        if not result:
            return None

        owner, repo = result

        # Try different README filenames
        readme_files = ["README.md", "README.rst", "README.txt", "README"]

        session = await self._get_session()

        for filename in readme_files:
            # Try main branch first
            api_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{filename}"
            try:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("encoding") == "base64" and data.get("content"):
                            import base64
                            content = base64.b64decode(data["content"]).decode("utf-8")
                            return content
            except Exception:
                continue

        # Try raw.githubusercontent.com as fallback
        for branch in ["main", "master"]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            try:
                async with session.get(raw_url) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception:
                continue

        return None

    async def search_repo(self, query: str, limit: int = 5) -> list:
        """Search for repositories by name.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of repository info dictionaries.
        """
        api_url = f"{self.base_url}/search/repositories"

        try:
            session = await self._get_session()
            params = {"q": query, "per_page": limit}
            async with session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    for item in data.get("items", []):
                        results.append({
                            "name": item.get("full_name"),
                            "url": item.get("html_url"),
                            "description": item.get("description"),
                            "stars": item.get("stargazers_count"),
                        })
                    return results
                else:
                    print(f"Search error: {response.status}")
                    return []
        except Exception as e:
            print(f"Error searching repos: {e}")
            return []


# Convenience functions
async def get_repo_info(github_url: str) -> Dict[str, Any]:
    """Get repository information."""
    service = GitHubService()
    try:
        return await service.get_repo_info(github_url)
    finally:
        await service.close()


async def get_readme(github_url: str) -> Optional[str]:
    """Get README content."""
    service = GitHubService()
    try:
        return await service.get_readme(github_url)
    finally:
        await service.close()


async def search_repo(query: str, limit: int = 5) -> list:
    """Search for repositories."""
    service = GitHubService()
    try:
        return await service.search_repo(query, limit)
    finally:
        await service.close()