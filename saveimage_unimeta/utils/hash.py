"""A utility for calculating the SHA256 hash of a file.

This module provides a function for computing the SHA256 hash of a file, with
an in-memory cache to avoid recomputing hashes for the same file.
"""
import hashlib

cache_model_hash: dict[str, str] = {}


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
