# ruff: noqa: N999 - Package folder name mandated by ComfyUI extension registry (CamelCase preserved)
"""Top-level package marker for tests and tooling.

Allows imports like:
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

Runtime (ComfyUI) does not require this, but test isolation does.
"""

import os
import sys

__all__ = [
    # Populated lazily; left for static analyzers
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
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

    # Use a module-level registry that persists across reimports
    # Store the marker in sys.modules to survive module reloads
    startup_key = f"_startup_logged_{__name__}"

    # Check if we've already logged startup for this module in this Python session
    if startup_key in sys.modules:
        return

    # Mark that we've logged startup for this module
    sys.modules[startup_key] = True

    logger = logging.getLogger(__name__)

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


_ENV = __import__("os").environ
if "PYTEST_CURRENT_TEST" not in _ENV and "METADATA_TEST_MODE" not in _ENV:
    _lazy_load_nodes()
    _maybe_log_startup()
