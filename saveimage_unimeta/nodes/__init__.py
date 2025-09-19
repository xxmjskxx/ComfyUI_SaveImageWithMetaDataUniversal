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
                )
            }
        }

    RETURN_TYPES = ("FORCED_CLASSES",)
    FUNCTION = "configure"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    OUTPUT_NODE = False

    @staticmethod
    def configure(force_include_node_class=""):
        updated = set_forced_include(force_include_node_class)
        # Return a sorted, comma string for potential downstream display/debug nodes.
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
