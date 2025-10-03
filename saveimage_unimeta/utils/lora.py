"""LoRA indexing and parsing utilities.

Includes:
* One-time index mapping LoRA base names to on-disk locations (for fast lookup).
* Lightweight syntax parsing helpers for ``<lora:name:sm[:sc]>`` tags shared by ext modules.
"""

import logging
import os
import re

import folder_paths

# --- Caches and Indexes for Performance ---
# This index will be built once and reused to speed up all subsequent LoRA lookups.
_LORA_INDEX: dict[str, dict[str, str]] | None = None
_LORA_INDEX_BUILT: bool = False
logger = logging.getLogger(__name__)


def build_lora_index() -> None:
    """Populate (idempotently) the in-memory LoRA file index.

    Scan order & behavior:
        * Enumerates every directory in ``folder_paths.get_folder_paths('loras')``.
        * Recursively walks subdirectories.
        * Records the FIRST occurrence of each base filename (stem) only.
        * Supported extensions: ``.safetensors``, ``.st``, ``.pt``, ``.bin``, ``.ckpt``.

    Idempotence:
        Subsequent calls short-circuit once the index has been built (``_LORA_INDEX_BUILT`` flag).

    Side Effects:
        Mutates module-level caches ``_LORA_INDEX`` and ``_LORA_INDEX_BUILT``.
    """
    global _LORA_INDEX, _LORA_INDEX_BUILT
    if _LORA_INDEX_BUILT:
        return

    logger.info("[Metadata Lib] Building LoRA file index for the first time...")
    _LORA_INDEX = {}
    lora_paths = folder_paths.get_folder_paths("loras")
    extensions = [".safetensors", ".st", ".pt", ".bin", ".ckpt"]

    for lora_dir in lora_paths:
        for root, _, files in os.walk(lora_dir):
            for file in files:
                file_base, file_ext = os.path.splitext(file)
                # Use the base name as the key for easy lookup
                if file_ext in extensions and file_base not in _LORA_INDEX:
                    _LORA_INDEX[file_base] = {
                        "filename": file,
                        "abspath": os.path.join(root, file),
                    }

    _LORA_INDEX_BUILT = True
    logger.info("[Metadata Lib] LoRA index built with %d entries.", len(_LORA_INDEX))


def find_lora_info(base_name: str) -> dict[str, str] | None:
    """Return indexed metadata for a given LoRA base name.

    Args:
        base_name: Stem of the LoRA file (without extension). Case sensitivity matches on-disk enumeration;
            callers should normalize (e.g. lowercase) if performing broad matching.

    Returns:
        Mapping with keys ``filename`` and ``abspath`` or ``None`` when the stem was not indexed.
    """
    build_lora_index()
    if _LORA_INDEX is None:
        return None
    return _LORA_INDEX.get(base_name)


# -----------------------------
# Shared LoRA syntax utilities
# -----------------------------

# Strict pattern capturing optional separate clip strength:
# <lora:name:model_strength> OR <lora:name:model_strength:clip_strength>
STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
# Fallback (legacy) pattern capturing anything after the second colon
LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")


def coerce_first(val) -> str:
    """Return first element from list-like, or the string itself, else ''."""
    if isinstance(val, list):
        return val[0] if val else ""
    return val if isinstance(val, str) else ""


def parse_lora_syntax(text: str) -> tuple[list[str], list[float], list[float]]:
    """Parse LoRA tags in text into (raw_names, model_strengths, clip_strengths).

    - Uses STRICT first, then LEGACY fallback where clip=sm when missing or non-numeric.
    - Names are not resolved to filenames here; call ``resolve_lora_display_names`` as needed.
    """
    names: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    if not text:
        return names, model_strengths, clip_strengths

    matches = STRICT.findall(text)
    if not matches:
        legacy = LEGACY.findall(text)
        for name, blob in legacy:
            try:
                parts = blob.split(":")
                if len(parts) == 2:
                    ms = float(parts[0])
                    cs = float(parts[1])
                else:
                    ms = float(parts[0])
                    cs = ms
            except Exception:
                ms = cs = 1.0
            names.append(name)
            model_strengths.append(ms)
            clip_strengths.append(cs)
        return names, model_strengths, clip_strengths

    for name, ms_s, cs_s in matches:
        try:
            ms = float(ms_s)
        except Exception:
            ms = 1.0
        try:
            cs = float(cs_s) if cs_s else ms
        except Exception:
            cs = ms
        names.append(name)
        model_strengths.append(ms)
        clip_strengths.append(cs)
    return names, model_strengths, clip_strengths


def resolve_lora_display_names(raw_names: list[str]) -> list[str]:
    """Resolve each raw base name to indexed filename for display when available."""
    out: list[str] = []
    for n in raw_names:
        try:
            info = find_lora_info(n)
            out.append(info["filename"] if info else n)
        except Exception:
            out.append(n)
    return out


__all__ = [
    "build_lora_index",
    "find_lora_info",
    # syntax helpers
    "STRICT",
    "LEGACY",
    "coerce_first",
    "parse_lora_syntax",
    "resolve_lora_display_names",
]
