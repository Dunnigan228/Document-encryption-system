"""
POST /api/encrypt — async job endpoint returning HTTP 202 immediately.

D-03: Returns AcceptedResponse with file_id, status, poll_url, original_filename, file_type, expires_at.
D-07/D-08: CPU-bound EncryptionEngine.encrypt() runs inside run_in_threadpool; file bytes read before 202.
D-05: JSON sidecar written via file_svc.register() before background task is added.
T-02-02-01: max_file_size_mb enforcement deferred to Phase 3 (API-02); FastAPI multipart limits apply now.
"""
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
from core.encryption_engine import EncryptionEngine
from core.key_manager import KeyManager
from utils.file_handler import FileHandler
from utils.validator import Validator

router = APIRouter(prefix="/api", tags=["encryption"])

_validator = Validator()
_key_manager = KeyManager()
_file_handler = FileHandler()


@router.post("/encrypt", response_model=AcceptedResponse, status_code=202)
async def encrypt_file(
    file: UploadFile = File(...),
    password: str = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    settings: Settings = Depends(get_settings),
    file_svc: FileService = Depends(get_file_service),
):
    # D-08: read bytes NOW — UploadFile is closed after endpoint returns
    content: bytes = await file.read()
    original_filename = file.filename or "upload"

    file_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.file_ttl_seconds)

    temp_dir = Path(settings.temp_dir)
    suffix = Path(original_filename).suffix or ".bin"
    src_path = temp_dir / "files" / f"{file_id}_src{suffix}"
    src_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.write_bytes(content)

    file_type = _validator.get_file_type(str(src_path))
    if not _validator.is_supported_format(file_type):
        src_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_type}")

    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    # D-05: write sidecar before adding background task
    file_svc.register(file_id, {
        "file_id": file_id,
        "status": "queued",
        "job_type": "encrypt",
        "original_filename": original_filename,
        "file_type": file_type,
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires_at_str,
        "error": None,
        "result_paths": {},
        "original_path": f"files/{src_path.name}",
    })

    background_tasks.add_task(
        _run_encrypt_job, file_id, str(src_path), original_filename,
        file_type, password, file_svc, settings,
    )

    return AcceptedResponse(
        file_id=file_id,
        status="queued",
        poll_url=f"/api/files/{file_id}",
        original_filename=original_filename,
        file_type=file_type,
        expires_at=expires_at_str,
    )


async def _run_encrypt_job(
    file_id: str,
    src_path: str,
    original_filename: str,
    file_type: str,
    password: Optional[str],
    file_svc: FileService,
    settings: Settings,
) -> None:
    """Async wrapper — marks status, offloads CPU work to thread pool, updates status on completion."""
    file_svc.update_status(file_id, "processing")
    try:
        result_paths = await run_in_threadpool(
            _sync_encrypt, file_id, src_path, original_filename, file_type, password, settings
        )
        file_svc.update_status(file_id, "complete", result_paths=result_paths)
    except Exception as exc:
        file_svc.update_status(file_id, "failed", error=str(exc))


def _sync_encrypt(
    file_id: str,
    src_path: str,
    original_filename: str,
    file_type: str,
    password: Optional[str],
    settings: Settings,
) -> dict:
    """Runs in ThreadPoolExecutor. May call blocking crypto freely. Returns result_paths dict."""
    key_manager = KeyManager()
    if password is None:
        password = key_manager.generate_master_password()

    engine = EncryptionEngine(password=password, key_manager=key_manager)
    file_data = _file_handler.read_file(src_path)
    encrypted_data = engine.encrypt(
        data=file_data, file_type=file_type, original_filename=original_filename
    )

    temp_dir = Path(settings.temp_dir)
    enc_path = temp_dir / "files" / f"{file_id}_encrypted.enc"
    key_path = temp_dir / "files" / f"{file_id}_key.key"
    enc_path.parent.mkdir(parents=True, exist_ok=True)

    _file_handler.write_file(str(enc_path), encrypted_data)
    key_manager.save_key_bundle(engine.get_key_bundle(), str(key_path))

    return {
        "encrypted_file": f"files/{enc_path.name}",
        "key_file": f"files/{key_path.name}",
    }
