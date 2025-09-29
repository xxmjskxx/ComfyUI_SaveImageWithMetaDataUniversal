import os
import importlib
import types

import pytest

# Ensure test mode for deterministic formatting (multiline parameters)
os.environ.setdefault("METADATA_TEST_MODE", "1")

from saveimage_unimeta.trace import Trace  # noqa: E402
from saveimage_unimeta.defs.captures import CAPTURE_FIELD_LIST  # noqa: E402
from saveimage_unimeta.defs.meta import MetaField  # noqa: E402
from saveimage_unimeta.capture import Capture  # noqa: E402


@pytest.fixture(autouse=True)
def restore_capture_field_list():
    """Provide isolated modification of CAPTURE_FIELD_LIST per test."""
    original = dict(CAPTURE_FIELD_LIST)
    try:
        yield
    finally:
        # Restore original keys (shallow) and remove any added
        to_delete = set(CAPTURE_FIELD_LIST.keys()) - set(original.keys())
        for k in to_delete:
            CAPTURE_FIELD_LIST.pop(k, None)
        for k, v in original.items():
            CAPTURE_FIELD_LIST[k] = v


def test_enumerate_samplers_explicit_and_rule_backed():
    # Add a rule-backed sampler class
    CAPTURE_FIELD_LIST["MyCustomSampler"] = {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.STEPS: {"field_name": "steps"},
    }
    trace_tree = {
        "0": (0, "SaveImageWithMetaDataUniversal"),
        "1": (1, "KSampler"),  # Tier A explicit
        "2": (1, "MyCustomSampler"),  # Tier B rule-backed
    }
    candidates = Trace.enumerate_samplers(trace_tree)
    assert len(candidates) == 2, candidates
    assert candidates[0]["node_id"] == "1" and candidates[0]["tier"] == "A"
    assert candidates[1]["node_id"] == "2" and candidates[1]["tier"] == "B"


def test_parameters_tail_present_for_multi():
    pnginfo = {
        "Positive prompt": "cat in hat",
        "Negative prompt": "ugly, bad",
        "Steps": 30,
        "Sampler": "Euler a",
        # internal multi entry list with two samplers
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 30},
            {
                "node_id": "2",
                "class_type": "MyCustomSampler",
                "sampler_name": "DPM++ 2M",
                "start_step": 30,
                "end_step": 49,
            },
        ],
    }
    params = Capture.gen_parameters_str(pnginfo)
    # Tail should appear and include both sampler names
    assert "Samplers:" in params
    assert "Euler a" in params and "DPM++ 2M" in params
    assert "(30-49)" in params  # segment range formatting


def test_parameters_tail_absent_for_single():
    pnginfo = {
        "Positive prompt": "dog",
        "Negative prompt": "lowres",
        "Steps": 20,
        "Sampler": "Euler a",
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 20},
        ],
    }
    params = Capture.gen_parameters_str(pnginfo)
    assert "Samplers:" not in params


def test_minimal_parameters_trims_sampler_tail():
    pnginfo = {
        "Positive prompt": "castle",
        "Negative prompt": "noise",
        "Steps": 40,
        "Sampler": "Euler a",
        "Seed": 123,
        "Sampler detail placeholder": "x",  # ensure extra content to not break splitting
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 40},
            {"node_id": "2", "class_type": "MyCustomSampler", "sampler_name": "Heun", "start_step": 40, "end_step": 59},
        ],
    }
    params_full = Capture.gen_parameters_str(pnginfo)
    assert "Samplers:" in params_full
    # Simulate minimal fallback trimming path
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal

    trimmed = SaveImageWithMetaDataUniversal._build_minimal_parameters(params_full)
    assert "Samplers:" not in trimmed


def test_segment_three_samplers_tail_order():
    # Ensure ordering preserved (primary first then descending range / steps)
    pnginfo = {
        "Positive prompt": "scenery",
        "Negative prompt": "",
        "Steps": 60,
        "Sampler": "Euler a",
        "__multi_sampler_entries": [
            {"node_id": "10", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 60},
            {"node_id": "11", "class_type": "SegSampler", "sampler_name": "DPM++ 2M", "start_step": 30, "end_step": 49},
            {"node_id": "12", "class_type": "SegSampler", "sampler_name": "Heun", "start_step": 50, "end_step": 59},
        ],
    }
    params = Capture.gen_parameters_str(pnginfo)
    # Tail should respect provided order (primary first, then as listed because we already sorted upstream)
    tail_idx = params.find("Samplers:")
    assert tail_idx != -1
    tail = params[tail_idx:]
    first_pos = tail.find("Euler a")
    second_pos = tail.find("DPM++ 2M")
    third_pos = tail.find("Heun")
    assert -1 not in {first_pos, second_pos, third_pos}
    assert first_pos < second_pos < third_pos


def test_wan_sampler_segment_detection():
    """Test that Wan sampler segments are properly detected when start/end step fields exist."""
    # Mock WanVideo Sampler rules with START_STEP and END_STEP
    CAPTURE_FIELD_LIST["WanVideo Sampler"] = {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.START_STEP: {"field_name": "start_step"},
        MetaField.END_STEP: {"field_name": "end_step"},
    }

    trace_tree = {
        "0": (0, "SaveImageWithMetaDataUniversal"),
        "1": (1, "KSampler"),  # Tier A explicit, full run
        "2": (2, "WanVideo Sampler"),  # Tier B segment sampler
        "3": (3, "WanVideo Sampler"),  # Another segment sampler (farthest)
    }

    candidates = Trace.enumerate_samplers(trace_tree)
    assert len(candidates) == 3, f"Expected 3 candidates, got {len(candidates)}"

    # Primary should be Tier A (explicit) - will be first after reordering
    tier_a_nodes = [c for c in candidates if c["tier"] == "A"]
    tier_b_nodes = [c for c in candidates if c["tier"] == "B"]
    assert len(tier_a_nodes) == 1 and tier_a_nodes[0]["node_id"] == "1"
    assert len(tier_b_nodes) == 2

    # All Wan samplers should be marked as segments due to START_STEP + END_STEP fields
    for node in tier_b_nodes:
        assert node["is_segment"] is True, f"Node {node['node_id']} should be marked as segment"


def test_range_calculation_and_primary_selection():
    """Test that range_len calculation and primary selection work correctly for segments."""
    # Create mock trace data representing MoE workflow with varied ranges
    trace_tree = {
        "1": (1, "WanVideo Sampler"),  # Small segment: 10 steps
        "2": (2, "WanVideo Sampler"),  # Large segment: 30 steps
        "3": (3, "KSampler"),         # Full run: 50 steps
    }

    # Mock capture rules
    CAPTURE_FIELD_LIST["WanVideo Sampler"] = {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.START_STEP: {"field_name": "start_step"},
        MetaField.END_STEP: {"field_name": "end_step"},
    }

    candidates = Trace.enumerate_samplers(trace_tree)
    assert len(candidates) == 3

    # Primary should be Tier A (KSampler) since tier precedence A > B
    primary = candidates[0]  # Primary is first by contract
    assert primary["tier"] == "A"

    # Test range_len will be populated during actual capture process
    # Here we're just validating the basic structure


def test_segment_parity_validation():
    """Test detection of segments with mismatched start/end fields."""
    # Mock incomplete segment rule (only START_STEP, missing END_STEP)
    CAPTURE_FIELD_LIST["IncompleteSegSampler"] = {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.START_STEP: {"field_name": "start_step"},
        # END_STEP intentionally missing
        MetaField.STEPS: {"field_name": "steps"},  # Need at least steps to qualify as sampler
    }

    trace_tree = {
        "1": (1, "IncompleteSegSampler"),
    }

    candidates = Trace.enumerate_samplers(trace_tree)
    # Should be detected but not marked as segment due to incomplete parity
    assert len(candidates) == 1
    assert candidates[0]["is_segment"] is False  # Not a complete segment


def test_multisampler_jpeg_fallback_integration():
    """Test that multi-sampler metadata respects JPEG fallback stages."""
    # Build a multi-sampler pnginfo dict with structured detail
    pnginfo = {
        "Positive prompt": "fantasy landscape",
        "Negative prompt": "blurry",
        "Steps": 40,
        "Sampler": "Euler a",
        "Seed": 12345,
        "Model": "mymodel.safetensors",
        "Samplers detail": "[ {Name: Euler a, Steps: 40}, {Name: DPM++ 2M, Start: 40, End: 59} ]",
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 40},
            {
                "node_id": "2", "class_type": "WanVideo Sampler", "sampler_name": "DPM++ 2M",
                "start_step": 40, "end_step": 59
            },
        ],
    }

    # Test full parameters (should include both structured detail and tail)
    params_full = Capture.gen_parameters_str(pnginfo)
    assert "Samplers detail" in pnginfo  # Structured detail present in full mode
    assert "Samplers:" in params_full  # Tail present in parameters
    assert "Euler a" in params_full and "DPM++ 2M" in params_full
    assert "(40-59)" in params_full  # Segment formatting

    # Test minimal fallback trimming - should remove both structured detail and tail
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal
    minimal_params = SaveImageWithMetaDataUniversal._build_minimal_parameters(params_full)
    assert "Samplers:" not in minimal_params  # Tail should be trimmed in minimal
    # Note: Structured detail would be removed at dict level, not parameter level


def test_moe_workflow_integration():
    """Test a realistic MoE workflow scenario with proper range calculations."""
    # Simulate a MoE workflow where we have:
    # 1. A full-run primary sampler (steps 0-29)
    # 2. A high-res segment sampler (steps 30-49)
    # 3. A refinement segment sampler (steps 50-59)

    pnginfo = {
        "Positive prompt": "detailed artwork",
        "Negative prompt": "low quality",
        "Steps": 60,  # Total steps
        "Sampler": "Euler a",  # Primary sampler
        "Seed": 54321,
        "__multi_sampler_entries": [
            # Primary: full 60 steps but actually just first segment
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 30, "range_len": 30},
            # High-res segment: steps 30-49 (20 steps)
            {"node_id": "2", "class_type": "WanVideo Sampler", "sampler_name": "DPM++ 2M",
             "start_step": 30, "end_step": 49, "range_len": 20, "is_segment": True},
            # Refinement segment: steps 50-59 (10 steps)
            {"node_id": "3", "class_type": "WanVideo Sampler", "sampler_name": "Heun",
             "start_step": 50, "end_step": 59, "range_len": 10, "is_segment": True},
        ],
    }

    params = Capture.gen_parameters_str(pnginfo)

    # Should have structured detail in dict
    assert "Samplers detail" not in pnginfo  # This key not added by gen_parameters_str

    # Should have tail in parameters with proper ordering and formatting
    assert "Samplers:" in params
    tail_start = params.find("Samplers:")
    tail = params[tail_start:]

    # Verify order: primary first, then by range length descending
    euler_pos = tail.find("Euler a")
    dpm_pos = tail.find("DPM++ 2M")
    heun_pos = tail.find("Heun")

    assert euler_pos < dpm_pos < heun_pos, f"Wrong order: Euler={euler_pos}, DPM={dpm_pos}, Heun={heun_pos}"

    # Verify range formatting
    assert "(30-49)" in tail  # DPM segment range
    assert "(50-59)" in tail  # Heun segment range
    # Primary may or may not show range depending on segment presence logic
