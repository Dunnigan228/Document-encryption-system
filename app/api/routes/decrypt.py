"""
POST /api/decrypt — synchronous file decryption endpoint.
D-06: Keeps synchronous behavior from app/main.py. Async conversion is Phase 2.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_file_service
from app.config import Settings, get_settings
from app.schemas.common import DecryptResponse
from app.services.file_service import FileService
from core.decryption_engine import DecryptionEngine
from core.key_manager import KeyManager
from utils.file_handler import FileHandler

router = APIRouter(prefix="/api", tags=["decryption"])

_key_manager = KeyManager()
_file_handler = FileHandler()


@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt_file(
    encrypted_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    password: str = Form(None),
    settings: Settings = Depends(get_settings),
    file_svc: FileService = Depends(get_file_service),
):
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    temp_enc_path = temp_dir / f"{file_id}_encrypted_input.enc"
    temp_key_path = temp_dir / f"{file_id}_key_input.key"

    try:
        temp_enc_path.write_bytes(await encrypted_file.read())
        temp_key_path.write_bytes(await key_file.read())

        key_bundle = _key_manager.load_key_bundle(str(temp_key_path), password)
        engine = DecryptionEngine(key_bundle=key_bundle, key_manager=_key_manager)
        encrypted_data = _file_handler.read_file(str(temp_enc_path))
        result = engine.decrypt(encrypted_data)

        decrypted_filename = f"{file_id}_decrypted_{result['original_filename']}"
        decrypted_path = temp_dir / decrypted_filename
        _file_handler.write_file(str(decrypted_path), result["data"])

        temp_enc_path.unlink(missing_ok=True)
        temp_key_path.unlink(missing_ok=True)

        file_svc.register(file_id, {
            "decrypted_file": decrypted_filename,
            "original_filename": result["original_filename"],
            "file_type": result["file_type"],
            "size": len(result["data"]),
        })

        return DecryptResponse(
            success=True,
            file_id=file_id,
            original_filename=result["original_filename"],
            decrypted_filename=decrypted_filename,
            file_type=result["file_type"],
            size=len(result["data"]),
        )

    except HTTPException:
        raise
    except Exception as exc:
        temp_enc_path.unlink(missing_ok=True)
        temp_key_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc))
