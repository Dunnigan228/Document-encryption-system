"""
POST /api/decrypt — async job endpoint returning HTTP 202 immediately.

D-03: Returns AcceptedResponse with file_id, status, poll_url, original_filename, file_type, expires_at.
D-07/D-08: CPU-bound DecryptionEngine.decrypt() runs inside run_in_threadpool; both UploadFile bytes
           read before 202 is returned.
D-05: JSON sidecar written via file_svc.register() before background task is added.
D-04/D-11/WR-01: Size check on encrypted file BEFORE write_bytes — oversized input never hits disk.
D-12/WR-02: try/finally ensures both temp files cleaned in all error paths.
D-03/CR-02: Background task stores generic error string, not raw exception.
FILE-02, FILE-07: Async job pattern with thread-pool offload for decryption.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_file_service
from app.config import Settings, get_settings
from app.schemas.common import AcceptedResponse
from app.services.file_service import FileService
from core.decryption_engine import DecryptionEngine
from core.key_manager import KeyManager
from utils.file_handler import FileHandler

router = APIRouter(prefix="/api", tags=["decryption"])

_key_manager = KeyManager()
_file_handler = FileHandler()
_logger = logging.getLogger(__name__)


@router.post("/decrypt", response_model=AcceptedResponse, status_code=202)
async def decrypt_file(
    encrypted_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    password: str = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    settings: Settings = Depends(get_settings),
    file_svc: FileService = Depends(get_file_service),
):
    # D-08: read BOTH UploadFiles NOW — both are closed after endpoint returns
    enc_content: bytes = await encrypted_file.read()
    key_content: bytes = await key_file.read()
    original_enc_filename = encrypted_file.filename or "upload.enc"

    # D-04/D-11/WR-01: size check BEFORE any disk write
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(enc_content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": f"Encrypted file exceeds the {settings.max_file_size_mb} MB limit",
                "detail": f"Received {len(enc_content):,} bytes",
            },
        )

    file_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.file_ttl_seconds)
    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    temp_dir = Path(settings.temp_dir)
    files_dir = temp_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    enc_path = files_dir / f"{file_id}_src.enc"
    key_path = files_dir / f"{file_id}_src.key"
    enc_path.write_bytes(enc_content)
    key_path.write_bytes(key_content)

    # D-12/WR-02: wrap register + enqueue in try/finally to clean up both temp files on any error
    try:
        # D-05: register sidecar before adding background task
        file_svc.register(file_id, {
            "file_id": file_id,
            "status": "queued",
            "job_type": "decrypt",
            "original_filename": original_enc_filename,
            "file_type": "encrypted",
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": expires_at_str,
            "error": None,
            "result_paths": {},
            "original_path": f"files/{enc_path.name}",
        })

        background_tasks.add_task(
            _run_decrypt_job, file_id, str(enc_path), str(key_path),
            password, file_svc, settings,
        )

        return AcceptedResponse(
            file_id=file_id,
            status="queued",
            poll_url=f"/api/files/{file_id}",
            original_filename=original_enc_filename,
            file_type="encrypted",
            expires_at=expires_at_str,
        )
    except HTTPException:
        enc_path.unlink(missing_ok=True)
        key_path.unlink(missing_ok=True)
        raise
    except Exception:
        enc_path.unlink(missing_ok=True)
        key_path.unlink(missing_ok=True)
        _logger.exception("Unexpected error in decrypt upload handler")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "PROCESSING_FAILED",
                "message": "Internal processing error",
                "detail": None,
            },
        )


async def _run_decrypt_job(
    file_id: str,
    enc_path: str,
    key_path: str,
    password: Optional[str],
    file_svc: FileService,
    settings: Settings,
) -> None:
    """Async wrapper — marks status, offloads CPU work to thread pool, updates status on completion."""
    file_svc.update_status(file_id, "processing")
    try:
        result_paths = await run_in_threadpool(
            _sync_decrypt, file_id, enc_path, key_path, password, settings
        )
        file_svc.update_status(file_id, "complete", result_paths=result_paths)
    except Exception:
        # D-03/CR-02: log full traceback server-side; store only generic message in registry
        _logger.exception("Decrypt job failed for file_id=%s", file_id)
        file_svc.update_status(file_id, "failed", error="Processing failed")


def _sync_decrypt(
    file_id: str,
    enc_path: str,
    key_path: str,
    password: Optional[str],
    settings: Settings,
) -> dict:
    """Runs in ThreadPoolExecutor. Returns result_paths dict."""
    key_manager = KeyManager()
    key_bundle = key_manager.load_key_bundle(key_path, password)
    engine = DecryptionEngine(key_bundle=key_bundle, key_manager=key_manager)
    encrypted_data = _file_handler.read_file(enc_path)
    result = engine.decrypt(encrypted_data)

    original_filename = result.get("original_filename", "decrypted_file")
    suffix = Path(original_filename).suffix or ".bin"
    temp_dir = Path(settings.temp_dir)
    out_path = temp_dir / "files" / f"{file_id}_decrypted{suffix}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _file_handler.write_file(str(out_path), result["data"])

    return {
        "decrypted_file": f"files/{out_path.name}",
        "original_filename": original_filename,
        "file_type": result.get("file_type", "unknown"),
    }
