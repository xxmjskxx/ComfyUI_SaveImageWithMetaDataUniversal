# ruff: noqa: N999 - Package folder name mandated by ComfyUI extension registry (CamelCase preserved)
"""Top-level package marker for tests and tooling.

Allows imports like:
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

Runtime (ComfyUI) does not require this, but test isolation does.
"""

import os
import importlib  # moved to module scope to avoid repeated import in __getattr__


__all__ = [
    # Populated lazily; left for static analyzers
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "saveimage_unimeta",  # exposed via __getattr__ for lazy import
]

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")


def _lazy_load_nodes():  # pragma: no cover - side-effect only
    global NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    if NODE_CLASS_MAPPINGS:  # already loaded
        return
    try:
        from .saveimage_unimeta.nodes import (
            NODE_CLASS_MAPPINGS as _NCM,
        )
        from .saveimage_unimeta.nodes import (
            NODE_DISPLAY_NAME_MAPPINGS as _NDNM,
        )

        NODE_CLASS_MAPPINGS = _NCM
        NODE_DISPLAY_NAME_MAPPINGS = _NDNM
    except Exception:  # noqa: BLE001
        # In unit test environment without ComfyUI dependencies we silently continue.
        NODE_CLASS_MAPPINGS = {}
        NODE_DISPLAY_NAME_MAPPINGS = {}


def _maybe_log_startup():  # pragma: no cover
    """Log startup message exactly once per Python session."""
    import logging

    # Use logging module's internal registry as persistent storage
    # This survives module reloads and reimports within the same Python session
    logger = logging.getLogger(__name__)
    startup_registry = logging.getLogger("_startup_registry")
    startup_marker = f"{__name__}_logged"

    # Check if we've already logged startup for this module
    if hasattr(startup_registry, startup_marker):
        return

    # Mark that we've logged startup for this module
    setattr(startup_registry, startup_marker, True)

    try:
        from .saveimage_unimeta.utils.color import cstr  # local import to avoid heavy deps early
    except ImportError:
        # Fallback for test environments without full dependencies
        class MockCstr:
            def __init__(self, text):
                self.text = str(text)

            @property
            def msg_o(self):
                return self.text

            @property
            def lightviolet(self):
                return self.text

            @property
            def end(self):
                return self.text

        cstr = MockCstr

    try:
        count = len(NODE_CLASS_MAPPINGS.keys())
    except Exception:  # noqa: BLE001
        count = 0

    logger.info(
        " ".join(
            [
                cstr("Finished.").msg_o,
                cstr("Loaded").lightviolet,
                cstr(count).end,
                cstr("nodes successfully.").lightviolet,
            ]
        )
    )


# --- Lazy attribute access -------------------------------------------------
# Some tests (and potentially user code) attempt to patch or access
# 'ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.*'. When the top
# level package is imported using a custom loader (as done in tests with
# importlib.util.module_from_spec), Python's usual automatic addition of
# submodules to the parent package's namespace can be bypassed. Implement
# PEP 562 style module __getattr__ so attribute resolution triggers a lazy
# import of the subpackage.
def __getattr__(name):  # pragma: no cover - simple passthrough
    if name == "saveimage_unimeta":
        mod = importlib.import_module(f"{__name__}.saveimage_unimeta")
        # Cache the module to avoid redundant imports
        globals()[name] = mod
        return mod
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


_ENV = __import__("os").environ
if "PYTEST_CURRENT_TEST" not in _ENV and "METADATA_TEST_MODE" not in _ENV:
    _lazy_load_nodes()
    _maybe_log_startup()
