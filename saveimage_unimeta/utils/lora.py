"""Provides utilities for indexing and parsing LoRA files.

This module includes functions for creating an in-memory index of available
LoRA files for fast lookups, as well as helpers for parsing the LoRA syntax
used in prompts (e.g., `<lora:name:strength>`). This allows for the efficient
extraction and resolution of LoRA metadata from a ComfyUI workflow.
Includes:
* One-time index mapping LoRA base names to on-disk locations (for fast lookup).
"""

import logging
import os
import re

import folder_paths
from .pathresolve import SUPPORTED_MODEL_EXTENSIONS
import json

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

    Build an in-memory index of LoRA files for fast lookups.

    This function scans the LoRA directories specified in ComfyUI's
    `folder_paths`, creating an index that maps the base name of each LoRA file
    to its full path and filename. The index is built only once and is then
    cached for subsequent calls.
    """
    global _LORA_INDEX, _LORA_INDEX_BUILT
    if _LORA_INDEX_BUILT:
        return

    logger.info("[Metadata Lib] Building LoRA file index for the first time...")
    _LORA_INDEX = {}
    lora_paths = folder_paths.get_folder_paths("loras")
    extensions = list(SUPPORTED_MODEL_EXTENSIONS)

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
    try:
        dump_env = os.environ.get("METADATA_DUMP_LORA_INDEX")
        if dump_env:
            dump_path = dump_env.strip()
            if dump_path.lower() == "1":
                dump_path = os.path.join(os.getcwd(), "_lora_index_dump.json")
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(_LORA_INDEX, f, indent=2, sort_keys=True)
            logger.info("[Metadata Lib] LoRA index dumped to %s", dump_path)
    except Exception as e:  # pragma: no cover - diagnostic optional
        logger.debug("[Metadata Lib] Failed dumping LoRA index: %r", e)


def find_lora_info(base_name: str) -> dict[str, str] | None:
    """Find the indexed information for a LoRA by its base name.

    This function looks up a LoRA in the in-memory index created by
    `build_lora_index`.

    Args:
        base_name (str): The base name of the LoRA file (without the
            extension).

    Returns:
        dict[str, str] | None: A dictionary containing the `filename` and
            `abspath` of the LoRA, or None if not found.
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
    """Parse LoRA tags in text into (raw_names, model_strengths, clip_strengths).

    - Uses STRICT first, then LEGACY fallback where clip=sm when missing or non-numeric.
    - Names are not resolved to filenames here; call ``resolve_lora_display_names`` as needed.

    Return the first element of a list or the value itself if not a list.

    Args:
        val: The value to be coerced.

    Returns:
        str: The first element of the list or the string representation of the
            value.
    """
    if isinstance(val, list):
        return val[0] if val else ""
    return val if isinstance(val, str) else ""


def parse_lora_syntax(text: str) -> tuple[list[str], list[float], list[float]]:
    """Parse LoRA syntax from a string.

    This function uses regular expressions to find and parse LoRA tags in the
    format `<lora:name:model_strength:clip_strength>` from a given text. It
    supports both a strict format and a legacy format for backward
    compatibility.

    Args:
        text (str): The text to be parsed.

    Returns:
        tuple[list[str], list[float], list[float]]: A tuple containing three
            lists: the raw names of the LoRAs, their model strengths, and their
            CLIP strengths.
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
    """Resolve raw LoRA names to their display filenames.

    This function takes a list of raw LoRA base names and looks them up in the
    LoRA index to find their full filenames.

    Args:
        raw_names (list[str]): A list of raw LoRA base names.

    Returns:
        list[str]: A list of resolved LoRA filenames.
    """
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
