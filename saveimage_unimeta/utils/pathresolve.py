"""Unified artifact name → path + hashing helpers (Phase 1).

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

import folder_paths  # type: ignore

try:  # local import guarded for tests (calc_hash optional patch)
    from .hash import calc_hash  # type: ignore
except (ImportError, ModuleNotFoundError):  # pragma: no cover - test fallback
    def calc_hash(path: str) -> str:  # type: ignore
        import hashlib
        with open(path, 'rb') as f:
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
    """Return a normalized candidate filename stem.

    Behavior and rationale:
    - Strips surrounding single/double quotes when the entire string is quoted.
    - Optionally trims trailing spaces and dots only at the very end of the
      string (internal punctuation is preserved). This is for Windows
      portability: the Win32 layer normalizes paths so a trailing space/dot is
      disallowed or silently collapsed (e.g., "foo." and "foo " map to
      "foo"). Trimming here avoids lookup/hashing mismatches across OSes.

    Note: This function is conservative by design and does not alter internal
    dots or spaces, only terminal punctuation when enabled.
    """
    if not isinstance(name, str):  # defensive
        return str(name)
    # Strip outer whitespace then symmetric single/double quote wrapping
    cleaned = name.strip()
    if (cleaned.startswith("'") and cleaned.endswith("'")) or (
        cleaned.startswith('"') and cleaned.endswith('"')
    ):
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
    display_name: str
    full_path: str | None


def _iter_container_candidates(container: Any) -> Iterable[Any]:
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
    """Return True if *name* ends with any supported extension (case-insensitive)."""
    ln = name.lower()
    return any(ln.endswith(ext) for ext in SUPPORTED_MODEL_EXTENSIONS)


def _probe_folder(kind: str, base_name: str) -> str | None:
    """Attempt direct + extension fallback lookups for *base_name* with debug candidate capture.

    Enhancements over earlier version:
      * Always records attempted candidate names into _LAST_PROBE_CANDIDATES.
      * When a recognized extension lookup fails, still performs extension probing on the stem.
      * Treats unknown/numeric extensions (e.g. .01) as part of stem and probes normal extension list.
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
    """Generic resolution algorithm.

    Args:
        kind: folder type for `folder_paths` (e.g. 'checkpoints', 'loras').
        name_like: Arbitrary structure containing a name reference.
        post_resolvers: Optional callables taking the *display_name* and
            returning an absolute path or None (e.g. LoRA index lookup) if the
            primary folder/extension strategy fails.
        max_depth: Prevent runaway recursion on pathological nested structures.

    Returns:
        ResolutionResult(display_name, full_path|None)
    """
    visited: set[int] = set()

    def _recurse(obj: Any, depth: int = 0) -> tuple[str, str | None]:
        if depth > max_depth:
            return str(obj), None
        oid = id(obj)
        if oid in visited:
            return str(obj), None
        visited.add(oid)

        # Direct string case
        if isinstance(obj, str):
            path = _probe_folder(kind, obj)
            return obj, path

        # Container cases
        if isinstance(obj, list | tuple | dict) or any(
            hasattr(obj, a) for a in RESOLUTION_ATTR_KEYS
        ):
            for cand in _iter_container_candidates(obj):
                dn, fp = _recurse(cand, depth + 1)
                if fp:
                    return dn, fp
            return str(obj), None

        # Path-like direct file
        try:
            if isinstance(obj, str) and os.path.exists(obj):
                return obj, obj
        except OSError:  # pragma: no cover
            pass
        return str(obj), None

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
    truncate: int = 10,
    sidecar_ext: str = ".sha256",
    on_compute: Callable[[str], None] | None = None,
    sidecar_error_cb: Callable[[str, Exception], None] | None = None,
    force_rehash: bool | None = None,
) -> str | None:
    """Return truncated hash loading/writing a sidecar opportunistically.
    Full hash is save to sidecar for compatibility with existing usages in other modules and programs.
    Truncated to 10 chars for compatibility with Civitai and other sites/tools that read metadata hashes.

    Args:
        filepath: Absolute path to file to hash.
        truncate: Number of starting characters to retain (None → full hash).
        sidecar_ext: Extension appended to base path for caching.
        on_compute: Optional callback invoked only when a new hash is computed.

    Returns:
        (Possibly truncated) hex hash or None on failure.
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
