"""
GET /api/download/{file_id}/{file_type} — file download endpoint.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_file_service
from app.config import Settings, get_settings
from app.services.file_service import FileService

router = APIRouter(prefix="/api", tags=["files"])


@router.get("/download/{file_id}/{file_type}")
async def download_file(
    file_id: str,
    file_type: str,
    settings: Settings = Depends(get_settings),
    file_svc: FileService = Depends(get_file_service),
):
    file_info = file_svc.get(file_id)
    if file_info is None:
        raise HTTPException(status_code=404, detail="File not found")

    if file_type == "encrypted":
        filename = file_info.get("encrypted_file")
        media_type = "application/octet-stream"
        download_name = f"{file_info['original_filename']}.encrypted"
    elif file_type == "key":
        filename = file_info.get("key_file")
        media_type = "application/json"
        download_name = f"{file_info['original_filename']}.key"
    elif file_type == "decrypted":
        filename = file_info.get("decrypted_file")
        media_type = "application/octet-stream"
        download_name = file_info.get("original_filename", filename)
    else:
        raise HTTPException(status_code=400, detail="Invalid file type. Use: encrypted, key, decrypted")

    if not filename:
        raise HTTPException(status_code=404, detail="File not found for this file_id")

    file_path = Path(settings.temp_dir) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path=str(file_path), media_type=media_type, filename=download_name)
