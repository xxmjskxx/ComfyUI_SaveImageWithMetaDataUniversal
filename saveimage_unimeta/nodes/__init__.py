import os

from .save_image import SaveImageWithMetaDataUniversal  # extracted from node.py
from .extra_metadata import CreateExtraMetaDataUniversal  # extracted from node.py
from .rules_view import ShowGeneratedUserRules  # extracted from node.py
from .rules_save import SaveGeneratedUserRules  # extracted from node.py
from .scanner import MetadataRuleScanner  # extracted from node.py
from .rules_writer import SaveCustomMetadataRules  # moved out of legacy node.py
from .show_text import ShowText  # local unimeta variant (separate file for clarity)
from .show_any import ShowAnyToString  # new any->string display node
from ..defs import set_forced_include

class MetadataForceInclude:
    """Configure globally forced node class names for metadata capture.

    Separated from the scanning node so the scanner (`MetadataRuleScanner` implemented
    in `node.py`) can expose its own inputs: exclude_keywords, include_existing,
    mode, force_include_metafields, etc.

    Outputs:
        forced_classes (FORCED_CLASSES): Internal custom type (semantic marker) containing the
            comma-separated forced class list. Use mainly for tooling or future automation.
        forced_classes_str (STRING): Plain comma-separated list of currently forced node class
            names. Connect this to a text display node (e.g. Show Text (UniMeta)) to audit the
            active configuration.
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

    # Provide both the custom type (for clarity / future tooling) and a plain STRING mirror so
    # users can connect directly into generic text display nodes without union inputs.
    RETURN_TYPES = ("FORCED_CLASSES", "STRING")
    RETURN_NAMES = ("forced_classes", "forced_classes_str")
    # Non-standard helper mapping (safe no-op if frontend ignores it) supplying UI tooltip text for outputs.
    OUTPUT_TOOLTIPS = {
        "forced_classes": "Custom marker type with the current forced node class names (same data as string output).",
        "forced_classes_str": "Plain comma-separated list of forced node class names for display/logging.",
    }
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
        joined = ",".join(sorted(updated))
        return (joined, joined)

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):  # noqa: N802
        return float("nan")


__all__ = [
    "SaveImageWithMetaDataUniversal",
    "CreateExtraMetaDataUniversal",
    "MetadataForceInclude",
    "MetadataRuleScanner",
    "ShowGeneratedUserRules",
    "SaveGeneratedUserRules",
    "SaveCustomMetadataRules",
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
    "ShowAny|unimeta": ShowAnyToString,
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
    "ShowAny|unimeta": "Show Any (Any to String)",
}

_enable_test_nodes = os.environ.get("METADATA_ENABLE_TEST_NODES", "").strip().lower()
if _enable_test_nodes and _enable_test_nodes not in {"0", "false", "no"}:
    try:  # pragma: no cover - exercised in runtime integration tests
        from .testing_stubs import (
            TEST_NODE_CLASS_MAPPINGS,
            TEST_NODE_DISPLAY_NAME_MAPPINGS,
        )

        NODE_CLASS_MAPPINGS.update(TEST_NODE_CLASS_MAPPINGS)
        NODE_DISPLAY_NAME_MAPPINGS.update(TEST_NODE_DISPLAY_NAME_MAPPINGS)
    except Exception:  # noqa: BLE001 - fall back silently if stubs unavailable
        pass
