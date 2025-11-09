#!/usr/bin/env python3
"""Tests for _OutputCacheCompat wrapper for ComfyUI 0.3.65+ compatibility."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path (must be before project imports for test environment)
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from saveimage_unimeta.capture import _OutputCacheCompat  # noqa: E402


def test_output_cache_compat_basic():
    """Test basic functionality of _OutputCacheCompat wrapper."""
    outputs = {
        "1": ("output1",),
        "2": ("output2", "extra"),
        "3": None,
    }

    compat = _OutputCacheCompat(outputs)

    # Test get_output_cache method
    assert compat.get_output_cache("1", "current") == ("output1",)
    assert compat.get_output_cache("2", "current") == ("output2", "extra")
    assert compat.get_output_cache("3", "current") is None
    assert compat.get_output_cache("nonexistent", "current") is None


def test_output_cache_compat_none_input():
    """Test _OutputCacheCompat with None input."""
    compat = _OutputCacheCompat(None)

    # Should handle None gracefully by using empty dict
    assert compat.get_output_cache("any", "current") is None


def test_output_cache_compat_empty_dict():
    """Test _OutputCacheCompat with empty dict."""
    compat = _OutputCacheCompat({})

    # Should return None for any key
    assert compat.get_output_cache("any", "current") is None


def test_output_cache_compat_interface():
    """Test that _OutputCacheCompat has the expected interface."""
    compat = _OutputCacheCompat({})

    # Should have get_output_cache method
    assert hasattr(compat, "get_output_cache")
    assert callable(compat.get_output_cache)

    # Should accept two arguments
    result = compat.get_output_cache("input_id", "unique_id")
    assert result is None  # Empty dict case


def test_output_cache_compat_preserves_values():
    """Test that _OutputCacheCompat preserves complex output values."""
    complex_output = {
        "node1": ([1, 2, 3], {"key": "value"}),
        "node2": (["string", 42, None],),
        "node3": (None, None, None),
    }

    compat = _OutputCacheCompat(complex_output)

    # Should preserve exact values
    assert compat.get_output_cache("node1", "x") == ([1, 2, 3], {"key": "value"})
    assert compat.get_output_cache("node2", "x") == (["string", 42, None],)
    assert compat.get_output_cache("node3", "x") == (None, None, None)


def test_output_cache_compat_get_cache_alias():
    """Test that get_cache method works as an alias for get_output_cache.

    Some ComfyUI versions call get_cache() instead of get_output_cache().
    This test verifies both methods return the same results.
    """
    outputs = {
        "1": ("output1",),
        "2": ("output2", "extra"),
        "3": None,
    }

    compat = _OutputCacheCompat(outputs)

    # Test that get_cache exists and works
    assert hasattr(compat, "get_cache")
    assert callable(compat.get_cache)

    # Test that get_cache returns the same results as get_output_cache
    assert compat.get_cache("1", "current") == compat.get_output_cache("1", "current")
    assert compat.get_cache("2", "current") == compat.get_output_cache("2", "current")
    assert compat.get_cache("3", "current") == compat.get_output_cache("3", "current")
    assert compat.get_cache("nonexistent", "current") == compat.get_output_cache("nonexistent", "current")

    # Verify specific values
    assert compat.get_cache("1", "current") == ("output1",)
    assert compat.get_cache("2", "current") == ("output2", "extra")
    assert compat.get_cache("3", "current") is None
    assert compat.get_cache("nonexistent", "current") is None
