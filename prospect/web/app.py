"""FastAPI application factory."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

# Paths
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
FRONTEND_DIR = WEB_DIR / "frontend"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Prospect Scraper API",
        description="Internal API for prospect discovery",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
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

    # Legacy HTML routes (kept at root for backward compatibility)
    from prospect.web.routes import router as html_router
    app.include_router(html_router, tags=["legacy"])

    # Serve frontend SPA
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend(request: Request):
        """Serve the frontend SPA."""
        frontend_path = FRONTEND_DIR / "index.html"
        if frontend_path.exists():
            return HTMLResponse(content=frontend_path.read_text())
        else:
            # Redirect to legacy UI if new frontend not found
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/legacy/")

    # Serve frontend static files
    if FRONTEND_DIR.exists():
        app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


# Create default app instance
app = create_app()
