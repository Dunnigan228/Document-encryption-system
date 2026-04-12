"""
POST /api/files/inspect — read-only encrypted file header inspection.

D-09: Accepts an encrypted file upload, parses the binary header, returns metadata.
D-11: Inspection is read-only — file bytes are never written to disk.
D-12: Invalid/non-encrypted files return HTTP 422 with structured error.
INSP-01: Satisfies header inspection requirement.
"""
import logging
import struct

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.schemas.common import ErrorResponse, InspectFlagsResponse, InspectResponse
from core.header_parser import parse_encrypted_header

router = APIRouter(prefix="/api/files", tags=["files"])

_logger = logging.getLogger(__name__)


@router.post(
    "/inspect",
    response_model=InspectResponse,
    status_code=200,
    summary="Inspect encrypted file header",
    description=(
        "Parse and return the public metadata from an encrypted file's header "
        "without requiring the decryption key. Returns format version, original "
        "filename, file type, timestamp, flags, and size fields. "
        "Returns 422 if the file is not a valid encrypted document."
    ),
    responses={
        413: {"model": ErrorResponse, "description": "File exceeds size limit"},
        422: {"model": ErrorResponse, "description": "File is not a valid encrypted document"},
    },
)
async def inspect_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> InspectResponse:
    """Read encrypted file bytes, parse header, return metadata. Nothing written to disk."""
    content: bytes = await file.read()

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": f"File exceeds the {settings.max_file_size_mb} MB limit",
                "detail": f"Received {len(content):,} bytes",
            },
        )

    try:
        header = parse_encrypted_header(content)
    except (ValueError, struct.error) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_ENCRYPTED_FILE",
                "message": "File is not a valid encrypted document",
                "detail": str(exc),
            },
        )

    # content goes out of scope here — no disk write ever occurred
    return InspectResponse(
        format_version=header["format_version"],
        original_filename=header["original_filename"],
        file_type=header["file_type"],
        timestamp=header["timestamp"],
        flags=InspectFlagsResponse(**header["flags"]),
        original_size=header["original_size"],
        compressed_size=header["compressed_size"],
    )
