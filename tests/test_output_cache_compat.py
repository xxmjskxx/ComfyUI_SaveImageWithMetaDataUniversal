"""Test _OutputCacheCompat wrapper for ComfyUI 0.3.65+ API compatibility."""

import os

# Ensure test mode is enabled before importing capture
os.environ["METADATA_TEST_MODE"] = "1"

from saveimage_unimeta.capture import _OutputCacheCompat


def test_output_cache_compat_basic():
    """Test that _OutputCacheCompat provides get_output_cache method."""
    outputs = {
        "node1": ("output1",),
        "node2": ("output2", "output3"),
        "node3": None,
    }

    compat = _OutputCacheCompat(outputs)

    # Test retrieval of existing entries
    assert compat.get_output_cache("node1", "current") == ("output1",)
    assert compat.get_output_cache("node2", "current") == ("output2", "output3")
    assert compat.get_output_cache("node3", "current") is None

    # Test retrieval of non-existent entry
    assert compat.get_output_cache("nonexistent", "current") is None


def test_output_cache_compat_empty():
    """Test that _OutputCacheCompat handles empty dict."""
    compat = _OutputCacheCompat({})
    assert compat.get_output_cache("any", "node") is None


def test_output_cache_compat_none():
    """Test that _OutputCacheCompat handles None input."""
    compat = _OutputCacheCompat(None)
    assert compat.get_output_cache("any", "node") is None


def test_output_cache_compat_unique_id_unused():
    """Test that unique_id parameter is accepted but not used in dict lookup."""
    outputs = {"node1": ("value",)}
    compat = _OutputCacheCompat(outputs)

    # The second parameter (unique_id) should be ignored
    assert compat.get_output_cache("node1", "ignored1") == ("value",)
    assert compat.get_output_cache("node1", "ignored2") == ("value",)
    assert compat.get_output_cache("node1", None) == ("value",)
