"""
Pydantic response models for encryption/decryption endpoints.
"""
from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    """Standard error response shape for all API error codes. Per D-01."""
    error_code: str          # e.g. FILE_TOO_LARGE, NOT_FOUND, UNSUPPORTED_FORMAT
    message: str             # Human-readable English message
    detail: Optional[str] = None  # Extra context; never contains stack traces or file paths


class EncryptResponse(BaseModel):
    success: bool
    file_id: str
    original_filename: str
    encrypted_filename: str
    key_filename: str
    file_type: str
    original_size: int
    encrypted_size: int


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


class JobStatusResponse(BaseModel):
    """Response for GET /api/files/{file_id} — reflects current job state.

    Per D-02: status=="failed" is a valid terminal state for a known job.
    The endpoint returns HTTP 200 for all known jobs (including failed).
    HTTP 404 is returned only when the file_id is unknown.
    """
    file_id: str
    status: str                          # queued | processing | complete | failed
    job_type: str                        # encrypt | decrypt
    original_filename: str
    file_type: str
    expires_at: str                      # ISO 8601 UTC
    poll_url: str                        # "/api/files/{file_id}"
    download_url: Optional[str] = None  # set only when status == "complete"
    error: Optional[str] = None         # set only when status == "failed"


class KeyGenerateResponse(BaseModel):
    """Response for POST /api/keys/generate. Per D-06.
    NOTE: private_key is PKCS8 PEM (-----BEGIN PRIVATE KEY-----).
    NEVER log this response object — it contains private key material.
    """
    public_key: str    # PEM-encoded (-----BEGIN PUBLIC KEY-----)
    private_key: str   # PKCS8 PEM-encoded (-----BEGIN PRIVATE KEY-----)
    key_size: int      # Always 4096
    format: str        # Always "PEM"


class InspectFlagsResponse(BaseModel):
    """Parsed flags bitmask from encrypted file header. Per D-10."""
    compressed: bool
    multi_layer: bool
    rsa_protected: bool
    integrity_check: bool
    metadata_encrypted: bool


class InspectResponse(BaseModel):
    """Response for POST /api/files/inspect. Per D-10."""
    format_version: str       # e.g. "1.0.0"
    original_filename: str
    file_type: str
    timestamp: int            # Unix epoch seconds
    flags: InspectFlagsResponse
    original_size: int        # bytes
    compressed_size: int      # bytes


class HealthResponse(BaseModel):
    """Response for GET /health. Per API-04 annotation audit."""
    status: str               # always "ok"
