"""Extended tests for trace.py covering edge cases and debug logging paths.

These tests complement test_trace.py by covering:
- _trace_debug_enabled function
- Debug logging output in trace, find_sampler_node_id, filter_inputs_by_trace_tree
- Edge cases in BFS traversal
- Handling of malformed inputs in filter_inputs_by_trace_tree
"""

import importlib
import logging
import os
import sys

import pytest


@pytest.fixture
def trace_module(monkeypatch):
    """Import a fresh trace module to reset state."""
    mod_name = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.trace"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    trace = importlib.import_module(mod_name)
    return trace


@pytest.fixture
def meta_module():
    """Import the MetaField enum."""
    return importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
    )


class TestTraceDebugEnabled:
    """Tests for _trace_debug_enabled function."""

    def test_trace_debug_disabled_by_default(self, trace_module, monkeypatch):
        """Debug should be disabled when env var is not set."""
        monkeypatch.delenv("METADATA_DEBUG_PROMPTS", raising=False)
        assert not trace_module._trace_debug_enabled()

    def test_trace_debug_enabled_when_set(self, trace_module, monkeypatch):
        """Debug should be enabled when env var is non-empty."""
        monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "1")
        assert trace_module._trace_debug_enabled()

    def test_trace_debug_disabled_when_empty(self, trace_module, monkeypatch):
        """Debug should be disabled when env var is empty string."""
        monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "")
        assert not trace_module._trace_debug_enabled()

    def test_trace_debug_disabled_when_whitespace(self, trace_module, monkeypatch):
        """Debug should be disabled when env var is just whitespace."""
        monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "   ")
        assert not trace_module._trace_debug_enabled()


class TestTraceEntry:
    """Tests for TraceEntry named tuple."""

    def test_trace_entry_creation(self, trace_module):
        """TraceEntry should store distance and class_type."""
        entry = trace_module.TraceEntry(3, "KSampler")
        assert entry.distance == 3
        assert entry.class_type == "KSampler"

    def test_trace_entry_unpacking(self, trace_module):
        """TraceEntry should support tuple unpacking."""
        entry = trace_module.TraceEntry(5, "ModelLoader")
        dist, cls = entry
        assert dist == 5
        assert cls == "ModelLoader"


class TestTraceBFS:
    """Tests for Trace.trace BFS traversal."""

    def test_trace_with_debug_logging(self, trace_module, monkeypatch, caplog):
        """Trace should log debug messages when debug is enabled."""
        monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "1")

        prompt = {
            "1": {"class_type": "SaveNode", "inputs": {"img": ["2", 0]}},
            "2": {"class_type": "Sampler", "inputs": {}},
        }

        caplog.set_level(logging.DEBUG)
        result = trace_module.Trace.trace("1", prompt)

        assert "1" in result
        assert "2" in result

    def test_trace_empty_inputs(self, trace_module):
        """Trace should handle nodes with empty inputs."""
        prompt = {
            "root": {"class_type": "SaveNode", "inputs": {}},
        }

        result = trace_module.Trace.trace("root", prompt)

        assert result == {"root": trace_module.TraceEntry(0, "SaveNode")}

    def test_trace_ignores_non_list_inputs(self, trace_module):
        """Non-list input values should be ignored (e.g., strings, ints)."""
        prompt = {
            "save": {
                "class_type": "SaveNode",
                "inputs": {
                    "text": "plain string",
                    "number": 42,
                    "bool": True,
                    "none": None,
                    "dict": {"key": "value"},
                },
            },
        }

        result = trace_module.Trace.trace("save", prompt)

        # Only the start node should be in result
        assert result == {"save": trace_module.TraceEntry(0, "SaveNode")}

    def test_trace_deep_chain(self, trace_module):
        """Trace should handle deep chains correctly."""
        prompt = {
            "n1": {"class_type": "Node1", "inputs": {"in": ["n2", 0]}},
            "n2": {"class_type": "Node2", "inputs": {"in": ["n3", 0]}},
            "n3": {"class_type": "Node3", "inputs": {"in": ["n4", 0]}},
            "n4": {"class_type": "Node4", "inputs": {"in": ["n5", 0]}},
            "n5": {"class_type": "Node5", "inputs": {}},
        }

        result = trace_module.Trace.trace("n1", prompt)

        assert result["n1"].distance == 0
        assert result["n2"].distance == 1
        assert result["n3"].distance == 2
        assert result["n4"].distance == 3
        assert result["n5"].distance == 4

    def test_trace_with_branches(self, trace_module):
        """Trace should handle branching graphs correctly."""
        prompt = {
            "save": {
                "class_type": "SaveNode",
                "inputs": {
                    "a": ["branch_a", 0],
                    "b": ["branch_b", 0],
                },
            },
            "branch_a": {
                "class_type": "BranchA",
                "inputs": {"model": ["shared", 0]},
            },
            "branch_b": {
                "class_type": "BranchB",
                "inputs": {"model": ["shared", 0]},
            },
            "shared": {"class_type": "SharedModel", "inputs": {}},
        }

        result = trace_module.Trace.trace("save", prompt)

        assert result["save"].distance == 0
        assert result["branch_a"].distance == 1
        assert result["branch_b"].distance == 1
        # Shared should be distance 2 (first encountered via one of the branches)
        assert result["shared"].distance == 2

    def test_trace_cycles_handled(self, trace_module):
        """Trace should not enter infinite loop on cycles."""
        # This is a pathological case - cycles shouldn't exist in ComfyUI
        # but the BFS visited set should prevent infinite loops
        prompt = {
            "a": {"class_type": "NodeA", "inputs": {"in": ["b", 0]}},
            "b": {"class_type": "NodeB", "inputs": {"in": ["a", 0]}},  # cycle back
        }

        result = trace_module.Trace.trace("a", prompt)

        # Should complete without hanging
        assert "a" in result
        assert "b" in result


class TestFindSamplerNodeId:
    """Tests for Trace.find_sampler_node_id."""

    def test_find_sampler_returns_minus_one_when_empty(self, trace_module, monkeypatch):
        """Should return -1 when trace tree is empty."""
        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(trace_module, "CAPTURE_FIELD_LIST", {}, raising=False)

        result = trace_module.Trace.find_sampler_node_id(
            {},
            trace_module.SAMPLER_SELECTION_METHOD[0],
            None,
        )

        assert result == -1

    def test_find_sampler_by_node_id_not_in_tree(self, trace_module, monkeypatch):
        """By node ID selection should return -1 if node not in trace tree."""
        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(trace_module, "CAPTURE_FIELD_LIST", {}, raising=False)

        trace_tree = {
            "100": trace_module.TraceEntry(1, "SomeNode"),
        }

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree,
            trace_module.SAMPLER_SELECTION_METHOD[2],
            "999",  # not in tree
        )

        assert result == -1

    def test_find_sampler_by_node_id_converts_to_string(self, trace_module, monkeypatch):
        """By node ID should accept int and convert to string."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {"SamplerNode": {meta.MetaField.SAMPLER_NAME: "name"}},
            raising=False,
        )

        trace_tree = {
            "42": trace_module.TraceEntry(1, "SamplerNode"),
        }

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree,
            trace_module.SAMPLER_SELECTION_METHOD[2],
            42,  # integer node_id
        )

        assert result == "42"

    def test_find_sampler_with_debug_logging(self, trace_module, monkeypatch, caplog):
        """Should log debug messages when debug is enabled."""
        monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "1")
        monkeypatch.setattr(
            trace_module, "SAMPLERS", {"KSampler": {"positive": "p"}}, raising=False
        )
        monkeypatch.setattr(trace_module, "CAPTURE_FIELD_LIST", {}, raising=False)

        trace_tree = {
            "save": trace_module.TraceEntry(0, "SaveNode"),
            "sampler": trace_module.TraceEntry(1, "KSampler"),
        }

        caplog.set_level(logging.DEBUG)
        result = trace_module.Trace.find_sampler_node_id(
            trace_tree,
            trace_module.SAMPLER_SELECTION_METHOD[0],
            None,
        )

        assert result == "sampler"

    def test_find_sampler_no_exact_match_uses_heuristic(self, trace_module, monkeypatch):
        """When no exact SAMPLERS match, should fall back to heuristics."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {
                "CustomSampler": {
                    meta.MetaField.STEPS: "steps",
                    meta.MetaField.CFG: "cfg",
                }
            },
            raising=False,
        )

        trace_tree = {
            "save": trace_module.TraceEntry(0, "SaveNode"),
            "custom": trace_module.TraceEntry(2, "CustomSampler"),
        }

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree,
            trace_module.SAMPLER_SELECTION_METHOD[0],
            None,
        )

        assert result == "custom"

    def test_find_sampler_exact_match_preferred_over_heuristic(
        self, trace_module, monkeypatch
    ):
        """Exact SAMPLERS match should be found before heuristic nodes."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(
            trace_module, "SAMPLERS", {"ExactSampler": {"positive": "p"}}, raising=False
        )
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {
                "HeuristicSampler": {
                    meta.MetaField.STEPS: "steps",
                    meta.MetaField.CFG: "cfg",
                }
            },
            raising=False,
        )

        trace_tree = {
            "save": trace_module.TraceEntry(0, "SaveNode"),
            "exact": trace_module.TraceEntry(5, "ExactSampler"),
            "heuristic": trace_module.TraceEntry(2, "HeuristicSampler"),
        }

        # Farthest first - both should be found, exact match preferred
        result = trace_module.Trace.find_sampler_node_id(
            trace_tree,
            trace_module.SAMPLER_SELECTION_METHOD[0],
            None,
        )

        # Exact match at distance 5 should be returned (it's sorted first for Farthest)
        # but the algorithm does Pass 1 (exact) before Pass 2 (heuristic)
        assert result == "exact"


class TestFilterInputsByTraceTree:
    """Tests for Trace.filter_inputs_by_trace_tree."""

    def test_filter_empty_inputs(self, trace_module):
        """Empty inputs should return empty dict."""
        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree({}, trace_tree)
        assert result == {}

    def test_filter_empty_trace_tree(self, trace_module, meta_module):
        """Empty trace tree should filter out all inputs."""
        inputs = {
            meta_module.MetaField.STEPS: [("node1", 30)],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, {})
        assert result == {}

    def test_filter_handles_string_entry(self, trace_module, meta_module):
        """Should skip non-tuple/list entries like strings."""
        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.SAMPLER_NAME: [
                ("node", "euler"),  # valid
                "just a string",  # invalid - should be skipped
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert meta_module.MetaField.SAMPLER_NAME in result
        assert len(result[meta_module.MetaField.SAMPLER_NAME]) == 1
        assert result[meta_module.MetaField.SAMPLER_NAME][0] == ("node", "euler", 1)

    def test_filter_handles_short_tuple(self, trace_module, meta_module):
        """Should skip entries with less than 2 elements."""
        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.CFG: [
                ("node", 7.5),  # valid
                ("single",),  # too short - skip
                (),  # empty - skip
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert meta_module.MetaField.CFG in result
        assert len(result[meta_module.MetaField.CFG]) == 1

    def test_filter_handles_list_entries(self, trace_module, meta_module):
        """Should accept list entries as well as tuples."""
        trace_tree = {
            "node": trace_module.TraceEntry(2, "Node"),
        }
        inputs = {
            meta_module.MetaField.STEPS: [
                ["node", 30],  # list form
                ["node", 40, "extra"],  # list with extra elements
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert meta_module.MetaField.STEPS in result
        assert len(result[meta_module.MetaField.STEPS]) == 2

    def test_filter_with_debug_logging(
        self, trace_module, meta_module, monkeypatch, caplog
    ):
        """Should log debug messages when debug is enabled."""
        monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "1")

        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.STEPS: [("node", 30)],
        }

        caplog.set_level(logging.DEBUG)
        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert meta_module.MetaField.STEPS in result

    def test_filter_sorts_by_distance(self, trace_module, meta_module):
        """Results should be sorted by distance (ascending)."""
        trace_tree = {
            "near": trace_module.TraceEntry(1, "NearNode"),
            "far": trace_module.TraceEntry(5, "FarNode"),
            "mid": trace_module.TraceEntry(3, "MidNode"),
        }
        inputs = {
            meta_module.MetaField.CFG: [
                ("far", 7.5),
                ("near", 5.0),
                ("mid", 6.0),
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        sorted_entries = result[meta_module.MetaField.CFG]
        # Should be sorted by distance: 1, 3, 5
        assert sorted_entries[0][2] == 1  # near
        assert sorted_entries[1][2] == 3  # mid
        assert sorted_entries[2][2] == 5  # far

    def test_filter_handles_dict_entry(self, trace_module, meta_module):
        """Should skip dict entries."""
        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.SAMPLER_NAME: [
                ("node", "euler"),
                {"invalid": "dict"},  # should be skipped
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert len(result[meta_module.MetaField.SAMPLER_NAME]) == 1

    def test_filter_handles_numeric_entry(self, trace_module, meta_module):
        """Should skip plain numeric entries."""
        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.STEPS: [
                ("node", 30),
                42,  # plain int - should be skipped
                3.14,  # plain float - should be skipped
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert len(result[meta_module.MetaField.STEPS]) == 1

    def test_filter_handles_none_entry(self, trace_module, meta_module):
        """Should skip None entries."""
        trace_tree = {
            "node": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.CFG: [
                ("node", 7.0),
                None,  # should be skipped
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert len(result[meta_module.MetaField.CFG]) == 1

    def test_filter_node_not_in_trace_tree(self, trace_module, meta_module):
        """Should skip entries for nodes not in trace tree."""
        trace_tree = {
            "in_tree": trace_module.TraceEntry(1, "Node"),
        }
        inputs = {
            meta_module.MetaField.STEPS: [
                ("in_tree", 30),  # should be kept
                ("not_in_tree", 40),  # should be filtered out
            ],
        }

        result = trace_module.Trace.filter_inputs_by_trace_tree(inputs, trace_tree)

        assert len(result[meta_module.MetaField.STEPS]) == 1
        assert result[meta_module.MetaField.STEPS][0][0] == "in_tree"


class TestIsSamplerLikeHeuristic:
    """Tests for the is_sampler_like heuristic in find_sampler_node_id."""

    def test_is_sampler_like_explicit_sampler(self, trace_module, monkeypatch):
        """Explicit SAMPLERS entries should always be sampler-like."""
        monkeypatch.setattr(
            trace_module, "SAMPLERS", {"ExplicitSampler": {}}, raising=False
        )
        monkeypatch.setattr(trace_module, "CAPTURE_FIELD_LIST", {}, raising=False)

        trace_tree = {"s": trace_module.TraceEntry(1, "ExplicitSampler")}

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree, trace_module.SAMPLER_SELECTION_METHOD[0], None
        )

        assert result == "s"

    def test_is_sampler_like_by_sampler_name_field(self, trace_module, monkeypatch):
        """Nodes with SAMPLER_NAME capture should be sampler-like."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {"NameNode": {meta.MetaField.SAMPLER_NAME: "name"}},
            raising=False,
        )

        trace_tree = {"n": trace_module.TraceEntry(1, "NameNode")}

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree, trace_module.SAMPLER_SELECTION_METHOD[0], None
        )

        assert result == "n"

    def test_is_sampler_like_by_steps_and_cfg(self, trace_module, monkeypatch):
        """Nodes with both STEPS and CFG capture should be sampler-like."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {"StepCfgNode": {meta.MetaField.STEPS: "s", meta.MetaField.CFG: "c"}},
            raising=False,
        )

        trace_tree = {"sc": trace_module.TraceEntry(1, "StepCfgNode")}

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree, trace_module.SAMPLER_SELECTION_METHOD[0], None
        )

        assert result == "sc"

    def test_is_sampler_like_steps_only_not_enough(self, trace_module, monkeypatch):
        """Nodes with only STEPS (no CFG) should not be sampler-like."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {"StepsOnly": {meta.MetaField.STEPS: "s"}},
            raising=False,
        )

        trace_tree = {
            "save": trace_module.TraceEntry(0, "SaveNode"),
            "steps": trace_module.TraceEntry(1, "StepsOnly"),
        }

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree, trace_module.SAMPLER_SELECTION_METHOD[0], None
        )

        # Should return -1 since StepsOnly doesn't meet heuristics
        assert result == -1

    def test_is_sampler_like_cfg_only_not_enough(self, trace_module, monkeypatch):
        """Nodes with only CFG (no STEPS) should not be sampler-like."""
        meta = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        )

        monkeypatch.setattr(trace_module, "SAMPLERS", {}, raising=False)
        monkeypatch.setattr(
            trace_module,
            "CAPTURE_FIELD_LIST",
            {"CfgOnly": {meta.MetaField.CFG: "c"}},
            raising=False,
        )

        trace_tree = {
            "save": trace_module.TraceEntry(0, "SaveNode"),
            "cfg": trace_module.TraceEntry(1, "CfgOnly"),
        }

        result = trace_module.Trace.find_sampler_node_id(
            trace_tree, trace_module.SAMPLER_SELECTION_METHOD[0], None
        )

        assert result == -1
