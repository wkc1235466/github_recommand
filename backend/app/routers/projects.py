"""Project API routes."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId

from ..database import get_collection
from ..schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    CrawlResult,
    AnalyzeRequest,
    AnalyzeResult,
    CategoryResponse,
    ReadmeResponse,
)
from ..crawler.bilibili import BilibiliCrawler
from ..services.ai_analyzer import AIAnalyzer
from ..services.github_service import GitHubService, get_readme
from ..models.project import CATEGORIES

router = APIRouter(prefix="/projects", tags=["projects"])


def objectid_to_str(obj_id) -> str:
    """Convert ObjectId to string."""
    return str(obj_id)


def project_doc_to_response(doc: dict) -> dict:
    """Convert MongoDB document to response format."""
    if doc:
        doc["_id"] = objectid_to_str(doc["_id"])
    return doc


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    needs_url: Optional[bool] = Query(None, description="Filter projects that need URL"),
):
    """Get paginated list of projects."""
    collection = get_collection("projects")

    # Build query
    query = {}
    if category:
        query["category"] = category
    if tag:
        query["tags"] = tag
    if needs_url is not None:
        query["needs_url"] = needs_url
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"recommend_reason": {"$regex": search, "$options": "i"}},
        ]

    # Get total count
    total = await collection.count_documents(query)

    # Get paginated results
    skip = (page - 1) * page_size
    cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    projects = await cursor.to_list(length=page_size)

    # Convert to response format
    projects = [project_doc_to_response(p) for p in projects]

    return ProjectListResponse(
        projects=projects,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + page_size) < total,
    )


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories():
    """Get list of all categories with counts."""
    collection = get_collection("projects")

    categories = []
    for cat in CATEGORIES:
        count = await collection.count_documents({"category": cat["id"]})
        categories.append(CategoryResponse(
            id=cat["id"],
            name=cat["name"],
            description=cat["description"],
            count=count
        ))

    return categories


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a single project by ID."""
    collection = get_collection("projects")

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await collection.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project_doc_to_response(project)


@router.get("/{project_id}/readme", response_model=ReadmeResponse)
async def get_project_readme(project_id: str):
    """Get README content for a project."""
    collection = get_collection("projects")

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await collection.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    github_url = project.get("github_url")
    if not github_url:
        raise HTTPException(status_code=400, detail="Project has no GitHub URL")

    # Check if we have cached README
    readme_cache = project.get("readme_cache")
    if readme_cache:
        return ReadmeResponse(
            project_id=project_id,
            name=project.get("name"),
            readme=readme_cache,
            github_url=github_url
        )

    # Fetch README from GitHub
    try:
        readme = await get_readme(github_url)
        if readme:
            # Cache it for future use
            await collection.update_one(
                {"_id": obj_id},
                {"$set": {"readme_cache": readme, "updated_at": datetime.utcnow()}}
            )
        return ReadmeResponse(
            project_id=project_id,
            name=project.get("name"),
            readme=readme,
            github_url=github_url
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch README: {str(e)}")


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """Create a new project manually."""
    collection = get_collection("projects")

    # Check if project with same GitHub URL already exists
    if project.github_url:
        existing = await collection.find_one({"github_url": project.github_url})
        if existing:
            raise HTTPException(status_code=409, detail="Project with this GitHub URL already exists")

    # Check if project with same name already exists
    existing = await collection.find_one({"name": project.name})
    if existing:
        raise HTTPException(status_code=409, detail="Project with this name already exists")

    # Create document
    doc = project.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()

    result = await collection.insert_one(doc)
    doc["_id"] = result.inserted_id

    return project_doc_to_response(doc)


@router.post("/crawl", response_model=CrawlResult)
async def trigger_crawl(sources: Optional[str] = Query(None, description="Comma-separated list of sources")):
    """Trigger the crawler to fetch new projects from Bilibili."""
    # Parse sources
    source_list = sources.split(",") if sources else None

    crawler = BilibiliCrawler(sources=source_list)

    try:
        # Run the crawler
        projects = await crawler.crawl()
        projects = crawler.merge_sources(projects)

        if not projects:
            return CrawlResult(
                success=True,
                message="Crawl completed but no new projects found",
                projects_added=0,
                projects_updated=0,
                projects_need_url=0,
            )

        # Save to database
        collection = get_collection("projects")
        added = 0
        updated = 0
        need_url = 0

        for project in projects:
            github_url = project.get("github_url")
            name = project.get("name")

            # Determine query key
            query_key = github_url if github_url else name
            query_field = "github_url" if github_url else "name"

            existing = await collection.find_one({query_field: query_key})
            project["updated_at"] = datetime.utcnow()

            if existing:
                # Update existing project, merge sources
                existing_sources = existing.get("sources") or []
                if existing.get("source"):
                    existing_sources.append(existing.get("source"))

                new_source = project.get("source")
                if new_source and new_source not in existing_sources:
                    existing_sources.append(new_source)

                project["sources"] = existing_sources
                if "source" in project:
                    del project["source"]

                await collection.update_one(
                    {"_id": existing["_id"]}, {"$set": project}
                )
                updated += 1
            else:
                # Insert new project
                project["created_at"] = datetime.utcnow()
                await collection.insert_one(project)
                added += 1
                if not github_url:
                    need_url += 1

        return CrawlResult(
            success=True,
            message=f"Crawl completed successfully",
            projects_added=added,
            projects_updated=updated,
            projects_need_url=need_url,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")


@router.post("/{project_id}/analyze", response_model=AnalyzeResult)
async def analyze_project(project_id: str, request: AnalyzeRequest = AnalyzeRequest()):
    """Trigger AI analysis for a project."""
    collection = get_collection("projects")

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    project = await collection.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already analyzed
    if project.get("ai_analysis") and not request.force:
        return AnalyzeResult(
            success=True,
            message="Project already analyzed. Use force=true to re-analyze.",
            project_id=project_id,
            category=project.get("category"),
            summary=project.get("ai_analysis", {}).get("summary")
        )

    # Run AI analysis
    try:
        analyzer = AIAnalyzer()
        analysis = await analyzer.analyze_project(
            name=project.get("name"),
            github_url=project.get("github_url"),
            existing_description=project.get("description")
        )

        # Update project
        update_data = {
            "ai_analysis": analysis.model_dump(),
            "category": analysis.suggested_tags[0] if analysis.suggested_tags else "其他工具",
            "updated_at": datetime.utcnow()
        }

        await collection.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )

        return AnalyzeResult(
            success=True,
            message="Analysis completed successfully",
            project_id=project_id,
            category=update_data["category"],
            summary=analysis.summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project by ID."""
    collection = get_collection("projects")

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    return None