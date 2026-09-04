"""Validation and deterministic serialization for the four Civitai hashes.

The ``HASH_PRIORITY`` table lists the supported algorithms in authority order
with their exact hex lengths. ``normalize_hash`` enforces length + hex validity
so malformed values are never mistaken for identity, and ``HashRecord`` is the
canonical in-memory shape shared by the hash cache, the hash computation
pipeline, and the structured ``Hash detail`` metadata section.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

# (external name, field name, hex length) in strongest-first order.
HASH_PRIORITY = (
    ("SHA256", "sha256", 64),
    ("AutoV3", "auto_v3", 12),
    ("AutoV2", "auto_v2", 10),
    ("AutoV1", "auto_v1", 8),
)

_HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")


def normalize_hash(value: object, *, length: int) -> str | None:
    """Return one exact-length lowercase hex hash value or ``None``."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if len(stripped) != length or _HEX_RE.fullmatch(stripped) is None:
        return None
    return stripped.casefold()


@dataclass(frozen=True, slots=True)
class HashRecord:
    """One resource's known hashes; absent algorithms are ``None``."""

    sha256: str | None = None
    auto_v3: str | None = None
    auto_v2: str | None = None
    auto_v1: str | None = None

    @property
    def is_empty(self) -> bool:
        return not any((self.sha256, self.auto_v3, self.auto_v2, self.auto_v1))


def hash_record_from_mapping(value: object) -> HashRecord | None:
    """Parse a ``{algorithm: hex}`` mapping into a validated ``HashRecord``.

    Returns ``None`` for malformed input or an all-``None`` record, so unknown
    or corrupt data is never treated as identity.
    """
    if not isinstance(value, Mapping):
        return None
    normalized = {
        field_name: normalize_hash(value.get(name), length=length)
        for name, field_name, length in HASH_PRIORITY
    }
    record = HashRecord(**normalized)
    return None if record.is_empty else record


def hash_record_to_mapping(record: HashRecord) -> dict[str, str]:
    """Serialize known hashes in deterministic authority order."""
    result: dict[str, str] = {}
    for name, field_name, _length in HASH_PRIORITY:
        value = getattr(record, field_name)
        if value is not None:
            result[name] = value
    return result


def iter_hashes(record: HashRecord) -> Iterator[tuple[str, str]]:
    """Yield known hashes from strongest to weakest."""
    for name, field_name, _length in HASH_PRIORITY:
        value = getattr(record, field_name)
        if value is not None:
            yield name, value


__all__ = [
    "HASH_PRIORITY",
    "HashRecord",
    "hash_record_from_mapping",
    "hash_record_to_mapping",
    "iter_hashes",
    "normalize_hash",
]
