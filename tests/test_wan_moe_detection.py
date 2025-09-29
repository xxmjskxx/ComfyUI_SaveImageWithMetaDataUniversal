"""Test WAN MoE detection and enhanced multi-sampler functionality."""

import os
import json
import pytest

# Ensure test mode for deterministic formatting
os.environ.setdefault("METADATA_TEST_MODE", "1")

from saveimage_unimeta.nodes.save_image import _is_wan_moe_workflow
from saveimage_unimeta.defs.meta import MetaField
from saveimage_unimeta.defs.ext.wan_video_wrapper import CAPTURE_FIELD_LIST


def test_wan_moe_detection_two_models_two_samplers():
    """MoE should be detected with ≥2 model loaders and ≥2 samplers."""
    trace_tree = {
        "1": (3, "WanVideoModelLoader"),  # high model
        "2": (2, "WanVideoModelLoader"),  # low model
        "3": (1, "WanVideo Sampler"),    # first sampler
        "4": (0, "WanVideo Sampler"),    # second sampler
        "5": (0, "SaveImageWithMetaDataUniversal"),
    }
    assert _is_wan_moe_workflow(trace_tree) is True


def test_wan_moe_detection_single_model():
    """MoE should NOT be detected with only 1 model loader."""
    trace_tree = {
        "1": (2, "WanVideoModelLoader"),
        "2": (1, "WanVideo Sampler"),
        "3": (0, "WanVideo Sampler"),
        "4": (0, "SaveImageWithMetaDataUniversal"),
    }
    assert _is_wan_moe_workflow(trace_tree) is False


def test_wan_moe_detection_single_sampler():
    """MoE should NOT be detected with only 1 sampler (even with 2 models)."""
    trace_tree = {
        "1": (2, "WanVideoModelLoader"),
        "2": (2, "WanVideoModelLoader"),
        "3": (1, "WanVideo Sampler"),
        "4": (0, "SaveImageWithMetaDataUniversal"),
    }
    assert _is_wan_moe_workflow(trace_tree) is False


def test_wan_moe_force_environment_flag(monkeypatch):
    """METADATA_WAN_MOE_FORCE=1 should force MoE detection."""
    monkeypatch.setenv("METADATA_WAN_MOE_FORCE", "1")

    # Even single sampler should be detected as MoE when forced
    trace_tree = {
        "1": (1, "WanVideoModelLoader"),
        "2": (0, "WanVideo Sampler"),
        "3": (0, "SaveImageWithMetaDataUniversal"),
    }
    assert _is_wan_moe_workflow(trace_tree) is True


def test_wan_moe_disable_environment_flag(monkeypatch):
    """METADATA_WAN_MOE_DISABLE=1 should disable MoE detection."""
    monkeypatch.setenv("METADATA_WAN_MOE_DISABLE", "1")

    # Even clear MoE pattern should be disabled
    trace_tree = {
        "1": (3, "WanVideoModelLoader"),
        "2": (2, "WanVideoModelLoader"),
        "3": (1, "WanVideo Sampler"),
        "4": (0, "WanVideo Sampler"),
        "5": (0, "SaveImageWithMetaDataUniversal"),
    }
    assert _is_wan_moe_workflow(trace_tree) is False


def test_wan_sampler_has_start_end_step_fields():
    """WanVideo Sampler should have START_STEP and END_STEP capture rules."""
    rules = CAPTURE_FIELD_LIST.get("WanVideo Sampler", {})

    assert MetaField.START_STEP in rules
    assert MetaField.END_STEP in rules

    # Should map to field_name
    assert rules[MetaField.START_STEP]["field_name"] == "start_step"
    assert rules[MetaField.END_STEP]["field_name"] == "end_step"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
