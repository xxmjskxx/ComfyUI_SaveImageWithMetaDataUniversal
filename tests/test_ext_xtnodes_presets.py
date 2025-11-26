"""Tests for XTNodes and size_from_presets extension modules.

This module tests the selector and formatter functions defined in:
- saveimage_unimeta/defs/ext/XTNodes.py
- saveimage_unimeta/defs/ext/size_from_presets.py

Tests cover:
- LoRA data extraction from XTNodes LoraLoaderWithPreviews
- Dimension extraction from SizeFromPresets nodes
"""

from __future__ import annotations

import pytest

from saveimage_unimeta.defs.ext.XTNodes import (
    get_lora_data,
    get_lora_model_name,
    get_lora_strength,
    CAPTURE_FIELD_LIST as XTNODES_CAPTURE,
)
from saveimage_unimeta.defs.ext.size_from_presets import (
    get_width,
    get_height,
    CAPTURE_FIELD_LIST as PRESETS_CAPTURE,
)


# --- XTNodes tests ---


class TestXTNodesGetLoraData:
    """Tests for the get_lora_data helper function."""

    def test_extracts_active_lora_names(self):
        """Should extract lora names where on=True."""
        input_data = [
            {
                "lora_1": [{"lora": "model_a.safetensors", "strength": 0.8, "on": True}],
                "lora_2": [{"lora": "model_b.safetensors", "strength": 0.6, "on": True}],
            }
        ]
        result = get_lora_data(input_data, "lora")
        assert result == ["model_a.safetensors", "model_b.safetensors"]

    def test_extracts_active_lora_strengths(self):
        """Should extract strength values where on=True."""
        input_data = [
            {
                "lora_1": [{"lora": "model_a.safetensors", "strength": 0.8, "on": True}],
                "lora_2": [{"lora": "model_b.safetensors", "strength": 0.6, "on": True}],
            }
        ]
        result = get_lora_data(input_data, "strength")
        assert result == [0.8, 0.6]

    def test_filters_inactive_loras(self):
        """Should skip loras where on=False."""
        input_data = [
            {
                "lora_1": [{"lora": "active.safetensors", "strength": 1.0, "on": True}],
                "lora_2": [{"lora": "inactive.safetensors", "strength": 0.5, "on": False}],
            }
        ]
        result = get_lora_data(input_data, "lora")
        assert result == ["active.safetensors"]

    def test_ignores_non_lora_keys(self):
        """Should only process keys starting with 'lora_'."""
        input_data = [
            {
                "lora_1": [{"lora": "model.safetensors", "strength": 0.8, "on": True}],
                "other_key": [{"lora": "other.safetensors", "strength": 0.5, "on": True}],
                "model_name": [{"lora": "skip.safetensors", "strength": 0.3, "on": True}],
            }
        ]
        result = get_lora_data(input_data, "lora")
        assert result == ["model.safetensors"]

    def test_empty_input(self):
        """Should return empty list for empty input."""
        input_data = [{}]
        result = get_lora_data(input_data, "lora")
        assert result == []

    def test_all_inactive(self):
        """Should return empty list when all loras are off."""
        input_data = [
            {
                "lora_1": [{"lora": "off1.safetensors", "strength": 0.8, "on": False}],
                "lora_2": [{"lora": "off2.safetensors", "strength": 0.6, "on": False}],
            }
        ]
        assert get_lora_data(input_data, "lora") == []


class TestXTNodesGetLoraModelName:
    """Tests for the get_lora_model_name selector function."""

    def test_returns_active_lora_names(self):
        """Should return list of active LoRA names."""
        input_data = [
            {
                "lora_1": [{"lora": "my_lora.safetensors", "strength": 0.9, "on": True}],
            }
        ]
        result = get_lora_model_name(
            node_id="1",
            obj=None,
            prompt={},
            extra_data={},
            outputs={},
            input_data=input_data,
        )
        assert result == ["my_lora.safetensors"]


class TestXTNodesGetLoraStrength:
    """Tests for the get_lora_strength selector function."""

    def test_returns_active_lora_strengths(self):
        """Should return list of active LoRA strengths."""
        input_data = [
            {
                "lora_1": [{"lora": "lora1.safetensors", "strength": 0.75, "on": True}],
                "lora_2": [{"lora": "lora2.safetensors", "strength": 0.5, "on": True}],
            }
        ]
        result = get_lora_strength(
            node_id="1",
            obj=None,
            prompt={},
            extra_data={},
            outputs={},
            input_data=input_data,
        )
        assert result == [0.75, 0.5]


class TestXTNodesCaptureFieldList:
    """Tests for the XTNodes CAPTURE_FIELD_LIST structure."""

    def test_defines_lora_loader_with_previews(self):
        """Should define LoraLoaderWithPreviews node."""
        assert "LoraLoaderWithPreviews" in XTNODES_CAPTURE

    def test_defines_expected_metafields(self):
        """Should define expected metadata fields for the node."""
        from saveimage_unimeta.defs.meta import MetaField

        node_def = XTNODES_CAPTURE["LoraLoaderWithPreviews"]
        assert MetaField.LORA_MODEL_NAME in node_def
        assert MetaField.LORA_MODEL_HASH in node_def
        assert MetaField.LORA_STRENGTH_MODEL in node_def
        assert MetaField.LORA_STRENGTH_CLIP in node_def

    def test_selectors_are_callable(self):
        """All selectors should be callable functions."""
        from saveimage_unimeta.defs.meta import MetaField

        node_def = XTNODES_CAPTURE["LoraLoaderWithPreviews"]
        for field, rule in node_def.items():
            assert "selector" in rule
            assert callable(rule["selector"])


# --- size_from_presets tests ---


class TestSizeFromPresetsGetWidth:
    """Tests for the get_width formatter function."""

    def test_extracts_width_from_preset(self):
        """Should extract width from preset string."""
        result = get_width("1024 x 768", {})
        assert result == "1024"

    def test_handles_various_formats(self):
        """Should handle different spacing in preset strings."""
        assert get_width("512x512", {}) == "512"
        assert get_width("1920  x  1080", {}) == "1920"
        assert get_width("  640 x 480  ", {}) == "640"

    def test_handles_large_dimensions(self):
        """Should handle large dimension values."""
        result = get_width("4096 x 2160", {})
        assert result == "4096"


class TestSizeFromPresetsGetHeight:
    """Tests for the get_height formatter function."""

    def test_extracts_height_from_preset(self):
        """Should extract height from preset string."""
        result = get_height("1024 x 768", {})
        assert result == "768"

    def test_handles_various_formats(self):
        """Should handle different spacing in preset strings."""
        assert get_height("512x512", {}) == "512"
        assert get_height("1920  x  1080", {}) == "1080"
        assert get_height("  640 x 480  ", {}) == "480"

    def test_handles_large_dimensions(self):
        """Should handle large dimension values."""
        result = get_height("4096 x 2160", {})
        assert result == "2160"


class TestSizeFromPresetsCaptureFieldList:
    """Tests for the size_from_presets CAPTURE_FIELD_LIST structure."""

    def test_defines_sd15_node(self):
        """Should define EmptyLatentImageFromPresetsSD15 node."""
        assert "EmptyLatentImageFromPresetsSD15" in PRESETS_CAPTURE

    def test_defines_sdxl_node(self):
        """Should define EmptyLatentImageFromPresetsSDXL node."""
        assert "EmptyLatentImageFromPresetsSDXL" in PRESETS_CAPTURE

    def test_defines_expected_metafields(self):
        """Should define width and height fields for both nodes."""
        from saveimage_unimeta.defs.meta import MetaField

        for node_name in ["EmptyLatentImageFromPresetsSD15", "EmptyLatentImageFromPresetsSDXL"]:
            node_def = PRESETS_CAPTURE[node_name]
            assert MetaField.IMAGE_WIDTH in node_def
            assert MetaField.IMAGE_HEIGHT in node_def

    def test_uses_correct_field_name(self):
        """Should use 'preset' as the field_name."""
        from saveimage_unimeta.defs.meta import MetaField

        for node_name in ["EmptyLatentImageFromPresetsSD15", "EmptyLatentImageFromPresetsSDXL"]:
            node_def = PRESETS_CAPTURE[node_name]
            assert node_def[MetaField.IMAGE_WIDTH]["field_name"] == "preset"
            assert node_def[MetaField.IMAGE_HEIGHT]["field_name"] == "preset"

    def test_formatters_are_callable(self):
        """All formatters should be callable functions."""
        from saveimage_unimeta.defs.meta import MetaField

        for node_name in ["EmptyLatentImageFromPresetsSD15", "EmptyLatentImageFromPresetsSDXL"]:
            node_def = PRESETS_CAPTURE[node_name]
            assert callable(node_def[MetaField.IMAGE_WIDTH]["format"])
            assert callable(node_def[MetaField.IMAGE_HEIGHT]["format"])

