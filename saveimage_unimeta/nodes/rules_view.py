"""Read-only viewer for ``generated_user_rules.py`` contents."""

import logging
import os

logger = logging.getLogger(__name__)


class ShowGeneratedUserRules:
    """Expose the generated Python rules file as a STRING output node."""

    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
        """Provide a no-input interface (button node) for the ComfyUI UI."""
        return {"required": {}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("generated_user_rules.py",)
    FUNCTION = "show_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = "Display the contents of generated_user_rules.py for review or editing."

    def _rules_path(self) -> str:
        """Return the absolute path to ``defs/ext/generated_user_rules.py``."""
        base_py = os.path.dirname(os.path.dirname(__file__))  # .../py
        return os.path.join(base_py, "defs", "ext", "generated_user_rules.py")

    def show_rules(self) -> tuple[str]:
        """Read the generated rules file and return its contents as text."""
        path = self._rules_path()
        if not os.path.exists(path):
            return ("",)
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            logger.warning("[Metadata Rules] I/O error reading %s: %s", path, e)
            return (f"Error reading generated_user_rules.py: {e}",)
        return (content,)
