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
except (ImportError, ModuleNotFoundError):  # noqa: BLE001 - provide minimal stubs for tests
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
import sys as _sys

# Unified hash logging mode for all artifact types (model, lora, vae, unet, embeddings).
# Modes: none | filename | path | detailed | debug
HASH_LOG_MODE: str = _os.environ.get("METADATA_HASH_LOG_MODE", "none")
# Propagation control (default ON for visibility)
_HASH_LOG_PROPAGATE: bool = _os.environ.get("METADATA_HASH_LOG_PROPAGATE", "1") != "0"

_WARNED_SIDECAR: set[str] = set()
_WARNED_UNRESOLVED: set[str] = set()
_LOGGER_INITIALIZED = False
_HANDLER_TAG = "__hash_logger_handler__"
_BANNER_PRINTED = False

# Prevent duplicate module instances under different package names (runtime vs tests)
_SELF = _sys.modules.get(__name__)
_ALT_NAMES = [
    "saveimage_unimeta.defs.formatters",
    "custom_nodes.ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters",
]
for _n in _ALT_NAMES:
    if _n not in _sys.modules and _SELF is not None:
        _sys.modules[_n] = _SELF

def set_hash_log_mode(mode: str):
    """Programmatically adjust hash log mode (tests / UI) and re-init logger."""
    global HASH_LOG_MODE, _LOGGER_INITIALIZED
    HASH_LOG_MODE = (mode or "none").lower()
    _LOGGER_INITIALIZED = False  # force re-init next log call


def _ensure_logger():  # runtime init when mode activated
    global _LOGGER_INITIALIZED, _HASH_LOG_PROPAGATE, _BANNER_PRINTED
    if _LOGGER_INITIALIZED:
        return
    mode = (HASH_LOG_MODE or "none").lower()
    if mode == "none":
        return
    # Re-evaluate propagate flag at runtime (may change between calls/tests)
    _HASH_LOG_PROPAGATE = os.environ.get("METADATA_HASH_LOG_PROPAGATE", "1") != "0"
    try:
        logger.setLevel(logging.INFO)
        # Ensure we have a tagged StreamHandler and that it binds to the CURRENT sys.stderr.
        handler_added = False
        tagged_handler = None
        for h in logger.handlers:
            if getattr(h, _HANDLER_TAG, False):
                tagged_handler = h
                break
        if tagged_handler is None:
            tagged_handler = logging.StreamHandler()  # defaults to sys.stderr
            setattr(tagged_handler, _HANDLER_TAG, True)
            handler_added = True
            logger.addHandler(tagged_handler)
        # Rebind stream to current sys.stderr to cooperate with pytest's capsys
        try:
            tagged_handler.setStream(sys.stderr)
        except Exception:  # pragma: no cover
            pass
        tagged_handler.setLevel(logging.INFO)
        tagged_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        # Allow caller to control propagation to root via env flag
        logger.propagate = _HASH_LOG_PROPAGATE
        _LOGGER_INITIALIZED = True
        # Print banner only once per process to prevent startup + first-run duplicates
        if not _BANNER_PRINTED:
            try:
                logger.info(
                    "[Hash] logging initialized (mode=%s propagate=%s handler_added=%s suppress_dup=%s)",
                    mode,
                    logger.propagate,
                    handler_added,
                    handler_added,
                )
            except Exception:  # pragma: no cover
                pass
            _BANNER_PRINTED = True
    except OSError:  # pragma: no cover
        try:
            if not getattr(_ensure_logger, "_warned", False):
                print("[Hash] logger initialization failed", file=sys.stderr)
                _ensure_logger._warned = True  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
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

_MAX_EMBEDDING_NAME_CHARS = 80
_EMBEDDING_TRAILING_STRIP = " ,，。.;；:：!?！？、·"


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
        except OSError:  # pragma: no cover
            full = None
        # If direct lookup failed OR produced non-existent path, probe extensions
        if not full or not os.path.exists(full):
            full = _resolve_model_path_with_extensions("checkpoints", candidate)
        # If still unresolved and we altered the name, try original form
        if (not full or not os.path.exists(full)) and candidate != original:
            try:
                full = folder_paths.get_full_path("checkpoints", original)
            except OSError:  # pragma: no cover
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
    except (TypeError, OSError):  # pragma: no cover - defensive guard, isinstance check should prevent this
        pass
    if isinstance(fp, str) and fp:
        try:
            return os.path.basename(fp)
        except (TypeError, OSError):  # pragma: no cover - defensive guard, isinstance check should prevent this
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
                except (FileNotFoundError, OSError):
                    fp = None
                if fp and os.path.exists(fp):
                    filename = fp
                    break
    if not filename:
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            # Retry with basename using display_name (may still contain separators) first
            if isinstance(display_name, str) and ("/" in display_name or "\\" in display_name):
                base_candidate = os.path.basename(display_name)
                if mode == "debug":
                    _log("model", f"retry basename={base_candidate} from token={display_name}")
                if base_candidate and base_candidate != display_name:
                    for e in EXTENSION_ORDER:
                        try:
                            fp2 = folder_paths.get_full_path(
                                "checkpoints",
                                base_candidate if base_candidate.endswith(e) else base_candidate + e,
                            )
                        except (FileNotFoundError, OSError):
                            fp2 = None
                        if fp2 and os.path.exists(fp2):
                            filename = fp2
                            if mode == "debug":
                                _log("model", f"basename resolved {base_candidate} -> {fp2}")
                            break
            # If display_name was sanitized (lost separators) retry using original token
            if not filename and isinstance(model_name, str) and ("/" in model_name or "\\" in model_name):
                base_candidate = os.path.basename(model_name)
                if mode == "debug":
                    _log(
                        "model",
                        (
                            "retry basename="
                            f"{base_candidate} from original_token={model_name} sanitized_token={display_name}"
                        ),
                    )
                for e in EXTENSION_ORDER:
                    try:
                        fp2 = folder_paths.get_full_path(
                            "checkpoints",
                            base_candidate if base_candidate.endswith(e) else base_candidate + e,
                        )
                    except (FileNotFoundError, OSError):
                        fp2 = None
                    if fp2 and os.path.exists(fp2):
                        filename = fp2
                        if mode == "debug":
                            _log("model", f"basename resolved {base_candidate} -> {fp2}")
                        break
            if not filename:
                if mode in {"detailed", "debug"}:
                    _warn_unresolved_once("model", str(display_name))
                if mode == "debug":
                    _log("model", f"hash skipped reason=unresolved token={display_name}")
                return "N/A"
    # Reject obviously invalid tokens ONLY if we failed to resolve a real file; allow path-like inputs that
    # successfully resolved via basename recovery or direct path usage.
    if not filename and isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
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
    if not isinstance(hashed, str) and mode == "debug":
        _log("model", f"hash skipped reason=compute-failed token={display_name}")
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
    except (TypeError, OSError):  # pragma: no cover - defensive guard, isinstance check should prevent this
        pass
    if isinstance(fp, str) and fp:
        try:
            return os.path.basename(fp)
        except (TypeError, OSError):  # pragma: no cover - defensive guard, isinstance check should prevent this
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
    # Only reject invalid tokens if we FAILED to resolve a real file; allow path-like inputs.
    if (not filename) and isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        if mode == "debug":
            _log("vae", f"hash skipped reason=invalid-token token={model_name}")
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
    if mode in {"detailed", "debug"}:
        _log("lora", f"resolving token={display_name}")

    # Rely on centralized resolver and index fallback; avoid ad-hoc extension probing here
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
    except Exception:  # pragma: no cover - defensive guard for edge cases in str() conversion
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
            except (OSError, KeyError):
                info = None
            if info:
                full_path = info.get("abspath")

        # If both fallbacks fail, return N/A
        if not full_path and isinstance(model_name, str) and os.path.exists(model_name):
            full_path = model_name
        if not full_path:
            if mode in {"detailed", "debug"}:
                _warn_unresolved_once("lora", str(display_name))
            if mode == "debug":
                _log("lora", f"hash skipped reason=unresolved token={display_name}")
            return "N/A"

    # Now we have the absolute path, so we can check for a .sha256 file or hash it.
    # Only reject invalid tokens if we FAILED to resolve a real file; allow path-like inputs.
    if (not full_path) and isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        if mode == "debug":
            _log("lora", f"hash skipped reason=invalid-token token={model_name}")
        return "N/A"
    # Determine logging preference
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

    if mode in {"detailed", "debug"}:
        exists_flag = bool(full_path and os.path.exists(full_path))
        _log(
            "lora",
            f"resolved (lora) {display_name} -> {full_path if full_path else 'None'} "
            f"exists={exists_flag}",
        )
        _maybe_debug_candidates("lora", str(display_name))
    if mode in {"filename", "path", "detailed", "debug"}:
        verb = "reading" if sidecar_valid else "hashing"
        _log("lora", f"{verb} {_fmt_display(full_path)} hash")

    # Retrieve truncated hash but guarantee sidecar stores full hash (handled in load_or_calc_hash).
    if mode == "debug":
        _log("lora", f"hashing target={full_path} token={display_name}")
    hashed = _hash_file("lora", full_path, truncate=10)
    if not hashed:
        try:
            logger.debug("[Metadata Lib] Failed to hash LoRA '%s' at '%s'", display_name, full_path)
        except Exception:  # pragma: no cover
            pass
        if mode == "debug":
            _log("lora", f"hash skipped reason=compute-failed token={display_name}")
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
    mode = (HASH_LOG_MODE or "none").lower()
    if not filename:
        # Best effort: if it's a direct path string
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            # print(f"[Metadata Lib] UNet '{model_name}' could not be resolved to a file. Skipping hash.")
            if mode == "debug":
                _log("unet", f"hash skipped reason=unresolved token={model_name}")
            return "N/A"
    # Only reject invalid tokens if we FAILED to resolve a real file; allow path-like inputs.
    if (not filename) and isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        if mode == "debug":
            _log("unet", f"hash skipped reason=invalid-token token={model_name}")
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
    if not isinstance(hashed, str) and mode == "debug":
        _log("unet", f"hash skipped reason=compute-failed token={model_name}")
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
    embedding_names, _, _ = _extract_embedding_candidates(text, input_data)

    return embedding_names


def extract_embedding_hashes(text, input_data):
    embedding_names, _, resolved_paths = _extract_embedding_candidates(text, input_data)
    mode = (HASH_LOG_MODE or "none").lower()
    hashes: list[str] = []

    for embedding_name, embedding_path in zip(embedding_names, resolved_paths):
        if not embedding_path or not os.path.exists(embedding_path):
            if mode in {"detailed", "debug"}:
                _warn_unresolved_once("embedding", embedding_name)
            hashes.append("N/A")
            continue
        if mode in {"filename", "path", "detailed", "debug"}:
            _log("embedding", f"hashing {_fmt_display(embedding_path)} hash")
        try:
            hash_value = calc_hash(embedding_path)
        except (OSError, TypeError, ValueError) as err:  # pragma: no cover - defensive
            logger.debug("[Metadata Lib] Skipping embedding hash due to error: %r", err)
            if mode in {"detailed", "debug"}:
                _warn_unresolved_once("embedding", embedding_name)
            hashes.append("N/A")
            continue
        if mode == "debug":
            _log("embedding", f"full hash {os.path.basename(embedding_path)}={hash_value}")
        hashes.append(hash_value[:10] if isinstance(hash_value, str) else hash_value)

    if len(hashes) != len(embedding_names):
        logger.debug(
            "[Metadata Lib] Embedding name/hash count mismatch filtered names=%s hashes=%s",
            len(embedding_names),
            len(hashes),
        )

    return hashes


def _extract_embedding_candidates(text, input_data):
    embedding_identifier = "embedding:"
    clip_ = input_data[0]["clip"][0]
    clip = None
    embedding_dir = None
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
        if clip is not None:
            embedding_dir = getattr(clip, "embedding_directory", None)
            ident = getattr(clip, "embedding_identifier", None)
            if isinstance(ident, str) and ident.strip():
                embedding_identifier = ident
    if not isinstance(text, str):
        text = "".join(str(item) if item is not None else "" for item in text)
    text = escape_important(text)
    parsed_weights = token_weights(text, 1.0)

    # tokenize words
    if clip is None or not embedding_dir:
        return [], clip, []

    embedding_names: list[str] = []
    resolved_paths: list[str] = []
    seen: set[str] = set()
    for weighted_segment, weight in parsed_weights:
        to_tokenize = unescape_important(weighted_segment).replace("\n", " ").split(" ")
        to_tokenize = [x for x in to_tokenize if x != ""]
        for word in to_tokenize:
            # find an embedding, deal with the embedding
            if not word.startswith(embedding_identifier):
                continue
            raw_name = word[len(embedding_identifier) :].strip()
            if not raw_name:
                continue
            sanitized = raw_name.strip(_EMBEDDING_TRAILING_STRIP)
            if not sanitized:
                continue
            display_name = os.path.basename(sanitized).strip(_EMBEDDING_TRAILING_STRIP)
            if not display_name:
                continue
            if display_name.upper() == "N/A":
                continue
            if len(display_name) > _MAX_EMBEDDING_NAME_CHARS:
                logger.debug(
                    "[Metadata Lib] Skipping embedding candidate '%s' (length %s exceeds max)",
                    display_name,
                    len(display_name),
                )
                continue
            cache_key = display_name.lower()
            if cache_key in seen:
                continue
            try:
                path = get_embedding_file_path(sanitized, clip)
            except (OSError, TypeError, ValueError) as err:
                logger.debug(
                    "[Metadata Lib] Skipping embedding '%s' due to resolution error: %r",
                    display_name,
                    err,
                )
                continue
            if not path:
                logger.debug(
                    "[Metadata Lib] Embedding '%s' could not be resolved to a file; skipping",
                    display_name,
                )
                continue
            seen.add(cache_key)
            embedding_names.append(display_name)
            resolved_paths.append(path)

    return embedding_names, clip, resolved_paths
