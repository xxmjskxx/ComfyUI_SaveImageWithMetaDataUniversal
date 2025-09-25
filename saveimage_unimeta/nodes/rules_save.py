import logging
import os

logger = logging.getLogger(__name__)


class SaveGeneratedUserRules:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
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
        base_py = os.path.dirname(os.path.dirname(__file__))  # .../py
        return os.path.join(base_py, "defs", "ext", "generated_user_rules.py")

    def _validate_python(self, text: str) -> tuple[bool, str | None]:
        import ast

        try:
            ast.parse(text)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}:{e.offset}"
        except (ValueError, TypeError) as e:  # unlikely for source text but explicit
            return False, f"Error: {e}"

    def _find_dict_span(self, text: str, name: str) -> tuple[int | None, int | None]:
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
