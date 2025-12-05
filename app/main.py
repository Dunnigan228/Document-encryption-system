import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse
from fastapi.requests import Request
import uvicorn
import uuid
import shutil
from datetime import datetime, timedelta
import asyncio

from core.encryption_engine import EncryptionEngine
from core.decryption_engine import DecryptionEngine
from core.key_manager import KeyManager
from utils.file_handler import FileHandler
from utils.validator import Validator
from config.settings import Settings

app = FastAPI(title="Document Encryption System", version="1.0.0")

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
TEMP_STORAGE = BASE_DIR.parent / "temp_storage"

TEMP_STORAGE.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

file_handler = FileHandler()
validator = Validator()
key_manager = KeyManager()
settings = Settings()

storage = {}


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/encrypt")
async def encrypt_file(
    file: UploadFile = File(...),
    password: str = Form(None)
):
    try:
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        original_filename = file.filename
        temp_input_path = TEMP_STORAGE / f"{file_id}_input_{original_filename}"

        with open(temp_input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        file_type = validator.get_file_type(str(temp_input_path))

        if not validator.is_supported_format(file_type):
            os.remove(temp_input_path)
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_type}")

        if password is None:
            password = key_manager.generate_master_password()

        encryption_engine = EncryptionEngine(
            password=password,
            key_manager=key_manager
        )

        file_data = file_handler.read_file(str(temp_input_path))

        encrypted_data = encryption_engine.encrypt(
            data=file_data,
            file_type=file_type,
            original_filename=original_filename
        )

        encrypted_filename = f"{file_id}_encrypted.enc"
        encrypted_path = TEMP_STORAGE / encrypted_filename
        file_handler.write_file(str(encrypted_path), encrypted_data)

        key_bundle = encryption_engine.get_key_bundle()
        key_filename = f"{file_id}_key.key"
        key_path = TEMP_STORAGE / key_filename
        key_manager.save_key_bundle(key_bundle, str(key_path))

        os.remove(temp_input_path)

        storage[file_id] = {
            "encrypted_file": encrypted_filename,
            "key_file": key_filename,
            "original_filename": original_filename,
            "created_at": datetime.now(),
            "file_type": file_type,
            "original_size": len(file_data),
            "encrypted_size": len(encrypted_data)
        }

        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "original_filename": original_filename,
            "encrypted_filename": encrypted_filename,
            "key_filename": key_filename,
            "file_type": file_type,
            "original_size": len(file_data),
            "encrypted_size": len(encrypted_data),
            "password_generated": password if password else None
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/decrypt")
async def decrypt_file(
    encrypted_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    password: str = Form(None)
):
    try:
        file_id = str(uuid.uuid4())

        temp_encrypted_path = TEMP_STORAGE / f"{file_id}_encrypted_input.enc"
        with open(temp_encrypted_path, "wb") as buffer:
            content = await encrypted_file.read()
            buffer.write(content)

        temp_key_path = TEMP_STORAGE / f"{file_id}_key_input.key"
        with open(temp_key_path, "wb") as buffer:
            content = await key_file.read()
            buffer.write(content)

        key_bundle = key_manager.load_key_bundle(str(temp_key_path), password)

        decryption_engine = DecryptionEngine(
            key_bundle=key_bundle,
            key_manager=key_manager
        )

        encrypted_data = file_handler.read_file(str(temp_encrypted_path))

        decrypted_result = decryption_engine.decrypt(encrypted_data)

        decrypted_filename = f"{file_id}_decrypted_{decrypted_result['original_filename']}"
        decrypted_path = TEMP_STORAGE / decrypted_filename
        file_handler.write_file(str(decrypted_path), decrypted_result['data'])

        os.remove(temp_encrypted_path)
        os.remove(temp_key_path)

        storage[file_id] = {
            "decrypted_file": decrypted_filename,
            "original_filename": decrypted_result['original_filename'],
            "created_at": datetime.now(),
            "file_type": decrypted_result['file_type'],
            "size": len(decrypted_result['data'])
        }

        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "original_filename": decrypted_result['original_filename'],
            "decrypted_filename": decrypted_filename,
            "file_type": decrypted_result['file_type'],
            "size": len(decrypted_result['data'])
        })

    except Exception as e:
        if 'temp_encrypted_path' in locals() and os.path.exists(temp_encrypted_path):
            os.remove(temp_encrypted_path)
        if 'temp_key_path' in locals() and os.path.exists(temp_key_path):
            os.remove(temp_key_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{file_id}/{file_type}")
async def download_file(file_id: str, file_type: str):
    if file_id not in storage:
        raise HTTPException(status_code=404, detail="File not found")

    file_info = storage[file_id]

    if file_type == "encrypted":
        filename = file_info.get("encrypted_file")
    elif file_type == "key":
        filename = file_info.get("key_file")
    elif file_type == "decrypted":
        filename = file_info.get("decrypted_file")
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    if not filename:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = TEMP_STORAGE / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    if file_type == "encrypted":
        media_type = "application/octet-stream"
        download_name = f"{file_info['original_filename']}.encrypted"
    elif file_type == "key":
        media_type = "application/json"
        download_name = f"{file_info['original_filename']}.key"
    elif file_type == "decrypted":
        media_type = "application/octet-stream"
        download_name = file_info['original_filename']

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=download_name
    )


async def cleanup_old_files():
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        expired_ids = []

        for file_id, info in storage.items():
            if now - info['created_at'] > timedelta(hours=24):
                expired_ids.append(file_id)

                if 'encrypted_file' in info:
                    file_path = TEMP_STORAGE / info['encrypted_file']
                    if file_path.exists():
                        os.remove(file_path)

                if 'key_file' in info:
                    file_path = TEMP_STORAGE / info['key_file']
                    if file_path.exists():
                        os.remove(file_path)

                if 'decrypted_file' in info:
                    file_path = TEMP_STORAGE / info['decrypted_file']
                    if file_path.exists():
                        os.remove(file_path)

        for file_id in expired_ids:
            del storage[file_id]


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_files())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
