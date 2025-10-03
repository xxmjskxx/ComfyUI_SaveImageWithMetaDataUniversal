#!/usr/bin/env python3
"""Test for startup message deduplication in __init__.py"""

import importlib
import logging
import os
import sys
from io import StringIO
from unittest.mock import patch


def test_startup_message_only_once():
    """Test that startup message is only logged once even with multiple imports."""
    # Set up logging capture
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger("ComfyUI_SaveImageWithMetaDataUniversal")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Clean up any existing module state
    module_name = "ComfyUI_SaveImageWithMetaDataUniversal"
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Temporarily disable test mode to allow startup logging
    original_env = os.environ.get("METADATA_TEST_MODE")
    if "METADATA_TEST_MODE" in os.environ:
        del os.environ["METADATA_TEST_MODE"]

    try:
        # Import the module multiple times
        ncm_path = 'ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.NODE_CLASS_MAPPINGS'
        ndnm_path = 'ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.NODE_DISPLAY_NAME_MAPPINGS'

        with patch(ncm_path, {'TestNode': 'TestClass'}):
            with patch(ndnm_path, {'TestNode': 'Test Node'}):
                # First import
                spec = importlib.util.find_spec(module_name)
                module1 = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module1
                spec.loader.exec_module(module1)

                # Second import (should not log again)
                importlib.reload(module1)

                # Third import attempt
                importlib.reload(module1)

        # Check log output
        log_output = log_capture.getvalue()

        # Count startup messages
        startup_messages = log_output.count("Loaded")

        # Should only have one startup message despite multiple imports
        expected_max = 1
        assert startup_messages <= expected_max, (
            f"Expected at most {expected_max} startup message, got {startup_messages}. "
            f"Log output: {log_output}"
        )

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["METADATA_TEST_MODE"] = original_env

        # Clean up logging
        logger.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    test_startup_message_only_once()
    print("Startup message deduplication test passed!")
