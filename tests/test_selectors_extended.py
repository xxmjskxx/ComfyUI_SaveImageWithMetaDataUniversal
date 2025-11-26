"""Additional tests for defs/selectors.py to cover edge cases and uncovered paths."""

from saveimage_unimeta.defs.selectors import (
    _aligned_strengths_for_prefix,
    _build_normalized_map,
    _coerce_first,
    _extract_index,
    _gather_indices,
    _normalize_key,
    _resolve_counter,
    _toggle_truthy,
    _value_for_index,
    collect_lora_stack,
    select_by_prefix,
    select_stack_by_prefix,
    SELECTORS,
)


def _mk_input(d):
    """Helper to wrap a dict into the input_data structure used by selectors."""
    return [d]


# --- _coerce_first tests ---


class TestCoerceFirst:
    """Tests for the _coerce_first helper function."""

    def test_returns_first_from_list(self):
        """Should return first element of a list."""
        assert _coerce_first([1, 2, 3]) == 1

    def test_returns_first_from_tuple(self):
        """Should return first element of a tuple."""
        assert _coerce_first((10, 20)) == 10

    def test_returns_none_for_empty_list(self):
        """Should return None for empty list."""
        assert _coerce_first([]) is None

    def test_returns_none_for_empty_tuple(self):
        """Should return None for empty tuple."""
        assert _coerce_first(()) is None

    def test_returns_value_for_scalar(self):
        """Should return the value unchanged for non-sequence."""
        assert _coerce_first("hello") == "hello"
        assert _coerce_first(42) == 42


# --- _normalize_key tests ---


class TestNormalizeKey:
    """Tests for the _normalize_key helper function."""

    def test_lowercases_key(self):
        """Should lowercase the key."""
        assert _normalize_key("LoRa_Name") == "lora_name"

    def test_replaces_spaces_with_underscores(self):
        """Should replace spaces with underscores."""
        assert _normalize_key("lora name") == "lora_name"

    def test_combined_normalization(self):
        """Should handle both space replacement and lowercasing."""
        assert _normalize_key("LoRa Model Name") == "lora_model_name"


# --- _build_normalized_map tests ---


class TestBuildNormalizedMap:
    """Tests for the _build_normalized_map helper function."""

    def test_empty_input_data(self):
        """Should return empty dict for empty input."""
        assert _build_normalized_map([]) == {}
        assert _build_normalized_map(None) == {}

    def test_non_list_input(self):
        """Should return empty dict for non-list input."""
        assert _build_normalized_map("not a list") == {}

    def test_non_dict_first_element(self):
        """Should return empty dict if first element is not a dict."""
        assert _build_normalized_map(["not a dict"]) == {}

    def test_skips_non_string_keys(self):
        """Should skip non-string keys."""
        result = _build_normalized_map([{123: "value", "valid_key": "other"}])
        assert "123" not in result
        assert "valid_key" in result

    def test_normalizes_and_stores_original(self):
        """Should store both normalized and original key."""
        result = _build_normalized_map([{"LoRa Name": ["value"]}])
        assert "lora_name" in result
        assert result["lora_name"] == ("LoRa Name", ["value"])


# --- _extract_index tests ---


class TestExtractIndex:
    """Tests for the _extract_index helper function."""

    def test_extracts_simple_index(self):
        """Should extract index from simple key."""
        assert _extract_index("lora_1", "lora_") == 1
        assert _extract_index("lora_10", "lora_") == 10

    def test_extracts_index_with_extra_underscore(self):
        """Should handle extra underscore before index."""
        assert _extract_index("lora__5", "lora_") == 5

    def test_no_match_without_prefix(self):
        """Should return None if key doesn't start with prefix."""
        assert _extract_index("other_1", "lora_") is None

    def test_no_index_digits(self):
        """Should return None if no digits follow prefix."""
        assert _extract_index("lora_name", "lora_") is None

    def test_empty_suffix(self):
        """Should return None for empty suffix after prefix."""
        assert _extract_index("lora_", "lora_") is None

    def test_index_with_trailing_text(self):
        """Should extract digits before non-digit characters."""
        assert _extract_index("lora_5_name", "lora_") == 5


# --- _gather_indices tests ---


class TestGatherIndices:
    """Tests for the _gather_indices helper function."""

    def test_gathers_multiple_indices(self):
        """Should gather all unique indices from normalized map."""
        normalized = {
            "lora_1": ("lora_1", ["a"]),
            "lora_2": ("lora_2", ["b"]),
            "other": ("other", ["c"]),
        }
        indices = _gather_indices(normalized, ("lora_",))
        assert indices == {1, 2}

    def test_multiple_prefixes(self):
        """Should check all provided prefixes."""
        normalized = {
            "lora_1": ("lora_1", ["a"]),
            "switch_2": ("switch_2", ["on"]),
        }
        indices = _gather_indices(normalized, ("lora_", "switch_"))
        assert indices == {1, 2}


# --- _value_for_index tests ---


class TestValueForIndex:
    """Tests for the _value_for_index helper function."""

    def test_finds_value_with_index(self):
        """Should find value matching index."""
        normalized = {
            "lora_name_1": ("lora_name_1", ["first"]),
            "lora_name_2": ("lora_name_2", ["second"]),
        }
        assert _value_for_index(normalized, ("lora_name",), 1) == "first"
        assert _value_for_index(normalized, ("lora_name",), 2) == "second"

    def test_finds_zero_padded_index(self):
        """Should find value with zero-padded index."""
        normalized = {
            "lora_01": ("lora_01", ["padded"]),
        }
        assert _value_for_index(normalized, ("lora",), 1) == "padded"

    def test_returns_none_when_not_found(self):
        """Should return None when index not found."""
        normalized = {"lora_1": ("lora_1", ["value"])}
        assert _value_for_index(normalized, ("lora",), 99) is None


# --- _toggle_truthy tests ---


class TestToggleTruthy:
    """Tests for the _toggle_truthy helper function."""

    def test_boolean_true(self):
        """Should return True for boolean True."""
        assert _toggle_truthy(True) is True

    def test_boolean_false(self):
        """Should return False for boolean False."""
        assert _toggle_truthy(False) is False

    def test_numeric_nonzero(self):
        """Should return True for nonzero numbers."""
        assert _toggle_truthy(1) is True
        assert _toggle_truthy(0.5) is True
        assert _toggle_truthy(-1) is True

    def test_numeric_zero(self):
        """Should return False for zero (within tolerance)."""
        assert _toggle_truthy(0) is False
        assert _toggle_truthy(0.0) is False

    def test_string_off_variants(self):
        """Should return False for 'off' variants."""
        assert _toggle_truthy("off") is False
        assert _toggle_truthy("OFF") is False
        assert _toggle_truthy("false") is False
        assert _toggle_truthy("0") is False
        assert _toggle_truthy("disable") is False
        assert _toggle_truthy("disabled") is False
        assert _toggle_truthy("no") is False

    def test_string_on_variants(self):
        """Should return True for 'on' variants."""
        assert _toggle_truthy("on") is True
        assert _toggle_truthy("ON") is True
        assert _toggle_truthy("true") is True
        assert _toggle_truthy("1") is True
        assert _toggle_truthy("enable") is True
        assert _toggle_truthy("enabled") is True
        assert _toggle_truthy("yes") is True

    def test_empty_string(self):
        """Should return False for empty string."""
        assert _toggle_truthy("") is False
        assert _toggle_truthy("   ") is False

    def test_unknown_string_defaults_true(self):
        """Should default to True for unknown strings."""
        assert _toggle_truthy("maybe") is True
        assert _toggle_truthy("active") is True


# --- _resolve_counter tests ---


class TestResolveCounter:
    """Tests for the _resolve_counter helper function."""

    def test_finds_lora_count(self):
        """Should find counter from lora_count key."""
        normalized = {"lora_count": ("lora_count", [3])}
        assert _resolve_counter(normalized) == 3

    def test_finds_num_loras(self):
        """Should find counter from num_loras key."""
        normalized = {"num_loras": ("num_loras", [5])}
        assert _resolve_counter(normalized) == 5

    def test_handles_float_counter(self):
        """Should convert float counter to int."""
        normalized = {"lora_count": ("lora_count", [2.7])}
        assert _resolve_counter(normalized) == 2

    def test_returns_none_when_not_found(self):
        """Should return None when no counter key found."""
        assert _resolve_counter({}) is None

    def test_handles_invalid_counter_value(self):
        """Should return None for invalid counter values."""
        normalized = {"lora_count": ("lora_count", ["invalid"])}
        assert _resolve_counter(normalized) is None


# --- collect_lora_stack edge cases ---


class TestCollectLoraStackEdgeCases:
    """Additional edge case tests for collect_lora_stack."""

    def test_empty_input(self):
        """Should return empty list for empty input."""
        assert collect_lora_stack([]) == []
        assert collect_lora_stack([{}]) == []

    def test_skips_zero_or_negative_indices(self):
        """Should skip entries with zero or negative indices."""
        data = _mk_input({
            "lora_count": [2],
            "lora_name_0": ["zero.safetensors"],
            "lora_name_1": ["one.safetensors"],
        })
        stack = collect_lora_stack(data)
        assert len(stack) == 1
        assert stack[0][0] == "one.safetensors"

    def test_skips_empty_names(self):
        """Should skip entries with empty names."""
        data = _mk_input({
            "lora_count": [3],
            "lora_name_1": [""],
            "lora_name_2": ["  "],
            "lora_name_3": ["valid.safetensors"],
        })
        stack = collect_lora_stack(data)
        # Both empty and whitespace-only names are skipped, only valid remains
        assert len(stack) == 1
        assert stack[0][0] == "valid.safetensors"

    def test_fallback_to_toggle_indices(self):
        """Should fall back to toggle prefixes when no lora names found."""
        data = _mk_input({
            "switch_1": ["On"],
            "switch_2": ["Off"],
        })
        # This tests the fallback path, even if it doesn't produce results
        stack = collect_lora_stack(data)
        assert stack == []


# --- select_stack_by_prefix edge cases ---


class TestSelectStackByPrefixEdgeCases:
    """Additional edge case tests for select_stack_by_prefix."""

    def test_include_indices_mode(self):
        """Should return (index, value) tuples when include_indices=True."""
        data = _mk_input({
            "lora_1": ["first"],
            "lora_2": ["second"],
        })
        result = select_stack_by_prefix(data, "lora_", include_indices=True)
        assert result == [(1, "first"), (2, "second")]

    def test_counter_key_not_in_results(self):
        """Counter key should not be included in results."""
        data = _mk_input({
            "lora_1": ["first"],
            "lora_count": [5],
        })
        result = select_stack_by_prefix(data, "lora_", counter_key="lora_count")
        assert "5" not in result
        assert result == ["first"]

    def test_none_first_element_in_input(self):
        """Should return empty for input with None first element."""
        assert select_stack_by_prefix([None], "prefix_") == []

    def test_sorts_null_indices_after_valid(self):
        """Items without numeric indices should sort after indexed items."""
        data = _mk_input({
            "lora_name": ["no_index"],  # No numeric suffix
            "lora_1": ["first"],
        })
        result = select_stack_by_prefix(data, "lora_")
        # First should come before no_index due to having valid index
        assert result[0] == "first"


# --- select_by_prefix tests ---


class TestSelectByPrefix:
    """Tests for select_by_prefix function."""

    def test_empty_prefix(self):
        """Should return empty list for empty prefix."""
        data = _mk_input({"key": ["value"]})
        assert select_by_prefix(data, "") == []

    def test_filters_none_values(self):
        """Should filter out 'None' values."""
        data = _mk_input({
            "x_1": ["valid"],
            "x_2": ["None"],
        })
        result = select_by_prefix(data, "x_")
        assert result == ["valid"]


# --- _aligned_strengths_for_prefix tests ---


class TestAlignedStrengthsForPrefix:
    """Tests for the _aligned_strengths_for_prefix helper function."""

    def test_aligns_strengths_to_names(self):
        """Should align strengths to name indices."""
        data = _mk_input({
            "lora_name_1": ["first"],
            "lora_name_2": ["second"],
            "model_str_1": [0.5],
            "model_str_2": [0.8],
        })
        result = _aligned_strengths_for_prefix(data, "model_str")
        assert result == [0.5, 0.8]

    def test_fallback_when_no_names(self):
        """Should fall back to raw strength selection when no names."""
        data = _mk_input({
            "model_str_1": [0.5],
            "model_str_2": [0.8],
        })
        result = _aligned_strengths_for_prefix(data, "model_str")
        assert result == [0.5, 0.8]

    def test_handles_mismatched_indices(self):
        """Should handle when strength indices don't match name indices."""
        data = _mk_input({
            "lora_name_1": ["first"],
            "lora_name_3": ["third"],  # Gap in indices
            "model_str_1": [0.5],
            "model_str_2": [0.6],  # Doesn't match name indices
            "model_str_3": [0.8],
        })
        result = _aligned_strengths_for_prefix(data, "model_str")
        # Should align 0.5 to index 1, 0.8 to index 3
        assert 0.5 in result
        assert 0.8 in result


# --- SELECTORS dict tests ---


class TestSelectorsDict:
    """Tests for the SELECTORS dictionary."""

    def test_contains_expected_selectors(self):
        """SELECTORS dict should contain expected selector functions."""
        assert "select_by_prefix" in SELECTORS
        assert "collect_lora_stack" in SELECTORS
        assert "select_lora_names" in SELECTORS
        assert "select_lora_model_strengths" in SELECTORS
        assert "select_lora_clip_strengths" in SELECTORS

    def test_selectors_are_callable(self):
        """All selectors should be callable."""
        for name, selector in SELECTORS.items():
            assert callable(selector), f"{name} is not callable"
