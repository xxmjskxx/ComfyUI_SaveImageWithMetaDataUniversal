"""Bounded, non-mutating redaction for embedded workflow metadata.

ComfyUI workflow JSON (both the executed prompt and the UI-side
``extra_pnginfo`` payload) can contain secret-like values such as API keys,
passwords, bearer tokens, or absolute filesystem paths. Before that JSON is
embedded into saved images it is passed through :func:`sanitize_metadata_json`,
which returns a sanitized *copy* and never mutates the input.

The sanitizer is bounded so a pathological payload cannot cause unbounded work
or memory use; exceeding the limits raises :class:`MetadataSanitizationError`
and callers should fall back to embedding the raw (unsanitized) value rather
than failing the save.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping

MAX_METADATA_DEPTH = 32
MAX_METADATA_ITEMS = 500_000
MAX_METADATA_KEY_CHARS = 1_024
MAX_METADATA_STRING_CHARS = 1_000_000

REDACTED_SECRET = "<redacted-secret>"
REDACTED_PATH = "<redacted-path>"

# Absolute Windows (drive-letter or UNC) and POSIX home paths.
_ABSOLUTE_PATH_FRAGMENT = re.compile(
    r"(?i)(?:[a-z]:[\\/]|\\\\)[^\s\"'<>|]+|/(?:Users|home)/[^\s\"'<>|]+"
)
# "Bearer <credential>" literals.
_BEARER_SECRET = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")

# Key names whose values are always redacted in full, regardless of shape.
_SENSITIVE_KEYS = frozenset(
    {
        "accesstoken",
        "apikey",
        "api_key",
        "authorization",
        "bearer",
        "password",
        "refreshtoken",
        "secret",
        "token",
    }
)

# Control characters that are allowed to survive cleaning (newlines in prompts).
_KEEP_CONTROL = ("\n", "\r", "\t")


class MetadataSanitizationError(ValueError):
    """Raised when embedded metadata exceeds a configured safety limit."""


class _Budget:
    """Mutable counters threaded through the recursive sanitizer."""

    def __init__(self) -> None:
        self.items = 0
        self.redactions = 0


def _normalized_key(value: object) -> str:
    key = unicodedata.normalize("NFC", str(value))
    if not key or len(key) > MAX_METADATA_KEY_CHARS or "\x00" in key:
        raise MetadataSanitizationError("metadata_key_invalid")
    return key


def _is_sensitive_key(key: str) -> bool:
    normalized = "".join(ch for ch in key.casefold() if ch.isalnum())
    return normalized in _SENSITIVE_KEYS


def _clean_text(value: str) -> tuple[str, int]:
    """Normalize one string, removing control chars and redacting secrets/paths.

    Returns the cleaned string and the number of redactions applied.
    """
    if len(value) > MAX_METADATA_STRING_CHARS:
        raise MetadataSanitizationError("metadata_string_limit_exceeded")
    normalized = unicodedata.normalize("NFC", value)
    cleaned = "".join(
        ch if ch in _KEEP_CONTROL or unicodedata.category(ch) != "Cc" else " "
        for ch in normalized
    )
    redacted, path_count = _ABSOLUTE_PATH_FRAGMENT.subn(REDACTED_PATH, cleaned)
    redacted, secret_count = _BEARER_SECRET.subn("Bearer " + REDACTED_SECRET, redacted)
    return redacted, path_count + secret_count


def _sanitize(value: object, budget: _Budget, depth: int, sensitive: bool = False) -> object:
    """Recursively sanitize ``value`` in place-free fashion, returning a copy."""
    if depth > MAX_METADATA_DEPTH:
        raise MetadataSanitizationError("metadata_depth_limit_exceeded")
    budget.items += 1
    if budget.items > MAX_METADATA_ITEMS:
        raise MetadataSanitizationError("metadata_item_limit_exceeded")
    if sensitive:
        budget.redactions += 1
        return REDACTED_SECRET
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MetadataSanitizationError("metadata_number_nonfinite")
        return value
    if isinstance(value, str):
        cleaned, count = _clean_text(value)
        budget.redactions += count
        return cleaned
    if isinstance(value, list | tuple):
        return [_sanitize(item, budget, depth + 1) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for raw_key, item in value.items():
            key = _normalized_key(raw_key)
            if key in result:
                raise MetadataSanitizationError("metadata_key_collision")
            result[key] = _sanitize(item, budget, depth + 1, sensitive=_is_sensitive_key(key))
        return result
    raise MetadataSanitizationError("metadata_value_type_unsupported")


def sanitize_metadata_json(value: object) -> tuple[object, int]:
    """Return a sanitized copy of ``value`` and the number of redactions applied.

    Never mutates ``value``. Raises :class:`MetadataSanitizationError` only when
    the value exceeds configured safety limits (depth/items/string length/key
    validity); the caller is expected to degrade gracefully (e.g. embed the raw
    value or omit it) rather than fail the save.
    """
    budget = _Budget()
    sanitized = _sanitize(value, budget, 0)
    return sanitized, budget.redactions


__all__ = [
    "MAX_METADATA_DEPTH",
    "MAX_METADATA_ITEMS",
    "MAX_METADATA_KEY_CHARS",
    "MAX_METADATA_STRING_CHARS",
    "MetadataSanitizationError",
    "REDACTED_PATH",
    "REDACTED_SECRET",
    "sanitize_metadata_json",
]
