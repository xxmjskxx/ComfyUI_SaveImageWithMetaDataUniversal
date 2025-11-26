import importlib
import sys
from pathlib import Path

import pytest

try:  # Allow running from editable installs or repo checkout
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import hook as hook_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import (
        SaveImageWithMetaDataUniversal,
    )
except ModuleNotFoundError:  # pragma: no cover - fallback path for pytest
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import hook as hook_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import (
        SaveImageWithMetaDataUniversal,
    )


@pytest.fixture()
def fresh_hook_module():
    """Reload the hook module so globals reset before each scenario."""

    return importlib.reload(hook_mod)


# Verify pre_execute captures prompt + extra data into module-level globals.
def test_pre_execute_captures_state(fresh_hook_module):
    prompt = {"1": {"class_type": "Test"}}
    extra = {"note": "hello"}

    class DummyExecutor:  # simple marker for identity tests
        pass

    executor = DummyExecutor()
    fresh_hook_module.pre_execute(executor, prompt, "abc", extra, execute_outputs=None)

    assert fresh_hook_module.current_prompt is prompt
    assert fresh_hook_module.current_extra_data is extra
    assert fresh_hook_module.prompt_executer is executor


# Ensure pre_get_input_data only updates the save-node ID when class matches.
def test_pre_get_input_data_updates_only_for_save_node(fresh_hook_module):
    fresh_hook_module.current_save_image_node_id = -1

    fresh_hook_module.pre_get_input_data({}, SaveImageWithMetaDataUniversal, "node-123")
    assert fresh_hook_module.current_save_image_node_id == "node-123"

    # Other classes should leave the ID untouched
    class AnotherNode:
        pass

    fresh_hook_module.pre_get_input_data({}, AnotherNode, "ignored")
    assert fresh_hook_module.current_save_image_node_id == "node-123"
