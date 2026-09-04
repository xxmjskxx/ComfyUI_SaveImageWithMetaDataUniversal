"""Tests for M3: primary model selection and sampler-selection hardening."""

from __future__ import annotations

import pytest

from saveimage_unimeta import trace as trace_mod
from saveimage_unimeta.capture import Capture
from saveimage_unimeta.defs.combo import MODEL_SELECTION_METHOD, SAMPLER_SELECTION_METHOD
from saveimage_unimeta.defs.meta import MetaField

_CKPT_RULES = {
    MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
    MetaField.MODEL_HASH: {"field_name": "ckpt_name"},
}


@pytest.fixture()
def trace_rules(monkeypatch):
    """Install minimal SAMPLERS/CAPTURE_FIELD_LIST rules for the trace module."""
    monkeypatch.setattr(trace_mod, "SAMPLERS", {"KSampler": {"steps": "steps"}}, raising=False)
    monkeypatch.setattr(
        trace_mod,
        "CAPTURE_FIELD_LIST",
        {"CheckpointLoaderSimple": _CKPT_RULES},
        raising=False,
    )


def test_combo_values() -> None:
    assert SAMPLER_SELECTION_METHOD == ["Farthest", "Auto (Nearest)", "By node ID"]
    assert MODEL_SELECTION_METHOD == ["Auto", "By node ID"]


def test_sampler_selection_legacy_nearest_alias(trace_rules) -> None:
    prompt = {
        "s": {"class_type": "SaveImage", "inputs": {"images": ["1", 0]}},
        "1": {"class_type": "KSampler", "inputs": {"model": ["m", 0]}},
        "m": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}},
    }
    trace_tree = trace_mod.Trace.trace("s", prompt)
    assert trace_mod.Trace.find_sampler_node_id(trace_tree, "Nearest", 0) == "1"
    assert trace_mod.Trace.find_sampler_node_id(trace_tree, "Auto (Nearest)", 0) == "1"


def test_find_model_node_id_single_loader(trace_rules) -> None:
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {"model": ["2", 0]}},
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}},
    }
    assert trace_mod.Trace.find_model_node_id("1", prompt) == "2"


def test_find_model_node_id_by_node_id(trace_rules) -> None:
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {"model": ["2", 0]}},
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}},
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "y.safetensors"}},
    }
    assert trace_mod.Trace.find_model_node_id("1", prompt, MODEL_SELECTION_METHOD[1], "3") == "3"
    assert trace_mod.Trace.find_model_node_id("1", prompt, MODEL_SELECTION_METHOD[1], "99") == -1


def test_find_model_node_id_walks_intermediate_with_tiebreak(trace_rules) -> None:
    # The sampler's model input feeds a merge node consuming two loaders; both
    # are at distance 2, so the tie-break picks the lowest node id.
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {"model": ["3", 0]}},
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "a.safetensors"}},
        "3": {"class_type": "ModelMerge", "inputs": {"model1": ["2", 0], "model2": ["4", 0]}},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "b.safetensors"}},
    }
    assert trace_mod.Trace.find_model_node_id("1", prompt) == "2"


def test_find_model_node_id_no_loader(trace_rules) -> None:
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {"model": ["2", 0]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "hello"}},
    }
    assert trace_mod.Trace.find_model_node_id("1", prompt) == -1


def test_gen_pnginfo_dict_prefers_primary_model() -> None:
    inputs_before_sampler = {
        MetaField.MODEL_NAME: [("2", "refiner", 2), ("1", "base", 1)],
        MetaField.MODEL_HASH: [("2", "bbbbbbbbbb", 2), ("1", "aaaaaaaaaa", 1)],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs_before_sampler, {}, False, model_node_id="2")
    assert pnginfo["Model"] == "refiner"
    assert pnginfo["Model hash"] == "bbbbbbbbbb"
    assert pnginfo.get("Model 2") == "base"
    assert pnginfo.get("Model 2 hash") == "aaaaaaaaaa"


def test_gen_pnginfo_dict_no_node_id_keeps_capture_order() -> None:
    inputs_before_sampler = {
        MetaField.MODEL_NAME: [("1", "first", 1), ("2", "second", 2)],
        MetaField.MODEL_HASH: [("1", "aaaaaaaaaa", 1), ("2", "bbbbbbbbbb", 2)],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs_before_sampler, {}, False)
    assert pnginfo["Model"] == "first"
    assert pnginfo["Model hash"] == "aaaaaaaaaa"
    assert pnginfo.get("Model 2") == "second"
    assert pnginfo.get("Model 2 hash") == "bbbbbbbbbb"
