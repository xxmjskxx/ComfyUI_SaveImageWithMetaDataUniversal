"""Provides utilities for resolving artifact paths and calculating hashes.

This module contains functions for resolving the file paths of various
artifacts, such as models, VAEs, and LoRAs, from their names. It also
includes a utility for calculating the SHA256 hash of a file with sidecar
caching.

Unified artifact name → path + hashing helpers (Phase 1).

Introduces consolidation primitives without refactoring existing call sites yet.
Future phases can migrate model / VAE / LoRA / UNet hash functions to use these
helpers. For now they provide:

- Ordered extension preference constant (`EXTENSION_ORDER`).
- Trailing punctuation normalization (Windows-friendly) via `sanitize_candidate`.
- Generic recursive resolution: `try_resolve_artifact` handling list / tuple /
  dict / attribute forms uniformly with depth guard.
- Sidecar based hashing utility `load_or_calc_hash` (shared logic prototype).

Design goals:
- Non-invasive: existing behavior unchanged until explicit adoption.
- Deterministic ordering & minimal logging except in debug contexts.
- Extensibility: post-resolvers (e.g., LoRA index) can be chained later.

NOTE: This module intentionally duplicates *some* logic now present in
`defs/formatters.py`; subsequent refactors will remove that duplication once
stability is verified.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import logging
import os
from typing import Any
from collections.abc import Callable, Iterable, Sequence

import folder_paths

try:  # local import guarded for tests (calc_hash optional patch)
    from .hash import calc_hash
except (ImportError, ModuleNotFoundError):  # pragma: no cover - test fallback

    def calc_hash(path: str) -> str:  # type: ignore
        """A fallback hash calculation function for testing."""
        import hashlib

        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()


# Central, user-maintainable list of supported model/LoRA/VAE/UNet/embedding extensions
# Order matters: earlier entries are preferred when multiple variants share a stem.
SUPPORTED_MODEL_EXTENSIONS: tuple[str, ...] = (
    ".safetensors",
    ".st",
    ".ckpt",
    ".pt",
    ".bin",
)

# Backward compatibility alias (older code/tests may import EXTENSION_ORDER)
EXTENSION_ORDER: tuple[str, ...] = SUPPORTED_MODEL_EXTENSIONS
RESOLUTION_ATTR_KEYS: tuple[str, ...] = (
    "ckpt_name",
    "model_name",
    "model",
    "name",
    "filename",
    "path",
    "model_path",
    "lora_name",
    "unet_name",
)

logger = logging.getLogger(__name__)

# Captured candidate names from the most recent _probe_folder invocation (debug tooling).
_LAST_PROBE_CANDIDATES: list[str] = []

# Precompiled full-hex regex for fast 64-char validation
_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sanitize_candidate(name: str, trim_trailing_punct: bool = True) -> str:
    """Normalize a candidate filename.

    This function sanitizes a filename by stripping outer whitespace and
    quotes. It also provides an option to trim trailing punctuation, which is
    useful for ensuring cross-platform compatibility, particularly with
    Windows.

    Behavior and rationale:
    - Strips surrounding single/double quotes when the entire string is quoted.
    - Optionally trims trailing spaces and dots only at the very end of the
      string (internal punctuation is preserved). This is for Windows
      portability: the Win32 layer normalizes paths so a trailing space/dot is
      disallowed or silently collapsed (e.g., "foo." and "foo " map to
      "foo"). Trimming here avoids lookup/hashing mismatches across OSes.

    Note: This function is conservative by design and does not alter internal
    dots or spaces, only terminal punctuation when enabled.

    Args:
        name (str): The filename to be sanitized.
        trim_trailing_punct (bool, optional): If True, trailing spaces and
            dots are removed. Defaults to True.

    Returns:
        str: The sanitized filename.
    """
    if not isinstance(name, str):  # defensive
        return str(name)
    # Strip outer whitespace then symmetric single/double quote wrapping
    cleaned = name.strip()
    if (cleaned.startswith("'") and cleaned.endswith("'")) or (cleaned.startswith('"') and cleaned.endswith('"')):
        if len(cleaned) >= 2:
            cleaned = cleaned[1:-1]
    if trim_trailing_punct:
        # Repeated trailing spaces/dots collapsed.
        while cleaned.endswith(" ") or cleaned.endswith("."):
            cleaned = cleaned[:-1]
            if not cleaned:
                break
    return cleaned


@dataclass(slots=True)
class ResolutionResult:
    """A data class to hold the results of artifact resolution.

    Attributes:
        display_name (str): The display name of the artifact.
        full_path (str | None): The absolute path to the artifact file, or
            None if not found.
    """

    display_name: str
    full_path: str | None


def _iter_container_candidates(container: Any) -> Iterable[Any]:
    """Iterate over potential artifact names within a container.

    This function extracts candidate names from various container types, such
    as lists, tuples, dictionaries, and objects with specific attributes.

    Args:
        container (Any): The container to be iterated over.

    Yields:
        Iterable[Any]: An iterator over the candidate names.
    """
    if isinstance(container, list | tuple):
        yield from container
    elif isinstance(container, dict):
        for key in RESOLUTION_ATTR_KEYS:
            if key in container and container[key]:
                yield container[key]
    else:  # object with attributes
        for attr in RESOLUTION_ATTR_KEYS:
            if hasattr(container, attr):
                try:
                    val = getattr(container, attr)
                except Exception:  # pragma: no cover
                    continue
                if val:
                    yield val


def has_supported_extension(name: str) -> bool:
    """Check if a filename has a supported model extension.

    Args:
        name (str): The filename to be checked.

    Returns:
        bool: True if the filename has a supported extension, False otherwise.
    """
    ln = name.lower()
    return any(ln.endswith(ext) for ext in SUPPORTED_MODEL_EXTENSIONS)


def _probe_folder(kind: str, base_name: str) -> str | None:
    """Search for an artifact in a specific folder.

    This function attempts to find an artifact by its base name within a folder
    of a given kind (e.g., 'checkpoints', 'loras'). It performs a direct
    lookup and also tries adding supported extensions if the direct lookup
    fails.

    Attempt direct + extension fallback lookups for *base_name* with debug candidate capture.

    Enhancements over earlier version:
      * Always records attempted candidate names into _LAST_PROBE_CANDIDATES.
      * When a recognized extension lookup fails, still performs extension probing on the stem.
      * Treats unknown/numeric extensions (e.g. .01) as part of stem and probes normal extension list.

    Args:
        kind (str): The kind of folder to search in.
        base_name (str): The base name of the artifact to find.

    Returns:
        str | None: The absolute path to the found artifact, or None if not
            found.
    """
    _LAST_PROBE_CANDIDATES.clear()
    _LAST_PROBE_CANDIDATES.append(base_name)
    # First attempt raw
    try:
        raw = folder_paths.get_full_path(kind, base_name)
        if raw and os.path.exists(raw):
            return raw
    except (FileNotFoundError, OSError):  # pragma: no cover
        pass

    stem, ext = os.path.splitext(base_name)
    # If extension unrecognized (numeric suffix) treat as part of stem so we still probe EXTENSION_ORDER.
    recognized = ext.lower() in EXTENSION_ORDER if ext else False
    if ext and not recognized:
        stem = base_name
        ext = ""

    candidate_names: list[str] = []
    if ext and recognized:
        # Provided recognized extension but direct lookup failed:
        # attempt sanitized variant + fallback probing using stem
        sanitized = sanitize_candidate(base_name)
        if sanitized != base_name:
            candidate_names.append(sanitized)
        stem_only = os.path.splitext(sanitized)[0]
        for e in EXTENSION_ORDER:
            if stem_only + e not in candidate_names:
                candidate_names.append(stem_only + e)
    else:
        sanitized_stem = sanitize_candidate(stem)
        for e in EXTENSION_ORDER:
            candidate_names.append(sanitized_stem + e)
        if sanitized_stem != stem:
            for e in EXTENSION_ORDER:
                candidate_names.append(stem + e)

    for name in candidate_names:
        _LAST_PROBE_CANDIDATES.append(name)
        try:
            cand = folder_paths.get_full_path(kind, name)
            if cand and os.path.exists(cand):
                return cand
        except (FileNotFoundError, OSError):  # pragma: no cover
            continue
    return None


def try_resolve_artifact(
    kind: str,
    name_like: Any,
    *,
    post_resolvers: Sequence[Callable[[str], str | None]] | None = None,
    max_depth: int = 5,
) -> ResolutionResult:
    """Resolve an artifact name to its full path.

    This function attempts to find the full path of an artifact given a
    "name-like" object, which can be a string, list, tuple, dictionary, or
    other object containing a name reference. It uses a recursive approach to
    search for a valid path and can be extended with post-resolver functions
    for custom lookup logic.

    Args:
        kind (str): The kind of artifact to resolve (e.g., 'checkpoints',
            'loras').
        name_like (Any): The object containing the name reference.
        post_resolvers (Sequence[Callable[[str], str | None]] | None, optional):
            A sequence of functions to be called if the primary resolution
            fails. Defaults to None.
        max_depth (int, optional): The maximum recursion depth. Defaults to 5.

    Returns:
        ResolutionResult: A `ResolutionResult` object containing the display
            name and the full path of the artifact.
    """
    visited_ids: set[int] = set()

    def _recurse(candidate: Any, depth: int = 0) -> tuple[str, str | None]:
        display_value = str(candidate)
        if depth > max_depth:
            return display_value, None
        candidate_id = id(candidate)
        if candidate_id in visited_ids:
            return display_value, None
        visited_ids.add(candidate_id)

        # Direct string case
        if isinstance(candidate, str):
            path = _probe_folder(kind, candidate)
            return candidate, path

        # Container cases
        if isinstance(candidate, list | tuple | dict) or any(hasattr(candidate, attr) for attr in RESOLUTION_ATTR_KEYS):
            for nested_candidate in _iter_container_candidates(candidate):
                nested_display, nested_path = _recurse(nested_candidate, depth + 1)
                if nested_path:
                    return nested_display, nested_path
            return display_value, None

        # Path-like object (e.g., pathlib.Path) – strings already handled above
        if hasattr(candidate, '__fspath__') or isinstance(candidate, os.PathLike):
            try:
                fspath = os.fspath(candidate)
                if os.path.exists(fspath):
                    return fspath, fspath
            except (OSError, TypeError):  # pragma: no cover
                pass
        return display_value, None

    display_name, path = _recurse(name_like, 0)

    if not path and post_resolvers:
        for resolver in post_resolvers:
            try:
                path = resolver(display_name)
            except Exception:  # pragma: no cover
                path = None
            if path and os.path.exists(path):  # final validation
                break
            else:
                path = None

    return ResolutionResult(display_name=display_name, full_path=path)


def load_or_calc_hash(
    filepath: str,
    *,
    truncate: int | None = 10,
    sidecar_ext: str = ".sha256",
    on_compute: Callable[[str], None] | None = None,
    sidecar_error_cb: Callable[[str, Exception], None] | None = None,
    force_rehash: bool | None = None,
) -> str | None:
    """Load a hash from a sidecar file or calculate and save it.

    This function provides an efficient way to get the hash of a file by
    caching the result in a sidecar file. If the sidecar file exists, the hash
    is read from it; otherwise, the hash is computed, saved to the sidecar,
    and then returned.

    Args:
        filepath (str): The absolute path to the file to be hashed.
        truncate (int, optional): The number of characters to truncate the hash
            to. If None, the full hash is returned. Defaults to 10.
        sidecar_ext (str, optional): The extension for the sidecar file.
            Defaults to ".sha256".
        on_compute (Callable[[str], None] | None, optional): A callback to be
            invoked when a new hash is computed. Defaults to None.
        sidecar_error_cb (Callable[[str, Exception], None] | None, optional):
            A callback for handling errors when writing to the sidecar file.
            Defaults to None.
        force_rehash (bool | None, optional): If True, the hash is recomputed
            even if a sidecar file exists. Defaults to None.

    Returns:
        str | None: The (possibly truncated) hash, or None on failure.
    """
    if not filepath or not os.path.exists(filepath):
        return None
    base, _ = os.path.splitext(filepath)
    sidecar = base + sidecar_ext
    full_hash: str | None = None
    if force_rehash is None:
        # Allow runtime override (env) to force recomputation (debug / mismatch diagnosis).
        force_rehash = os.environ.get("METADATA_FORCE_REHASH") == "1"

    if not force_rehash and os.path.exists(sidecar):
        try:
            with open(sidecar, encoding="utf-8") as f:
                candidate = f.read().strip()
                if candidate and _HEX64_RE.match(candidate):
                    full_hash = candidate.lower()
                else:
                    full_hash = None
        except OSError as e:  # pragma: no cover
            logger.debug("[PathResolve] Failed reading sidecar '%s': %s", sidecar, e)
    if not full_hash:
        try:
            full_hash = calc_hash(filepath)
        except OSError as e:  # pragma: no cover
            logger.debug("[PathResolve] Could not hash '%s': %s", filepath, e)
            return None
        if on_compute:
            try:
                on_compute(filepath)
            except Exception:  # pragma: no cover
                pass
        # Always ensure sidecar has FULL 64-char hash (never truncated)
        if full_hash and len(full_hash) == 64:
            try:
                with open(sidecar, "w", encoding="utf-8") as f:
                    f.write(full_hash)
            except OSError as e:  # pragma: no cover
                logger.debug("[PathResolve] Could not write sidecar '%s': %s", sidecar, e)
                if sidecar_error_cb:
                    try:
                        sidecar_error_cb(sidecar, e)
                    except Exception:
                        # Ignore errors from sidecar_error_cb to avoid interfering with main flow.
                        pass
    return full_hash if truncate is None else full_hash[:truncate]


__all__ = [
    "EXTENSION_ORDER",
    "SUPPORTED_MODEL_EXTENSIONS",
    "has_supported_extension",
    "sanitize_candidate",
    "try_resolve_artifact",
    "load_or_calc_hash",
    "ResolutionResult",
    "_LAST_PROBE_CANDIDATES",
]
