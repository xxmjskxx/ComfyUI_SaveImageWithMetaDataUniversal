"""Extended tests for show_any module.

This module adds additional edge case tests for:
- saveimage_unimeta/nodes/show_any.py

Tests cover:
- _format_shape helper function
- Edge cases in _safe_to_str
- Error handling in notify()
- ShowAnyToString node edge cases
"""

from __future__ import annotations

from saveimage_unimeta.nodes.show_any import (
    ShowAnyToString,
    _safe_to_str,
    _format_shape,
    AnyType,
    any_type,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# --- _format_shape tests ---


class TestFormatShape:
    """Tests for the _format_shape helper function."""

    def test_none_returns_question_mark(self):
        """Should return '?' for None input."""
        assert _format_shape(None) == "?"

    def test_string_returns_string(self):
        """Should return string as-is."""
        assert _format_shape("(2, 3, 4)") == "(2, 3, 4)"

    def test_bytes_returns_string(self):
        """Should convert bytes to string."""
        assert _format_shape(b"shape") == "b'shape'"

    def test_bytearray_returns_string(self):
        """Should convert bytearray to string."""
        result = _format_shape(bytearray(b"test"))
        assert "test" in result

    def test_tuple_returns_tuple_string(self):
        """Should convert tuple to tuple string."""
        assert _format_shape((2, 3, 4)) == "(2, 3, 4)"

    def test_list_returns_tuple_string(self):
        """Should convert list to tuple string."""
        assert _format_shape([2, 3, 4]) == "(2, 3, 4)"

    def test_integer_returns_string(self):
        """Should convert integer to string."""
        assert _format_shape(512) == "512"

    def test_empty_tuple(self):
        """Should handle empty tuple."""
        assert _format_shape(()) == "()"

    def test_generator_returns_tuple_string(self):
        """Should convert generator to tuple string."""
        gen = (x for x in [1, 2, 3])
        result = _format_shape(gen)
        assert result == "(1, 2, 3)"


# --- _safe_to_str extended tests ---


class TestSafeToStrExtended:
    """Extended tests for the _safe_to_str function."""

    def test_bytearray_decoding(self):
        """Should decode bytearray as utf-8."""
        result = _safe_to_str(bytearray(b"hello"))
        assert result == "hello"

    def test_bytes_with_invalid_utf8(self):
        """Should ignore invalid UTF-8 sequences."""
        invalid_bytes = b"valid\xff\xfeinvalid"
        result = _safe_to_str(invalid_bytes)
        # Should not raise and should contain valid parts
        assert "valid" in result

    def test_shape_attribute_error(self):
        """Should handle errors when accessing shape attribute."""

        class BadShape:
            @property
            def shape(self):
                raise RuntimeError("Shape access error")

            @property
            def dtype(self):
                return "float32"

        result = _safe_to_str(BadShape())
        assert "BadShape" in result

    def test_size_mode_attribute_error(self):
        """Should handle errors when accessing size/mode attributes."""

        class BadImage:
            @property
            def size(self):
                raise RuntimeError("Size access error")

            @property
            def mode(self):
                return "RGB"

        result = _safe_to_str(BadImage())
        assert "BadImage" in result

    def test_repr_fallback(self):
        """Should use repr as fallback when JSON fails."""

        class NonJsonSerializable:
            def __repr__(self):
                return "<NonJsonSerializable instance>"

        result = _safe_to_str(NonJsonSerializable())
        assert "NonJsonSerializable" in result

    def test_str_fallback(self):
        """Should use str as final fallback."""

        class OnlyStrable:
            def __repr__(self):
                raise TypeError("No repr")

            def __str__(self):
                return "Only str works"

        result = _safe_to_str(OnlyStrable())
        assert "Only str works" in result or "OnlyStrable" in result

    def test_list_serialization(self):
        """Should serialize list as JSON."""
        result = _safe_to_str([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_dict_serialization(self):
        """Should serialize dict as JSON."""
        result = _safe_to_str({"a": 1, "b": 2})
        # JSON may have different ordering
        assert '"a":' in result or '"a": ' in result

    def test_nested_structure(self):
        """Should serialize nested structures."""
        result = _safe_to_str({"nested": [1, 2, {"deep": True}]})
        assert "nested" in result
        assert "deep" in result

    def test_custom_max_len(self):
        """Should respect custom max_len parameter."""
        long_text = "x" * 100
        result = _safe_to_str(long_text, max_len=50)
        assert len(result) < 100
        assert "chars)" in result

    def test_exact_max_len_no_truncation(self):
        """Should not truncate when exactly at max_len."""
        text = "x" * 50
        result = _safe_to_str(text, max_len=50)
        assert result == text

    def test_one_under_max_len_no_truncation(self):
        """Should not truncate when one under max_len."""
        text = "x" * 49
        result = _safe_to_str(text, max_len=50)
        assert result == text


# --- ShowAnyToString node extended tests ---


class TestShowAnyToStringExtended:
    """Extended tests for the ShowAnyToString node."""

    def test_input_types_structure(self):
        """Should return properly structured INPUT_TYPES."""
        input_types = ShowAnyToString.INPUT_TYPES()

        assert "required" in input_types
        assert "optional" in input_types
        assert "hidden" in input_types

        assert "value" in input_types["required"]
        assert "display" in input_types["optional"]
        assert "unique_id" in input_types["hidden"]
        assert "extra_pnginfo" in input_types["hidden"]

    def test_class_attributes(self):
        """Should have correct class attributes."""
        assert ShowAnyToString.INPUT_IS_LIST is True
        assert ShowAnyToString.RETURN_TYPES == ("STRING",)
        assert ShowAnyToString.FUNCTION == "notify"
        assert ShowAnyToString.OUTPUT_NODE is True
        assert ShowAnyToString.OUTPUT_IS_LIST == (True,)
        assert ShowAnyToString.CATEGORY == "SaveImageWithMetaDataUniversal/util"

    def test_description_attribute(self):
        """Should have a description."""
        assert hasattr(ShowAnyToString, "DESCRIPTION")
        assert len(ShowAnyToString.DESCRIPTION) > 0

    def test_notify_with_none_value(self):
        """Should handle None value gracefully."""
        node = ShowAnyToString()
        result = node.notify(value=None)

        assert "ui" in result
        assert "result" in result
        assert result["ui"]["text"] == []
        assert result["result"] == ([],)

    def test_notify_with_empty_list(self):
        """Should handle empty list."""
        node = ShowAnyToString()
        result = node.notify(value=[])

        assert result["ui"]["text"] == []
        assert result["result"] == ([],)

    def test_notify_with_complex_objects(self):
        """Should handle complex objects in list."""

        class DummyTensor:
            def __init__(self):
                self.shape = (1, 3, 512, 512)
                self.dtype = "float32"

        node = ShowAnyToString()
        result = node.notify(value=[DummyTensor(), {"key": "value"}])

        assert len(result["ui"]["text"]) == 2
        # First should be tensor summary
        assert "DummyTensor" in result["ui"]["text"][0]
        # Second should be JSON
        assert "key" in result["ui"]["text"][1]

    def test_notify_malformed_extra_pnginfo_not_list(self):
        """Should handle extra_pnginfo that is not a list."""
        node = ShowAnyToString()
        result = node.notify(
            value=["test"],
            unique_id=[1],
            extra_pnginfo={"workflow": {}},  # Should be a list
        )
        # Should not crash
        assert result["ui"]["text"] == ["test"]

    def test_notify_malformed_extra_pnginfo_empty_list(self):
        """Should handle empty extra_pnginfo list."""
        node = ShowAnyToString()
        result = node.notify(
            value=["test"],
            unique_id=[1],
            extra_pnginfo=[],  # Empty list
        )
        # Should not crash
        assert result["ui"]["text"] == ["test"]

    def test_notify_malformed_extra_pnginfo_no_workflow(self):
        """Should handle extra_pnginfo without workflow key."""
        node = ShowAnyToString()
        result = node.notify(
            value=["test"],
            unique_id=[1],
            extra_pnginfo=[{"other_key": "value"}],  # Missing workflow
        )
        # Should not crash
        assert result["ui"]["text"] == ["test"]

    def test_notify_node_not_found_in_workflow(self):
        """Should handle case where node is not found in workflow."""
        node = ShowAnyToString()
        workflow = {"nodes": [{"id": 999}]}  # Different ID
        result = node.notify(
            value=["test"],
            unique_id=[1],
            extra_pnginfo=[{"workflow": workflow}],
        )
        # Should not crash and should not modify workflow
        assert result["ui"]["text"] == ["test"]
        assert "widgets_values" not in workflow["nodes"][0]

    def test_notify_with_single_item(self):
        """Should handle single item list."""
        node = ShowAnyToString()
        workflow = {"nodes": [{"id": 42}]}
        node.notify(
            value=["single"],
            unique_id=[42],
            extra_pnginfo=[{"workflow": workflow}],
        )
        assert workflow["nodes"][0]["widgets_values"] == ["single"]


# --- AnyType tests ---


class TestAnyType:
    """Tests for the AnyType wildcard class."""

    def test_equals_any_string(self):
        """Should equal any string."""
        wt = AnyType("*")
        assert wt == "anything"
        assert wt == "STRING"
        assert wt == ""
        assert wt == "123"

    def test_not_equals_returns_false(self):
        """Should never be not-equal to anything."""
        wt = AnyType("*")
        assert not (wt != "something")
        assert not (wt != "")
        assert not (wt != 123)  # Even non-strings

    def test_is_string_subclass(self):
        """Should be a string subclass."""
        assert isinstance(any_type, str)
        assert any_type == "*"  # String value is "*"


# --- Module exports tests ---


class TestModuleExports:
    """Tests for module-level exports."""

    def test_node_class_mappings(self):
        """Should export NODE_CLASS_MAPPINGS."""
        assert "ShowAny|unimeta" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["ShowAny|unimeta"] is ShowAnyToString

    def test_node_display_name_mappings(self):
        """Should export NODE_DISPLAY_NAME_MAPPINGS."""
        assert "ShowAny|unimeta" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["ShowAny|unimeta"] == "Show Any (Any to String)"
