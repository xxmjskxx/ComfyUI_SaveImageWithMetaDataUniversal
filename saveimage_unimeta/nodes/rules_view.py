"""A read-only viewer for the saved user metadata rules (JSON).

This module provides a ComfyUI node that shows the user rules saved by
`Save Custom Metadata Rules` (`user_captures.json` and `user_samplers.json`).
This is useful for debugging and understanding how the metadata is being captured.
"""

import json
import logging
import os

from .. import defs as defs_mod

logger = logging.getLogger(__name__)


class ShowGeneratedUserRules:
    """A node to expose the saved user rules as a STRING output.

    The output uses the scanner's `{"nodes": ..., "samplers": ...}` shape, so it can be
    edited and fed back into `Save Custom Metadata Rules`.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `ShowGeneratedUserRules` node.

        This node does not have any inputs, as it only reads files from disk.

        Returns:
            dict: An empty dictionary for the `required` inputs.
        """
        return {"required": {}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("user_rules_json",)
    FUNCTION = "show_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = "Display the saved user rules JSON for review or editing in Save Custom Metadata Rules."

    def _rules_path(self) -> str:
        """Return the directory holding `user_captures.json` and `user_samplers.json`."""
        return defs_mod.resolve_user_rules_dir()

    def show_rules(self) -> tuple[str]:
        """Read the saved user rules and return them as one JSON document.

        Returns:
            tuple[str]: The rules JSON, an empty string when no rules are saved,
                or an error message.
        """
        rules_dir = self._rules_path()
        combined = {}
        for key, name in (("nodes", "user_captures.json"), ("samplers", "user_samplers.json")):
            path = os.path.join(rules_dir, name)
            if not os.path.exists(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    combined[key] = json.load(f)
            except (OSError, ValueError) as e:
                logger.warning("[Metadata Rules] Error reading %s: %s", path, e)
                return (f"Error reading {name}: {e}",)
        if not combined:
            return ("",)
        return (json.dumps(combined, indent=4),)
