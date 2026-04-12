"""
FastAPI dependency providers shared across routes.
"""
from app.config import Settings, get_settings
from app.services.file_service import file_service, FileService


def get_file_service() -> FileService:
    """Provide the module-level FileService singleton."""
    return file_service
