"""Main FastAPI application entry point."""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db, close_db
from .routers import projects_router, xuanli199_router, itcoffee_router
from .logger import setup_logging, log

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    # Setup logging
    setup_logging(debug=settings.debug)
    log.info(f"正在启动 {settings.app_name}")

    # Startup - initialize SQLite database
    await init_db()
    log.info("数据库初始化完成")

    yield

    # Shutdown - close database connection
    await close_db()
    log.info("数据库连接已关闭")
    log.info("应用已停止")


app = FastAPI(
    title=settings.app_name,
    description="A system for crawling and recommending trending GitHub projects from Bilibili UP owners",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有 HTTP 请求"""
    log.info(f"请求: {request.method} {request.url.path}")
    response = await call_next(request)
    log.info(f"响应: {request.method} {request.url.path} - 状态码: {response.status_code}")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    log.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )


# Include routers
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(xuanli199_router, prefix=settings.api_prefix)
app.include_router(itcoffee_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    log.debug("健康检查请求")
    return {"status": "healthy", "app": settings.app_name}


# Mount static files for frontend (after API routes)
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/")
async def root():
    """根路径端点 - 返回前端页面"""
    if STATIC_DIR.exists():
        return FileResponse(STATIC_DIR / "index.html")
    return {
        "message": "GitHub Project Recommendation API",
        "docs": "/docs",
        "health": "/health",
    }


# Catch-all route for frontend SPA routing
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """处理前端路由，返回 index.html"""
    # 不处理 API 路由和静态资源
    if full_path.startswith("api/") or full_path.startswith("assets/") or full_path == "health":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if STATIC_DIR.exists():
        return FileResponse(STATIC_DIR / "index.html")
    return JSONResponse(status_code=404, content={"detail": "Not found"})