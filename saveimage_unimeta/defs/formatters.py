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

cache_model_hash = {}
logger = logging.getLogger(__name__)


def _resolve_model_path_with_extensions(
    folder_type: str,
    name_like: str,
    extensions: list[str] | None = None
) -> str | None:
    """Try to resolve a model name to full path, with extension fallback.

    Args:
        folder_type: The folder type for folder_paths.get_full_path (e.g., "loras", "checkpoints")
        name_like: The model name to resolve
        extensions: List of extensions to try. Defaults to common model extensions.

    Returns:
        Resolved absolute path or None if not found
    """
    if extensions is None:
        extensions = [".safetensors", ".st", ".pt", ".bin", ".ckpt"]

    # First try exact name (in case it includes extension)
    try:
        return folder_paths.get_full_path(folder_type, name_like)
    except Exception:
        pass

    # If that fails, try adding common extensions
    for ext in extensions:
        try:
            return folder_paths.get_full_path(folder_type, name_like + ext)
        except Exception:
            continue

    return None


def _ckpt_name_to_path(name_like: Any) -> tuple[str, str | None]:
    """
    Resolve checkpoint/model identifier to a file path.
    Accepts strings, lists/tuples (tries each), dicts/objects with common keys/attrs.
    Returns (display_name, full_path or None).
    """
    # If list/tuple, try entries
    if isinstance(name_like, list | tuple):  # noqa: UP038
        display = None
        for item in name_like:
            dn, fp = _ckpt_name_to_path(item)
            if dn and display is None:
                display = dn
            if fp:
                return dn, fp
        return display or str(name_like), None

    # If dict, check keys
    if isinstance(name_like, dict):
        for key in (
            "ckpt_name",
            "model_name",
            "model",
            "name",
            "filename",
            "path",
            "model_path",
        ):
            if key in name_like and name_like[key]:
                return _ckpt_name_to_path(name_like[key])
        return str(name_like), None

    # If object, check attrs
    for attr in (
        "ckpt_name",
        "model_name",
        "model",
        "name",
        "filename",
        "path",
        "model_path",
    ):
        if hasattr(name_like, attr):
            try:
                val = getattr(name_like, attr)
            except Exception:  # pragma: no cover - very unlikely attribute access error
                continue
            if val:
                return _ckpt_name_to_path(val)

    # String: resolve via folder_paths
    if isinstance(name_like, str):
        full = _resolve_model_path_with_extensions("checkpoints", name_like)
        return name_like, full

    # Fallback: stringify
    return str(name_like), None


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
            logger.debug("Model '%s' could not be resolved to a file. Skipping hash.", display_name)
            return "N/A"
    # Prefer precomputed sibling .sha256 file
    base, _ = os.path.splitext(filename)
    sha_path = base + ".sha256"
    full_hash: str | None = None
    if os.path.exists(sha_path):
        try:
            with open(sha_path, encoding="utf-8") as f:
                full_hash = f.read().strip() or None
        except OSError as e:  # pragma: no cover - log & continue
            logger.debug(
                "[Metadata Lib] Failed reading model sha256 sidecar '%s': %s",
                sha_path,
                e,
            )
    if not full_hash:
        logger.debug(
            "[Metadata Lib] Calculating hash for model '%s' at '%s'...",
            display_name,
            filename,
        )
        full_hash = calc_hash(filename)
        try:
            with open(sha_path, "w", encoding="utf-8") as f:
                f.write(str(full_hash))
        except OSError as e:  # pragma: no cover - ignore cache write issues
            logger.debug("[Metadata Lib] Could not write model sidecar '%s': %s", sha_path, e)
    return full_hash[:10] if isinstance(full_hash, str) else full_hash


def _vae_name_to_path(model_name: Any) -> tuple[str, str | None]:
    """Resolve a VAE identifier (object / name / path) to a filesystem path.

    Returns (display_name, full_path_or_None). Tries common attributes on objects,
    then falls back to direct folder_paths resolution when a string is provided.
    """
    # Object-like case: attempt attribute-based resolution
    if any(hasattr(model_name, attr) for attr in ("filename", "name", "ckpt", "ckpt_name", "model")):
        display_name = (
            getattr(model_name, "name", None)
            or getattr(model_name, "ckpt_name", None)
            or getattr(model_name, "filename", None)
            or str(model_name)
        )
        fp = getattr(model_name, "filename", None)
        if isinstance(fp, str) and os.path.exists(fp):
            return display_name, fp
        # Try a series of name-like attributes via folder_paths
        for attr in ("name", "ckpt_name", "filename", "model"):
            val = getattr(model_name, attr, None)
            if isinstance(val, str):
                try:
                    full = folder_paths.get_full_path("vae", val)
                except Exception:  # pragma: no cover
                    full = None
                if full and os.path.exists(full):
                    return display_name or val, full
        return display_name or str(model_name), None

    # String case
    if isinstance(model_name, str):
        full = _resolve_model_path_with_extensions("vae", model_name)
        return model_name, full

    # Fallback
    return str(model_name), None


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
    base, _ = os.path.splitext(filename)
    sha_path = base + ".sha256"
    full_hash: str | None = None
    if os.path.exists(sha_path):
        try:
            with open(sha_path, encoding="utf-8") as f:
                full_hash = f.read().strip() or None
        except OSError as e:  # pragma: no cover
            logger.debug("[Metadata Lib] Failed reading VAE sha256 sidecar '%s': %s", sha_path, e)
    if not full_hash:
        full_hash = calc_hash(filename)
        try:
            with open(sha_path, "w", encoding="utf-8") as f:
                f.write(str(full_hash))
        except OSError as e:  # pragma: no cover
            logger.debug("[Metadata Lib] Could not write VAE sidecar '%s': %s", sha_path, e)
    return full_hash[:10] if isinstance(full_hash, str) else full_hash


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

    def _lora_name_to_path(name_like: Any) -> tuple[str, str | None]:
        """Attempt to resolve a LoRA reference of varied shape to a filesystem path.

        Supports nested containers, dicts, and attribute-bearing objects. Returns
        a tuple (display_name, absolute_path_or_None).
        """
        # If list/tuple, try each candidate in order
        if isinstance(name_like, list | tuple):  # noqa: UP038
            display = None
            for item in name_like:
                dn, fp = _lora_name_to_path(item)
                if dn and display is None:
                    display = dn
                if fp:  # first resolvable path wins
                    return dn, fp
            return display or str(name_like), None

        # If dict, try common keys
        if isinstance(name_like, dict):
            for key in ("lora_name", "name", "filename", "path", "model", "model_path"):
                if key in name_like and name_like[key]:
                    return _lora_name_to_path(name_like[key])
            return str(name_like), None

        # If object, try attributes
        for attr in ("lora_name", "name", "filename", "path", "model", "model_path"):
            if hasattr(name_like, attr):
                try:
                    val = getattr(name_like, attr)
                except Exception:  # pragma: no cover
                    continue
                if val:
                    return _lora_name_to_path(val)

        # String: resolve via folder_paths
        if isinstance(name_like, str):
            full = _resolve_model_path_with_extensions("loras", name_like)
            return name_like, full

        # Fallback: stringify
        return str(name_like), None

    display_name, full_path = _lora_name_to_path(model_name)

    # If no meaningful name was provided, skip with N/A quietly
    try:
        dn = "" if display_name is None else str(display_name).strip()
        if dn == "" or dn.lower() in {"none", "null", "n/a"}:
            return "N/A"
    except Exception:
        pass

    # If not resolved, try lookup by base name (dynamic index)
    if not full_path or not os.path.exists(full_path):
        base_name = None
        if isinstance(display_name, str):
            base_name = os.path.splitext(display_name)[0]
        try:
            if base_name:
                info = find_lora_info(base_name)
            else:
                info = None
        except Exception:
            info = None
        if info:
            full_path = info.get("abspath")
        else:
            # Quietly return N/A when unresolved (avoid noisy logs for empty loaders)
            return "N/A"

    # Now we have the absolute path, so we can check for a .sha256 file or hash it.
    base, _ = os.path.splitext(full_path)
    hash_filepath = base + ".sha256"
    full_hash = None

    if os.path.exists(hash_filepath):
        try:
            with open(hash_filepath, encoding="utf-8") as f:
                full_hash = f.read().strip() or None
        except OSError as e:  # pragma: no cover
            logger.debug(
                "[Metadata Lib] Failed reading LoRA sha256 sidecar '%s': %s",
                hash_filepath,
                e,
            )

    if not full_hash:
        logger.debug(
            "[Metadata Lib] Calculating hash for LoRA '%s' at '%s'...",
            display_name,
            full_path,
        )
        full_hash = calc_hash(full_path)
        # Persist full hash for future runs
        try:
            with open(hash_filepath, "w", encoding="utf-8") as f:
                f.write(str(full_hash))
        except OSError as e:  # pragma: no cover
            logger.debug("[Metadata Lib] Could not write LoRA sidecar '%s': %s", hash_filepath, e)

    return full_hash[:10] if isinstance(full_hash, str) else full_hash


def calc_unet_hash(model_name: Any, input_data: list) -> str:
    """Return truncated (10 char) sha256 hash for a UNet if resolvable.

    Args:
        model_name: UNet identifier (string / list / dict / object form).
        input_data: Unused (legacy signature compatibility).

    Returns:
        10-character truncated hex hash or 'N/A'.
    """

    def _unet_name_to_path(name_like: Any) -> tuple[str, str | None]:
        """Resolve a UNet reference (varied container/object forms) to a path.

        Returns (display_name, path_or_None). Tries nested containers, dict keys,
        and object attributes in a resilient manner.
        """
        # If list/tuple, evaluate candidates in order
        if isinstance(name_like, list | tuple):  # noqa: UP038
            display = None
            for item in name_like:
                dn, fp = _unet_name_to_path(item)
                if dn and display is None:
                    display = dn
                if fp:
                    return dn, fp
            return display or str(name_like), None

        # If dict, inspect common keys
        if isinstance(name_like, dict):
            for key in ("unet_name", "model_name", "model", "filename", "path", "model_path"):
                if key in name_like and name_like[key]:
                    return _unet_name_to_path(name_like[key])
            return str(name_like), None

        # If object, inspect attributes
        for attr in ("unet_name", "model_name", "model", "filename", "path", "model_path"):
            if hasattr(name_like, attr):
                try:
                    val = getattr(name_like, attr)
                except Exception:  # pragma: no cover
                    continue
                if val:
                    return _unet_name_to_path(val)

        # Direct string: resolve via folder_paths
        if isinstance(name_like, str):
            full = _resolve_model_path_with_extensions("unet", name_like)
            return name_like, full

        # Fallback
        return str(name_like), None

    display_name, filename = _unet_name_to_path(model_name)
    if not filename:
        # Best effort: if it's a direct path string
        if isinstance(model_name, str) and os.path.exists(model_name):
            filename = model_name
        else:
            logger.debug("UNet '%s' could not be resolved to a file. Skipping hash.", display_name)
            return "N/A"
    base, _ = os.path.splitext(filename)
    sha_path = base + ".sha256"
    full_hash: str | None = None
    if os.path.exists(sha_path):
        try:
            with open(sha_path, encoding="utf-8") as f:
                full_hash = f.read().strip() or None
        except OSError as e:  # pragma: no cover
            logger.debug(
                "[Metadata Lib] Failed reading UNet sha256 sidecar '%s': %s",
                sha_path,
                e,
            )
    if not full_hash:
        logger.debug(
            "[Metadata Lib] Calculating hash for UNet '%s' at '%s'...",
            display_name,
            filename,
        )
        full_hash = calc_hash(filename)
        try:
            with open(sha_path, "w", encoding="utf-8") as f:
                f.write(str(full_hash))
        except OSError as e:  # pragma: no cover
            logger.debug("[Metadata Lib] Could not write UNet sidecar '%s': %s", sha_path, e)
    return full_hash[:10] if isinstance(full_hash, str) else full_hash


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
