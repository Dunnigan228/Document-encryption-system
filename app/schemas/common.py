"""
Pydantic response models for encryption/decryption endpoints.
"""
from pydantic import BaseModel
from typing import Optional


class EncryptResponse(BaseModel):
    success: bool
    file_id: str
    original_filename: str
    encrypted_filename: str
    key_filename: str
    file_type: str
    original_size: int
    encrypted_size: int
    password_generated: Optional[str] = None


class DecryptResponse(BaseModel):
    success: bool
    file_id: str
    original_filename: str
    decrypted_filename: str
    file_type: str
    size: int


class DownloadInfo(BaseModel):
    file_id: str
    filename: str
    media_type: str
