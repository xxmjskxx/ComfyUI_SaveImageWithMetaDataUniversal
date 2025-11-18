"""Provides metadata definitions for the PCLazyLoraLoader custom nodes.

This module is designed to integrate with the `comfyui-prompt-control` custom nodes,
specifically `PCLazyLoraLoader` and `PCLazyLoraLoaderAdvanced`. The original implementation
can be found at: https://github.com/asagi4/comfyui-prompt-control

The primary function of this module is to parse LoRA syntax (e.g., `<lora:name:strength>`)
from the text input of these nodes. It extracts LoRA names, strengths, and corresponding
hashes, making this information available for metadata capture.

To optimize performance, the parsed data is cached based on the node ID and the text input.
This avoids redundant parsing when the workflow is executed multiple times without changes
to the prompt.

The module defines selector functions (`get_lora_model_names`, `get_lora_model_hashes`,
`get_lora_strengths`) that are used in the `CAPTURE_FIELD_LIST` to retrieve the
parsed LoRA data.

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary that maps the `PCLazyLoraLoader` and
                               `PCLazyLoraLoaderAdvanced` nodes to their metadata
                               capture configurations. It uses custom selector
                               functions to extract LoRA-related information.
"""
# https://github.com/asagi4/comfyui-prompt-control
# from ..validators import is_node_connected
import logging

from ...utils.lora import (
    coerce_first,
    parse_lora_syntax,
    resolve_lora_display_names,
)
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[PC Meta DBG] PC metadata definition file loaded.")

_NODE_DATA_CACHE: dict[int, dict] = {}


def _get_lora_data_from_node(node_id, input_data):
    """Parses LoRA tags from a node's text input and caches the result.

    This function extracts LoRA names, strengths, and hashes from the text input
    of a given node. It uses a cache (`_NODE_DATA_CACHE`) to store the parsed data,
    keyed by the node ID and the text content. If the text input for a node has not
    changed since the last call, the cached data is returned to avoid redundant
    processing.

    Args:
        node_id (int): The ID of the node being processed.
        input_data (tuple): A tuple containing the node's input data, where the
                          first element is a dictionary with a "text" key.

    Returns:
        dict: A dictionary containing the parsed LoRA data with keys "names",
              "hashes", and "strengths".
    """
    global _NODE_DATA_CACHE

    text_input = input_data[0].get("text", "")
    text_to_parse = coerce_first(text_input)

    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get("text") == text_to_parse:
        return cached["data"]

    names: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    raw_names, ms_list, cs_list = parse_lora_syntax(text_to_parse)
    if raw_names:
        names = resolve_lora_display_names(raw_names)
        model_strengths = ms_list
        clip_strengths = cs_list
    # Hashes must be computed from raw_names (not display names)
    hashes = [calc_lora_hash(raw, input_data) for raw in raw_names] if raw_names else []

    result = {
        "names": names,
        "hashes": hashes,
        "model_strengths": model_strengths,
        "clip_strengths": clip_strengths,
    }
    _NODE_DATA_CACHE[node_id] = {"text": text_to_parse, "data": result}
    return result


def get_lora_model_names(node_id, *args):
    """Selector function to retrieve LoRA model names from a node.

    This function serves as a selector for the metadata capture system. It calls
    `_get_lora_data_from_node` to parse and retrieve LoRA data, then returns
    only the list of LoRA names.

    Args:
        node_id (int): The ID of the node.
        *args: Variable length argument list, with the last argument being the
               node's input data.

    Returns:
        list: A list of LoRA model names.
    """
    return _get_lora_data_from_node(node_id, args[-1])["names"]


def get_lora_model_hashes(node_id, *args):
    """Selector function to retrieve LoRA model hashes from a node.

    This function serves as a selector for the metadata capture system. It calls
    `_get_lora_data_from_node` to parse and retrieve LoRA data, then returns
    only the list of LoRA hashes.

    Args:
        node_id (int): The ID of the node.
        *args: Variable length argument list, with the last argument being the
               node's input data.

    Returns:
        list: A list of LoRA model hashes.
    """
    return _get_lora_data_from_node(node_id, args[-1])["hashes"]


def get_lora_strengths(node_id, *args):
    """Selector function to retrieve LoRA strengths from a node.

    This function serves as a selector for the metadata capture system. It calls
    `_get_lora_data_from_node` to parse and retrieve LoRA data, then returns
    only the list of LoRA strengths.

    Args:
        node_id (int): The ID of the node.
        *args: Variable length argument list, with the last argument being the
               node's input data.

    Returns:
        list: A list of LoRA strengths.
    """
    return _get_lora_data_from_node(node_id, args[-1])["model_strengths"]


def get_lora_clip_strengths(node_id, *args):
    """Selector function to retrieve LoRA CLIP strengths from a node."""

    return _get_lora_data_from_node(node_id, args[-1])["clip_strengths"]


# We need to update the main capture list with our new definition
CAPTURE_FIELD_LIST = {
    "PCLazyLoraLoader": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
    "PCLazyLoraLoaderAdvanced": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
}
