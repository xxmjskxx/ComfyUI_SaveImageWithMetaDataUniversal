"""Extended tests for efficiency_nodes module helper functions.

This module tests helper functions in:
- saveimage_unimeta/defs/ext/efficiency_nodes.py

Tests cover:
- _stack_from_outputs
- _normalize_connection_target
- _collect_stack_from_connection
- _first_input_value
- _normalize_lora_name
- _build_loader_lora_entries
"""

from __future__ import annotations

from saveimage_unimeta.defs.ext.efficiency_nodes import (
    _stack_from_outputs,
    _normalize_connection_target,
    _collect_stack_from_connection,
    _first_input_value,
    _normalize_lora_name,
    _build_loader_lora_entries,
)


# --- _stack_from_outputs tests ---


class TestStackFromOutputs:
    """Tests for the _stack_from_outputs helper function."""

    def test_returns_none_for_non_dict_outputs(self):
        """Should return None if outputs is not a dict."""
        assert _stack_from_outputs("node1", "not a dict") is None
        assert _stack_from_outputs("node1", [1, 2, 3]) is None
        assert _stack_from_outputs("node1", None) is None

    def test_returns_none_for_missing_node_id(self):
        """Should return None if node_id not in outputs."""
        outputs = {"other_node": {"lora_stack": []}}
        assert _stack_from_outputs("node1", outputs) is None

    def test_parses_lora_stack_key(self):
        """Should parse lora_stack from dict output."""
        outputs = {
            "node1": {
                "lora_stack": [
                    ("lora1.safetensors", 0.8, 0.6),
                    ("lora2.safetensors", 0.5, 0.5),
                ]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 2
        assert result[0] == ("lora1.safetensors", 0.8, 0.6)

    def test_parses_LORA_STACK_key(self):
        """Should parse LORA_STACK (uppercase) key."""
        outputs = {
            "node1": {
                "LORA_STACK": [("lora.safetensors", 1.0, 1.0)]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1

    def test_parses_numeric_key(self):
        """Should parse from key 0 or '0'."""
        outputs = {
            "node1": {
                0: [("lora.safetensors", 0.9, 0.9)]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1

    def test_handles_tuple_wrapped_list(self):
        """Should unwrap tuple containing single list."""
        outputs = {
            "node1": {
                "lora_stack": ([("lora.safetensors", 0.7, 0.7)],)
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1

    def test_handles_list_output(self):
        """Should handle list outputs directly."""
        outputs = {
            "node1": [[("lora.safetensors", 0.6, 0.6)]]
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1

    def test_returns_empty_list_for_empty_stack(self):
        """Should return empty list for empty stack."""
        outputs = {"node1": {"lora_stack": []}}
        result = _stack_from_outputs("node1", outputs)
        assert result == []

    def test_skips_none_names(self):
        """Should skip entries with None names."""
        outputs = {
            "node1": {
                "lora_stack": [
                    (None, 0.8, 0.6),
                    ("valid.safetensors", 0.5, 0.5),
                ]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1
        assert result[0][0] == "valid.safetensors"

    def test_skips_empty_names(self):
        """Should skip entries with empty string names."""
        outputs = {
            "node1": {
                "lora_stack": [
                    ("", 0.8, 0.6),
                    ("  ", 0.7, 0.7),
                    ("valid.safetensors", 0.5, 0.5),
                ]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1

    def test_skips_none_string_names(self):
        """Should skip entries where name is literally 'none'."""
        outputs = {
            "node1": {
                "lora_stack": [
                    ("none", 0.8, 0.6),
                    ("None", 0.7, 0.7),
                    ("valid.safetensors", 0.5, 0.5),
                ]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1

    def test_uses_model_strength_as_clip_if_missing(self):
        """Should use model_strength as clip_strength if clip is missing."""
        outputs = {
            "node1": {
                "lora_stack": [
                    ("lora.safetensors", 0.8),  # Only 2 elements
                ]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1
        assert result[0] == ("lora.safetensors", 0.8, 0.8)

    def test_handles_single_element_entry(self):
        """Should handle entry with only name."""
        outputs = {
            "node1": {
                "lora_stack": [
                    ("lora.safetensors",),  # Only 1 element
                ]
            }
        }
        result = _stack_from_outputs("node1", outputs)
        assert len(result) == 1
        assert result[0] == ("lora.safetensors", None, None)


# --- _normalize_connection_target tests ---


class TestNormalizeConnectionTarget:
    """Tests for the _normalize_connection_target helper function."""

    def test_extracts_from_list(self):
        """Should extract first element from list."""
        assert _normalize_connection_target(["node1"]) == "node1"

    def test_extracts_from_tuple(self):
        """Should extract first element from tuple."""
        assert _normalize_connection_target(("node1",)) == "node1"

    def test_returns_none_for_empty_list(self):
        """Should return None for empty list."""
        assert _normalize_connection_target([]) is None

    def test_returns_none_for_none_value(self):
        """Should return None for None input."""
        assert _normalize_connection_target(None) is None

    def test_returns_none_for_none_string(self):
        """Should return None for 'none' string."""
        assert _normalize_connection_target("none") is None
        assert _normalize_connection_target("None") is None
        assert _normalize_connection_target("NONE") is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        assert _normalize_connection_target("") is None
        assert _normalize_connection_target("   ") is None

    def test_strips_whitespace(self):
        """Should strip whitespace from value."""
        assert _normalize_connection_target("  node1  ") == "node1"

    def test_handles_numeric_id(self):
        """Should convert numeric ID to string."""
        assert _normalize_connection_target(123) == "123"


# --- _first_input_value tests ---


class TestFirstInputValue:
    """Tests for the _first_input_value helper function."""

    def test_extracts_direct_value(self):
        """Should extract direct value from input_data."""
        input_data = [{"field": "value"}]
        assert _first_input_value(input_data, "field") == "value"

    def test_extracts_first_from_list(self):
        """Should extract first element if value is a list."""
        input_data = [{"field": ["first", "second"]}]
        assert _first_input_value(input_data, "field") == "first"

    def test_extracts_first_from_tuple(self):
        """Should extract first element if value is a tuple."""
        input_data = [{"field": ("first", "second")}]
        assert _first_input_value(input_data, "field") == "first"

    def test_returns_none_for_empty_list_value(self):
        """Should return None if value is empty list."""
        input_data = [{"field": []}]
        assert _first_input_value(input_data, "field") is None

    def test_returns_none_for_missing_field(self):
        """Should return None if field doesn't exist."""
        input_data = [{"other": "value"}]
        assert _first_input_value(input_data, "field") is None

    def test_returns_none_for_empty_input_data(self):
        """Should return None for empty input_data."""
        assert _first_input_value([], "field") is None
        assert _first_input_value(None, "field") is None

    def test_returns_none_for_empty_field_name(self):
        """Should return None for empty field name."""
        input_data = [{"field": "value"}]
        assert _first_input_value(input_data, "") is None
        assert _first_input_value(input_data, None) is None


# --- _normalize_lora_name tests ---


class TestNormalizeLoraName:
    """Tests for the _normalize_lora_name helper function."""

    def test_returns_none_for_none(self):
        """Should return None for None input."""
        assert _normalize_lora_name(None) is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        assert _normalize_lora_name("") is None
        assert _normalize_lora_name("   ") is None

    def test_returns_none_for_none_string(self):
        """Should return None for 'none' string."""
        assert _normalize_lora_name("none") is None
        assert _normalize_lora_name("None") is None

    def test_extracts_from_list(self):
        """Should extract first element from list."""
        assert _normalize_lora_name(["lora.safetensors"]) == "lora.safetensors"

    def test_extracts_from_tuple(self):
        """Should extract first element from tuple."""
        assert _normalize_lora_name(("lora.safetensors",)) == "lora.safetensors"

    def test_returns_none_for_empty_list(self):
        """Should return None for empty list."""
        assert _normalize_lora_name([]) is None

    def test_strips_whitespace(self):
        """Should strip whitespace from name."""
        assert _normalize_lora_name("  lora.safetensors  ") == "lora.safetensors"


# --- _collect_stack_from_connection tests ---


class TestCollectStackFromConnection:
    """Tests for the _collect_stack_from_connection helper function."""

    def test_returns_empty_for_non_dict_inputs(self):
        """Should return empty list for non-dict node_inputs."""
        assert _collect_stack_from_connection("not a dict", {}, {}) == []
        assert _collect_stack_from_connection(None, {}, {}) == []

    def test_returns_empty_for_missing_key(self):
        """Should return empty list if key not in node_inputs."""
        node_inputs = {"other_key": "value"}
        assert _collect_stack_from_connection(node_inputs, {}, {}) == []

    def test_resolves_from_outputs(self):
        """Should resolve stack from upstream node outputs."""
        node_inputs = {"lora_stack": ["upstream_node"]}
        outputs = {
            "upstream_node": {
                "lora_stack": [("lora.safetensors", 0.8, 0.8)]
            }
        }
        result = _collect_stack_from_connection(node_inputs, {}, outputs)
        assert len(result) == 1

    def test_falls_back_to_prompt(self):
        """Should fall back to prompt if not in outputs."""
        node_inputs = {"lora_stack": ["upstream_node"]}
        prompt = {
            "upstream_node": {
                "inputs": {
                    "lora_name_1": ["lora.safetensors"],
                    "lora_count": [1],
                }
            }
        }
        result = _collect_stack_from_connection(node_inputs, prompt, {})
        # Should attempt to collect from pseudo input
        assert isinstance(result, list)

    def test_custom_key(self):
        """Should use custom key parameter."""
        node_inputs = {"custom_stack": ["upstream"]}
        outputs = {
            "upstream": {
                "lora_stack": [("lora.safetensors", 0.5, 0.5)]
            }
        }
        result = _collect_stack_from_connection(node_inputs, {}, outputs, key="custom_stack")
        assert len(result) == 1


# --- _build_loader_lora_entries tests ---


class TestBuildLoaderLoraEntries:
    """Tests for the _build_loader_lora_entries helper function."""

    def test_builds_inline_entry(self):
        """Should build entry from inline spec."""
        input_data = [{
            "lora_name": ["my_lora.safetensors"],
            "lora_strength": [0.8],
        }]
        inline_spec = {
            "name": "lora_name",
            "strength_model": "lora_strength",
            "strength_clip": "lora_strength",
        }
        result = _build_loader_lora_entries(
            node_id="1",
            prompt={},
            outputs={},
            input_data=input_data,
            inline_spec=inline_spec,
        )
        assert len(result) == 1
        assert result[0][0] == "my_lora.safetensors"
        assert result[0][1] == 0.8

    def test_uses_model_strength_as_clip_fallback(self):
        """Should use model strength as clip strength fallback."""
        input_data = [{
            "lora_name": ["lora.safetensors"],
            "strength_model": [0.7],
            # No strength_clip
        }]
        inline_spec = {
            "name": "lora_name",
            "strength_model": "strength_model",
            "strength_clip": "strength_clip",
        }
        result = _build_loader_lora_entries(
            node_id="1",
            prompt={},
            outputs={},
            input_data=input_data,
            inline_spec=inline_spec,
        )
        assert len(result) == 1
        assert result[0][2] == 0.7  # clip should equal model

    def test_skips_inline_if_no_name(self):
        """Should skip inline entry if name is invalid."""
        input_data = [{
            "lora_name": [""],  # Empty name
            "lora_strength": [0.8],
        }]
        inline_spec = {
            "name": "lora_name",
            "strength_model": "lora_strength",
        }
        result = _build_loader_lora_entries(
            node_id="1",
            prompt={},
            outputs={},
            input_data=input_data,
            inline_spec=inline_spec,
        )
        assert len(result) == 0

    def test_appends_stack_from_connection(self):
        """Should append entries from connected stack."""
        input_data = [{}]
        prompt = {
            "1": {"inputs": {"lora_stack": ["upstream"]}},
        }
        outputs = {
            "upstream": {
                "lora_stack": [("connected_lora.safetensors", 0.5, 0.5)]
            }
        }
        result = _build_loader_lora_entries(
            node_id="1",
            prompt=prompt,
            outputs=outputs,
            input_data=input_data,
        )
        assert len(result) == 1
        assert result[0][0] == "connected_lora.safetensors"

    def test_combines_inline_and_connected(self):
        """Should combine inline and connected entries."""
        input_data = [{
            "lora_name": ["inline.safetensors"],
            "strength": [0.8],
        }]
        inline_spec = {
            "name": "lora_name",
            "strength_model": "strength",
        }
        prompt = {
            "1": {"inputs": {"lora_stack": ["upstream"]}},
        }
        outputs = {
            "upstream": {
                "lora_stack": [("connected.safetensors", 0.5, 0.5)]
            }
        }
        result = _build_loader_lora_entries(
            node_id="1",
            prompt=prompt,
            outputs=outputs,
            input_data=input_data,
            inline_spec=inline_spec,
        )
        assert len(result) == 2
