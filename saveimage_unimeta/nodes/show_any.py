"""Show Any (Any to String) node (UniMeta variant) to display any input type as a string.

Accepts any input type, converts to a human-readable string, displays it in the UI,
and outputs it as a STRING for wiring into nodes that only accept strings
(e.g. Create Extra MetaData).

Notes:
- Mirrors the behavior of the local Show Text (UniMeta) node for UI persistence.
- Input is treated as a list (Comfy batching). Each element is converted to a string.
- Conversion is conservative; large/complex objects are summarized to avoid huge UI blobs.

This module provides the `ShowAnyToString` node, which can accept any data
type as input, convert it to a human-readable string, display it in the
ComfyUI interface, and output the string for use in other nodes. This is
particularly useful for debugging and for converting non-string data types
into a format that can be used with nodes that only accept string inputs, such
as the `CreateExtraMetaData` node.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from typing import Any

logger = logging.getLogger(__name__)


class AnyType(str):
    """A wildcard type that is equal to any other type.

    This class is a string subclass that overrides the equality and inequality
    operators to always return `True` for equality and `False` for inequality.
    This is a common pattern in ComfyUI for creating nodes that can accept any
    input type.

    Wildcard type that compares equal to any type name.

    This mirrors a common ComfyUI pattern for accepting any input type by
    using a custom string subclass that always returns True for equality
    comparisons. We also override __ne__ for safety.
    A special class that is always equal in not equal comparisons. Credit to
    pythongosssss / rgthree.
    """

    def __eq__(self, __value: object) -> bool:
        """Always returns True, indicating equality with any other object."""
        return True

    def __ne__(self, __value: object) -> bool:
        """Always returns False, indicating no inequality with any other object."""
        return False


any_type = AnyType("*")


def _format_shape(shape: Any) -> str:
    """Return a safe string for tensor-like shape attributes."""

    if shape is None:
        return "?"
    if isinstance(shape, str | bytes | bytearray):
        return str(shape)
    if isinstance(shape, Iterable):
        try:
            return str(tuple(shape))
        except TypeError:
            return str(shape)
    return str(shape)


def _safe_to_str(obj: Any, max_len: int = 2000) -> str:
    """Safely convert any object to a string with a maximum length.

     This function attempts to convert an object to a string in a robust and
     safe manner. It handles primitive types, bytes, and provides summaries for
     common large objects like tensors and images. If the resulting string is
     longer than `max_len`, it is truncated.

     - str for primitives
     - decode bytes as utf-8 (ignore errors)
     - summarize arrays/tensors/images if shape/size available
     - fall back to json.dumps(default=str) then repr/str
     Truncates long results with an ellipsis marker.

     Args:
         obj (Any): The object to convert to a string.
         max_len (int, optional): The maximum length of the output string.
             Defaults to 2000.

     Returns:
         str: The string representation of the object.
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
                    s = f"<{obj.__class__.__name__} shape={_format_shape(shape)} dtype={dtype}>"
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
    """A node to convert any input to a string and display it."""

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `ShowAnyToString` node.

        This node has a single required input, 'value', which can be of any
        type. It also has an optional 'display' input, which is a text widget
        used to show the converted string in the UI.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
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

    def notify(
        self,
        value: Sequence[Any] | None,
        display: str | None = None,
        unique_id: Sequence[str] | None = None,
        extra_pnginfo: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Convert the input to a string and return it.

        This method takes the input `value`, converts each item in the list to a
        string using the `_safe_to_str` function, and returns the list of
        strings. It also updates the node's display widget with the converted
        text.

        Args:
            value (list): The list of input values to be converted.
            display (str, optional): The current value of the display widget.
                Defaults to None.
            unique_id (str, optional): The unique ID of the node. Defaults to None.
            extra_pnginfo (dict, optional): Extra PNG info. Defaults to None.

        Returns:
            dict: A dictionary containing the UI and result data, with the
                converted strings as the output.
        """
        # Convert batched inputs to strings.
        iterable = list(value) if value is not None else []
        try:
            strings = [_safe_to_str(v) for v in iterable]
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
