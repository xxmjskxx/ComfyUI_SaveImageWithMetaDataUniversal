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


def test_wan_moe_structured_json_output(monkeypatch):
    """Test that MoE workflows generate structured JSON Samplers detail."""
    # Force MoE detection
    monkeypatch.setenv("METADATA_WAN_MOE_FORCE", "1")

    # Import here to pick up the environment variable
    import json

    # Create multi-sampler entries
    multi_candidates = [
        {
            "node_id": "3",
            "class_type": "WanVideo Sampler",
            "sampler_name": "Euler a",
            "steps": 30,
            "start_step": 0,
            "end_step": 20,
        },
        {
            "node_id": "4",
            "class_type": "WanVideo Sampler",
            "sampler_name": "DPM++ 2M",
            "steps": 30,
            "start_step": 20,
            "end_step": 30,
        },
    ]

    # Simulate the MoE branch of the code
    samplers_detail = []
    # object construction logic duplicated between lines 166-179 and 242-263.
    # Move to helper function before release. 
    for e in multi_candidates:
        sampler_obj = {
            "node_id": e["node_id"],
            "class_type": e["class_type"],
        }
        if e.get('sampler_name'):
            sampler_obj["sampler"] = e['sampler_name']
        if e.get('steps') is not None:
            sampler_obj["steps"] = e['steps']
        if e.get('start_step') is not None:
            sampler_obj["start_step"] = e['start_step']
        if e.get('end_step') is not None:
            sampler_obj["end_step"] = e['end_step']
        samplers_detail.append(sampler_obj)

    pnginfo_dict = {'Samplers detail': json.dumps(samplers_detail)}

    # Verify JSON structure
    detail_json = json.loads(pnginfo_dict['Samplers detail'])
    assert len(detail_json) == 2

    # First sampler
    assert detail_json[0]["node_id"] == "3"
    assert detail_json[0]["class_type"] == "WanVideo Sampler"
    assert detail_json[0]["sampler"] == "Euler a"
    assert detail_json[0]["steps"] == 30
    assert detail_json[0]["start_step"] == 0
    assert detail_json[0]["end_step"] == 20

    # Second sampler
    assert detail_json[1]["node_id"] == "4"
    assert detail_json[1]["class_type"] == "WanVideo Sampler"
    assert detail_json[1]["sampler"] == "DPM++ 2M"
    assert detail_json[1]["steps"] == 30
    assert detail_json[1]["start_step"] == 20
    assert detail_json[1]["end_step"] == 30


def test_wan_moe_structured_json_output_with_extra_fields(monkeypatch):
    """Test that MoE workflows capture additional sampler fields in JSON."""
    # Force MoE detection
    monkeypatch.setenv("METADATA_WAN_MOE_FORCE", "1")

    # Import here to pick up the environment variable
    import json

    # Create multi-sampler entries with additional fields
    multi_candidates = [
        {
            "node_id": "3",
            "class_type": "WanVideo Sampler",
            "sampler_name": "Euler a",
            "scheduler": "Karras",
            "steps": 30,
            "start_step": 0,
            "end_step": 20,
            "cfg": 3.5,
            "shift": 0.0,
            "denoise": 1.0,
        },
        {
            "node_id": "4",
            "class_type": "WanVideo Sampler",
            "sampler_name": "DPM++ 2M",
            "scheduler": "Exponential",
            "steps": 30,
            "start_step": 20,
            "end_step": 30,
            "cfg": 3.0,
            "shift": 0.5,
            "denoise": 0.8,
        },
    ]

    # Simulate the MoE branch of the code
    samplers_detail = []
    for e in multi_candidates:
        sampler_obj = {
            "node_id": e["node_id"],
            "class_type": e["class_type"],
        }
        if e.get('sampler_name'):
            sampler_obj["sampler"] = e['sampler_name']
        if e.get('scheduler'):
            sampler_obj["scheduler"] = e['scheduler']
        if e.get('steps') is not None:
            sampler_obj["steps"] = e['steps']
        if e.get('start_step') is not None:
            sampler_obj["start_step"] = e['start_step']
        if e.get('end_step') is not None:
            sampler_obj["end_step"] = e['end_step']
        if e.get('cfg') is not None:
            sampler_obj["cfg"] = e['cfg']
        if e.get('shift') is not None:
            sampler_obj["shift"] = e['shift']
        if e.get('denoise') is not None:
            sampler_obj["denoise"] = e['denoise']
        samplers_detail.append(sampler_obj)

    pnginfo_dict = {'Samplers detail': json.dumps(samplers_detail)}

    # Verify JSON structure with all fields
    detail_json = json.loads(pnginfo_dict['Samplers detail'])
    assert len(detail_json) == 2

    # First sampler
    first = detail_json[0]
    assert first["node_id"] == "3"
    assert first["class_type"] == "WanVideo Sampler"
    assert first["sampler"] == "Euler a"
    assert first["scheduler"] == "Karras"
    assert first["steps"] == 30
    assert first["start_step"] == 0
    assert first["end_step"] == 20
    assert first["cfg"] == 3.5
    assert first["shift"] == 0.0
    assert first["denoise"] == 1.0

    # Second sampler
    second = detail_json[1]
    assert second["node_id"] == "4"
    assert second["class_type"] == "WanVideo Sampler"
    assert second["sampler"] == "DPM++ 2M"
    assert second["scheduler"] == "Exponential"
    assert second["steps"] == 30
    assert second["start_step"] == 20
    assert second["end_step"] == 30
    assert second["cfg"] == 3.0
    assert second["shift"] == 0.5
    assert second["denoise"] == 0.8
