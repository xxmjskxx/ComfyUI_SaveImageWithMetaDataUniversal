from .node import (  # noqa: N999 - package path inherited from external naming constraints
    CreateExtraMetaDataUniversal,
    SaveCustomMetadataRules,
    SaveGeneratedUserRules,
    SaveImageWithMetaDataUniversal,
    ShowGeneratedUserRules,
)
from ..defs import set_forced_include

class MetadataRuleScanner:
    """Utility node to configure metadata rule scanning behavior.

    Currently supports forcing inclusion of specific node class names so that
    user definition loading logic treats them as required even if traversal
    heuristics would normally skip them.
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
                            "include in metadata rule scanning."
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
                        "tooltip": "If true, do not modify global set; just echo what would be applied.",
                    },
                ),
            },
        }

    RETURN_TYPES = ("FORCED_CLASSES",)
    FUNCTION = "configure"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    OUTPUT_NODE = False

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
        # Return a sorted comma string and count for diagnostics
        return (",".join(sorted(updated)),)

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):  # noqa: N802, D401
        # Always allow re-execution so users can adjust classes mid-workflow.
        return float("nan")


__all__ = [
    "SaveImageWithMetaDataUniversal",
    "MetadataRuleScanner",
]

NODE_CLASS_MAPPINGS = {
    "SaveImageWithMetaDataUniversal": SaveImageWithMetaDataUniversal,
    "CreateExtraMetaDataUniversal": CreateExtraMetaDataUniversal,
    "MetadataRuleScanner": MetadataRuleScanner,
    "SaveCustomMetadataRules": SaveCustomMetadataRules,
    "ShowGeneratedUserRules": ShowGeneratedUserRules,
    "SaveGeneratedUserRules": SaveGeneratedUserRules,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithMetaDataUniversal": "Save Image w/ Metadata Universal",
    "CreateExtraMetaDataUniversal": "Create Extra MetaData",
    "MetadataRuleScanner": "Metadata Rule Scanner",
    "SaveCustomMetadataRules": "Save Custom Metadata Rules",
    "ShowGeneratedUserRules": "Show generated_user_rules.py",
    "SaveGeneratedUserRules": "Save generated_user_rules.py",
}
