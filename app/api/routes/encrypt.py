"""
POST /api/encrypt — synchronous file encryption endpoint.
D-06: Keeps synchronous behavior from app/main.py. Async conversion is Phase 2.
"""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_file_service
from app.config import Settings, get_settings
from app.schemas.common import EncryptResponse
from app.services.file_service import FileService
from core.encryption_engine import EncryptionEngine
from core.key_manager import KeyManager
from utils.file_handler import FileHandler
from utils.validator import Validator

router = APIRouter(prefix="/api", tags=["encryption"])

_validator = Validator()
_key_manager = KeyManager()
_file_handler = FileHandler()


@router.post("/encrypt", response_model=EncryptResponse)
async def encrypt_file(
    file: UploadFile = File(...),
    password: str = Form(None),
    settings: Settings = Depends(get_settings),
    file_svc: FileService = Depends(get_file_service),
):
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    temp_input_path = temp_dir / f"{file_id}_input_{original_filename}"

    try:
        content = await file.read()
        temp_input_path.write_bytes(content)

        file_type = _validator.get_file_type(str(temp_input_path))
        if not _validator.is_supported_format(file_type):
            temp_input_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_type}")

        if password is None:
            password = _key_manager.generate_master_password()

        engine = EncryptionEngine(password=password, key_manager=_key_manager)
        file_data = _file_handler.read_file(str(temp_input_path))
        encrypted_data = engine.encrypt(
            data=file_data,
            file_type=file_type,
            original_filename=original_filename,
        )

        encrypted_filename = f"{file_id}_encrypted.enc"
        encrypted_path = temp_dir / encrypted_filename
        _file_handler.write_file(str(encrypted_path), encrypted_data)

        key_bundle = engine.get_key_bundle()
        key_filename = f"{file_id}_key.key"
        key_path = temp_dir / key_filename
        _key_manager.save_key_bundle(key_bundle, str(key_path))

        temp_input_path.unlink(missing_ok=True)

        file_svc.register(file_id, {
            "encrypted_file": encrypted_filename,
            "key_file": key_filename,
            "original_filename": original_filename,
            "file_type": file_type,
            "original_size": len(file_data),
            "encrypted_size": len(encrypted_data),
        })

        return EncryptResponse(
            success=True,
            file_id=file_id,
            original_filename=original_filename,
            encrypted_filename=encrypted_filename,
            key_filename=key_filename,
            file_type=file_type,
            original_size=len(file_data),
            encrypted_size=len(encrypted_data),
            password_generated=password,
        )

    except HTTPException:
        raise
    except Exception as exc:
        temp_input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc))
