"""
POST /api/keys/generate — synchronous RSA-4096 key pair generation.

D-05: Returns KeyGenerateResponse with public_key and private_key in PEM format.
D-07: Keys generated in-memory via KeyManager; no disk I/O, no file_id.
D-08: Private key NEVER logged. Only "generated successfully" string is logged.
KEY-01, KEY-02: Satisfies key generation and no-server-storage requirements.
"""
import logging

from fastapi import APIRouter

from app.schemas.common import ErrorResponse, KeyGenerateResponse
from core.key_manager import KeyManager

router = APIRouter(prefix="/api/keys", tags=["keys"])

_logger = logging.getLogger(__name__)


@router.post(
    "/generate",
    response_model=KeyGenerateResponse,
    status_code=200,
    summary="Generate RSA-4096 key pair",
    description=(
        "Generate a new RSA-4096 key pair. Both keys are returned in PEM format "
        "as part of the JSON response. Keys are NOT stored on the server — "
        "the caller is responsible for saving them. "
        "Private key format: PKCS8 (-----BEGIN PRIVATE KEY-----)."
    ),
    responses={
        500: {"model": ErrorResponse, "description": "Key generation failed"},
    },
)
async def generate_keys() -> KeyGenerateResponse:
    """Generate RSA-4096 keypair and return both keys as PEM strings.

    Keys exist only in local variables within this function scope.
    After the response is serialised the objects go out of scope immediately.
    """
    km = KeyManager()
    public_key_obj, private_key_obj = km.generate_rsa_keypair(key_size=4096)
    pub_pem: str = km.serialize_public_key(public_key_obj).decode("utf-8")
    priv_pem: str = km.serialize_private_key(private_key_obj).decode("utf-8")
    # D-08: log ONLY this string — never log pub_pem, priv_pem, or the response object
    _logger.info("RSA-4096 key pair generated successfully")
    return KeyGenerateResponse(
        public_key=pub_pem,
        private_key=priv_pem,
        key_size=4096,
        format="PEM",
    )
