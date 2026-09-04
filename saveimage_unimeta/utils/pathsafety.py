"""Path-safety helpers for the save node's expanded filename template.

Filename tokens such as ``%model%`` or ``%pprompt%`` interpolate user-controlled
text into the output path. This module guarantees that whatever those tokens
produce, the final path is a safe *relative* path inside the output directory:
absolute paths, drive letters, UNC roots, directory traversal (``..``), reserved
Windows device names, and invalid filename characters are all neutralized. The
functions always return a usable fallback rather than raising, so an image is
never skipped because of an unsafe filename.
"""

from __future__ import annotations

import re
import unicodedata

MAX_TEMPLATE_LENGTH = 512
MAX_COMPONENT_LENGTH = 120

# Characters invalid in Windows filenames, plus C0 control characters.
_INVALID_FILENAME = re.compile(r'[<>:"|?*\x00-\x1f]')

_RESERVED_WINDOWS_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)

_FALLBACK_COMPONENT = "image"


def sanitize_component(value: str) -> str:
    """Return a single safe filename component for ``value``.

    Normalizes Unicode, replaces invalid characters and separators with ``_``,
    strips trailing dots/spaces, neutralizes reserved Windows device names, and
    clamps the length. The result is always non-empty and filesystem-safe.
    """
    normalized = unicodedata.normalize("NFC", str(value))
    cleaned = _INVALID_FILENAME.sub("_", normalized).replace("\\", "_").replace("/", "_")
    cleaned = cleaned.rstrip(" .")
    if not cleaned:
        return _FALLBACK_COMPONENT
    # Windows treats the pre-extension stem as a device name after stripping
    # trailing dots/spaces, e.g. "CON .txt" still refers to the reserved "CON".
    stem = cleaned.split(".", 1)[0].rstrip(" .").upper()
    if stem in _RESERVED_WINDOWS_NAMES:
        cleaned = "_" + cleaned
    return cleaned[:MAX_COMPONENT_LENGTH]


def sanitize_filename(filename_prefix: str) -> str:
    """Return a safe, relative output path derived from ``filename_prefix``.

    Normalizes separators, strips drive-letter/UNC/root prefixes, drops ``.``,
    ``..``, and empty components, sanitizes each remaining component, and clamps
    the overall length. The result never escapes the output directory.
    """
    normalized = unicodedata.normalize("NFC", str(filename_prefix)).replace("\\", "/")
    drive = re.match(r"^[a-zA-Z]:", normalized)
    if drive:
        normalized = normalized[drive.end():]
    normalized = normalized.lstrip("/")
    parts = [part for part in normalized.split("/") if part not in {"", ".", ".."}]
    safe_parts = [sanitize_component(part) for part in parts]
    if not safe_parts:
        return _FALLBACK_COMPONENT
    result = "/".join(safe_parts)
    if len(result) > MAX_TEMPLATE_LENGTH:
        # Truncation may land mid-component on a trailing dot or separator;
        # strip both so the result never ends in a directory-like "/" or ".".
        result = result[:MAX_TEMPLATE_LENGTH].rstrip(" /.")
        if not result:
            return _FALLBACK_COMPONENT
    return result


__all__ = [
    "MAX_COMPONENT_LENGTH",
    "MAX_TEMPLATE_LENGTH",
    "sanitize_component",
    "sanitize_filename",
]
