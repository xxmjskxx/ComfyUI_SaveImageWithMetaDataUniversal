"""Tests for color module.

This module tests:
- saveimage_unimeta/utils/color.py

Tests cover:
- cstr class for colored console output
- Color code constants
- Dynamic attribute access
- add_code method
"""

from __future__ import annotations

import pytest

from saveimage_unimeta.utils.color import cstr


class TestCstrBasics:
    """Tests for basic cstr functionality."""

    def test_creates_string(self):
        """Should create a string."""
        result = cstr("Hello")
        assert isinstance(result, str)
        assert "Hello" in str(result)

    def test_is_string_subclass(self):
        """Should be a str subclass."""
        result = cstr("test")
        assert isinstance(result, str)

    def test_preserves_text(self):
        """Should preserve the original text."""
        result = cstr("my text")
        assert "my text" in result


class TestCstrColors:
    """Tests for color application."""

    def test_red_color(self):
        """Should apply red color code."""
        result = cstr("text").red
        assert cstr.color.RED in result
        assert cstr.color.END in result
        assert "text" in result

    def test_green_color(self):
        """Should apply green color code."""
        result = cstr("text").green
        assert cstr.color.GREEN in result
        assert cstr.color.END in result

    def test_blue_color(self):
        """Should apply blue color code."""
        result = cstr("text").blue
        assert cstr.color.BLUE in result

    def test_yellow_color(self):
        """Should apply yellow color code."""
        result = cstr("text").yellow
        assert cstr.color.YELLOW in result

    def test_bold_style(self):
        """Should apply bold style."""
        result = cstr("text").bold
        assert cstr.color.BOLD in result

    def test_italic_style(self):
        """Should apply italic style."""
        result = cstr("text").italic
        assert cstr.color.ITALIC in result

    def test_underline_style(self):
        """Should apply underline style."""
        result = cstr("text").underline
        assert cstr.color.UNDERLINE in result


class TestCstrChaining:
    """Tests for chaining color attributes."""

    def test_chain_color_and_style(self):
        """Should allow chaining color and style."""
        result = cstr("text").red.bold
        assert cstr.color.RED in result
        assert cstr.color.BOLD in result
        assert "text" in result

    def test_chain_multiple_styles(self):
        """Should allow multiple style chains."""
        result = cstr("text").bold.italic
        assert cstr.color.BOLD in result
        assert cstr.color.ITALIC in result

    def test_returns_cstr_instance(self):
        """Chaining should return cstr instance."""
        result = cstr("text").red
        assert isinstance(result, cstr)


class TestColorConstants:
    """Tests for color constant values."""

    def test_end_code(self):
        """END code should be ANSI reset."""
        assert cstr.color.END == "\33[0m"

    def test_bold_code(self):
        """BOLD code should be ANSI bold."""
        assert cstr.color.BOLD == "\33[1m"

    def test_black_code(self):
        """BLACK code should be ANSI black foreground."""
        assert cstr.color.BLACK == "\33[30m"

    def test_red_code(self):
        """RED code should be ANSI red foreground."""
        assert cstr.color.RED == "\33[31m"

    def test_white_code(self):
        """WHITE code should be ANSI white foreground."""
        assert cstr.color.WHITE == "\33[37m"

    def test_orange_code(self):
        """ORANGE code should use extended ANSI."""
        assert "38;5;208" in cstr.color.ORANGE


class TestAddCode:
    """Tests for the add_code static method."""

    def test_adds_new_code(self):
        """Should add a new color code."""
        cstr.color.add_code("test_custom", "\33[99m")
        assert hasattr(cstr.color, "TEST_CUSTOM")
        assert cstr.color.TEST_CUSTOM == "\33[99m"

    def test_raises_on_duplicate(self):
        """Should raise ValueError for duplicate code name."""
        # RED already exists
        with pytest.raises(ValueError, match="already contains"):
            cstr.color.add_code("red", "\33[99m")

    def test_uppercase_name(self):
        """Should store code with uppercase name."""
        cstr.color.add_code("test_lower", "\33[98m")
        assert hasattr(cstr.color, "TEST_LOWER")


class TestCstrGetattr:
    """Tests for __getattr__ behavior."""

    def test_raises_for_invalid_attribute(self):
        """Should raise AttributeError for invalid attribute."""
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = cstr("text").nonexistent_color

    def test_case_insensitive_colors(self):
        """Should handle case-insensitive color names."""
        result1 = cstr("text").RED
        result2 = cstr("text").red
        # Both should contain the red code
        assert cstr.color.RED in result1
        assert cstr.color.RED in result2


class TestCstrPrint:
    """Tests for the print method."""

    def test_print_method_exists(self):
        """Should have a print method."""
        c = cstr("test")
        assert hasattr(c, "print")
        assert callable(c.print)

    def test_print_method_calls_print(self, capsys):
        """Should print the colored string."""
        cstr("hello").print()
        captured = capsys.readouterr()
        assert "hello" in captured.out


class TestMessageTemplates:
    """Tests for pre-defined message templates."""

    def test_msg_template_exists(self):
        """Should have MSG template."""
        assert hasattr(cstr.color, "MSG")

    def test_msg_o_template_exists(self):
        """Should have MSG_O template."""
        assert hasattr(cstr.color, "MSG_O")

    def test_warning_template_exists(self):
        """Should have WARNING template."""
        assert hasattr(cstr.color, "WARNING")

    def test_warn_template_exists(self):
        """Should have WARN template."""
        assert hasattr(cstr.color, "WARN")

    def test_error_template_exists(self):
        """Should have ERROR template."""
        assert hasattr(cstr.color, "ERROR")

    def test_msg_contains_name(self):
        """MSG template should contain SaveImageWithMetaData."""
        assert "SaveImageWithMetaData" in cstr.color.MSG

    def test_warning_contains_warning_tag(self):
        """WARNING template should contain [Warning]."""
        assert "[Warning]" in cstr.color.WARNING

    def test_error_contains_error_tag(self):
        """ERROR template should contain [Error]."""
        assert "[Error]" in cstr.color.ERROR
