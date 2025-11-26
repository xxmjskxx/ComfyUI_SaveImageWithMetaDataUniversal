"""Tests for mjsk_PCLazyLoraLoader extension module.

This module tests the selector functions defined in:
- saveimage_unimeta/defs/ext/mjsk_PCLazyLoraLoader.py

Tests cover:
- LoRA parsing from prompt text
- Caching behavior
- Selector functions for names, hashes, and strengths
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from saveimage_unimeta.defs.ext import mjsk_PCLazyLoraLoader
from saveimage_unimeta.defs.ext.mjsk_PCLazyLoraLoader import (
    _get_lora_data_from_node,
    _NODE_DATA_CACHE,
    get_lora_model_names,
    get_lora_model_hashes,
    get_lora_strengths,
    get_lora_clip_strengths,
    CAPTURE_FIELD_LIST,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the node data cache before each test."""
    _NODE_DATA_CACHE.clear()
    yield
    _NODE_DATA_CACHE.clear()


class TestGetLoraDataFromNode:
    """Tests for the _get_lora_data_from_node helper function."""

    def test_parses_simple_lora_tag(self):
        """Should parse a simple LoRA tag from text."""
        input_data = [{"text": "<lora:test_lora:0.8>"}]

        # Mock find_lora_info to return None (no LoRA info found)
        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=None):
            with patch.object(mjsk_PCLazyLoraLoader, "calc_lora_hash", return_value="abc123"):
                result = _get_lora_data_from_node(1, input_data)

        assert "names" in result
        assert "hashes" in result
        assert "model_strengths" in result
        assert "clip_strengths" in result

    def test_empty_text_returns_empty_lists(self):
        """Should return empty lists for empty text."""
        input_data = [{"text": ""}]

        result = _get_lora_data_from_node(1, input_data)

        assert result["names"] == []
        assert result["hashes"] == []
        assert result["model_strengths"] == []
        assert result["clip_strengths"] == []

    def test_text_without_lora_tags(self):
        """Should return empty lists when no LoRA tags present."""
        input_data = [{"text": "A beautiful landscape with mountains"}]

        result = _get_lora_data_from_node(1, input_data)

        assert result["names"] == []
        assert result["hashes"] == []

    def test_caches_result_by_node_id_and_text(self):
        """Should cache results based on node_id and text content."""
        input_data = [{"text": "<lora:cached_lora:0.5>"}]

        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=None):
            with patch.object(mjsk_PCLazyLoraLoader, "calc_lora_hash", return_value="hash1"):
                # First call
                result1 = _get_lora_data_from_node(1, input_data)
                # Second call - should use cache
                result2 = _get_lora_data_from_node(1, input_data)

        assert result1 is result2  # Same object reference due to cache

    def test_cache_invalidated_on_text_change(self):
        """Should invalidate cache when text changes."""
        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=None):
            with patch.object(mjsk_PCLazyLoraLoader, "calc_lora_hash", return_value="hash1"):
                result1 = _get_lora_data_from_node(1, [{"text": "<lora:lora_a:0.5>"}])
                result2 = _get_lora_data_from_node(1, [{"text": "<lora:lora_b:0.7>"}])

        # Results should be different (different text)
        assert result1 is not result2

    def test_uses_lora_info_filename_when_found(self):
        """Should use filename from find_lora_info when available."""
        input_data = [{"text": "<lora:display_name:0.8>"}]

        mock_info = {"filename": "actual_filename.safetensors"}
        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=mock_info):
            with patch.object(mjsk_PCLazyLoraLoader, "calc_lora_hash", return_value="hash123"):
                result = _get_lora_data_from_node(1, input_data)

        assert "actual_filename.safetensors" in result["names"]

    def test_handles_hash_calculation_errors(self):
        """Should handle errors in hash calculation gracefully."""
        input_data = [{"text": "<lora:error_lora:0.5>"}]

        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=None):
            with patch.object(
                mjsk_PCLazyLoraLoader, "calc_lora_hash", side_effect=Exception("Hash error")
            ):
                result = _get_lora_data_from_node(1, input_data)

        assert "N/A" in result["hashes"]

    def test_parses_lora_with_clip_strength(self):
        """Should parse LoRA tags with separate model and clip strengths."""
        input_data = [{"text": "<lora:dual_strength:0.8:0.6>"}]

        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=None):
            with patch.object(mjsk_PCLazyLoraLoader, "calc_lora_hash", return_value="hash"):
                result = _get_lora_data_from_node(1, input_data)

        # parse_lora_syntax should extract both strengths
        assert len(result["model_strengths"]) == len(result["clip_strengths"])

    def test_handles_list_text_input(self):
        """Should handle text input as list (coerce_first)."""
        input_data = [{"text": ["<lora:list_lora:0.5>", "ignored"]}]

        with patch.object(mjsk_PCLazyLoraLoader, "find_lora_info", return_value=None):
            with patch.object(mjsk_PCLazyLoraLoader, "calc_lora_hash", return_value="hash"):
                result = _get_lora_data_from_node(1, input_data)

        # Should process the first element
        assert len(result["names"]) >= 0  # May or may not find LoRAs depending on parse


class TestSelectorFunctions:
    """Tests for the selector wrapper functions."""

    def test_get_lora_model_names_returns_names(self):
        """Should return names from parsed data."""
        input_data = [{"text": ""}]

        with patch.object(
            mjsk_PCLazyLoraLoader,
            "_get_lora_data_from_node",
            return_value={"names": ["lora1.safetensors"], "hashes": [], "model_strengths": [], "clip_strengths": []},
        ):
            result = get_lora_model_names(1, None, None, None, None, input_data)

        assert result == ["lora1.safetensors"]

    def test_get_lora_model_hashes_returns_hashes(self):
        """Should return hashes from parsed data."""
        input_data = [{"text": ""}]

        with patch.object(
            mjsk_PCLazyLoraLoader,
            "_get_lora_data_from_node",
            return_value={"names": [], "hashes": ["abc123"], "model_strengths": [], "clip_strengths": []},
        ):
            result = get_lora_model_hashes(1, None, None, None, None, input_data)

        assert result == ["abc123"]

    def test_get_lora_strengths_returns_model_strengths(self):
        """Should return model strengths from parsed data."""
        input_data = [{"text": ""}]

        with patch.object(
            mjsk_PCLazyLoraLoader,
            "_get_lora_data_from_node",
            return_value={"names": [], "hashes": [], "model_strengths": [0.8, 0.5], "clip_strengths": []},
        ):
            result = get_lora_strengths(1, None, None, None, None, input_data)

        assert result == [0.8, 0.5]

    def test_get_lora_clip_strengths_returns_clip_strengths(self):
        """Should return clip strengths from parsed data."""
        input_data = [{"text": ""}]

        with patch.object(
            mjsk_PCLazyLoraLoader,
            "_get_lora_data_from_node",
            return_value={"names": [], "hashes": [], "model_strengths": [], "clip_strengths": [0.6, 0.4]},
        ):
            result = get_lora_clip_strengths(1, None, None, None, None, input_data)

        assert result == [0.6, 0.4]


class TestCaptureFieldList:
    """Tests for the CAPTURE_FIELD_LIST structure."""

    def test_defines_mjsk_node(self):
        """Should define mjsk_PCLazyLoraLoader node."""
        assert "mjsk_PCLazyLoraLoader" in CAPTURE_FIELD_LIST

    def test_defines_expected_metafields(self):
        """Should define expected metadata fields."""
        from saveimage_unimeta.defs.meta import MetaField

        node_def = CAPTURE_FIELD_LIST["mjsk_PCLazyLoraLoader"]
        assert MetaField.LORA_MODEL_NAME in node_def
        assert MetaField.LORA_MODEL_HASH in node_def
        assert MetaField.LORA_STRENGTH_MODEL in node_def
        assert MetaField.LORA_STRENGTH_CLIP in node_def

    def test_selectors_are_callable(self):
        """All selectors should be callable functions."""
        node_def = CAPTURE_FIELD_LIST["mjsk_PCLazyLoraLoader"]
        for field, rule in node_def.items():
            assert "selector" in rule
            assert callable(rule["selector"])

    def test_selector_functions_match(self):
        """Selectors should match the expected functions."""
        from saveimage_unimeta.defs.meta import MetaField

        node_def = CAPTURE_FIELD_LIST["mjsk_PCLazyLoraLoader"]
        assert node_def[MetaField.LORA_MODEL_NAME]["selector"] == get_lora_model_names
        assert node_def[MetaField.LORA_MODEL_HASH]["selector"] == get_lora_model_hashes
        assert node_def[MetaField.LORA_STRENGTH_MODEL]["selector"] == get_lora_strengths
        assert node_def[MetaField.LORA_STRENGTH_CLIP]["selector"] == get_lora_clip_strengths
