"""Formatters & hashing helpers for metadata capture.

Provides resilient name resolution for models, VAEs, LoRAs, UNets, plus
embedding extraction utilities and deterministic hashing with optional
use of cached .sha256 sidecar files to avoid recomputation.
"""

import logging
import os
import time
from typing import Any
import sys

import folder_paths  # type: ignore
try:  # Attempt real comfy imports (runtime environment)
    from comfy.sd1_clip import (  # type: ignore
        SD1Tokenizer,
        escape_important,
        token_weights,
        unescape_important,
    )
    from comfy.sdxl_clip import SDXLTokenizer  # type: ignore
    from comfy.text_encoders.flux import FluxTokenizer  # type: ignore
    from comfy.text_encoders.sd2_clip import SD2Tokenizer  # type: ignore
    from comfy.text_encoders.sd3_clip import SD3Tokenizer  # type: ignore
except Exception:  # noqa: BLE001 - provide minimal stubs for tests
    class _BaseTok:
        def encode_with_weights(self, text):  # pragma: no cover - trivial stub
            return []

    SD1Tokenizer = SDXLTokenizer = FluxTokenizer = SD2Tokenizer = SD3Tokenizer = _BaseTok  # type: ignore

    def escape_important(x):  # type: ignore
        return x

    def unescape_important(x):  # type: ignore
        return x

    def token_weights(x):  # type: ignore
        return []

from ..utils.embedding import get_embedding_file_path
from ..utils.hash import calc_hash
from ..utils.lora import find_lora_info
from ..utils.pathresolve import (
    try_resolve_artifact,
    sanitize_candidate,
    EXTENSION_ORDER,
)

import os as _os

# Unified hash logging mode for all artifact types (model, lora, vae, unet, embeddings).
# Modes: none | filename | path | detailed | debug
HASH_LOG_MODE: str = _os.environ.get("METADATA_HASH_LOG_MODE", "none")
# Propagation control (default ON for visibility)
_HASH_LOG_PROPAGATE: bool = _os.environ.get("METADATA_HASH_LOG_PROPAGATE", "1") != "0"

_WARNED_SIDECAR: set[str] = set()
_WARNED_UNRESOLVED: set[str] = set()
_LOGGER_INITIALIZED = False
_HANDLER_TAG = "__hash_logger_handler__"

def set_hash_log_mode(mode: str):
    """Programmatically adjust hash log mode (tests / UI) and re-init logger."""
    global HASH_LOG_MODE, _LOGGER_INITIALIZED
    HASH_LOG_MODE = (mode or "none").lower()
    _LOGGER_INITIALIZED = False  # force re-init next log call


def _ensure_logger():  # runtime init when mode activated
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return
    mode = (HASH_LOG_MODE or "none").lower()
    if mode == "none":
        return
    try:
        # Always set level so even existing handlers receive messages
        logger.setLevel(logging.INFO)

        # Determine if a real (non NullHandler) handler already present
        has_real = any(not isinstance(h, logging.NullHandler) for h in logger.handlers)
        if not has_real:
            # Attach our dedicated stream handler
            h = logging.StreamHandler()
            setattr(h, _HANDLER_TAG, True)
            h.setLevel(logging.INFO)
            h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            logger.addHandler(h)
        # Propagate unless explicitly disabled
        logger.propagate = _HASH_LOG_PROPAGATE
        _LOGGER_INITIALIZED = True
        try:
            logger.info(
                "[Hash] logging initialized (mode=%s propagate=%s handler_added=%s)",
                mode,
                logger.propagate,
                (not has_real),
            )
        except Exception:  # pragma: no cover
            pass
    except Exception:  # pragma: no cover
        # Fallback: direct stderr warning once
        try:
            if not getattr(_ensure_logger, "_warned", False):
                print("[Hash] logger initialization failed", file=sys.stderr)
                _ensure_logger._warned = True  # type: ignore[attr-defined]
        except Exception:
            pass

def _log(kind: str, msg: str, level=logging.INFO):
    mode = (HASH_LOG_MODE or "none").lower()
    if mode == "none":
        return
    _ensure_logger()
    try:
        logger.log(level, f"[Hash] {msg}")
    except Exception:  # pragma: no cover
        pass

def _fmt_display(path: str) -> str:
    mode = (HASH_LOG_MODE or "none").lower()
    if mode in {"path", "detailed", "debug"}:
        return path
    # filename & other modes
    return os.path.basename(path)

def _sidecar_error_once(sidecar: str, exc: Exception):  # noqa: D401
    if sidecar in _WARNED_SIDECAR:
        return
    _WARNED_SIDECAR.add(sidecar)
    _log("generic", f"sidecar write failed {sidecar}: {exc}", level=logging.WARNING)

def _warn_unresolved_once(kind: str, token: str):
    key = f"{kind}:{token}"
    if key in _WARNED_UNRESOLVED:
        return
    _WARNED_UNRESOLVED.add(key)
    _log(kind, f"unresolved {kind} '{token}'", level=logging.WARNING)

def _maybe_debug_candidates(kind: str, display: str):
    from ..utils.pathresolve import _LAST_PROBE_CANDIDATES  # lazy import
    mode = (HASH_LOG_MODE or "none").lower()
    if mode == "debug" and _LAST_PROBE_CANDIDATES:
        _log(kind, f"candidates for '{display}': {_LAST_PROBE_CANDIDATES}")

def _hash_file(kind: str, path: str, truncate: int = 10) -> str | None:
    # Centralized hashing with sidecar callback + timing & debug full hash
    from ..utils.pathresolve import load_or_calc_hash  # local import to avoid cycles
    mode = (HASH_LOG_MODE or "none").lower()
    start = time.perf_counter()
    fresh_computed = {"flag": False}
    def _on_compute(_):
        fresh_computed["flag"] = True
    hashed = load_or_calc_hash(
        path,
        truncate=truncate,
        on_compute=_on_compute,
        sidecar_error_cb=_sidecar_error_once,
    )
    if hashed is not None:
        source = "computed" if fresh_computed["flag"] else "sidecar"
        if mode in {"filename", "path", "detailed", "debug"}:
            _log(kind, f"hash source={source} truncated={hashed}")
    if hashed and mode == "debug" and fresh_computed["flag"]:
        # Retrieve full hash by reloading sidecar (already written) without truncation
        from ..utils.pathresolve import load_or_calc_hash as _lc
        full_hash = _lc(path, truncate=None) or "?"
        dur_ms = (time.perf_counter() - start) * 1000.0
        _log(kind, f"full hash {os.path.basename(path)}={full_hash} ({dur_ms:.1f} ms)")
    return hashed

cache_model_hash = {}
logger = logging.getLogger(__name__)


def _ckpt_name_to_path(name_like: Any) -> tuple[str, str | None]:
    """Unified resolver wrapper for backward compatibility."""
    res = try_resolve_artifact("checkpoints", name_like)
    if res.full_path:
        return res.display_name, res.full_path
    # Legacy fallback (ensures test patches to this module's folder_paths still work)
    if isinstance(name_like, str):
        original = name_like
        sanitized = sanitize_candidate(original)
        candidate = sanitized or original
        full: str | None = None
        # First attempt sanitized/original candidate
        try:
            full = folder_paths.get_full_path("checkpoints", candidate)
        except Exception:  # pragma: no cover
            full = None
        # If direct lookup failed OR produced non-existent path, probe extensions
        if not full or not os.path.exists(full):
            full = _resolve_model_path_with_extensions("checkpoints", candidate)
        # If still unresolved and we altered the name, try original form
        if (not full or not os.path.exists(full)) and candidate != original:
            try:
                full = folder_paths.get_full_path("checkpoints", original)
            except Exception:  # pragma: no cover
                full = None
            if not full or not os.path.exists(full):
                full = _resolve_model_path_with_extensions("checkpoints", original)
        # Final guard: ensure path exists
        if full and not os.path.exists(full):
            full = None
        return candidate, full
    return res.display_name, None


def display_model_name(name_like: Any) -> str:
    """Return a human-friendly model name for display (usually a basename)."""
    dn, fp = _ckpt_name_to_path(name_like)
    try:
        if isinstance(dn, str) and dn:
            return os.path.basename(dn)
    except Exception:
        pass
    if isinstance(fp, str) and fp:
        try:
                return os.path.basename(fp)
        except Exception:
            return fp
    return str(name_like)


def calc_model_hash(model_name: Any, input_data: list) -> str:
    """Return truncated (10 char) sha256 hash for a model.

    Args:
        model_name: Name / path / object representing the checkpoint.
        input_data: Unused (legacy signature compatibility).

    Returns:
        10-character truncated hex hash or 'N/A' if resolution failed.
    """
    mode = (HASH_LOG_MODE or "none").lower()
    display_name, filename = _ckpt_name_to_path(model_name)
    mode = (HASH_LOG_MODE or "none").lower()
    if mode in {"detailed", "debug"}:
        _log("model", f"resolving token={display_name}")
    # If display_name looks like a filename with no resolved path yet, probe extensions directly
    if not filename and isinstance(display_name, str) and not os.path.isabs(display_name):
        maybe_stem, ext = os.path.splitext(display_name)
        if not ext or ext.lower() not in EXTENSION_ORDER:
            # Try extension probing explicitly
            for e in EXTENSION_ORDER:
                try:
                    fp = folder_paths.get_full_path("checkpoints", maybe_stem + e)
                except Exception:
                    fp = None
                if fp and os.path.exists(fp):
                    filename = fp
                    break
    if not filename:
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            if mode in {"detailed", "debug"}:
                _warn_unresolved_once("model", str(display_name))
            return "N/A"
    # Reject obviously invalid filename tokens containing reserved characters
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    if mode in {"detailed", "debug"}:
        exists_flag = bool(filename and os.path.exists(filename))
        _log(
            "model",
            f"resolved (model) {display_name} -> {filename if filename else 'None'} "
            f"exists={exists_flag}",
        )
        _maybe_debug_candidates("model", str(display_name))
    if mode in {"filename", "path", "detailed", "debug"}:
        verb = "hashing"
        # sidecar presence detection (quick)
        base, _ = os.path.splitext(filename)
        sc = base + ".sha256"
        if os.path.exists(sc):
            verb = "reading"
        _log("model", f"{verb} {_fmt_display(filename)} hash")
    hashed = _hash_file("model", filename, truncate=10)
    return hashed if isinstance(hashed, str) else "N/A"


def _vae_name_to_path(model_name: Any) -> tuple[str, str | None]:
    # Unified attempt
    res = try_resolve_artifact("vae", model_name)
    if res.full_path:
        return res.display_name, res.full_path
    # Legacy fallback for test-mocked folder_paths
    if isinstance(model_name, str):
        original = model_name
        sanitized = sanitize_candidate(original)
        candidate = sanitized or original
        full: str | None = None
        try:
                full = folder_paths.get_full_path("vae", candidate)
        except Exception:  # pragma: no cover
            full = None
        if not full or not os.path.exists(full):
            full = _resolve_model_path_with_extensions("vae", candidate)
        if (not full or not os.path.exists(full)) and candidate != original:
            try:
                full = folder_paths.get_full_path("vae", original)
            except Exception:  # pragma: no cover
                full = None
            if not full or not os.path.exists(full):
                full = _resolve_model_path_with_extensions("vae", original)
        if full and not os.path.exists(full):
            full = None
        return candidate, full
    return res.display_name, None


def display_vae_name(name_like: Any) -> str:
    """Return a human-friendly VAE name for display (usually a basename)."""
    dn, fp = _vae_name_to_path(name_like)
    try:
        if isinstance(dn, str) and dn:
            return os.path.basename(dn)
    except Exception:
        pass
    if isinstance(fp, str) and fp:
        try:
                return os.path.basename(fp)
        except Exception:
            return fp
    return str(name_like)


def calc_vae_hash(model_name: Any, input_data: list) -> str:
    """Return truncated (10 char) sha256 hash for a VAE file.

    Args:
        model_name: Name / path / VAE object.
        input_data: Unused (legacy signature compatibility).

    Returns:
        10-character truncated hex hash or 'N/A'.
    """
    display_name, filename = _vae_name_to_path(model_name)
    mode = (HASH_LOG_MODE or "none").lower()
    if mode in {"detailed", "debug"}:
        _log("vae", f"resolving token={display_name}")
    if not filename:
        # Try best-effort: if model_name looked like a path, hash it directly
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            return "N/A"
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    mode = (HASH_LOG_MODE or "none").lower()
    if mode in {"detailed", "debug"}:
        exists_flag = bool(filename and os.path.exists(filename))
        _log(
            "vae",
            f"resolved (vae) {display_name} -> {filename if filename else 'None'} "
            f"exists={exists_flag}",
        )
        _maybe_debug_candidates("vae", str(display_name))
    if mode in {"filename", "path", "detailed", "debug"}:
        verb = "hashing"
        base, _ = os.path.splitext(filename)
        if os.path.exists(base + ".sha256"):
            verb = "reading"
        _log("vae", f"{verb} {_fmt_display(filename)} hash")
    hashed = _hash_file("vae", filename, truncate=10)
    return hashed if isinstance(hashed, str) else "N/A"


def _resolve_model_path_with_extensions(folder_type: str, model_name: str) -> str | None:
    """Try to resolve a model path by testing common file extensions.

    Extensions are tried in order of preference, and the first match found is returned.

    This provides a fallback when folder_paths.get_full_path fails because
    the model_name doesn't include the file extension.

    Args:
        folder_type: The folder type for folder_paths ("loras", "checkpoints", etc.)
        model_name: The base model name without extension

    Returns:
        Full path if found, None otherwise
    """
    # Use centralized EXTENSION_ORDER to maintain a single source of truth
    for ext in EXTENSION_ORDER:
        try:
            full_path = folder_paths.get_full_path(folder_type, model_name + ext)
            if full_path and os.path.exists(full_path):  # Verify the path actually exists
                return full_path
        except OSError:  # pragma: no cover
            continue

    return None


# This new version of calc_lora_hash replaces the old one.
# It's now much more powerful, using the index to find files and
# checking for pre-computed .sha256 files before hashing manually.
def calc_lora_hash(model_name: Any, input_data: list) -> str:
    """Return truncated (10 char) sha256 hash for a LoRA.

    Accepts names/paths plus nested container / object forms. Utilizes cached `.sha256`
    siblings when present to avoid recomputation and writes new sidecars opportunistically.

    Args:
        model_name: LoRA identifier (string / list / dict / object).
        input_data: Unused (legacy signature compatibility).

    Returns:
        10-character truncated hex hash or 'N/A' if unresolved.
    """

    # Unified resolver + index fallback + legacy fallback for tests
    def _index_resolver(display: str) -> str | None:
        try:
            info = find_lora_info(display)
            return info.get("abspath") if info else None
        except Exception:  # pragma: no cover
            return None

    mode = (HASH_LOG_MODE or "none").lower()
    res = try_resolve_artifact("loras", model_name, post_resolvers=[_index_resolver])
    display_name, full_path = res.display_name, res.full_path

    # If multiple physical files share the same stem with different extensions, prefer first EXTENSION_ORDER
    if not full_path and isinstance(display_name, str):
        stem = os.path.splitext(display_name)[0]
        # Probe extensions explicitly in priority order
        for ext in EXTENSION_ORDER:
            try:
                candidate = folder_paths.get_full_path("loras", stem + ext)
            except Exception:  # pragma: no cover
                candidate = None
            if candidate and os.path.exists(candidate):
                full_path = candidate
                break
    if not full_path and isinstance(model_name, str):  # legacy fallback using patched folder_paths
        original = model_name
        candidate = sanitize_candidate(original) or original
        fp: str | None = None
        try:
            fp = folder_paths.get_full_path("loras", candidate)
        except Exception:  # pragma: no cover
            fp = None
        if not fp or not os.path.exists(fp):
            fp = _resolve_model_path_with_extensions("loras", candidate)
        if (not fp or not os.path.exists(fp)) and candidate != original:
            try:
                fp = folder_paths.get_full_path("loras", original)
            except Exception:  # pragma: no cover
                fp = None
            if not fp or not os.path.exists(fp):
                fp = _resolve_model_path_with_extensions("loras", original)
        # Index lookup as final fallback
        if (not fp or not os.path.exists(fp)):
            try:
                info = find_lora_info(candidate)
                if info and os.path.exists(info.get("abspath", "")):
                    fp = info.get("abspath")
            except Exception:  # pragma: no cover
                pass
        full_path = fp if fp and os.path.exists(fp) else None

    # If no meaningful name was provided, skip with N/A quietly
    try:
        dn = "" if display_name is None else str(display_name).strip()
        if dn == "" or dn.lower() in {"none", "null", "n/a"}:
            return "N/A"
    except Exception:
        pass

    # If not resolved, try extension fallback first, then LoRA index as secondary fallback
    if not full_path or not os.path.exists(full_path):
        # First, try extension fallback which works like folder_paths but with extensions
        if isinstance(display_name, str):
            full_path = _resolve_model_path_with_extensions("loras", display_name)

        # If extension fallback fails, try the LoRA index as secondary fallback
        if not full_path:
            try:
                if isinstance(display_name, str):
                    info = find_lora_info(display_name)
                else:
                    info = None
            except Exception:
                info = None
            if info:
                full_path = info.get("abspath")

        # If both fallbacks fail, return N/A
        if not full_path and isinstance(model_name, str) and os.path.exists(model_name):
            full_path = model_name
        if not full_path:
            if mode in {"detailed", "debug"}:
                _warn_unresolved_once("lora", str(display_name))
            return "N/A"

    # Now we have the absolute path, so we can check for a .sha256 file or hash it.
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    # Determine logging preference
    log_mode = mode
    sidecar_valid = False
    sidecar_path = None
    try:
        base, _ = os.path.splitext(full_path)
        sidecar_path = base + ".sha256"
        if os.path.exists(sidecar_path):
            try:
                with open(sidecar_path, encoding="utf-8") as sf:
                    cand = sf.read().strip()
                    if cand and len(cand) == 64 and all(c in "0123456789abcdefABCDEF" for c in cand):
                        sidecar_valid = True
            except Exception:  # pragma: no cover
                sidecar_valid = False
    except Exception:  # pragma: no cover
        pass

    # Select display filename for logging
    display_for_log: str | None = None
    if log_mode == "full":
        display_for_log = full_path
    elif log_mode == "short":
        display_for_log = os.path.basename(full_path)

    if mode in {"detailed", "debug"}:
        exists_flag = bool(full_path and os.path.exists(full_path))
        _log(
            "lora",
            f"resolved (lora) {display_name} -> {full_path if full_path else 'None'} "
            f"exists={exists_flag}",
        )
        _maybe_debug_candidates("lora", str(display_name))
    if display_for_log and mode != "none":
        verb = "reading" if sidecar_valid else "hashing"
        _log("lora", f"{verb} {display_for_log} hash")

    # Retrieve truncated hash but guarantee sidecar stores full hash (handled in load_or_calc_hash).
    hashed = _hash_file("lora", full_path, truncate=10)
    if not hashed:
        try:
            logger.debug("[Metadata Lib] Failed to hash LoRA '%s' at '%s'", display_name, full_path)
        except Exception:
            pass
        return "N/A"
    return hashed


def calc_unet_hash(model_name: Any, input_data: list) -> str:
    """Return truncated (10 char) sha256 hash for a UNet if resolvable.

    Args:
        model_name: UNet identifier (string / list / dict / object form).
        input_data: Unused (legacy signature compatibility).

    Returns:
        10-character truncated hex hash or 'N/A'.
    """

    # Unified attempt
    res = try_resolve_artifact("unet", model_name)
    filename = res.full_path
    if not filename and isinstance(model_name, str):  # legacy fallback for tests
        original = model_name
        candidate = sanitize_candidate(original) or original
        fp: str | None = None
        try:
            fp = folder_paths.get_full_path("unet", candidate)
        except Exception:  # pragma: no cover
            fp = None
        if not fp or not os.path.exists(fp):
            fp = _resolve_model_path_with_extensions("unet", candidate)
        if (not fp or not os.path.exists(fp)) and candidate != original:
            try:
                fp = folder_paths.get_full_path("unet", original)
            except Exception:  # pragma: no cover
                fp = None
            if not fp or not os.path.exists(fp):
                fp = _resolve_model_path_with_extensions("unet", original)
        filename = fp if fp and os.path.exists(fp) else None
    if not filename:
        # Best effort: if it's a direct path string
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            # print(f"[Metadata Lib] UNet '{model_name}' could not be resolved to a file. Skipping hash.")
            return "N/A"
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    mode = (HASH_LOG_MODE or "none").lower()
    if mode in {"detailed", "debug"}:
        exists_flag = bool(filename and os.path.exists(filename))
        _log(
            "unet",
            f"resolved (unet) {model_name} -> {filename if filename else 'None'} "
            f"exists={exists_flag}",
        )
        _maybe_debug_candidates("unet", str(model_name))
    if mode in {"filename", "path", "detailed", "debug"}:
        verb = "hashing"
        base, _ = os.path.splitext(filename)
        if os.path.exists(base + ".sha256"):
            verb = "reading"
        _log("unet", f"{verb} {_fmt_display(filename)} hash")
    hashed = _hash_file("unet", filename, truncate=10)
    return hashed if isinstance(hashed, str) else "N/A"


def convert_skip_clip(stop_at_clip_layer, input_data):
    return stop_at_clip_layer * -1


def get_scaled_width(scaled_by, input_data):
    samples = input_data[0]["samples"][0]["samples"]
    return round(samples.shape[3] * scaled_by * 8)


def get_scaled_height(scaled_by, input_data):
    samples = input_data[0]["samples"][0]["samples"]
    return round(samples.shape[2] * scaled_by * 8)


def extract_embedding_names(text, input_data):
    embedding_names, _ = _extract_embedding_names(text, input_data)

    return [os.path.basename(embedding_name) for embedding_name in embedding_names]


def extract_embedding_hashes(text, input_data):
    embedding_names, clip = _extract_embedding_names(text, input_data)
    mode = (HASH_LOG_MODE or "none").lower()
    hashes = []
    for embedding_name in embedding_names:
        try:
            embedding_file_path = get_embedding_file_path(embedding_name, clip)
        except Exception:
            embedding_file_path = None
        if not embedding_file_path or not os.path.exists(embedding_file_path):
            if mode in {"detailed", "debug"}:
                _warn_unresolved_once("embedding", embedding_name)
            hashes.append("N/A")
            continue
        if mode in {"filename", "path", "detailed", "debug"}:
            _log("embedding", f"hashing {_fmt_display(embedding_file_path)} hash")
        h = calc_hash(embedding_file_path)
        if mode == "debug":
            _log("embedding", f"full hash {os.path.basename(embedding_file_path)}={h}")
        hashes.append(h[:10])
    return hashes


def _extract_embedding_names(text, input_data):
    embedding_identifier = "embedding:"
    clip_ = input_data[0]["clip"][0]
    clip = None
    if clip_ is not None:
        tokenizer = clip_.tokenizer
        if isinstance(tokenizer, SD1Tokenizer):
            clip = tokenizer.clip_l
        elif isinstance(tokenizer, SD2Tokenizer):
            clip = tokenizer.clip_h
        elif isinstance(tokenizer, SDXLTokenizer):
            clip = tokenizer.clip_l
        elif isinstance(tokenizer, SD3Tokenizer):
            clip = tokenizer.clip_l
        elif isinstance(tokenizer, FluxTokenizer):
            clip = tokenizer.clip_l
        if clip is not None and hasattr(clip, "embedding_identifier"):
            embedding_identifier = clip.embedding_identifier
    if not isinstance(text, str):
        text = "".join(str(item) if item is not None else "" for item in text)
    text = escape_important(text)
    parsed_weights = token_weights(text, 1.0)

    # tokenize words
    embedding_names = []
    for weighted_segment, weight in parsed_weights:
        to_tokenize = unescape_important(weighted_segment).replace("\n", " ").split(" ")
        to_tokenize = [x for x in to_tokenize if x != ""]
        for word in to_tokenize:
            # find an embedding, deal with the embedding
            if word.startswith(embedding_identifier) and clip.embedding_directory is not None:
                embedding_name = word[len(embedding_identifier) :].strip("\n")
                embedding_names.append(embedding_name)

    return embedding_names, clip
