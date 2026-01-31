"""FastAPI application factory."""

import os
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from prospect.web.database import init_db

logger = logging.getLogger(__name__)

# Paths
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
FRONTEND_DIR = WEB_DIR / "frontend"


def create_app(skip_db_init: bool = False) -> FastAPI:
    """Create and configure the FastAPI application."""

    # Initialize database (can be skipped for testing)
    if not skip_db_init:
        try:
            init_db()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            logger.warning("Continuing without database initialization")

    app = FastAPI(
        title="Prospect Command Center",
        description="Marketing prospect discovery and management tool",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware for production
    origins = os.environ.get("ALLOWED_ORIGINS", "*")
    if origins != "*":
        origins = [o.strip() for o in origins.split(",")]
    else:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Templates (for legacy routes)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    # Static files (for legacy routes)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # API v1 routes
    from prospect.web.api.v1 import router as api_router
    app.include_router(api_router)

    # WebSocket routes
    from prospect.web.ws import router as ws_router
    app.include_router(ws_router)

    # Serve frontend SPA at root - MUST be before legacy routes
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend(request: Request):
        """Serve the frontend SPA."""
        frontend_path = FRONTEND_DIR / "index.html"
        if frontend_path.exists():
            return HTMLResponse(content=frontend_path.read_text())

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        login_path = TEMPLATES_DIR / "login.html"
        if login_path.exists():
            return HTMLResponse(content=login_path.read_text())
        return HTMLResponse(content="Login page not found", status_code=404)

    @app.get("/register", response_class=HTMLResponse)
    async def register_page():
        register_path = TEMPLATES_DIR / "register.html"
        if register_path.exists():
            return HTMLResponse(content=register_path.read_text())
        return HTMLResponse(content="Register page not found", status_code=404)


        else:
            # Redirect to legacy UI if new frontend not found
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/legacy/")

    # PWA manifest
    @app.get("/manifest.json")
    async def serve_manifest():
        """Serve the PWA manifest."""
        from fastapi.responses import FileResponse
        manifest_path = FRONTEND_DIR / "manifest.json"
        if manifest_path.exists():
            return FileResponse(manifest_path, media_type="application/json")
        return {"error": "Not found"}

    # Service worker (must be served from root for scope)
    @app.get("/sw.js")
    async def serve_service_worker():
        """Serve the service worker."""
        from fastapi.responses import FileResponse
        sw_path = FRONTEND_DIR / "sw.js"
        if sw_path.exists():
            return FileResponse(sw_path, media_type="application/javascript")
        return {"error": "Not found"}

    # Legacy HTML routes (moved to /legacy prefix to not conflict with new frontend)
    from prospect.web.routes import router as html_router
    app.include_router(html_router, prefix="/legacy", tags=["legacy"])

    # Serve frontend static files
    if FRONTEND_DIR.exists():
        app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    # Startup event for async initialization
    @app.on_event("startup")
    async def startup_event():
        """Initialize resources on startup."""
        logger.info("Prospect Command Center starting up...")
        logger.info(f"Frontend directory: {FRONTEND_DIR}")
        logger.info(f"Templates directory: {TEMPLATES_DIR}")

    return app


# Create default app instance
app = create_app()
