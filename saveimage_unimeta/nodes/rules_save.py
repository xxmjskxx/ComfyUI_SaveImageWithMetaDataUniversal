"""A ComfyUI node for persisting generated metadata rules to a file.

This module provides the `SaveGeneratedUserRules` class, a ComfyUI node that
allows users to save the output of the `MetadataRuleScanner` to a Python file `generated_user_rules.py`.
The node supports both overwriting and appending to the existing rules file,
and it includes validation to ensure that the saved text is syntactically
correct Python code.
It validates input via ``ast.parse`` before touching disk and mirrors
the same file layout used by the runtime loader so developers can iterate
entirely from within ComfyUI
"""

import logging
import os

logger = logging.getLogger(__name__)

# Characters that denote the start/end of a string literal in Python source.
_QUOTE_CHARS = ('"', "'")


class SaveGeneratedUserRules:
    """A node to persist scanner output to `defs/ext/generated_user_rules.py`.

    This node provides a user interface for saving generated metadata rules.
    It includes a text area (`rules_text`) for the rules and a boolean toggle (`append`) to control
    whether the new rules should overwrite or be appended to the existing file.
    Appending merges new entries into the `SAMPLERS` and `CAPTURE_FIELD_LIST`
    dictionaries.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `SaveGeneratedUserRules` node.

        This method specifies a multiline string input for the rules text and a
        boolean input to control the append behavior.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
        return {
            "required": {
                "rules_text": ("STRING", {"default": "", "multiline": True}),
                "append": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "If true, append new rules to existing file;\nif false, overwrite existing file.",
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "save_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = "Save the edited rules text back to generated_user_rules.py, with syntax validation."

    def _rules_path(self) -> str:
        """Construct the canonical path to `generated_user_rules.py`.

        This method determines the absolute path to the user-defined rules
        file, which is located in the `defs/ext` directory of the package.

        Returns:
            str: The absolute path to the `generated_user_rules.py` file.
        """
        package_root = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(package_root, "defs", "ext", "generated_user_rules.py")

    def _validate_python(self, text: str) -> tuple[bool, str | None]:
        """Validate that the given text is a valid Python source code.

        This method uses the `ast` module to parse the input text. If parsing
        succeeds, the text is considered valid Python.

        Args:
            text (str): The Python code to validate.

        Returns:
            tuple[bool, str | None]: A tuple containing a boolean indicating
                validity and an error message if the text is invalid.
        """
        import ast

        try:
            ast.parse(text)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}:{e.offset}"
        except (ValueError, TypeError) as e:  # unlikely for source text but explicit
            return False, f"Error: {e}"

    def _find_dict_span(self, text: str, name: str) -> tuple[int, int] | None:
        """Locate the substring that contains a named dictionary literal.

        Args:
            text (str): The Python source to scan.
            name (str): The dictionary variable name (e.g. ``"SAMPLERS"``).

        Returns:
            tuple[int, int] | None: The ``(start, end)`` indices in ``text``
                that wrap the dictionary braces, or ``None`` when the
                dictionary is absent.
        """
        import re

        match = re.search(rf"\b{name}\s*=\s*\{{", text)
        if not match:
            return None

        open_brace_index = match.end() - 1
        depth = 0
        cursor = open_brace_index
        in_string = False
        escaping = False
        active_quote = ""
        while cursor < len(text):
            char = text[cursor]
            if in_string:
                if escaping:
                    escaping = False
                elif char == "\\":
                    escaping = True
                elif char == active_quote:
                    in_string = False
            else:
                if char in _QUOTE_CHARS:
                    in_string = True
                    active_quote = char
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return open_brace_index, cursor
            cursor += 1
        return None

    def _parse_top_level_entries(self, body: str) -> list[tuple[str, str]]:
        """Extract (key, value_text) tuples from the body of a Python dict literal.

        The ``body`` argument should be the content between the braces of a Python
        dictionary literal (excluding the braces). For example, given:
            {
                "foo": 123,
                "bar": [1, 2, 3],
                "baz": {"nested": "dict"}
            }
        The ``body`` string (content between braces, not including them) would be:
        .. code-block:: text
            "foo": 123,
            "bar": [1, 2, 3],
            "baz": {"nested": "dict"}
        The function will return:
        .. code-block:: python
            [
                ("foo", "123"),
                ("bar", "[1, 2, 3]"),
                ("baz", '{"nested": "dict"}')
            ]
        Nested structures are preserved as strings: ``[1, 2]`` or ``{"nested": "dict"}``.

        Args:
            body: The string content between the braces of a Python dict literal.

        Returns:
            List of (key, value_text) pairs as strings.
        """
        parsed_entries: list[tuple[str, str]] = []
        cursor = 0
        body_length = len(body)
        while cursor < body_length:
            while cursor < body_length and body[cursor] in " \t\r\n,":
                cursor += 1
            if cursor >= body_length:
                break
            if body[cursor] not in _QUOTE_CHARS:
                cursor += 1
                continue
            quote = body[cursor]
            cursor += 1
            key_start = cursor
            escaping = False
            while cursor < body_length:
                ch = body[cursor]
                if escaping:
                    escaping = False
                elif ch == "\\":
                    escaping = True
                elif ch == quote:
                    break
                cursor += 1
            key = body[key_start:cursor]
            cursor += 1
            while cursor < body_length and body[cursor] in " \t\r\n":
                cursor += 1
            if cursor >= body_length or body[cursor] != ":":
                continue
            cursor += 1
            while cursor < body_length and body[cursor] in " \t\r\n":
                cursor += 1
            value_start = cursor
            depth = 0
            in_string = False
            escaping = False
            string_quote = ""
            while cursor < body_length:
                ch = body[cursor]
                if in_string:
                    if escaping:
                        escaping = False
                    elif ch == "\\":
                        escaping = True
                    elif ch == string_quote:
                        in_string = False
                else:
                    if ch in _QUOTE_CHARS:
                        in_string = True
                        string_quote = ch
                    elif ch in "{[(":
                        depth += 1
                    elif ch in ")]}":
                        depth -= 1
                    elif ch == "," and depth == 0:
                        break
                cursor += 1
            value_end = cursor
            value_text = body[value_start:value_end].rstrip()
            parsed_entries.append((key, value_text))
            if cursor < body_length and body[cursor] == ",":
                cursor += 1
        return parsed_entries

    def _rebuild_dict(self, name: str, existing_text: str, new_text: str) -> str:
        """Merge entries from a new dictionary into an existing one.

        This method takes the string representations of two Python files,
        finds a dictionary with a specific name in both, and merges the
        entries from the new dictionary into the existing one.

        Args:
            name (str): The name of the dictionary to merge.
            existing_text (str): The content of the existing Python file.
            new_text (str): The content of the new Python file.

        Returns:
            str: The merged content of the Python file.
        """
        existing_dict_span = self._find_dict_span(existing_text, name)
        if existing_dict_span is None:
            new_dict_span = self._find_dict_span(new_text, name)
            if new_dict_span is None:
                return existing_text
            new_start, new_end = new_dict_span
            block = new_text[new_start : new_end + 1]
            return existing_text + f"\n\n{name} = {block}\n"

        existing_start, existing_end = existing_dict_span
        existing_body = existing_text[existing_start + 1 : existing_end]
        new_dict_span = self._find_dict_span(new_text, name)
        if new_dict_span is None:
            return existing_text
        new_start, new_end = new_dict_span
        new_body = new_text[new_start + 1 : new_end]

        existing_entries = self._parse_top_level_entries(existing_body)
        new_entries = self._parse_top_level_entries(new_body)

        merged_entries = {key: value for key, value in existing_entries}
        key_order = [key for key, _ in existing_entries]
        for key, value in new_entries:
            new_value_normalized = value.strip()
            existing_value_normalized = merged_entries.get(key, "").strip()
            if key in merged_entries:
                if new_value_normalized != existing_value_normalized:
                    merged_entries[key] = value
            else:
                merged_entries[key] = value
                key_order.append(key)

        def _indent_continuation_lines(value_text: str) -> str:
            value_text = value_text.rstrip()
            lines = value_text.splitlines()
            if not lines:
                return value_text
            return "\n".join([lines[0]] + ["    " + line for line in lines[1:]])

        rebuilt_body_lines = []
        for key in key_order:
            value = merged_entries[key]
            entry_text = f'    "{key}": {_indent_continuation_lines(value)},'
            rebuilt_body_lines.append(entry_text)
        rebuilt_body = "\n" + "\n".join(rebuilt_body_lines) + "\n"

        return (
            existing_text[:existing_start]
            + "{"
            + rebuilt_body
            + "}"
            + existing_text[existing_end + 1 :]
        )

    def save_rules(self, rules_text: str = "", append: bool = True) -> tuple[str]:
        """Save the provided rules text to a file.

        This method writes the given `rules_text` to the user rules file.
        If `append` is True, it merges the new rules with the existing ones.
        Otherwise, it overwrites the file. It performs validation before
        writing to the file.

        Args:
            rules_text (str, optional): The text of the rules to save. Defaults to "".
            append (bool, optional): Whether to append to the existing file.
                Defaults to True.

        Returns:
            tuple[str]: A tuple containing a status message.
        """
        path = self._rules_path()
        ok, err = self._validate_python(rules_text)
        if not ok:
            return (f"Refused to write: provided text has errors. {err}",)

        if not append:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rules_text)
            except OSError as e:
                logger.warning("[Metadata Rules] Overwrite failed %s: %s", path, e)
                return (f"Failed to overwrite {path}: {e}",)
            return (f"Overwritten {path}",)

        try:
            if not os.path.exists(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(rules_text)
                except OSError as e:
                    logger.warning("[Metadata Rules] Create failed %s: %s", path, e)
                    return (f"Failed to create {path}: {e}",)
                return (f"Created {path}",)

            try:
                with open(path, encoding="utf-8") as f:
                    existing = f.read()
            except OSError as e:
                logger.warning("[Metadata Rules] Read existing failed %s: %s", path, e)
                return (f"Failed to read existing {path}: {e}",)

            merged = existing
            for dict_name in ("SAMPLERS", "CAPTURE_FIELD_LIST"):
                merged = self._rebuild_dict(dict_name, merged, rules_text)

            ok2, err2 = self._validate_python(merged)
            if not ok2:
                return (f"Merge aborted: merged content failed validation: {err2}",)

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(merged)
            except OSError as e:
                logger.warning("[Metadata Rules] Write merged failed %s: %s", path, e)
                return (f"Failed to write merged {path}: {e}",)
            return (f"Merged updates into {path}",)
        except Exception as e:  # pragma: no cover
            logger.exception("[Metadata Rules] Unexpected merge failure for %s", path)
            return (f"Failed to merge into {path}: {e}",)
