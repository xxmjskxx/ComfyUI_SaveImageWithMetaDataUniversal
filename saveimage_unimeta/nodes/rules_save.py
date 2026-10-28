"""Deprecated node that used to write `generated_user_rules.py`.

User rules are now stored and loaded only as JSON data (see `SaveCustomMetadataRules`),
so this node writes nothing. It stays registered so saved workflows that contain it still load.
"""


class SaveGeneratedUserRules:
    """Deprecated: no longer writes Python. Use `Save Custom Metadata Rules` with the scanner JSON."""

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {
            "required": {
                "rules_text": ("STRING", {"default": "", "multiline": True}),
                "append": ("BOOLEAN", {"default": True, "tooltip": "Deprecated, no effect."}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "save_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = "Deprecated, writes nothing. Save scanner JSON with Save Custom Metadata Rules instead."

    def save_rules(self, rules_text: str = "", append: bool = True) -> tuple[str]:
        return ("Deprecated: rules are no longer saved as Python. Use 'Save Custom Metadata Rules' with the scanner JSON.",)
