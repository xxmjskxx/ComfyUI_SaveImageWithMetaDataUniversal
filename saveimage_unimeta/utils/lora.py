"""Provides utilities for indexing and parsing LoRA files.

This module includes functions for creating an in-memory index of available
LoRA files for fast lookups, as well as helpers for parsing the LoRA syntax
used in prompts (e.g., `<lora:name:strength>`). This allows for the efficient
extraction and resolution of LoRA metadata from a ComfyUI workflow.
Includes:
* One-time index mapping LoRA base names to on-disk locations (for fast lookup).
* One-time index mapping checkpoint/UNet base names to on-disk locations.
"""

import json
import logging
import os
import platform
import re

import folder_paths
from .pathresolve import SUPPORTED_MODEL_EXTENSIONS


# --- Caches and Indexes for Performance ---
# This index will be built once and reused to speed up all subsequent LoRA lookups.
_LORA_INDEX: dict[str, dict[str, str]] | None = None
_LORA_INDEX_BUILT: bool = False
_CHECKPOINT_INDEX: dict[str, dict[str, str]] | None = None
_CHECKPOINT_INDEX_BUILT: bool = False
_UNET_INDEX: dict[str, dict[str, str]] | None = None
_UNET_INDEX_BUILT: bool = False
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LoraManager compat helpers – read extra lora paths from its settings.json
# ---------------------------------------------------------------------------
# Directory names the comfyui-lora-manager plugin is commonly installed under.
_LORA_MANAGER_DIR_NAMES: tuple[str, ...] = (
    "comfyui-lora-manager",
    "ComfyUI-Lora-Manager",
    "ComfyUI-LoRA-Manager",
    "comfyui_lora_manager",
    "ComfyUI_Lora_Manager",
)
# The app name used by LoraManager for its platformdirs user-config directory.
_LORA_MANAGER_APP_NAME = "ComfyUI-LoRA-Manager"


def _find_lora_manager_root() -> str | None:
    """Locate the comfyui-lora-manager custom node directory, or None if not installed.

    Derives the ``custom_nodes/`` parent from this file's own path
    (lora.py → utils/ → saveimage_unimeta/ → plugin_root/ → custom_nodes/)
    and then checks common directory names for the LoraManager plugin.
    """
    try:
        # Walk up four dirname levels: lora.py -> utils -> saveimage_unimeta -> plugin_root -> custom_nodes
        custom_nodes_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        for name in _LORA_MANAGER_DIR_NAMES:
            candidate = os.path.join(custom_nodes_dir, name)
            if os.path.isdir(candidate):
                return candidate
    except Exception:
        logger.debug(
            "Unexpected error while locating LoraManager plugin directory.",
            exc_info=True,
        )
    return None


def _get_lora_manager_user_config_path() -> str | None:
    """Return the platform-specific user-config path for LoraManager's settings.json.

    Tries ``platformdirs`` first (same library LoraManager itself uses), then
    falls back to per-platform manual derivation so we don't require it as a
    hard dependency.
    """
    app = _LORA_MANAGER_APP_NAME
    try:
        import platformdirs  # available when LoraManager is installed
        return os.path.join(platformdirs.user_config_dir(app, appauthor=False), "settings.json")
    except ImportError:
        pass
    except Exception:
        logger.debug(
            "Failed to resolve LoraManager user_config_dir via platformdirs; "
            "falling back to manual path derivation.",
            exc_info=True,
        )
    # Manual fallback per platform
    try:
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("APPDATA") or os.path.expanduser(os.path.join("~", "AppData", "Roaming"))
            return os.path.join(base, app, "settings.json")
        if system == "Darwin":
            return os.path.expanduser(os.path.join("~", "Library", "Application Support", app, "settings.json"))
        # Linux / other POSIX
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser(os.path.join("~", ".config"))
        return os.path.join(base, app, "settings.json")
    except Exception:
        return None


def _read_lora_manager_settings(plugin_root: str) -> dict | None:
    """Parse LoraManager's settings.json, handling portable vs user-config locations.

    Resolution order (mirrors LoraManager's own ``ensure_settings_file`` logic):

    1. **Portable mode** – ``<plugin_root>/settings.json`` exists *and* contains
       ``"use_portable_settings": true``.
    2. **User-config mode** – platform user-config directory
       (e.g. ``%APPDATA%\\ComfyUI-LoRA-Manager\\settings.json`` on Windows).
    3. **Legacy fallback** – ``<plugin_root>/settings.json`` without the portable
       flag (present before first migration to user-config dir).
    """
    portable_path = os.path.join(plugin_root, "settings.json")

    # 1. Portable mode
    if os.path.isfile(portable_path):
        try:
            with open(portable_path, encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("use_portable_settings"):
                return data
        except Exception:
            logger.debug("Failed to parse LoraManager settings at %r.", portable_path, exc_info=True)

    # 2. User-config directory
    user_path = _get_lora_manager_user_config_path()
    if user_path and os.path.isfile(user_path):
        try:
            with open(user_path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            logger.debug("Failed to parse LoraManager settings at %r.", user_path, exc_info=True)

    # 3. Legacy: settings.json in plugin root without portable flag
    if os.path.isfile(portable_path):
        try:
            with open(portable_path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            logger.debug("Failed to parse LoraManager settings at %r.", portable_path, exc_info=True)

    return None


def get_lora_manager_paths(model_type: str) -> list[str]:
    """Return extra model directory paths from LoraManager's settings.json.

    Reads from both ``extra_folder_paths.<model_type>`` and
    ``folder_paths.<model_type>`` keys in the settings file.

    Args:
        model_type: The model type key used in LoraManager's settings
            (e.g. ``"loras"``, ``"checkpoints"``, ``"unet"``,
            ``"embeddings"``).

    Returns:
        Deduplicated list of absolute path strings, or an empty list if
        LoraManager is not installed, has no settings file, or has no
        paths for the requested type.
    """
    plugin_root = _find_lora_manager_root()
    if not plugin_root:
        return []

    settings = _read_lora_manager_settings(plugin_root)
    if not settings or not isinstance(settings, dict):
        return []

    paths: list[str] = []
    for key in ("extra_folder_paths", "folder_paths"):
        section = settings.get(key)
        if not isinstance(section, dict):
            continue
        for p in section.get(model_type, []):
            if isinstance(p, str) and p.strip():
                normalized = os.path.abspath(os.path.expanduser(p.strip()))
                paths.append(normalized)

    # Deduplicate (case-insensitive on Windows) while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for p in paths:
        norm = os.path.normcase(os.path.normpath(p))
        if norm not in seen:
            seen.add(norm)
            unique.append(p)
    return unique


def _get_lora_manager_lora_paths() -> list[str]:
    """Return lora directory paths from LoraManager's settings.json.

    Reads from both ``extra_folder_paths.loras`` (paths exclusive to LoraManager)
    and ``folder_paths.loras`` (which may differ from ComfyUI's paths when the
    user has activated a non-default LoraManager library).

    Returns an empty list if LoraManager is not installed, has no settings file,
    or has no additional lora paths configured.
    """
    return get_lora_manager_paths("loras")


def build_lora_index() -> None:
    """Populate (idempotently) the in-memory LoRA file index.

    Scan order & behavior:
        * Enumerates every directory from two sources, merged and deduplicated:

          1. ``folder_paths.get_folder_paths('loras')`` — standard ComfyUI LoRA paths.
          2. ``_get_lora_manager_lora_paths()`` — any additional paths registered only with
             LoraManager (via its ``extra_folder_paths`` or ``folder_paths`` settings).

        * Deduplication is case-insensitive on Windows (``os.path.normcase`` + ``normpath``) so
          directories that appear in both sources are only walked once.
        * ComfyUI standard paths take precedence — they are walked first, so a
          filename in a standard directory shadows the same filename in a LoraManager-only path.
        * Recursively walks subdirectories within each unique directory.
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
    extensions = list(SUPPORTED_MODEL_EXTENSIONS)

    extra_lm_paths = _get_lora_manager_lora_paths()

    # Deduplicate across both sources (case-insensitive on Windows) to avoid
    # walking the same directory twice. Standard ComfyUI paths are added first
    # so they take precedence in the filename-stem index.
    seen_dirs: set[str] = set()
    all_lora_dirs: list[str] = []

    for d in lora_paths:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in seen_dirs:
            seen_dirs.add(norm)
            all_lora_dirs.append(d)

    extra_unique_dirs: list[str] = []
    for d in extra_lm_paths:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in seen_dirs:
            seen_dirs.add(norm)
            all_lora_dirs.append(d)
            extra_unique_dirs.append(d)

    if extra_lm_paths:
        if extra_unique_dirs:
            logger.info(
                "[Metadata Lib] Found %d extra LoRA path(s) from LoraManager settings.",
                len(extra_unique_dirs),
            )
        else:
            logger.info(
                "[Metadata Lib] LoraManager settings.json defined LoRA paths,"
                " but all are already covered by existing LoRA directories.",
            )

    for lora_dir in all_lora_dirs:
        def _walk_error(exc: OSError, _dir: str = lora_dir) -> None:
            logger.warning(
                "[Metadata Lib] Skipping unreadable LoRA path during index build: %s (%r)",
                _dir,
                exc,
            )
        try:
            for root, _, files in os.walk(lora_dir, onerror=_walk_error):
                for file in files:
                    file_base, file_ext = os.path.splitext(file)
                    # Use the base name as the key for easy lookup. Normalize the
                    # extension to lower-case so files with upper-case suffixes
                    # (e.g. `.SAFETENSORS`) are indexed, mirroring the behavior
                    # of `build_checkpoint_index` and `build_unet_index`.
                    if file_ext.lower() in extensions and file_base not in _LORA_INDEX:
                        _LORA_INDEX[file_base] = {
                            "filename": file,
                            "abspath": os.path.join(root, file),
                        }
        except OSError as exc:
            logger.warning(
                "[Metadata Lib] Aborted walk of LoRA directory %s during index build: %r",
                lora_dir,
                exc,
            )
            continue

    _LORA_INDEX_BUILT = True
    logger.info("[Metadata Lib] LoRA index built with %d entries.", len(_LORA_INDEX))
    try:
        if dump_env := os.environ.get("METADATA_DUMP_LORA_INDEX"):
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


# ---------------------------------------------------------------------------
# TODO: LoraManager currently only populates extra_folder_paths.loras in
#   practice, so build_checkpoint_index and build_unet_index will typically
#   return no extra paths. These functions are implemented for forward
#   compatibility when LoraManager expands its extra-paths support.
# ---------------------------------------------------------------------------


def build_checkpoint_index() -> None:
    """Populate (idempotently) the in-memory checkpoint file index.

    Mirrors :func:`build_lora_index` for checkpoint files.  Scans
    ``folder_paths.get_folder_paths('checkpoints')`` plus any extra
    paths from LoraManager's settings (forward-compat — not currently
    populated by LoraManager).

    Environment:
        ``METADATA_DUMP_CHECKPOINT_INDEX`` optionally writes the built
        index to disk for diagnostics or tests. The current behavior is:
        - unset or ``""``: skip writing a dump file;
        - ``"1"``: write JSON to
          ``os.path.join(os.getcwd(), "_checkpoint_index_dump.json")``;
        - any other non-empty value: trim leading and trailing
          whitespace with ``str.strip()`` and treat the result as the
          output file path.

    Side Effects:
        Mutates module-level caches ``_CHECKPOINT_INDEX`` and
        ``_CHECKPOINT_INDEX_BUILT``. When
        ``METADATA_DUMP_CHECKPOINT_INDEX`` is set as described above,
        also writes a JSON dump of ``_CHECKPOINT_INDEX`` to disk.
    """
    global _CHECKPOINT_INDEX, _CHECKPOINT_INDEX_BUILT
    if _CHECKPOINT_INDEX_BUILT:
        return

    logger.info("[Metadata Lib] Building checkpoint file index for the first time...")
    _CHECKPOINT_INDEX = {}
    ckpt_paths = folder_paths.get_folder_paths("checkpoints")
    extensions = list(SUPPORTED_MODEL_EXTENSIONS)

    extra_lm_paths = get_lora_manager_paths("checkpoints")

    seen_dirs: set[str] = set()
    all_ckpt_dirs: list[str] = []

    for d in ckpt_paths:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in seen_dirs:
            seen_dirs.add(norm)
            all_ckpt_dirs.append(d)

    extra_unique_dirs: list[str] = []
    for d in extra_lm_paths:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in seen_dirs:
            seen_dirs.add(norm)
            all_ckpt_dirs.append(d)
            extra_unique_dirs.append(d)

    if extra_lm_paths:
        if extra_unique_dirs:
            logger.info(
                "[Metadata Lib] Found %d extra checkpoint path(s) from LoraManager settings.",
                len(extra_unique_dirs),
            )
        else:
            logger.info(
                "[Metadata Lib] LoraManager settings.json defined checkpoint paths,"
                " but all are already covered by existing checkpoint directories.",
            )

    for ckpt_dir in all_ckpt_dirs:
        def _walk_error(exc: OSError, _dir: str = ckpt_dir) -> None:
            logger.warning(
                "[Metadata Lib] Skipping unreadable checkpoint path during index build: %s (%r)",
                _dir,
                exc,
            )
        try:
            for root, _, files in os.walk(ckpt_dir, onerror=_walk_error):
                for file in files:
                    file_base, file_ext = os.path.splitext(file)
                    if file_ext.lower() in extensions and file_base not in _CHECKPOINT_INDEX:
                        _CHECKPOINT_INDEX[file_base] = {
                            "filename": file,
                            "abspath": os.path.join(root, file),
                        }
        except OSError as exc:
            logger.warning(
                "[Metadata Lib] Aborted walk of checkpoint directory %s during index build: %r",
                ckpt_dir,
                exc,
            )
            continue

    _CHECKPOINT_INDEX_BUILT = True
    logger.info("[Metadata Lib] Checkpoint index built with %d entries.", len(_CHECKPOINT_INDEX))
    try:
        if dump_env := os.environ.get("METADATA_DUMP_CHECKPOINT_INDEX"):
            dump_path = dump_env.strip()
            if dump_path.lower() == "1":
                dump_path = os.path.join(os.getcwd(), "_checkpoint_index_dump.json")
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(_CHECKPOINT_INDEX, f, indent=2, sort_keys=True)
            logger.info("[Metadata Lib] Checkpoint index dumped to %s", dump_path)
    except Exception as e:  # pragma: no cover - diagnostic optional
        logger.debug("[Metadata Lib] Failed dumping checkpoint index: %r", e)


def find_checkpoint_info(base_name: str) -> dict[str, str] | None:
    """Find the indexed information for a checkpoint by its base name.

    Args:
        base_name (str): The base name of the checkpoint file (without the
            extension).

    Returns:
        dict[str, str] | None: A dictionary containing the ``filename`` and
            ``abspath`` of the checkpoint, or None if not found.
    """
    build_checkpoint_index()
    if _CHECKPOINT_INDEX is None:
        return None
    return _CHECKPOINT_INDEX.get(base_name)


def build_unet_index() -> None:
    """Populate (idempotently) the in-memory UNet file index.

    Mirrors :func:`build_lora_index` for UNet files.  Scans
    ``folder_paths.get_folder_paths('unet')`` plus any extra paths from
    LoraManager's settings (forward-compat — not currently populated by
    LoraManager).

    Environment:
        ``METADATA_DUMP_UNET_INDEX`` optionally writes the built index to
        disk for diagnostics or tests. The current behavior is:
        - unset or ``""``: skip writing a dump file;
        - ``"1"``: write JSON to
          ``os.path.join(os.getcwd(), "_unet_index_dump.json")``;
        - any other non-empty value: trim leading and trailing
          whitespace with ``str.strip()`` and treat the result as the
          output file path.

    Side Effects:
        Mutates module-level caches ``_UNET_INDEX`` and
        ``_UNET_INDEX_BUILT``. When ``METADATA_DUMP_UNET_INDEX`` is set
        as described above, also writes a JSON dump of ``_UNET_INDEX``
        to disk.
    """
    global _UNET_INDEX, _UNET_INDEX_BUILT
    if _UNET_INDEX_BUILT:
        return

    logger.info("[Metadata Lib] Building UNet file index for the first time...")
    _UNET_INDEX = {}
    unet_paths = folder_paths.get_folder_paths("unet")
    extensions = list(SUPPORTED_MODEL_EXTENSIONS)

    extra_lm_paths = get_lora_manager_paths("unet")

    seen_dirs: set[str] = set()
    all_unet_dirs: list[str] = []

    for d in unet_paths:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in seen_dirs:
            seen_dirs.add(norm)
            all_unet_dirs.append(d)

    extra_unique_dirs: list[str] = []
    for d in extra_lm_paths:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in seen_dirs:
            seen_dirs.add(norm)
            all_unet_dirs.append(d)
            extra_unique_dirs.append(d)

    if extra_lm_paths:
        if extra_unique_dirs:
            logger.info(
                "[Metadata Lib] Found %d extra UNet path(s) from LoraManager settings.",
                len(extra_unique_dirs),
            )
        else:
            logger.info(
                "[Metadata Lib] LoraManager settings.json defined UNet paths,"
                " but all are already covered by existing UNet directories.",
            )

    for unet_dir in all_unet_dirs:
        def _walk_error(exc: OSError, _dir: str = unet_dir) -> None:
            logger.warning(
                "[Metadata Lib] Skipping unreadable UNet path during index build: %s (%r)",
                _dir,
                exc,
            )
        try:
            for root, _, files in os.walk(unet_dir, onerror=_walk_error):
                for file in files:
                    file_base, file_ext = os.path.splitext(file)
                    if file_ext.lower() in extensions and file_base not in _UNET_INDEX:
                        _UNET_INDEX[file_base] = {
                            "filename": file,
                            "abspath": os.path.join(root, file),
                        }
        except OSError as exc:
            logger.warning(
                "[Metadata Lib] Aborted walk of UNet directory %s during index build: %r",
                unet_dir,
                exc,
            )
            continue

    _UNET_INDEX_BUILT = True
    logger.info("[Metadata Lib] UNet index built with %d entries.", len(_UNET_INDEX))
    try:
        if dump_env := os.environ.get("METADATA_DUMP_UNET_INDEX"):
            dump_path = dump_env.strip()
            if dump_path.lower() == "1":
                dump_path = os.path.join(os.getcwd(), "_unet_index_dump.json")
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(_UNET_INDEX, f, indent=2, sort_keys=True)
            logger.info("[Metadata Lib] UNet index dumped to %s", dump_path)
    except Exception as e:  # pragma: no cover - diagnostic optional
        logger.debug("[Metadata Lib] Failed dumping UNet index: %r", e)


def find_unet_info(base_name: str) -> dict[str, str] | None:
    """Find the indexed information for a UNet by its base name.

    Args:
        base_name (str): The base name of the UNet file (without the
            extension).

    Returns:
        dict[str, str] | None: A dictionary containing the ``filename`` and
            ``abspath`` of the UNet, or None if not found.
    """
    build_unet_index()
    if _UNET_INDEX is None:
        return None
    return _UNET_INDEX.get(base_name)


# -----------------------------
# Shared LoRA syntax utilities
# -----------------------------

# Strict pattern capturing optional separate clip strength:
# <lora:name:model_strength> OR <lora:name:model_strength:clip_strength>
STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
# Fallback (legacy) pattern capturing anything after the second colon
LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")


def coerce_first(val) -> str:
    """Return the first element when ``val`` is a list, otherwise the stringified value.

    Args:
        val: Object that may be a list or scalar value.

    Returns:
        str: ``val[0]`` when ``val`` is a non-empty list, an empty string for
        empty lists, or ``val`` when it is already a string.
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
    "get_lora_manager_paths",
    "build_lora_index",
    "find_lora_info",
    "build_checkpoint_index",
    "find_checkpoint_info",
    "build_unet_index",
    "find_unet_info",
    # syntax helpers
    "STRICT",
    "LEGACY",
    "coerce_first",
    "parse_lora_syntax",
    "resolve_lora_display_names",
]
