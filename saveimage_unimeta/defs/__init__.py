# ruff: noqa: N999 - Package folder name mandated by external distribution (cannot snake_case)
"""Dynamic definition loading for metadata capture.

Responsibilities:
    * Maintain baseline (default) sampler & capture rule dictionaries.
    * Load python extension modules (defs/ext) and merge their contributions.
    * Optionally merge user JSON definitions only when required classes are missing.
    * Expose helper entry points to refresh or partially load definitions.
"""

# import importlib
import glob  # noqa: N999 - retained package path naming required by distribution
import json
import os
import os as _os
from collections.abc import Mapping
from importlib import import_module
from json import JSONDecodeError
from logging import getLogger

# from .meta import MetaField
# from ..utils.color import cstr
from ..utils.deserialize import deserialize_input

_TEST_MODE = bool(_os.environ.get("METADATA_TEST_MODE"))
if not _TEST_MODE:
    from .captures import CAPTURE_FIELD_LIST  # type: ignore
    from .samplers import SAMPLERS  # type: ignore
else:  # Provide minimal placeholders sufficient for tests importing enums/utilities
    CAPTURE_FIELD_LIST = {}
    SAMPLERS = {}

FORCED_INCLUDE_CLASSES: set[str] = set()

def set_forced_include(raw: str) -> set[str]:  # pragma: no cover - simple setter
    """Parse and store forced include node class names.

    Args:
        raw: Comma or whitespace separated class names.

    Returns:
        The updated global set (for chaining / debugging / test assertions).
    """
    global FORCED_INCLUDE_CLASSES
    parsed = {c.strip() for c in raw.replace("\n", ",").split(",") if c.strip()}
    if parsed:
        FORCED_INCLUDE_CLASSES.update(parsed)
    return FORCED_INCLUDE_CLASSES

def clear_forced_include() -> set[str]:  # pragma: no cover - simple helper
    """Clear all globally forced include node classes.

    Returns:
        The now-empty global set (for chaining / test assertions).
    """
    FORCED_INCLUDE_CLASSES.clear()
    return FORCED_INCLUDE_CLASSES

__all__ = [
    "CAPTURE_FIELD_LIST",
    "FORCED_INCLUDE_CLASSES",
    "set_forced_include",
    "clear_forced_include",
]
###############################
# Extension loading utilities #
###############################

# --- Store the original, clean default lists ---
DEFAULT_SAMPLERS = SAMPLERS.copy()
DEFAULT_CAPTURES = CAPTURE_FIELD_LIST.copy()


def _reset_to_defaults() -> None:
    """Reset in-memory sampler & capture rule registries to their original defaults."""
    SAMPLERS.clear()
    CAPTURE_FIELD_LIST.clear()
    SAMPLERS.update(DEFAULT_SAMPLERS)
    CAPTURE_FIELD_LIST.update(DEFAULT_CAPTURES)


def _load_extensions() -> None:
    """Load python-based extensions from `defs/ext`.

    Only import errors or attribute errors are logged; other exceptions are allowed
    to propagate because they likely indicate programmer errors in extension code.
    """
    dir_name = os.path.dirname(os.path.abspath(__file__))
    for module_path in glob.glob(os.path.join(dir_name, "ext", "*.py")):
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        if module_name.startswith("__"):
            continue
        package_name = f"custom_nodes.ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.{module_name}"
        try:
            module = import_module(package_name)
        except ModuleNotFoundError as e:  # pragma: no cover - unlikely once packaged
            logger.warning("[Metadata Loader] Extension module not found '%s': %s", module_name, e)
            continue
        except ImportError as e:
            logger.warning("[Metadata Loader] Failed to import extension '%s': %s", module_name, e)
            continue
        # Merge captured dicts defensively
        # Merge CAPTURE_FIELD_LIST: deep-merge per node to avoid clobbering earlier fields
        try:
            ext_captures = getattr(module, "CAPTURE_FIELD_LIST", {})
            if isinstance(ext_captures, Mapping):  # type: ignore[arg-type]
                for node_name, rules in ext_captures.items():
                    # If either side is not a mapping, assign directly; otherwise merge fields
                    if (
                        node_name not in CAPTURE_FIELD_LIST
                        or not isinstance(CAPTURE_FIELD_LIST.get(node_name), Mapping)
                        or not isinstance(rules, Mapping)
                    ):  # type: ignore[arg-type]
                        CAPTURE_FIELD_LIST[node_name] = rules  # type: ignore[index]
                    else:
                        CAPTURE_FIELD_LIST[node_name].update(rules)  # type: ignore[assignment]
            else:  # pragma: no cover - defensive
                logger.warning(
                    "[Metadata Loader] Extension '%s' CAPTURE_FIELD_LIST not a mapping",
                    module_name,
                )
        except AttributeError:
            pass

        # Merge SAMPLERS: deep-merge per node key similar to captures
        try:
            ext_samplers = getattr(module, "SAMPLERS", {})
            if isinstance(ext_samplers, Mapping):  # type: ignore[arg-type]
                for key, val in ext_samplers.items():
                    if (
                        key not in SAMPLERS
                        or not isinstance(SAMPLERS.get(key), Mapping)
                        or not isinstance(val, Mapping)
                    ):  # type: ignore[arg-type]
                        SAMPLERS[key] = val  # type: ignore[index]
                    else:
                        SAMPLERS[key].update(val)  # type: ignore[assignment]
            else:  # pragma: no cover
                logger.warning(
                    "[Metadata Loader] Extension '%s' SAMPLERS not a mapping",
                    module_name,
                )
        except AttributeError:
            pass


def load_extensions_only() -> None:
    """Public helper to reset and load only defaults + extensions."""
    _reset_to_defaults()
    _load_extensions()


def load_user_definitions(required_classes: set | None = None, suppress_missing_log: bool = False) -> None:
    """
    Merge order and conditional loading per run:
      1) Reset to defaults
      2) Load python extensions (merge 1)
      3) If required_classes fully covered by merge 1, skip user JSON
         Otherwise, merge user JSON (merge 2)
    """
    logger.info("[Metadata Loader] Refreshing definitions (defaults + ext, then conditional user JSON)...")

    _reset_to_defaults()
    _load_extensions()

    # Compute coverage if requested
    cover_set = set(CAPTURE_FIELD_LIST.keys()) | set(SAMPLERS.keys())

    # Paths for user JSON
    NODE_PACK_DIR = os.path.dirname(  # noqa: N806
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    USER_CAPTURES_FILE = os.path.join(NODE_PACK_DIR, "py", "user_captures.json")  # noqa: N806
    USER_SAMPLERS_FILE = os.path.join(NODE_PACK_DIR, "py", "user_samplers.json")  # noqa: N806

    need_user_merge = True
    if required_classes:
        # If every required class is already covered by ext/defaults, we can skip user merge
        missing = [ct for ct in required_classes if ct not in cover_set]
        if not missing:
            need_user_merge = False
            logger.info("[Metadata Loader] Coverage satisfied by defaults+ext; skipping user JSON merge.")
        else:
            if not suppress_missing_log:
                logger.info(
                    "[Metadata Loader] Missing classes in defaults+ext: %s. Will attempt user JSON merge.",
                    missing,
                )

    if need_user_merge:
        if os.path.exists(USER_SAMPLERS_FILE):
            try:
                with open(USER_SAMPLERS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, Mapping):  # type: ignore[arg-type]
                    SAMPLERS.update(data)  # type: ignore[arg-type]
                else:  # pragma: no cover - defensive
                    logger.warning("[Metadata Loader] user_samplers.json did not contain a mapping; ignoring")
            except FileNotFoundError:  # pragma: no cover - race
                logger.warning("[Metadata Loader] user_samplers.json disappeared during load")
            except JSONDecodeError as e:
                logger.warning("[Metadata Loader] JSON decode error in user_samplers.json: %s", e)
            except OSError as e:  # IO problems
                logger.warning("[Metadata Loader] I/O error reading user_samplers.json: %s", e)

        if os.path.exists(USER_CAPTURES_FILE):
            try:
                deserialized_rules = deserialize_input(USER_CAPTURES_FILE)
                if isinstance(deserialized_rules, Mapping):  # type: ignore[arg-type]
                    for node_name, rules in deserialized_rules.items():
                        if node_name not in CAPTURE_FIELD_LIST:
                            CAPTURE_FIELD_LIST[node_name] = {}
                        # Each rules object should be a mapping
                        if isinstance(rules, Mapping):  # type: ignore[arg-type]
                            CAPTURE_FIELD_LIST[node_name].update(rules)  # type: ignore[arg-type]
                else:  # pragma: no cover
                    logger.warning("[Metadata Loader] user_captures did not deserialize to mapping; ignoring")
            except FileNotFoundError:  # pragma: no cover
                logger.warning("[Metadata Loader] user_captures.json disappeared during load")
            except JSONDecodeError as e:
                logger.warning("[Metadata Loader] JSON decode error in user_captures.json: %s", e)
            except OSError as e:
                logger.warning("[Metadata Loader] I/O error reading user_captures.json: %s", e)


# Logging setup
logger = getLogger(__name__)
