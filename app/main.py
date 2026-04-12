"""
Document Encryption Microservice — FastAPI application factory.

Entry point for Railway deployment. CLI entry point (main.py in project root) is unchanged.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for imports like `from core.encryption_engine import ...`
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import encrypt, decrypt, files, health
from app.config import get_settings
from app.services.file_service import file_service

_logger = logging.getLogger(__name__)


async def _periodic_cleanup(file_svc, temp_dir: Path, settings) -> None:
    """Delete expired jobs every 5 minutes. Per D-10/D-11 and FILE-06.

    Runs as an asyncio background task started in the lifespan context manager.
    Cancelled cleanly on shutdown (T-02-01-02 mitigation).
    """
    interval = 300  # 5 minutes
    while True:
        await asyncio.sleep(interval)
        now = datetime.now(timezone.utc)
        for file_id in file_svc.all_ids():
            entry = file_svc.get(file_id)
            if entry is None:
                continue
            expires_at_str = entry.get("expires_at")
            if not expires_at_str:
                continue
            try:
                expires_at = datetime.fromisoformat(
                    expires_at_str.rstrip("Z")
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if now >= expires_at:
                # Delete associated files (missing_ok prevents cleanup loop crash)
                result_paths = entry.get("result_paths") or {}
                for rel_path in result_paths.values():
                    if rel_path:
                        (temp_dir / rel_path).unlink(missing_ok=True)
                orig = entry.get("original_path")
                if orig:
                    (temp_dir / orig).unlink(missing_ok=True)
                file_svc.delete(file_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create dirs, restore job state, launch TTL cleanup. Shutdown: cancel cleanup."""
    settings = get_settings()
    temp_dir = Path(settings.temp_dir)
    (temp_dir / "jobs").mkdir(parents=True, exist_ok=True)
    (temp_dir / "files").mkdir(parents=True, exist_ok=True)

    restored = file_service.restore_from_disk(temp_dir)
    if restored:
        _logger.info("Restored %d job(s) from disk on startup", restored)

    cleanup_task = asyncio.create_task(
        _periodic_cleanup(file_service, temp_dir, settings)
    )
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


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
