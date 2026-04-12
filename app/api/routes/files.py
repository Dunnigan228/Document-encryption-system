"""
GET /api/files/{file_id}          — poll job status
GET /api/files/{file_id}/download — stream processed result file

Replaces the old GET /api/download/{file_id}/{file_type} endpoint.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_file_service
from app.config import Settings, get_settings
from app.schemas.common import JobStatusResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{file_id}", response_model=JobStatusResponse)
async def get_job_status(
    file_id: str,
    file_svc: FileService = Depends(get_file_service),
):
    """GET /api/files/{file_id} — poll job state.

    Per D-02: 'failed' status returns HTTP 200, not an error code.
    It is a valid terminal state for a known job.
    Returns 404 only when the file_id does not exist at all.
    """
    entry = file_svc.get(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {file_id}")

    status = entry.get("status", "unknown")
    download_url = f"/api/files/{file_id}/download" if status == "complete" else None

    return JobStatusResponse(
        file_id=file_id,
        status=status,
        job_type=entry.get("job_type", "unknown"),
        original_filename=entry.get("original_filename", ""),
        file_type=entry.get("file_type", ""),
        expires_at=entry.get("expires_at", ""),
        poll_url=f"/api/files/{file_id}",
        download_url=download_url,
        error=entry.get("error"),
    )


@router.get("/{file_id}/download")
async def download_result(
    file_id: str,
    settings: Settings = Depends(get_settings),
    file_svc: FileService = Depends(get_file_service),
):
    """GET /api/files/{file_id}/download — stream the processed result file.

    Returns 404 if job not found or not yet complete.
    Per D-09: deletes the original uploaded file after streaming the result.
    Does NOT delete the result file — that is handled by the TTL cleanup task.
    """
    entry = file_svc.get(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {file_id}")

    status = entry.get("status")
    if status != "complete":
        raise HTTPException(
            status_code=404,
            detail=f"File not ready for download. Current status: {status}",
        )

    result_paths = entry.get("result_paths") or {}
    temp_dir = Path(settings.temp_dir)

    # Determine which output file to serve and its download filename
    job_type = entry.get("job_type", "encrypt")
    if job_type == "encrypt":
        rel_path = result_paths.get("encrypted_file")
        original = entry.get("original_filename", "file")
        download_name = f"{original}.enc"
        media_type = "application/octet-stream"
    else:
        rel_path = result_paths.get("decrypted_file")
        original = result_paths.get("original_filename") or entry.get("original_filename", "file")
        download_name = original
        media_type = "application/octet-stream"

    if not rel_path:
        raise HTTPException(status_code=404, detail="Result file path not recorded in job")

    file_path = temp_dir / rel_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found on disk")

    # D-09: delete original AFTER building FileResponse (FileResponse streams lazily,
    # but the path is recorded now — safe to unlink the source, not the result).
    # T-02-03-03 mitigation: clear original_path in sidecar after first unlink so
    # repeated downloads call unlink(missing_ok=True) on None which is a no-op.
    original_path = entry.get("original_path")
    if original_path:
        (temp_dir / original_path).unlink(missing_ok=True)
        file_svc.update_status(file_id, status, original_path=None)

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=download_name,
    )
