"""Local ShowText node (UniMeta variant).

Adapted from pythongosssss / ComfyUI-Custom-Scripts ShowText implementation (MIT License).
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
    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {
            "required": {
                # Force input: must be connected; mirrors reference behavior
                "text": ("STRING", {"forceInput": True}),
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

    def notify(self, text, unique_id=None, extra_pnginfo=None):  # pylint: disable=unused-argument
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
