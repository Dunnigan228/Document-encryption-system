"""
Document Encryption Microservice — FastAPI application factory.

Entry point for Railway deployment. CLI entry point (main.py in project root) is unchanged.
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path for imports like `from core.encryption_engine import ...`
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import encrypt, decrypt, files, health
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create temp dir. Shutdown: nothing (Phase 2 adds cleanup task)."""
    settings = get_settings()
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
    yield
    # Phase 2: cancel background cleanup task here


settings = get_settings()

app = FastAPI(
    title="Document Encryption API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — origins from env var (CFG-01, API-03 handled in Phase 3)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routers — always mounted
app.include_router(health.router)
app.include_router(encrypt.router)
app.include_router(decrypt.router)
app.include_router(files.router)

# Conditional UI mount — D-07, UI-01
if settings.enable_ui:
    from fastapi.requests import Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates

    BASE_DIR = Path(__file__).parent
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    _templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return _templates.TemplateResponse(request, "index.html")

else:
    @app.get("/")
    async def home_api():
        return {"service": "Document Encryption API", "docs": "/docs", "health": "/health"}
