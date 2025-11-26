"""Extended tests for nodes/rules_save.py covering edge cases and internal functions.

These tests complement test_rules_save.py by covering:
- _validate_python with various error types
- _find_dict_span edge cases (nested braces, strings with braces, multiline)
- _parse_top_level_entries with complex structures
- _rebuild_dict merge scenarios
- save_rules error handling paths
"""

import importlib
import os
import sys

import pytest


@pytest.fixture
def rules_module(monkeypatch):
    """Import a fresh rules_save module."""
    mod_name = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.rules_save"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    rules = importlib.import_module(mod_name)
    return rules


@pytest.fixture
def rules_node(rules_module):
    """Create a SaveGeneratedUserRules node instance."""
    return rules_module.SaveGeneratedUserRules()


class TestValidatePython:
    """Tests for _validate_python method."""

    def test_validate_python_valid_code(self, rules_node):
        """Valid Python code should pass validation."""
        code = "SAMPLERS = {}\nCAPTURE_FIELD_LIST = {}"
        ok, err = rules_node._validate_python(code)
        assert ok
        assert err is None

    def test_validate_python_syntax_error(self, rules_node):
        """Syntax errors should be detected."""
        code = "SAMPLERS = {"  # unterminated dict
        ok, err = rules_node._validate_python(code)
        assert not ok
        assert "SyntaxError" in err

    def test_validate_python_indentation_error(self, rules_node):
        """Indentation errors should be detected."""
        code = "def foo():\npass"  # missing indentation
        ok, err = rules_node._validate_python(code)
        assert not ok
        assert "SyntaxError" in err or "Error" in err

    def test_validate_python_invalid_syntax_various(self, rules_node):
        """Various invalid syntax should be caught."""
        invalid_codes = [
            "def:",  # incomplete def
            "if True",  # missing colon
            "x = [1, 2,",  # unterminated list
            "'''",  # unterminated string
        ]
        for code in invalid_codes:
            ok, err = rules_node._validate_python(code)
            assert not ok, f"Expected failure for: {code}"

    def test_validate_python_empty_string(self, rules_node):
        """Empty string is valid Python."""
        ok, err = rules_node._validate_python("")
        assert ok
        assert err is None

    def test_validate_python_complex_valid(self, rules_node):
        """Complex but valid Python should pass."""
        code = """
from enum import Enum

class MetaField(Enum):
    STEPS = "Steps"

SAMPLERS = {
    "KSampler": {
        "positive": "positive",
        "negative": "negative",
    },
}

CAPTURE_FIELD_LIST = {
    "CLIPTextEncode": {
        MetaField.STEPS: {"field_name": "steps"},
    },
}
"""
        ok, err = rules_node._validate_python(code)
        assert ok


class TestFindDictSpan:
    """Tests for _find_dict_span method."""

    def test_find_dict_span_simple(self, rules_node):
        """Should find a simple dict."""
        text = "SAMPLERS = {}"
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result == (11, 12)

    def test_find_dict_span_with_content(self, rules_node):
        """Should find dict with content."""
        text = 'SAMPLERS = {"key": "value"}'
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None
        start, end = result
        assert text[start] == "{"
        assert text[end] == "}"

    def test_find_dict_span_nested(self, rules_node):
        """Should handle nested braces correctly."""
        text = 'CAPTURE_FIELD_LIST = {"Node": {"field": "value"}}'
        result = rules_node._find_dict_span(text, "CAPTURE_FIELD_LIST")
        assert result is not None
        start, end = result
        # Should span the entire outer dict
        assert text[start:end + 1] == '{"Node": {"field": "value"}}'

    def test_find_dict_span_not_found(self, rules_node):
        """Should return None when dict not found."""
        text = "OTHER_VAR = {}"
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is None

    def test_find_dict_span_with_whitespace(self, rules_node):
        """Should handle whitespace around equals."""
        text = "SAMPLERS   =   {}"
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None

    def test_find_dict_span_multiline(self, rules_node):
        """Should handle multiline dicts."""
        text = """SAMPLERS = {
    "KSampler": {
        "positive": "p",
    },
}"""
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None
        start, end = result
        assert text[start] == "{"
        assert text[end] == "}"

    def test_find_dict_span_string_with_braces(self, rules_node):
        """Should ignore braces inside strings."""
        text = 'SAMPLERS = {"key": "value { with } braces"}'
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None
        start, end = result
        content = text[start:end + 1]
        assert content == '{"key": "value { with } braces"}'

    def test_find_dict_span_escaped_quotes(self, rules_node):
        """Should handle escaped quotes in strings."""
        text = r'SAMPLERS = {"key": "value with \"quotes\""}'
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None

    def test_find_dict_span_single_quotes(self, rules_node):
        """Should handle single-quoted strings."""
        text = "SAMPLERS = {'key': 'value'}"
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None

    def test_find_dict_span_mixed_quotes(self, rules_node):
        """Should handle mixed quote styles."""
        text = """SAMPLERS = {"key": 'value', 'other': "stuff"}"""
        result = rules_node._find_dict_span(text, "SAMPLERS")
        assert result is not None


class TestParseTopLevelEntries:
    """Tests for _parse_top_level_entries method."""

    def test_parse_simple_entries(self, rules_node):
        """Should parse simple key-value pairs."""
        body = '"foo": 123, "bar": 456'
        entries = rules_node._parse_top_level_entries(body)
        assert entries == [("foo", "123"), ("bar", "456")]

    def test_parse_string_values(self, rules_node):
        """Should parse string values."""
        body = '"key": "value"'
        entries = rules_node._parse_top_level_entries(body)
        assert entries == [("key", '"value"')]

    def test_parse_nested_dict(self, rules_node):
        """Should preserve nested dicts as strings."""
        body = '"node": {"field": "value"}'
        entries = rules_node._parse_top_level_entries(body)
        assert len(entries) == 1
        assert entries[0][0] == "node"
        assert '{"field": "value"}' in entries[0][1]

    def test_parse_nested_list(self, rules_node):
        """Should preserve nested lists as strings."""
        body = '"items": [1, 2, 3]'
        entries = rules_node._parse_top_level_entries(body)
        assert len(entries) == 1
        assert entries[0][0] == "items"
        assert "[1, 2, 3]" in entries[0][1]

    def test_parse_empty_body(self, rules_node):
        """Should handle empty body."""
        entries = rules_node._parse_top_level_entries("")
        assert entries == []

    def test_parse_whitespace_body(self, rules_node):
        """Should handle whitespace-only body."""
        entries = rules_node._parse_top_level_entries("   \n\t  ")
        assert entries == []

    def test_parse_trailing_comma(self, rules_node):
        """Should handle trailing commas."""
        body = '"a": 1, "b": 2,'
        entries = rules_node._parse_top_level_entries(body)
        assert len(entries) == 2

    def test_parse_multiline_value(self, rules_node):
        """Should handle multiline values."""
        body = '''"node": {
    "field": "value",
    "other": "stuff"
}'''
        entries = rules_node._parse_top_level_entries(body)
        assert len(entries) == 1
        assert entries[0][0] == "node"

    def test_parse_commas_in_strings(self, rules_node):
        """Should handle commas inside strings."""
        body = '"key": "a, b, c"'
        entries = rules_node._parse_top_level_entries(body)
        assert len(entries) == 1
        assert entries[0][0] == "key"
        assert '"a, b, c"' in entries[0][1]

    def test_parse_single_quoted_keys(self, rules_node):
        """Should handle single-quoted keys."""
        body = "'key': 'value'"
        entries = rules_node._parse_top_level_entries(body)
        assert len(entries) == 1
        assert entries[0][0] == "key"


class TestRebuildDict:
    """Tests for _rebuild_dict method."""

    def test_rebuild_dict_new_entry(self, rules_node):
        """Should add new entries to existing dict."""
        existing = 'SAMPLERS = {\n    "A": {},\n}'
        new_text = 'SAMPLERS = {\n    "B": {},\n}'

        result = rules_node._rebuild_dict("SAMPLERS", existing, new_text)

        assert '"A"' in result
        assert '"B"' in result

    def test_rebuild_dict_update_entry(self, rules_node):
        """Should update existing entries."""
        existing = 'SAMPLERS = {\n    "A": {"old": "value"},\n}'
        new_text = 'SAMPLERS = {\n    "A": {"new": "value"},\n}'

        result = rules_node._rebuild_dict("SAMPLERS", existing, new_text)

        assert '"new"' in result
        # Old value should be replaced
        assert result.count('"A"') == 1

    def test_rebuild_dict_preserve_order(self, rules_node):
        """Should preserve key order from existing dict."""
        existing = 'SAMPLERS = {\n    "A": {},\n    "B": {},\n}'
        new_text = 'SAMPLERS = {\n    "C": {},\n}'

        result = rules_node._rebuild_dict("SAMPLERS", existing, new_text)

        # A and B should come before C
        idx_a = result.index('"A"')
        idx_b = result.index('"B"')
        idx_c = result.index('"C"')
        assert idx_a < idx_b < idx_c

    def test_rebuild_dict_missing_in_existing(self, rules_node):
        """Should append dict when missing from existing."""
        existing = "# Just a comment"
        new_text = "SAMPLERS = {}"

        result = rules_node._rebuild_dict("SAMPLERS", existing, new_text)

        assert "SAMPLERS = {}" in result

    def test_rebuild_dict_missing_in_new(self, rules_node):
        """Should preserve existing when missing from new."""
        existing = 'SAMPLERS = {"A": {}}'
        new_text = "# No samplers here"

        result = rules_node._rebuild_dict("SAMPLERS", existing, new_text)

        assert result == existing

    def test_rebuild_dict_both_missing(self, rules_node):
        """Should return existing when both are missing the dict."""
        existing = "# Just comments"
        new_text = "# More comments"

        result = rules_node._rebuild_dict("SAMPLERS", existing, new_text)

        assert result == existing


class TestSaveRules:
    """Tests for save_rules method."""

    def test_save_rules_invalid_python_rejected(self, rules_node):
        """Should reject invalid Python code."""
        (status,) = rules_node.save_rules("SAMPLERS = {")
        assert "Refused to write" in status
        assert "errors" in status.lower()

    def test_save_rules_overwrite_creates_file(self, rules_node, tmp_path, monkeypatch):
        """Should create file when overwriting."""
        test_path = tmp_path / "test_rules.py"
        monkeypatch.setattr(rules_node, "_rules_path", lambda: str(test_path))

        content = "SAMPLERS = {}\nCAPTURE_FIELD_LIST = {}"
        (status,) = rules_node.save_rules(content, append=False)

        assert "Overwritten" in status or "Created" in status
        assert test_path.exists()
        assert test_path.read_text() == content

    def test_save_rules_append_creates_when_missing(self, rules_node, tmp_path, monkeypatch):
        """Should create file when append=True but file doesn't exist."""
        test_path = tmp_path / "new_rules.py"
        monkeypatch.setattr(rules_node, "_rules_path", lambda: str(test_path))

        content = "SAMPLERS = {}"
        (status,) = rules_node.save_rules(content, append=True)

        assert "Created" in status
        assert test_path.exists()

    def test_save_rules_append_merges(self, rules_node, tmp_path, monkeypatch):
        """Should merge content when append=True and file exists."""
        test_path = tmp_path / "existing_rules.py"
        existing = 'SAMPLERS = {\n    "A": {},\n}\nCAPTURE_FIELD_LIST = {}'
        test_path.write_text(existing)
        monkeypatch.setattr(rules_node, "_rules_path", lambda: str(test_path))

        new_content = 'SAMPLERS = {\n    "B": {},\n}\nCAPTURE_FIELD_LIST = {}'
        (status,) = rules_node.save_rules(new_content, append=True)

        assert "Merged" in status
        result = test_path.read_text()
        assert '"A"' in result
        assert '"B"' in result

    def test_save_rules_merge_validation_failure(self, rules_node, tmp_path, monkeypatch):
        """Should abort if merged content fails validation."""
        test_path = tmp_path / "rules.py"
        # Create a file that when merged will be invalid
        existing = 'SAMPLERS = {"A": {}}'
        test_path.write_text(existing)
        monkeypatch.setattr(rules_node, "_rules_path", lambda: str(test_path))

        # Mock _rebuild_dict to return invalid Python
        def bad_rebuild(name, existing_text, new_text):
            return "SAMPLERS = {"  # Invalid
        monkeypatch.setattr(rules_node, "_rebuild_dict", bad_rebuild)

        (status,) = rules_node.save_rules('SAMPLERS = {"B": {}}', append=True)

        assert "aborted" in status.lower() or "failed validation" in status.lower()

    def test_save_rules_oserror_on_write(self, rules_node, tmp_path, monkeypatch):
        """Should handle OSError when writing."""
        test_path = tmp_path / "readonly"
        test_path.mkdir()  # Create directory instead of file to cause write error
        monkeypatch.setattr(rules_node, "_rules_path", lambda: str(test_path))  # Point to dir

        (status,) = rules_node.save_rules("SAMPLERS = {}", append=False)

        assert "Failed" in status

    def test_save_rules_empty_content(self, rules_node, tmp_path, monkeypatch):
        """Should handle empty content."""
        test_path = tmp_path / "empty_rules.py"
        monkeypatch.setattr(rules_node, "_rules_path", lambda: str(test_path))

        (status,) = rules_node.save_rules("", append=False)

        # Empty string is valid Python
        assert "Overwritten" in status or "Created" in status


class TestInputTypes:
    """Tests for INPUT_TYPES class method."""

    def test_input_types_has_required_fields(self, rules_module):
        """INPUT_TYPES should define rules_text and append."""
        inputs = rules_module.SaveGeneratedUserRules.INPUT_TYPES()

        assert "required" in inputs
        assert "rules_text" in inputs["required"]
        assert "append" in inputs["required"]

    def test_input_types_rules_text_multiline(self, rules_module):
        """rules_text should be multiline STRING."""
        inputs = rules_module.SaveGeneratedUserRules.INPUT_TYPES()

        rules_text_spec = inputs["required"]["rules_text"]
        assert rules_text_spec[0] == "STRING"
        assert rules_text_spec[1].get("multiline") is True

    def test_input_types_append_default_true(self, rules_module):
        """append should default to True."""
        inputs = rules_module.SaveGeneratedUserRules.INPUT_TYPES()

        append_spec = inputs["required"]["append"]
        assert append_spec[0] == "BOOLEAN"
        assert append_spec[1].get("default") is True


class TestRulesPath:
    """Tests for _rules_path method."""

    def test_rules_path_returns_absolute_path(self, rules_node):
        """_rules_path should return an absolute path."""
        path = rules_node._rules_path()
        assert os.path.isabs(path)

    def test_rules_path_ends_with_expected_filename(self, rules_node):
        """_rules_path should end with generated_user_rules.py."""
        path = rules_node._rules_path()
        assert path.endswith("generated_user_rules.py")

    def test_rules_path_in_defs_ext(self, rules_node):
        """_rules_path should be in defs/ext directory."""
        path = rules_node._rules_path()
        assert os.path.join("defs", "ext") in path


class TestClassAttributes:
    """Tests for class-level attributes."""

    def test_return_types(self, rules_module):
        """RETURN_TYPES should be tuple with STRING."""
        assert rules_module.SaveGeneratedUserRules.RETURN_TYPES == ("STRING",)

    def test_return_names(self, rules_module):
        """RETURN_NAMES should be tuple with status."""
        assert rules_module.SaveGeneratedUserRules.RETURN_NAMES == ("status",)

    def test_function_name(self, rules_module):
        """FUNCTION should be save_rules."""
        assert rules_module.SaveGeneratedUserRules.FUNCTION == "save_rules"

    def test_category(self, rules_module):
        """CATEGORY should be under SaveImageWithMetaDataUniversal."""
        assert "SaveImageWithMetaDataUniversal" in rules_module.SaveGeneratedUserRules.CATEGORY
