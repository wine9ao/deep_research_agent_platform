"""Main FastAPI application for the Deep Research Agent Platform."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import knowledge_router, research_router, sql_router
from .db.database import get_db_manager
from .utils.config import get_settings
from .utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Deep Research Agent Platform Starting...")
    logger.info("=" * 60)

    # Initialize database
    try:
        db = get_db_manager()
        db.create_all_sync()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    yield

    # Shutdown
    try:
        db = get_db_manager()
        await db.close()
        logger.info("Database connections closed.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Deep Research Agent Platform Shutdown.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Deep Research Agent Platform",
        description=(
            "面向行业分析与金融调研的多智能体深度研究Agent平台。\n\n"
            "支持6 Agent协作流水线：规划 → 检索 → 数据分析 → 图表 → 报告 → 评审。\n"
            "自动生成结构化中文研究报告。"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(research_router)
    app.include_router(knowledge_router)
    app.include_router(sql_router)

    # Health check
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    return app


# ── Application instance ──────────────────────────────────────────────────

app = create_app()


# ── Direct run support ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
