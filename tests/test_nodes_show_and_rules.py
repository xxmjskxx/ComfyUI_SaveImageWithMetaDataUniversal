"""Tests for nodes/show_text.py and nodes/rules_view.py node modules."""

import logging
import os

import pytest


# --- ShowText tests ---


class TestShowText:
    """Tests for the ShowText node class."""

    @pytest.fixture
    def show_text_node(self):
        """Create a ShowText instance for testing."""
        from saveimage_unimeta.nodes.show_text import ShowText

        return ShowText()

    def test_input_types_structure(self, show_text_node):
        """INPUT_TYPES should define expected input structure."""
        input_types = show_text_node.INPUT_TYPES()

        assert "required" in input_types
        assert "text" in input_types["required"]
        assert "hidden" in input_types
        assert "unique_id" in input_types["hidden"]
        assert "extra_pnginfo" in input_types["hidden"]

    def test_class_attributes(self, show_text_node):
        """ShowText should have expected class attributes."""
        assert show_text_node.RETURN_TYPES == ("STRING",)
        assert show_text_node.FUNCTION == "notify"
        assert show_text_node.OUTPUT_NODE is True
        assert show_text_node.INPUT_IS_LIST is True
        assert show_text_node.OUTPUT_IS_LIST == (True,)

    def test_notify_returns_text(self, show_text_node):
        """notify should return input text in result and UI."""
        result = show_text_node.notify(text="hello world")

        assert "ui" in result
        assert "text" in result["ui"]
        assert result["ui"]["text"] == "hello world"
        assert "result" in result
        assert result["result"] == ("hello world",)

    def test_notify_handles_list_text(self, show_text_node):
        """notify should handle text as a list (INPUT_IS_LIST)."""
        result = show_text_node.notify(text=["first", "second"])

        assert result["ui"]["text"] == ["first", "second"]
        assert result["result"] == (["first", "second"],)

    def test_notify_persists_to_workflow(self, show_text_node):
        """notify should persist text to workflow node widgets_values."""
        workflow = {
            "nodes": [
                {"id": "123", "widgets_values": []},
                {"id": "456", "widgets_values": []},
            ]
        }
        extra_pnginfo = [{"workflow": workflow}]

        show_text_node.notify(
            text="persisted text", unique_id=["123"], extra_pnginfo=extra_pnginfo
        )

        node = next(n for n in workflow["nodes"] if n["id"] == "123")
        assert node["widgets_values"] == ["persisted text"]

    def test_notify_without_extra_pnginfo(self, show_text_node):
        """notify should handle missing extra_pnginfo gracefully."""
        # Should not raise
        result = show_text_node.notify(text="test", unique_id=["1"])

        assert result["ui"]["text"] == "test"

    def test_notify_logs_warning_for_non_list_extra_pnginfo(
        self, show_text_node, caplog
    ):
        """notify should log warning if extra_pnginfo is not a list."""
        with caplog.at_level(logging.WARNING):
            show_text_node.notify(
                text="test", unique_id=["1"], extra_pnginfo="not a list"
            )

        assert "extra_pnginfo is not a list" in caplog.text

    def test_notify_logs_warning_for_missing_workflow(self, show_text_node, caplog):
        """notify should log warning if workflow key is missing."""
        with caplog.at_level(logging.WARNING):
            show_text_node.notify(
                text="test", unique_id=["1"], extra_pnginfo=[{"no_workflow": True}]
            )

        assert "missing 'workflow'" in caplog.text

    def test_notify_handles_empty_extra_pnginfo(self, show_text_node, caplog):
        """notify should handle empty extra_pnginfo list."""
        with caplog.at_level(logging.WARNING):
            show_text_node.notify(text="test", unique_id=["1"], extra_pnginfo=[])

        assert "malformed extra_pnginfo[0]" in caplog.text


# --- ShowGeneratedUserRules tests ---


class TestShowGeneratedUserRules:
    """Tests for the ShowGeneratedUserRules node class."""

    @pytest.fixture
    def rules_view_node(self):
        """Create a ShowGeneratedUserRules instance for testing."""
        from saveimage_unimeta.nodes.rules_view import ShowGeneratedUserRules

        return ShowGeneratedUserRules()

    def test_input_types_empty_required(self, rules_view_node):
        """INPUT_TYPES should have empty required inputs."""
        input_types = rules_view_node.INPUT_TYPES()

        assert "required" in input_types
        assert input_types["required"] == {}

    def test_class_attributes(self, rules_view_node):
        """ShowGeneratedUserRules should have expected class attributes."""
        assert rules_view_node.RETURN_TYPES == ("STRING",)
        assert rules_view_node.FUNCTION == "show_rules"
        assert "rules" in rules_view_node.CATEGORY

    def test_rules_path_returns_valid_path(self, rules_view_node):
        """_rules_path should return a path to generated_user_rules.py."""
        path = rules_view_node._rules_path()

        assert path.endswith("generated_user_rules.py")
        assert "defs" in path
        assert "ext" in path

    def test_show_rules_returns_empty_for_nonexistent_file(
        self, rules_view_node, monkeypatch
    ):
        """show_rules should return empty string if file doesn't exist."""
        monkeypatch.setattr(
            rules_view_node,
            "_rules_path",
            lambda: "/nonexistent/path/generated_user_rules.py",
        )

        result = rules_view_node.show_rules()

        assert result == ("",)

    def test_show_rules_reads_file_contents(self, rules_view_node, tmp_path):
        """show_rules should read and return file contents."""
        test_content = "# Generated rules\nFOO = 'bar'"
        test_file = tmp_path / "generated_user_rules.py"
        test_file.write_text(test_content, encoding="utf-8")

        # Monkey-patch the path method
        rules_view_node._rules_path = lambda: str(test_file)

        result = rules_view_node.show_rules()

        assert result == (test_content,)

    def test_show_rules_handles_read_error(
        self, rules_view_node, tmp_path, monkeypatch, caplog
    ):
        """show_rules should handle and log I/O errors."""
        test_file = tmp_path / "generated_user_rules.py"
        test_file.write_text("content")
        rules_view_node._rules_path = lambda: str(test_file)

        # Make the file unreadable by patching open to raise
        def mock_open(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr("builtins.open", mock_open)

        with caplog.at_level(logging.WARNING):
            result = rules_view_node.show_rules()

        assert "Error reading generated_user_rules.py" in result[0]


# --- Node registration tests ---


def test_show_text_node_registration():
    """ShowText should be properly registered in NODE_CLASS_MAPPINGS."""
    from saveimage_unimeta.nodes.show_text import (
        NODE_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS,
        ShowText,
    )

    assert "ShowText|unimeta" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["ShowText|unimeta"] is ShowText
    assert "ShowText|unimeta" in NODE_DISPLAY_NAME_MAPPINGS
    assert "UniMeta" in NODE_DISPLAY_NAME_MAPPINGS["ShowText|unimeta"]
