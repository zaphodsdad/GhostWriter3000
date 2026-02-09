"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path

from app.config import settings
from app.api.routes import health, generation, scenes, characters, world, projects, acts, chapters, chat, style, outline_import, series, references, manuscript_import, backups, extraction, tools, memory, chico, chapter_extraction
from app.api.routes import settings as settings_routes
from app.middleware.auth import APIKeyAuthMiddleware
from app.utils.logging import setup_logging, get_logger


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent browser caching of API responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Only add no-cache headers to API routes (not static files)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

# Setup logging
setup_logging()
logger = get_logger(__name__)

# --- MCP Server (optional — degrades gracefully if fastmcp not installed) ---
_mcp_app = None
try:
    from prose_mcp.server import mcp as mcp_server, register_all_tools
    register_all_tools()
    _mcp_app = mcp_server.http_app(path="/", transport="streamable-http")
    logger.info("MCP server initialized")
except ImportError:
    logger.info("FastMCP not installed, MCP endpoint disabled")
except Exception as e:
    logger.warning(f"Failed to initialize MCP server: {e}")


@asynccontextmanager
async def lifespan(app):
    """Application lifespan — initializes MCP and data directories."""
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.series_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data directories initialized at {settings.data_dir}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"API Auth: {'enabled' if settings.api_auth_key else 'disabled'}")

    if _mcp_app is not None:
        async with _mcp_app.router.lifespan_context(_mcp_app):
            logger.info("MCP server started")
            yield
            logger.info("MCP server stopping")
    else:
        yield

    logger.info("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title="Prose Generation Pipeline",
    description="Automated prose generation with critique-revision loop",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prevent browser caching of API responses
app.add_middleware(NoCacheMiddleware)

# Add API key authentication middleware (if configured)
app.add_middleware(APIKeyAuthMiddleware)

# Include API routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(settings_routes.router)  # Already has /api/settings prefix
app.include_router(extraction.router)  # Already has /api/extract prefix
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])

# Project routes (top-level)
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])

# Series routes (top-level)
app.include_router(series.router, prefix="/api/series", tags=["series"])

# Series memory routes
app.include_router(memory.router, prefix="/api/series", tags=["memory"])

# Chico - Series-level AI assistant
app.include_router(chico.router, prefix="/api/series", tags=["chico"])

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
project_router.include_router(backups.router, prefix="/backups", tags=["backups"])
project_router.include_router(chapter_extraction.router, prefix="/extract-chapters", tags=["extraction"])
app.include_router(project_router)

# Mount MCP app if available
if _mcp_app is not None:
    app.mount("/mcp", _mcp_app)
    logger.info("MCP server mounted at /mcp")

# Serve frontend static files (MUST be last — catches all unmatched paths)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )
