"""Formatters & hashing helpers for metadata capture.

Provides resilient name resolution for models, VAEs, LoRAs, UNets, plus
embedding extraction utilities and deterministic hashing with optional
use of cached .sha256 sidecar files to avoid recomputation.
"""

import logging
import os
from typing import Any

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
from ..utils.pathresolve import try_resolve_artifact, load_or_calc_hash, sanitize_candidate

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
    display_name, filename = _ckpt_name_to_path(model_name)
    if not filename:
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            # print(f"[Metadata Lib] Model '{display_name}' could not be resolved to a file. Skipping hash.")
            return "N/A"
    # Reject obviously invalid filename tokens containing reserved characters
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    hashed = load_or_calc_hash(filename)
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
    if not filename:
        # Try best-effort: if model_name looked like a path, hash it directly
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            return "N/A"
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    hashed = load_or_calc_hash(filename)
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
    # Common model file extensions in order of preference
    extensions = [".safetensors", ".st", ".pt", ".bin", ".ckpt"]

    for ext in extensions:
        try:
            full_path = folder_paths.get_full_path(folder_type, model_name + ext)
            if full_path and os.path.exists(full_path):  # Verify the path actually exists
                return full_path
        except Exception:  # pragma: no cover
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

    res = try_resolve_artifact("loras", model_name, post_resolvers=[_index_resolver])
    display_name, full_path = res.display_name, res.full_path
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
        if not full_path:
            return "N/A"

    # Now we have the absolute path, so we can check for a .sha256 file or hash it.
    if isinstance(model_name, str) and any(c in model_name for c in '<>:"/\\|?*'):
        return "N/A"
    hashed = load_or_calc_hash(full_path)
    return hashed if isinstance(hashed, str) else "N/A"


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
    hashed = load_or_calc_hash(filename)
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
    embedding_hashes = []
    for embedding_name in embedding_names:
        embedding_file_path = get_embedding_file_path(embedding_name, clip)
        embedding_hashes.append(calc_hash(embedding_file_path))

    return embedding_hashes


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
