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
from collections.abc import Mapping, MutableMapping
from importlib import import_module
from json import JSONDecodeError
from logging import getLogger
from typing import Any, cast

# from .meta import MetaField
# from ..utils.color import cstr
from ..utils.deserialize import deserialize_input

# Ensure submodule attribute access like `from saveimage_unimeta.defs import formatters`
# works reliably across environments/tests by importing the submodule here.
from . import formatters as formatters  # re-exported via __all__ for direct import

# Test mode is enabled only for explicit truthy tokens, not any non-empty string ("0" should be false)
# NOTE: Test mode is captured at import time for baseline import shaping, but
# path selection for user rules must be resilient to late environment flag
# injection (e.g. coverage run import ordering). We therefore also provide a
# runtime checker used inside loaders to avoid missing test-isolated files.
_TEST_MODE = _os.environ.get("METADATA_TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def _is_test_mode() -> bool:
    """Check if the package is running in test mode.

    This function checks the `METADATA_TEST_MODE` environment variable to
    determine if the package should operate in test mode.

    Returns:
        bool: True if test mode is enabled, False otherwise.
    """
    return _os.environ.get("METADATA_TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


CAPTURE_FIELD_LIST: dict[str, dict[str, Any]]
SAMPLERS: dict[str, dict[str, str]]

if not _TEST_MODE:
    from . import captures as _captures
    from . import samplers as _samplers

    CAPTURE_FIELD_LIST = cast(dict[str, dict[str, Any]], _captures.CAPTURE_FIELD_LIST)
    SAMPLERS = cast(dict[str, dict[str, str]], _samplers.SAMPLERS)
else:  # Provide minimal placeholders sufficient for tests importing enums/utilities
    CAPTURE_FIELD_LIST = {}
    SAMPLERS = {}

FORCED_INCLUDE_CLASSES: set[str] = set()
LOADED_RULES_VERSION: str | None = None


def set_forced_include(raw: str) -> set[str]:
    """Set the globally forced include node class names.

    This function parses a string of comma- or newline-separated node class
    names and adds them to the `FORCED_INCLUDE_CLASSES` set. These classes will
    always be included in the metadata capture process.

    Args:
        raw (str): A string containing comma or whitespace separated node class names to be forced.

    Returns:
        set[str]: The updated set of forced include class names (for chaining / debugging / test assertions).
    """
    global FORCED_INCLUDE_CLASSES
    parsed = {c.strip() for c in raw.replace("\n", ",").split(",") if c.strip()}
    if parsed:
        FORCED_INCLUDE_CLASSES.update(parsed)
    return FORCED_INCLUDE_CLASSES


def clear_forced_include() -> set[str]:
    """Clear the set of globally forced include node class names.

    Returns:
        set[str]: The (now empty) set of forced include class names (for chaining / test assertions).
    """
    FORCED_INCLUDE_CLASSES.clear()
    return FORCED_INCLUDE_CLASSES


__all__ = [
    "CAPTURE_FIELD_LIST",
    "FORCED_INCLUDE_CLASSES",
    "LOADED_RULES_VERSION",
    "set_forced_include",
    "clear_forced_include",
    # Submodules expected to be importable via package (tests rely on this)
    "formatters",
]
###############################
# Extension loading utilities #
###############################

# --- Store the original, clean default lists ---
DEFAULT_SAMPLERS = SAMPLERS.copy()
DEFAULT_CAPTURES = CAPTURE_FIELD_LIST.copy()


def _reset_to_defaults() -> None:
    """Reset the in-memory capture and sampler rules to their default state."""
    SAMPLERS.clear()
    CAPTURE_FIELD_LIST.clear()
    SAMPLERS.update(DEFAULT_SAMPLERS)
    CAPTURE_FIELD_LIST.update(DEFAULT_CAPTURES)
    global LOADED_RULES_VERSION
    LOADED_RULES_VERSION = None


def _load_extensions() -> None:
    """Load and merge python-based extensions from the `defs/ext` directory.
    Only import errors or attribute errors are logged; other exceptions are allowed
    to propagate because they likely indicate programmer errors in extension code.
    """
    dir_name = os.path.dirname(os.path.abspath(__file__))
    global LOADED_RULES_VERSION
    module_paths = glob.glob(os.path.join(dir_name, "ext", "*.py"))
    # Load generated_user_rules first so curated modules can override its raw field captures.
    module_paths.sort(
        key=lambda path: (
            os.path.splitext(os.path.basename(path))[0].lower() != "generated_user_rules",
            os.path.basename(path).lower(),
        )
    )

    for module_path in module_paths:
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        # Never import example/reference files
        if (
            module_name.startswith("__")
            or module_name.endswith("_examples")
            or module_name == "generated_user_rules_examples"
        ):
            continue
        package_name = f"custom_nodes.ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.{module_name}"
        try:
            module = import_module(package_name)
        except ModuleNotFoundError as e:  # pragma: no cover - expected when optional custom node not installed
            # Extensions are optional - only needed if the corresponding custom node is installed
            # Log at debug level since this is expected behavior, not an error
            logger.debug(
                "[Metadata Loader] Optional extension '%s' skipped (custom node not installed): %s",
                module_name,
                e,
            )
            continue
        except ImportError as e:
            logger.warning("[Metadata Loader] Failed to import extension '%s': %s", module_name, e)
            continue
        try:
            rules_version = getattr(module, "RULES_VERSION", None)
        except AttributeError:
            rules_version = None
        if isinstance(rules_version, str):
            normalized_version = rules_version.strip()
            if normalized_version and module_name == "generated_user_rules":
                LOADED_RULES_VERSION = normalized_version
        # Merge captured dicts defensively
        # Merge CAPTURE_FIELD_LIST: deep-merge per node to avoid clobbering earlier fields
        try:
            ext_captures = getattr(module, "CAPTURE_FIELD_LIST", {})
            if isinstance(ext_captures, Mapping):
                for node_name, rules in ext_captures.items():
                    _merge_extension_capture_entry(node_name, rules)
            else:  # pragma: no cover - defensive
                logger.warning(
                    "[Metadata Loader] Extension '%s' CAPTURE_FIELD_LIST not a mapping",
                    module_name,
                )
        except AttributeError:
            pass  # Extension doesn't define CAPTURE_FIELD_LIST - gracefully continue

        # Merge SAMPLERS: deep-merge per node key similar to captures
        try:
            ext_samplers = getattr(module, "SAMPLERS", {})
            if isinstance(ext_samplers, Mapping):
                for key, val in ext_samplers.items():
                    if (
                        key not in SAMPLERS
                        or not isinstance(SAMPLERS.get(key), Mapping)
                        or not isinstance(val, Mapping)
                    ):
                        SAMPLERS[key] = val
                    else:
                        SAMPLERS[key].update(val)
            else:  # pragma: no cover
                logger.warning(
                    "[Metadata Loader] Extension '%s' SAMPLERS not a mapping",
                    module_name,
                )
        except AttributeError:
            pass  # Extension doesn't define SAMPLERS - gracefully continue


def load_extensions_only() -> None:
    """Reset to defaults and load only the python-based extensions."""
    _reset_to_defaults()
    _load_extensions()


def _merge_extension_capture_entry(node_name: str, rules) -> None:
    """Merge a capture rule entry from an extension into the main list.
    Semantics (must match original inline logic):
      * If the existing entry or new value isn't a mapping, assign directly.
      * If both are mappings, shallow-update the existing mapping.
    Args:
        node_name (str): The name of the node the rule applies to.
        rules (dict): The dictionary of rules to be merged.
    """
    existing = CAPTURE_FIELD_LIST.get(node_name)
    if (
        node_name not in CAPTURE_FIELD_LIST
        or not isinstance(existing, MutableMapping)
        or not isinstance(rules, Mapping)
    ):
        CAPTURE_FIELD_LIST[node_name] = dict(rules) if isinstance(rules, Mapping) else rules
    else:
        existing.update(rules)


def _merge_user_capture_entry(node_name: str, rules, allowed: set[str] | None) -> None:
    """Merge a user-defined capture rule entry from JSON.
    Semantics (must match original inline logic):
      * Ensure a dict container exists for the node name.
      * Only update when the provided rules value is a mapping; otherwise skip.
    Args:
        node_name (str): The name of the node the rule applies to.
        rules (dict): The dictionary of rules to be merged.
    """
    if allowed is not None and node_name not in allowed and node_name not in CAPTURE_FIELD_LIST:
        return
    container = CAPTURE_FIELD_LIST.setdefault(node_name, {})
    if isinstance(container, MutableMapping) and isinstance(rules, Mapping):
        container.update(rules)


def _merge_user_sampler_entry(key: str, val, allowed: set[str] | None) -> None:
    """Merge a user-defined sampler entry from JSON.
    Rules:
      * Non-mapping values are skipped with a warning.
      * If the existing entry is absent or not a mapping, the value is assigned.
      * If both sides are mappings, perform an in-place update (shallow merge).
    Args:
        key (str): The key for the sampler entry.
        val (dict): The dictionary of sampler information to be merged.
    """
    if allowed is not None and key not in allowed and key not in SAMPLERS:
        return
    if not isinstance(val, Mapping):
        logger.warning(
            "[Metadata Loader] user_samplers key '%s' is not a mapping; skipping",
            key,
        )
        return
    existing_sampler = SAMPLERS.get(key)
    if not isinstance(existing_sampler, MutableMapping):
        SAMPLERS[key] = dict(val)
    else:
        existing_sampler.update(val)


def load_user_definitions(required_classes: set | None = None, suppress_missing_log: bool = False) -> None:
    """Load and merge user-defined capture and sampler rules.

    This function orchestrates the loading of metadata definitions, following a
    specific merge order:
    1. Reset to the default rules.
    2. Load and merge rules from python extensions.
    3. Conditionally load and merge rules from user-defined JSON files, if
       necessary to cover the `required_classes`.

    Args:
        required_classes (set | None, optional): A set of node class names that
            must be covered by the loaded rules. If None, user JSON files are
            always loaded. Defaults to None.
        suppress_missing_log (bool, optional): If True, warnings about missing
            class coverage are suppressed. Defaults to False.
    """
    logger.info("[Metadata Loader] Refreshing definitions (defaults + ext, then conditional user JSON)...")

    _reset_to_defaults()
    _load_extensions()

    # Compute coverage if requested
    cover_set = set(CAPTURE_FIELD_LIST.keys()) | set(SAMPLERS.keys())
    allowed_user_classes: set[str] | None = None
    if required_classes is not None:
        allowed_user_classes = set(required_classes)
        if FORCED_INCLUDE_CLASSES:
            allowed_user_classes.update(FORCED_INCLUDE_CLASSES)

    # Paths for user JSON
    NODE_PACK_DIR = os.path.dirname(  # noqa: N806
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    # User rule directory relocation: legacy was 'py/'. New directory 'user_rules/'.
    # In test mode, prefer an isolated tests/_test_outputs/user_rules directory if present to avoid polluting repo root.
    TEST_OUTPUTS_DIR = os.path.join(NODE_PACK_DIR, "tests/_test_outputs")
    # Re-evaluate test mode at runtime so late env mutation still enables
    # isolation (coverage run import ordering can differ from local pytest).
    runtime_test_mode = _is_test_mode()
    preferred_user_rules = os.path.join(TEST_OUTPUTS_DIR, "user_rules") if runtime_test_mode else None
    if preferred_user_rules and os.path.isdir(preferred_user_rules):
        USER_RULES_DIR = preferred_user_rules  # noqa: N806
    else:
        USER_RULES_DIR = os.path.join(NODE_PACK_DIR, "user_rules")  # noqa: N806
    os.makedirs(USER_RULES_DIR, exist_ok=True)
    USER_CAPTURES_FILE = os.path.join(USER_RULES_DIR, "user_captures.json")  # noqa: N806
    USER_SAMPLERS_FILE = os.path.join(USER_RULES_DIR, "user_samplers.json")  # noqa: N806
    # Migration shim: if new files absent but legacy exist, migrate once.
    LEGACY_PY_DIR = os.path.join(NODE_PACK_DIR, "py")  # noqa: N806
    # Test isolation: allow legacy files placed in tests/_test_outputs/py to migrate too.
    if _TEST_MODE:
        test_legacy = os.path.join(NODE_PACK_DIR, "tests/_test_outputs", "py")
        if os.path.isdir(test_legacy):  # prefer test-scoped legacy if present
            LEGACY_PY_DIR = test_legacy
    if not os.path.exists(USER_CAPTURES_FILE):
        legacy_caps = os.path.join(LEGACY_PY_DIR, "user_captures.json")
        if os.path.exists(legacy_caps):
            try:
                import shutil as _shutil

                _shutil.move(legacy_caps, USER_CAPTURES_FILE)
                logger.info("[Metadata Loader] Migrated legacy user_captures.json to user_rules/.")
            except Exception as e:  # pragma: no cover - non critical
                logger.warning("[Metadata Loader] Failed migrating user_captures.json: %s", e)
    if not os.path.exists(USER_SAMPLERS_FILE):
        legacy_samplers = os.path.join(LEGACY_PY_DIR, "user_samplers.json")
        if os.path.exists(legacy_samplers):
            try:
                import shutil as _shutil

                _shutil.move(legacy_samplers, USER_SAMPLERS_FILE)
                logger.info("[Metadata Loader] Migrated legacy user_samplers.json to user_rules/.")
            except Exception as e:  # pragma: no cover
                logger.warning("[Metadata Loader] Failed migrating user_samplers.json: %s", e)

    user_rules_exist = os.path.exists(USER_CAPTURES_FILE) or os.path.exists(USER_SAMPLERS_FILE)

    # Decide whether to attempt user JSON merge. We always merge when user files exist so that
    # overrides apply even if built-in coverage already handles the classes. When no user files are
    # present we skip the disk work unless the caller explicitly requested missing classes.
    need_user_merge = user_rules_exist or not required_classes
    if required_classes:
        missing = [ct for ct in required_classes if ct not in cover_set]
        if missing:
            need_user_merge = True
            if not suppress_missing_log:
                logger.info("[Metadata Loader] Missing classes in defaults+ext: %s. Will merge user JSON.", missing)
        elif not user_rules_exist:
            need_user_merge = False
            logger.info(
                "[Metadata Loader] Coverage satisfied by defaults+ext and no user rule files detected; skipping user JSON merge.",
            )

    if need_user_merge:
        if os.path.exists(USER_SAMPLERS_FILE):
            try:
                with open(USER_SAMPLERS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, Mapping):
                    for key, val in data.items():
                        _merge_user_sampler_entry(key, val, allowed_user_classes)
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
                if isinstance(deserialized_rules, Mapping):
                    for node_name, rules in deserialized_rules.items():
                        _merge_user_capture_entry(node_name, rules, allowed_user_classes)
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
