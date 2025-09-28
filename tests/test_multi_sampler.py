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
