import hashlib

cache_model_hash: dict[str, str] = {}


def calc_hash(filename: str, *, full: bool = True) -> str:
    """Return sha256 hash (full 64 chars by default).

    Legacy callers expected truncated (10) elsewhere, so sidecar logic now
    requests full and truncation happens at the formatting layer.
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
