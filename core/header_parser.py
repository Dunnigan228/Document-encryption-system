"""
Standalone encrypted file header parser.

Parses the public portion of the binary header format without requiring
key material. Used by POST /api/files/inspect.

Header layout (little-endian):
  0..5   MAGIC_NUMBER b'DOCENC' (6 bytes)
  6..7   version major.minor (2 bytes)
  8..11  flags uint32 LE (4 bytes)
  12..19 timestamp uint64 LE (8 bytes)
  20..23 HEADER_SEPARATOR b'\\xFF\\xFE\\xFD\\xFC' (4 bytes)
  24..25 file_type_len uint16 LE
  26..N  file_type UTF-8 string
  N+1..N+2 filename_len uint16 LE
  ...    filename UTF-8 string
  ...    original_size uint64 LE (8 bytes)
  ...    compressed_size uint64 LE (8 bytes)
"""
import struct

from config.constants import CryptoConstants


def parse_encrypted_header(data: bytes) -> dict:
    """Parse public header metadata from an encrypted file.

    Args:
        data: Raw bytes of the encrypted file (full file or at least ~200 bytes).

    Returns:
        dict with keys: format_version, original_filename, file_type, timestamp,
        flags, original_size, compressed_size.

    Raises:
        ValueError: If magic number does not match (not an encrypted file).
        struct.error: If file is truncated (too short to parse header).
    """
    constants = CryptoConstants()
    offset = 0

    # Magic number check
    if len(data) < 6:
        raise ValueError(
            f"File too short to contain magic number (need 6 bytes, got {len(data)})"
        )
    magic = data[offset:offset + 6]
    if magic != constants.MAGIC_NUMBER:
        raise ValueError(
            f"Invalid file format: magic number mismatch "
            f"(expected {constants.MAGIC_NUMBER!r}, got {magic!r})"
        )
    offset += 6

    # Version: major.minor as two bytes
    version_major = data[offset]
    version_minor = data[offset + 1]
    version = f"{version_major}.{version_minor}.0"
    offset += 2

    # Flags: uint32 LE
    (flags_int,) = struct.unpack('<I', data[offset:offset + 4])
    flags = constants.parse_flags(flags_int)
    offset += 4

    # Timestamp: uint64 LE
    (timestamp,) = struct.unpack('<Q', data[offset:offset + 8])
    offset += 8

    # Header separator (skip)
    offset += len(constants.HEADER_SEPARATOR)

    # file_type_len + file_type
    (file_type_len,) = struct.unpack('<H', data[offset:offset + 2])
    offset += 2
    file_type = data[offset:offset + file_type_len].decode('utf-8')
    offset += file_type_len

    # filename_len + filename
    (filename_len,) = struct.unpack('<H', data[offset:offset + 2])
    offset += 2
    filename = data[offset:offset + filename_len].decode('utf-8')
    offset += filename_len

    # Sizes
    (original_size,) = struct.unpack('<Q', data[offset:offset + 8])
    offset += 8
    (compressed_size,) = struct.unpack('<Q', data[offset:offset + 8])

    return {
        "format_version": version,
        "original_filename": filename,
        "file_type": file_type,
        "timestamp": timestamp,
        "flags": flags,
        "original_size": original_size,
        "compressed_size": compressed_size,
    }
