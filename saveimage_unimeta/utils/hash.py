"""A utility for calculating the SHA256 hash of a file.

This module provides a function for computing the SHA256 hash of a file, with
an in-memory cache to avoid recomputing hashes for the same file. It also
exposes :func:`calc_all_hashes`, a single-pass reader that computes the four
Civitai/A1111-compatible hashes (AutoV1, AutoV2, AutoV3, and full SHA-256) in
one file scan.
"""
import hashlib
import json
import os
import struct

cache_model_hash: dict[str, str] = {}

# Civitai AutoV1 samples a fixed 64 KiB block at a 1 MiB offset.
AUTO_V1_OFFSET = 0x100000
AUTO_V1_SIZE = 0x10000
# AutoV2 is the first 10 hex chars of the full SHA-256.
AUTO_V2_CHARS = 10
# AutoV3 is the first 12 hex chars of the safetensors *payload* digest.
AUTO_V3_CHARS = 12

_HASH_CHUNK_SIZE = 1024 * 1024
_SAFETENSORS_LENGTH_BYTES = 8
_MIN_SAFETENSORS_HEADER_BYTES = 2
_MAX_SAFETENSORS_HEADER_BYTES = 16 * 1024 * 1024


def calc_hash(filename: str, *, full: bool = True) -> str:
    """Calculate the SHA256 hash of a file.

    This function computes the SHA256 hash of a given file. It includes an
    in-memory cache to store the results for previously hashed files, which
    can improve performance when the same file is hashed multiple times.

    Args:
        filename (str): The path to the file to be hashed.
        full (bool, optional): If True, the full 64-character hash is
            returned. If False, a truncated 10-character hash is returned for
            legacy compatibility. Defaults to True.

    Returns:
        str: The SHA256 hash of the file.
    """
    if filename in cache_model_hash and full:
        return cache_model_hash[filename]
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    digest = sha256_hash.hexdigest()
    if full:
        cache_model_hash[filename] = digest
        return digest
    return digest[:10]


def _safetensors_payload_offset(path: str) -> int | None:
    """Return the byte offset of a safetensors payload, or ``None``.

    Safetensors files begin with an 8-byte little-endian header length followed
    by that many bytes of JSON header. The payload (tensor data) starts
    immediately after. Non-safetensors files and malformed headers return
    ``None``.
    """
    if os.path.splitext(path)[1].casefold() != ".safetensors":
        return None
    try:
        with open(path, "rb") as handle:
            raw_length = handle.read(_SAFETENSORS_LENGTH_BYTES)
            if len(raw_length) != _SAFETENSORS_LENGTH_BYTES:
                return None
            header_length = struct.unpack("<Q", raw_length)[0]
            if header_length < _MIN_SAFETENSORS_HEADER_BYTES or header_length > _MAX_SAFETENSORS_HEADER_BYTES:
                return None
            header = handle.read(header_length)
    except OSError:
        return None
    try:
        decoded = json.loads(header.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return _SAFETENSORS_LENGTH_BYTES + header_length if isinstance(decoded, dict) else None


def calc_all_hashes(path: str) -> dict[str, str | None]:
    """Compute all four Civitai/A1111 hashes in a single file scan.

    Returns a dict with keys ``sha256`` (64 chars), ``auto_v2`` (10 chars),
    ``auto_v1`` (8 chars), and ``auto_v3`` (12 chars, or ``None`` for
    non-safetensors files).

    Args:
        path (str): The path to the file to be hashed.

    Returns:
        dict: The computed hashes keyed by algorithm name.

    Raises:
        OSError: If the file cannot be read.
    """
    payload_offset = _safetensors_payload_offset(path)
    full_digest = hashlib.sha256()
    payload_digest = hashlib.sha256() if payload_offset is not None else None
    auto_v1_bytes = bytearray()
    position = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            full_digest.update(chunk)
            chunk_end = position + len(chunk)
            # Collect the AutoV1 window [AUTO_V1_OFFSET, AUTO_V1_OFFSET + AUTO_V1_SIZE).
            auto_start = max(position, AUTO_V1_OFFSET)
            auto_end = min(chunk_end, AUTO_V1_OFFSET + AUTO_V1_SIZE)
            if auto_start < auto_end:
                auto_v1_bytes.extend(chunk[auto_start - position : auto_end - position])
            # Hash only the payload (everything after the safetensors header).
            if payload_digest is not None and payload_offset is not None and chunk_end > payload_offset:
                payload_start = max(position, payload_offset)
                payload_digest.update(chunk[payload_start - position :])
            position = chunk_end
    sha256 = full_digest.hexdigest()
    return {
        "sha256": sha256,
        "auto_v2": sha256[:AUTO_V2_CHARS],
        "auto_v1": hashlib.sha256(auto_v1_bytes).hexdigest()[:8],
        "auto_v3": payload_digest.hexdigest()[:AUTO_V3_CHARS] if payload_digest is not None else None,
    }


__all__ = ["AUTO_V1_OFFSET", "AUTO_V1_SIZE", "calc_all_hashes", "calc_hash"]
