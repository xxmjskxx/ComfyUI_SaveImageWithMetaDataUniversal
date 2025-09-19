"""LoRA indexing and lookup utilities.

Builds a one-time in-memory index mapping LoRA base names to their on-disk
locations to accelerate hash computation and metadata enrichment.
"""

import logging
import os

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
        * Supported extensions: ``.safetensors``, ``.pt``, ``.bin``, ``.ckpt``.

    Idempotence:
        Subsequent calls short‑circuit once the index has been built (``_LORA_INDEX_BUILT`` flag).

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


__all__ = ["build_lora_index", "find_lora_info"]
