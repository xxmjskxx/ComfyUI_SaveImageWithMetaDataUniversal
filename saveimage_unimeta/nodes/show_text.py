"""A UniMeta variant of the `ShowText` node for displaying text in ComfyUI.

This module provides a custom `ShowText` node that is adapted from the
implementation in the `pythongosssss/ComfyUI-Custom-Scripts` repository. It is
namespaced with `|unimeta` to prevent conflicts with other custom nodes that
may provide a node with the same name.
Key differences:
- Uses mapping key "ShowText|unimeta" to avoid conflicts with other packs.
- Display name includes a suffix for clarity.

Logging Policy:
    Uses module-level logger instead of bare prints for warnings so users can
    configure verbosity. (Final mandated completion prints elsewhere remain.)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ShowText:
    """A node to display text in the ComfyUI interface.

    This class implements a node that takes a string input and displays it in
    the ComfyUI frontend. It also persists the displayed text in the workflow's
    metadata, ensuring that the text is restored when the workflow is reloaded.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `ShowText` node.

        This node has a single required input, 'text', which is a string that
        will be displayed in the UI.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
        return {
            "required": {
                # Single STRING input (original behavior). To show forced classes, use the
                # second STRING output now exposed by the Metadata Force Include node.
                "text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "tooltip": (
                            "Text to display (STRING). Connect the Metadata Force Include string output "
                            "to view forced classes."
                        ),
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
    CATEGORY = "SaveImageWithMetaDataUniversal/util"

    def notify(self, text, unique_id=None, extra_pnginfo=None):
        """Display the text and persist it in the workflow.

        This method is the main execution function for the node. It takes the
        input text and returns it, while also updating the workflow's metadata
        to include the text in the node's widget values.

        Args:
            text (str): The text to be displayed.
            unique_id (str, optional): The unique ID of the node. Injected by
                ComfyUI. Defaults to None.
            extra_pnginfo (dict, optional): Extra PNG info, which includes the
                workflow. Injected by ComfyUI. Defaults to None.

        Returns:
            dict: A dictionary containing the UI and result data, with the
                input text as the output.
        """
        # Replicate reference behavior: persist text into workflow for reload persistence.
        if unique_id is not None and extra_pnginfo is not None:
            if not isinstance(extra_pnginfo, list):
                logger.warning("[ShowText|unimeta] extra_pnginfo is not a list (type=%s)", type(extra_pnginfo))
            elif not extra_pnginfo or not isinstance(extra_pnginfo[0], dict) or "workflow" not in extra_pnginfo[0]:
                logger.warning("[ShowText|unimeta] malformed extra_pnginfo[0] or missing 'workflow'")
            else:
                workflow = extra_pnginfo[0]["workflow"]
                node = next((x for x in workflow.get("nodes", []) if str(x.get("id")) == str(unique_id[0])), None)
                if node:
                    node["widgets_values"] = [text]
        return {"ui": {"text": text}, "result": (text,)}


NODE_CLASS_MAPPINGS = {"ShowText|unimeta": ShowText}
NODE_DISPLAY_NAME_MAPPINGS = {"ShowText|unimeta": "Show Text (UniMeta)"}
