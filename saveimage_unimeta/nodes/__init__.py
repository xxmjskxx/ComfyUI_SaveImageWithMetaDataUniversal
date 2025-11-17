"""Initializes the `saveimage_unimeta.nodes` package and registers custom nodes.

This module imports all the custom nodes from the `saveimage_unimeta` package
and registers them with ComfyUI. It defines the `NODE_CLASS_MAPPINGS` and
`NODE_DISPLAY_NAME_MAPPINGS` dictionaries, which are used by ComfyUI to
discover and display the custom nodes in the user interface. It also includes
the `MetadataForceInclude` node for managing forced node class names.
"""

import logging
import os


from .save_image import SaveImageWithMetaDataUniversal  # extracted from node.py
from .extra_metadata import CreateExtraMetaDataUniversal  # extracted from node.py
from .rules_view import ShowGeneratedUserRules  # extracted from node.py
from .rules_save import SaveGeneratedUserRules  # extracted from node.py
from .scanner import MetadataRuleScanner  # extracted from node.py
from .rules_writer import SaveCustomMetadataRules  # moved out of legacy node.py
from .show_text import ShowText  # local unimeta variant (separate file for clarity)
from .show_any import ShowAnyToString  # new any->string display node
from .testing_stubs import MetadataTestSampler  # test stub node for metadata capture testing
from ..defs import set_forced_include

logger = logging.getLogger(__name__)


class MetadataForceInclude:
    """A node to configure globally forced node class names for metadata capture.

    This node allows users to specify a list of node class names that should
    always be included in the metadata capture process, regardless of the
    rules defined in the `MetadataRuleScanner`. This is useful for ensuring
    that certain nodes are always processed.
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
        """Define the input types for the `MetadataForceInclude` node.

        This method specifies the inputs for the node, including a multiline
        string for the node class names, a boolean to reset the list, and a
        dry run option.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
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
        """Configure the forced include list.

        This method updates the global set of forced include classes based on
        the provided inputs. It can reset the list, add new classes, or perform
        a dry run.

        Args:
            force_include_node_class (str, optional): A string of comma or
                newline-separated node class names. Defaults to "".
            reset_forced (bool, optional): If True, the existing list is cleared
                before adding new classes. Defaults to False.
            dry_run (bool, optional): If True, the global list is not modified.
                Defaults to False.

        Returns:
            tuple[str, str]: A tuple containing the updated list of forced
                classes as a comma-separated string.
        """
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
        """Indicate that the node's output can change even if inputs are the same.

        This method returns `float("nan")` to signal to ComfyUI that this node
        should be re-executed every time the graph is run.

        Returns:
            float: A NaN value.
        """
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
    "MetadataTestSampler|unimeta": MetadataTestSampler,
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
    "MetadataTestSampler|unimeta": "Metadata Test Sampler",
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
    except Exception as err:  # noqa: BLE001 - fall back silently if stubs unavailable
        logger.debug("Failed to import test stubs: %r", err)
