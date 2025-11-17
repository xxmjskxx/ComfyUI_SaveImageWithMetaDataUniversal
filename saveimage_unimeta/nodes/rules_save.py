"""A ComfyUI node for persisting generated metadata rules to a file.

This module provides the `SaveGeneratedUserRules` class, a ComfyUI node that
allows users to save the output of the `MetadataRuleScanner` to a Python file.
The node supports both overwriting and appending to the existing rules file,
and it includes validation to ensure that the saved text is syntactically
correct Python code.
"""

import logging
import os

logger = logging.getLogger(__name__)


class SaveGeneratedUserRules:
    """A node to persist scanner output to `defs/ext/generated_user_rules.py`.

    This node provides a user interface for saving generated metadata rules.
    It includes a text area for the rules and a boolean toggle to control
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
        base_py = os.path.dirname(os.path.dirname(__file__))  # .../py
        return os.path.join(base_py, "defs", "ext", "generated_user_rules.py")

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

    def _find_dict_span(self, text: str, name: str) -> tuple[int | None, int | None]:
        """Find the start and end indices of a dictionary in a string.

        This method searches for a dictionary with a given name in the provided
        text and returns the start and end indices of its content, including
        the curly braces.

        Args:
            text (str): The text to search within.
            name (str): The name of the dictionary to find.

        Returns:
            tuple[int | None, int | None]: A tuple containing the start and end
                indices of the dictionary, or (None, None) if not found.
        """
        import re

        m = re.search(rf"\b{name}\s*=\s*\{{", text)
        if not m:
            return None, None
        start = m.end() - 1  # position of '{'
        depth = 0
        i = start
        in_str = False
        esc = False
        quote = ""
        while i < len(text):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    in_str = False
            else:
                if ch in ('"', "'"):
                    in_str = True
                    quote = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return start, i
            i += 1
        return None, None

    def _parse_top_level_entries(self, body: str) -> list[tuple[str, str]]:
        """Parse the key-value pairs from a dictionary's body.

        This method extracts the top-level key-value pairs from the string
        representation of a dictionary's content.

        Args:
            body (str): The string content of the dictionary (without braces).

        Returns:
            list[tuple[str, str]]: A list of (key, value_text) tuples.
        """
        entries = []
        i = 0
        n = len(body)
        while i < n:
            while i < n and body[i] in " \t\r\n,":
                i += 1
            if i >= n:
                break
            if body[i] not in ('"', "'"):
                i += 1
                continue
            quote = body[i]
            i += 1
            key_start = i
            esc = False
            while i < n:
                ch = body[i]
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    break
                i += 1
            key = body[key_start:i]
            i += 1
            while i < n and body[i] in " \t\r\n":
                i += 1
            if i >= n or body[i] != ":":
                continue
            i += 1
            while i < n and body[i] in " \t\r\n":
                i += 1
            val_start = i
            depth = 0
            in_str = False
            esc = False
            str_q = ""
            while i < n:
                ch = body[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == str_q:
                        in_str = False
                else:
                    if ch in ('"', "'"):
                        in_str = True
                        str_q = ch
                    elif ch in "{[(":
                        depth += 1
                    elif ch in ")]}":
                        depth -= 1
                    elif ch == "," and depth == 0:
                        break
                i += 1
            val_end = i
            value_text = body[val_start:val_end].rstrip()
            entries.append((key, value_text))
            if i < n and body[i] == ",":
                i += 1
        return entries

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
        es, ee = self._find_dict_span(existing_text, name)
        if es is None:
            ns, ne = self._find_dict_span(new_text, name)
            if ns is None:
                return existing_text
            block = new_text[ns : ne + 1]
            return existing_text + f"\n\n{name} = {block}\n"

        e_body = existing_text[es + 1 : ee]
        nms = self._find_dict_span(new_text, name)
        if nms == (None, None):
            return existing_text
        ns, ne = nms
        n_body = new_text[ns + 1 : ne]

        e_entries = self._parse_top_level_entries(e_body)
        n_entries = self._parse_top_level_entries(n_body)

        e_map = {k: v for k, v in e_entries}
        order = [k for k, _ in e_entries]
        for k, v in n_entries:
            nv_norm = v.strip()
            ev_norm = e_map.get(k, "").strip()
            if k in e_map:
                if nv_norm != ev_norm:
                    e_map[k] = v
            else:
                e_map[k] = v
                order.append(k)

        def indent_value(val):
            val = val.rstrip()
            lines = val.splitlines()
            if not lines:
                return val
            return "\n".join([lines[0]] + [("    " + ln) for ln in lines[1:]])

        new_body_lines = []
        for k in order:
            v = e_map[k]
            entry_text = f'    "{k}": {indent_value(v)},'
            new_body_lines.append(entry_text)
        new_body = "\n" + "\n".join(new_body_lines) + "\n"

        return existing_text[:es] + "{" + new_body + "}" + existing_text[ee + 1 :]

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
