import importlib
import logging
import sys
from pathlib import Path

import pytest

try:  # Allow running tests both as editable install and from custom_nodes checkout
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import trace as trace_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField
except ModuleNotFoundError:  # pragma: no cover - fallback for local execution paths
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import trace as trace_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

@pytest.fixture()
def fresh_trace_module():
    """Reload the trace module to clear any patches left by other suites."""

    return importlib.reload(trace_mod)


def test_trace_builds_distance_map_and_ignores_missing_edges(fresh_trace_module):
    """Ensure BFS traversal records distances while skipping invalid edges."""

    prompt = {
        "save": {
            "class_type": "SaveNode",
            "inputs": {"sampler": ["sampler", 0], "noise": ["noise", 0], "text": "ignored"},
        },
        "sampler": {
            "class_type": "SamplerClass",
            "inputs": {"model": ["model", 0], "missing": ["absent", 0]},
        },
        "noise": {"class_type": "NoiseClass", "inputs": {}},
        "model": {"class_type": "ModelLoader", "inputs": {}},
    }

    trace_entry = fresh_trace_module.TraceEntry
    trace_tree = fresh_trace_module.Trace.trace("save", prompt)

    assert trace_tree["save"] == trace_entry(0, "SaveNode")
    assert trace_tree["sampler"].distance == 1
    assert trace_tree["model"].distance == 2
    assert trace_tree["noise"].distance == 1
    assert "absent" not in trace_tree  # missing downstream nodes are ignored


def test_trace_warns_when_start_node_missing(fresh_trace_module, caplog):
    """Verify missing start IDs emit a warning and return an empty trace."""

    caplog.set_level(logging.WARNING)
    trace_tree = fresh_trace_module.Trace.trace(
        "invalid",
        {"save": {"class_type": "SaveNode", "inputs": {}}},
    )

    assert trace_tree == {}
    assert "not found" in caplog.text


def test_find_sampler_node_id_respects_distance_strategy(fresh_trace_module, monkeypatch):
    """Explicit sampler entries should honor Farthest/Nearest distance ordering."""

    monkeypatch.setattr(
        fresh_trace_module,
        "SAMPLERS",
        {"ExplicitSampler": {"positive": "p"}},
        raising=False,
    )
    monkeypatch.setattr(fresh_trace_module, "CAPTURE_FIELD_LIST", {}, raising=False)

    trace_entry = fresh_trace_module.TraceEntry
    trace_tree = {
        "save": trace_entry(0, "SaveNode"),
        "near": trace_entry(1, "ExplicitSampler"),
        "far": trace_entry(4, "ExplicitSampler"),
    }

    far_id = fresh_trace_module.Trace.find_sampler_node_id(
        trace_tree,
        fresh_trace_module.SAMPLER_SELECTION_METHOD[0],
        None,
    )
    near_id = fresh_trace_module.Trace.find_sampler_node_id(
        trace_tree,
        fresh_trace_module.SAMPLER_SELECTION_METHOD[1],
        None,
    )

    assert far_id == "far"
    assert near_id == "near"


def test_find_sampler_node_id_uses_heuristics(fresh_trace_module, monkeypatch):
    """Sampler heuristics must fall back to capture rules when SAMPLERS is empty."""

    monkeypatch.setattr(fresh_trace_module, "SAMPLERS", {}, raising=False)
    monkeypatch.setattr(
        fresh_trace_module,
        "CAPTURE_FIELD_LIST",
        {
            "SamplerNameNode": {MetaField.SAMPLER_NAME: "name_field"},
            "StepCfgSampler": {MetaField.STEPS: "steps", MetaField.CFG: "cfg"},
        },
        raising=False,
    )

    trace_entry = fresh_trace_module.TraceEntry
    trace_tree = {
        "save": trace_entry(0, "SaveNode"),
        "heuristic_near": trace_entry(1, "SamplerNameNode"),
        "heuristic_far": trace_entry(3, "StepCfgSampler"),
    }

    result_nearest = fresh_trace_module.Trace.find_sampler_node_id(
        trace_tree,
        fresh_trace_module.SAMPLER_SELECTION_METHOD[1],
        None,
    )
    result_farthest = fresh_trace_module.Trace.find_sampler_node_id(
        trace_tree,
        fresh_trace_module.SAMPLER_SELECTION_METHOD[0],
        None,
    )

    assert result_nearest == "heuristic_near"
    assert result_farthest == "heuristic_far"


def test_find_sampler_node_id_by_node_id_requires_sampler_like(fresh_trace_module, monkeypatch):
    """By-node selection should only accept IDs that look like samplers."""

    monkeypatch.setattr(fresh_trace_module, "SAMPLERS", {}, raising=False)
    monkeypatch.setattr(
        fresh_trace_module,
        "CAPTURE_FIELD_LIST",
        {"SamplerNameNode": {MetaField.SAMPLER_NAME: "name_field"}},
        raising=False,
    )

    trace_entry = fresh_trace_module.TraceEntry
    trace_tree = {
        "100": trace_entry(2, "SamplerNameNode"),
        "200": trace_entry(1, "NotSampler"),
    }

    by_id_valid = fresh_trace_module.Trace.find_sampler_node_id(
        trace_tree,
        fresh_trace_module.SAMPLER_SELECTION_METHOD[2],
        100,
    )
    by_id_invalid = fresh_trace_module.Trace.find_sampler_node_id(
        trace_tree,
        fresh_trace_module.SAMPLER_SELECTION_METHOD[2],
        "200",
    )

    assert by_id_valid == "100"
    assert by_id_invalid == -1


def test_filter_inputs_by_trace_tree_sorts_and_filters(fresh_trace_module):
    """Filtering should drop malformed rows and order entries by trace distance."""

    inputs = {
        MetaField.SAMPLER_NAME: [
            ("sampler", "euler"),
            ("missing", "skip"),
            ("sampler",),
            ["sampler", "tensor"],
            "not-a-tuple",
        ],
        MetaField.STEPS: [
            ("loader", 30, "steps"),
            ["loader", 32, "steps"],
            ["unknown"],
        ],
    }

    trace_entry = fresh_trace_module.TraceEntry
    trace_tree = {
        "sampler": trace_entry(1, "Sampler"),
        "loader": trace_entry(2, "Loader"),
    }

    filtered = fresh_trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

    assert MetaField.SAMPLER_NAME in filtered
    assert MetaField.STEPS in filtered
    assert filtered[MetaField.SAMPLER_NAME] == [("sampler", "euler", 1), ("sampler", "tensor", 1)]
    assert filtered[MetaField.STEPS] == [("loader", 30, 2), ("loader", 32, 2)]
