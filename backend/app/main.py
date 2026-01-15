"""FastAPI application entry point."""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api.routes import health, generation, scenes, characters, world, projects, acts, chapters, chat, style, outline_import, series, references, manuscript_import
from app.api.routes import settings as settings_routes
from app.middleware.auth import APIKeyAuthMiddleware
from app.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Prose Generation Pipeline",
    description="Automated prose generation with critique-revision loop",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API key authentication middleware (if configured)
app.add_middleware(APIKeyAuthMiddleware)

# Include API routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(settings_routes.router)  # Already has /api/settings prefix

# Project routes (top-level)
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])

# Series routes (top-level)
app.include_router(series.router, prefix="/api/series", tags=["series"])

# Project-scoped routes
# These routes are nested under /api/projects/{project_id}/
project_router = APIRouter(prefix="/api/projects/{project_id}")
project_router.include_router(acts.router, prefix="/acts", tags=["acts"])
project_router.include_router(chapters.router, prefix="/chapters", tags=["chapters"])
project_router.include_router(characters.router, prefix="/characters", tags=["characters"])
project_router.include_router(world.router, prefix="/world", tags=["world"])
project_router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
project_router.include_router(generation.router, prefix="/generations", tags=["generation"])
project_router.include_router(chat.router, prefix="/chat", tags=["chat"])
project_router.include_router(style.router, prefix="/style", tags=["style"])
project_router.include_router(outline_import.router, prefix="/outline", tags=["outline"])
project_router.include_router(references.router, prefix="/references", tags=["references"])
project_router.include_router(manuscript_import.router, prefix="/manuscript", tags=["manuscript"])
app.include_router(project_router)

# Serve frontend static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Ensure directories exist
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.series_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data directories initialized at {settings.data_dir}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"API Auth: {'enabled' if settings.api_auth_key else 'disabled'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )
