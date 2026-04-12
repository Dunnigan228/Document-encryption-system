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


class AcceptedResponse(BaseModel):
    """202 response returned immediately when a file upload is accepted for processing."""
    file_id: str
    status: str           # always "queued" at acceptance time
    poll_url: str         # e.g. "/api/files/{file_id}"
    original_filename: str
    file_type: str
    expires_at: str       # ISO 8601 UTC string
