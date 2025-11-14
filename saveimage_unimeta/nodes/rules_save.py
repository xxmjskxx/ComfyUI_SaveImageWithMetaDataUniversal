"""ComfyUI node that persists generated metadata rules back to disk.

The saver writes the textual output from :class:`MetadataRuleScanner` to the
`generated_user_rules.py` extension file, optionally merging with existing
entries. It validates input via ``ast.parse`` before touching disk and mirrors
the same file layout used by the runtime loader so developers can iterate
entirely from within ComfyUI.
"""

import logging
import os
from ..capture import resolve_runtime_version

logger = logging.getLogger(__name__)


class SaveGeneratedUserRules:
    """Persist scanner output into ``defs/ext/generated_user_rules.py``.

    The node exposes a simple text area (``rules_text``) plus an ``append``
    toggle that controls whether to overwrite the file or merge new entries
    into the existing SAMPLERS / CAPTURE_FIELD_LIST dictionaries.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802,N804
        """ComfyUI schema describing the editable text field and append flag."""
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
        """Return the canonical path to ``generated_user_rules.py``."""
        base_py = os.path.dirname(os.path.dirname(__file__))  # .../py
        return os.path.join(base_py, "defs", "ext", "generated_user_rules.py")

    def _validate_python(self, text: str) -> tuple[bool, str | None]:
        """Parse user text to ensure it is valid Python source."""
        import ast

        try:
            ast.parse(text)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}:{e.offset}"
        except (ValueError, TypeError) as e:  # unlikely for source text but explicit
            return False, f"Error: {e}"

    def _find_dict_span(self, text: str, name: str) -> tuple[int | None, int | None]:
        """Locate the ``{...}`` span for the named top-level dictionary."""
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
        """Split a dictionary body into ``(key, value_text)`` tuples."""
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
        """Merge entries from ``new_text`` into dictionary ``name``."""
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

    def _inject_version_header(self, rules_text: str) -> str:
        """Prepend version constant to rules text for version tracking."""
        version = resolve_runtime_version()
        version_header = (
            f'"""Auto-generated metadata capture rules."""\n\n'
            f'# Generated with metadata generator version: {version}\n'
            f'GENERATED_RULES_VERSION = "{version}"\n\n'
        )

        # If text already has a version header, replace it
        import re
        version_pattern = re.compile(
            r'^(""".*?"""\s*\n+)?# Generated with metadata generator version:.*?\nGENERATED_RULES_VERSION\s*=\s*["\'].*?["\']\s*\n+',
            re.MULTILINE | re.DOTALL
        )
        if version_pattern.search(rules_text):
            rules_text = version_pattern.sub("", rules_text, count=1)

        # Remove any existing docstring at the start to avoid duplication
        docstring_pattern = re.compile(r'^""".*?"""\s*\n+', re.DOTALL)
        rules_text = docstring_pattern.sub("", rules_text, count=1)

        return version_header + rules_text

    def save_rules(self, rules_text: str = "", append: bool = True) -> tuple[str]:
        """Write or merge rules text, returning a short status message."""
        path = self._rules_path()
        ok, err = self._validate_python(rules_text)
        if not ok:
            return (f"Refused to write: provided text has errors. {err}",)

        # Inject version header before writing
        rules_text = self._inject_version_header(rules_text)

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

            # Update version header in merged content
            merged = self._inject_version_header(merged)

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
