"""Show Any (Any to String) node (UniMeta variant).

Accepts any input type, converts to a human-readable string, displays it in the UI,
and outputs it as a STRING for wiring into nodes that only accept strings
(e.g. Create Extra MetaData).

Notes:
- Mirrors the behavior of the local Show Text (UniMeta) node for UI persistence.
- Input is treated as a list (Comfy batching). Each element is converted to a string.
- Conversion is conservative; large/complex objects are summarized to avoid huge UI blobs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AnyType(str):
        """Wildcard type that compares equal to any type name.

        This mirrors a common ComfyUI pattern for accepting any input type by
        using a custom string subclass that always returns True for equality
        comparisons. We also override __ne__ for safety.
        A special class that is always equal in not equal comparisons. Credit to
        pythongosssss / rgthree.
        """

        def __eq__(self, __value: object) -> bool:  # noqa: D401
                return True

        def __ne__(self, __value: object) -> bool:  # noqa: D401
                return False

any_type = AnyType("*")


def _safe_to_str(obj: Any, max_len: int = 2000) -> str:
    """Best-effort stringify with size safeguards.

    - str for primitives
    - decode bytes as utf-8 (ignore errors)
    - summarize arrays/tensors/images if shape/size available
    - fall back to json.dumps(default=str) then repr/str
    Truncates long results with an ellipsis marker.
    """
    try:
        # Fast paths
        if obj is None:
            s = ""
        elif isinstance(obj, str):
            s = obj
        elif isinstance(obj, int | float | bool):
            s = str(obj)
        elif isinstance(obj, bytes | bytearray):
            s = bytes(obj).decode("utf-8", "ignore")
        else:
            # Heuristics for common heavy types
            # numpy/torch-like
            if hasattr(obj, "shape"):
                try:
                    shape = getattr(obj, "shape", None)
                    dtype = getattr(obj, "dtype", None)
                    s = f"<{obj.__class__.__name__} shape={tuple(shape)} dtype={dtype}>"
                except Exception:  # noqa: BLE001
                    s = f"<{obj.__class__.__name__}>"
            # PIL-like
            elif hasattr(obj, "size") and hasattr(obj, "mode"):
                try:
                    s = f"<{obj.__class__.__name__} size={getattr(obj, 'size', '?')} mode={getattr(obj, 'mode', '?')}>"
                except Exception:  # noqa: BLE001
                    s = f"<{obj.__class__.__name__}>"
            else:
                # Try JSON (shallow) then fallback
                try:
                    s = json.dumps(obj, ensure_ascii=False, default=str)
                except Exception:  # noqa: BLE001
                    try:
                        s = repr(obj)
                    except Exception:  # noqa: BLE001
                        s = str(obj)
        if len(s) > max_len:
            return s[:max_len] + f" …(+{len(s) - max_len} chars)"
        return s
    except Exception as e:  # noqa: BLE001
        logger.warning("[ShowAny|unimeta] stringify error for type=%s: %s", type(obj), e)
        return f"<{type(obj).__name__}>"


class ShowAnyToString:
    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {
            "required": {
                "value": (
                    any_type,
                    {
                        "forceInput": True,
                        "tooltip": (
                            "Any input to display as text. Values are converted to strings; "
                            "large/complex objects are summarized.\nPrimarily intended to convert ints, floats, and "
                            "bools and wire them into Create Extra MetaData. Truncates very long strings to 2000 chars."
                        ),
                    },
                ),
            },
            "optional": {
                # A visible text widget so the node can display the converted value on the canvas.
                # We populate this programmatically in notify() using widgets_values.
                "display": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Auto-filled with the converted string value for on-canvas viewing.",
                    },
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "notify"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)
    DESCRIPTION = (
        "Accepts any input type, converts to a human-readable string, displays it in the UI, "
        "and outputs it as a STRING for wiring into nodes that only accept strings (or for debugging). Primarily "
        "intended to convert ints, floats, and bools to strings and wire them into the Create Extra MetaData node."
    )
    CATEGORY = "SaveImageWithMetaDataUniversal/util"

    def notify(self, value, display=None, unique_id=None, extra_pnginfo=None):  # pylint: disable=unused-argument
        # Convert batched inputs to strings.
        try:
            strings = [_safe_to_str(v) for v in (value or [])]
        except Exception as e:  # noqa: BLE001
            logger.warning("[ShowAny|unimeta] conversion error: %s", e)
            strings = ["<error: see log>"]

        # Persist displayed value into workflow (mirrors ShowText) and populate the visible text widget.
        if unique_id is not None and extra_pnginfo is not None:
            if not isinstance(extra_pnginfo, list):
                logger.warning("[ShowAny|unimeta] extra_pnginfo is not a list (type=%s)", type(extra_pnginfo))
            elif not extra_pnginfo or not isinstance(extra_pnginfo[0], dict) or "workflow" not in extra_pnginfo[0]:
                logger.warning("[ShowAny|unimeta] malformed extra_pnginfo[0] or missing 'workflow'")
            else:
                workflow = extra_pnginfo[0]["workflow"]
                node = next((x for x in workflow.get("nodes", []) if str(x.get("id")) == str(unique_id[0])), None)
                if node:
                    # Join to a single display block for the multiline widget.
                    display_text = "\n".join(strings) if isinstance(strings, list) else str(strings)
                    node["widgets_values"] = [display_text]

        return {"ui": {"text": strings}, "result": (strings,)}


NODE_CLASS_MAPPINGS = {"ShowAny|unimeta": ShowAnyToString}
NODE_DISPLAY_NAME_MAPPINGS = {"ShowAny|unimeta": "Show Any (Any to String)"}
