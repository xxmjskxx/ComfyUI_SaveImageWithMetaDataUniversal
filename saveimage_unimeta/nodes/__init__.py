from .node import (  # noqa: N999 - package path inherited from external naming constraints
    CreateExtraMetaDataUniversal,
    SaveCustomMetadataRules,
    SaveGeneratedUserRules,
    SaveImageWithMetaDataUniversal,
    ShowGeneratedUserRules,
    MetadataRuleScanner,
)
from .show_text import ShowText  # local unimeta variant (separate file for clarity)
from ..defs import set_forced_include

class MetadataForceInclude:
    """Configure globally forced node class names for metadata capture.

    Separated from the scanning node so the scanner (`MetadataRuleScanner` implemented
    in `node.py`) can expose its own inputs: exclude_keywords, include_existing,
    mode, force_include_metafields, etc.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {
            "required": {
                "force_include_node_class": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": (
                            "Comma/newline separated node class names to always "
                            "treat as required for loading user metadata definitions."
                        ),
                    },
                ),
                "reset_forced": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "If true, clear previously forced classes before applying new list.",
                    },
                ),
            },
            "optional": {
                "dry_run": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "If true, do not modify global set; just echo the current list.",
                    },
                ),
            },
        }

    RETURN_TYPES = ("FORCED_CLASSES",)
    FUNCTION = "configure"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    OUTPUT_NODE = False
    DESCRIPTION = "Force include specific node class names for metadata capture merging logic."

    @staticmethod
    def configure(force_include_node_class="", reset_forced=False, dry_run=False):
        from ..defs import clear_forced_include  # local import to avoid cycle
        if reset_forced and not dry_run:
            clear_forced_include()
        if force_include_node_class and not dry_run:
            updated = set_forced_include(force_include_node_class)
        else:
            from ..defs import FORCED_INCLUDE_CLASSES as _F
            updated = _F
        return (",".join(sorted(updated)),)

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):  # noqa: N802
        return float("nan")


__all__ = [
    "SaveImageWithMetaDataUniversal",
    "MetadataForceInclude",
    "MetadataRuleScanner",
]

NODE_CLASS_MAPPINGS = {
    "SaveImageWithMetaDataUniversal": SaveImageWithMetaDataUniversal,
    "CreateExtraMetaDataUniversal": CreateExtraMetaDataUniversal,
    "MetadataForceInclude": MetadataForceInclude,
    "MetadataRuleScanner": MetadataRuleScanner,
    "SaveCustomMetadataRules": SaveCustomMetadataRules,
    "ShowGeneratedUserRules": ShowGeneratedUserRules,
    "SaveGeneratedUserRules": SaveGeneratedUserRules,
    "ShowText|unimeta": ShowText,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithMetaDataUniversal": "Save Image w/ Metadata Universal",
    "CreateExtraMetaDataUniversal": "Create Extra MetaData",
    "MetadataForceInclude": "Metadata Force Include",
    "MetadataRuleScanner": "Metadata Rule Scanner",
    "SaveCustomMetadataRules": "Save Custom Metadata Rules",
    "ShowGeneratedUserRules": "Show generated_user_rules.py",
    "SaveGeneratedUserRules": "Save generated_user_rules.py",
    "ShowText|unimeta": "Show Text (UniMeta)",
}
