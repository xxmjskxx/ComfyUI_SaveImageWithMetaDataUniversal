"""Provides metadata definitions for the rgthree-comfy custom nodes.

This module is designed to integrate with the `rgthree-comfy` custom node pack,
which can be found at: https://github.com/rgthree/rgthree-comfy

It supports two main types of nodes for LoRA handling:
1.  **Lora Loaders**: Nodes like `Power Lora Loader` and `Lora Loader Stack` that
    manage LoRAs through dedicated input slots.
2.  **Power Prompts**: Nodes such as `Power Prompt` that parse LoRA syntax
    (e.g., `<lora:name:strength>`) directly from text inputs.

The module provides distinct sets of selector functions to handle these two
mechanisms. For Power Prompts, it includes a caching system to avoid re-parsing
text that has not changed.

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary mapping the rgthree nodes to their
                               metadata capture configurations.
"""
# https://github.com/rgthree/rgthree-comfy
import logging

from ...utils.lora import (
    coerce_first,
    parse_lora_syntax,
    resolve_lora_display_names,
)
from ..selectors import select_stack_by_prefix
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] rgthree extension definitions loaded.")


def get_lora_model_name(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector for LoRA names from rgthree's Power Lora Loader."""
    return get_lora_data(input_data, "lora")


def get_lora_model_hash(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector for LoRA hashes from rgthree's Power Lora Loader."""
    return [calc_lora_hash(model_name, input_data) for model_name in get_lora_data(input_data, "lora")]


def get_lora_strength(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector for LoRA strengths from rgthree's Power Lora Loader."""
    return get_lora_data(input_data, "strength")


def get_lora_data(input_data, attribute):
    """Helper to extract data from active LoRA inputs on a Power Lora Loader."""
    return [v[0][attribute] for k, v in input_data[0].items() if k.startswith("lora_") and v[0]["on"]]


def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector for LoRA names from rgthree's Lora Loader Stack."""
    return select_stack_by_prefix(input_data, "lora_", filter_none=True)


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector for LoRA hashes from rgthree's Lora Loader Stack."""
    names = select_stack_by_prefix(input_data, "lora_", filter_none=True)
    return [calc_lora_hash(model_name, input_data) for model_name in names]


def get_lora_strength_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector for LoRA strengths from rgthree's Lora Loader Stack."""
    return select_stack_by_prefix(input_data, "strength_", filter_none=True)


# Local stack helper removed in favor of shared selector above.


_SYNTAX_CACHE = {}


def _parse_syntax(text: str):
    """Parses LoRA syntax from a string and returns structured data.

    This function extracts LoRA names, calculates their hashes, and parses their
    model and CLIP strengths from a text string containing LoRA syntax.

    Args:
        text (str): The text to parse.

    Returns:
        tuple: A tuple of lists: (display_names, hashes, model_strengths, clip_strengths).
    """
    display_names: list[str] = []
    hashes: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    raw_names, ms_list, cs_list = parse_lora_syntax(text)
    if not raw_names:
        return display_names, hashes, model_strengths, clip_strengths
    # Resolve display names in bulk
    display_names = resolve_lora_display_names(raw_names)
    # Compute hashes using the raw names (preserves original behavior)
    for raw in raw_names:
        hashes.append(calc_lora_hash(raw, None))
    model_strengths = ms_list
    clip_strengths = cs_list
    return display_names, hashes, model_strengths, clip_strengths


def _get_syntax(node_id, input_data):
    """Extracts text from a Power Prompt node and parses it for LoRA syntax.

    This function identifies the relevant text field in a Power Prompt node,
    retrieves its content, and then uses `_parse_syntax` to extract LoRA data.
    Results are cached to avoid redundant parsing.

    Args:
        node_id (int): The ID of the node.
        input_data (dict): The input data for the node.

    Returns:
        dict: A dictionary containing the parsed LoRA data.
    """
    # Candidate textual fields used by rgthree prompt nodes
    candidates = ["prompt", "text", "positive", "clip", "t5", "combined"]
    for key in candidates:
        raw = input_data[0].get(key)
        if raw:
            text = coerce_first(raw)
            cached = _SYNTAX_CACHE.get(node_id)
            if cached and cached.get("text") == text:
                return cached["data"]
            names, hashes, ms, cs = _parse_syntax(text)
            data = {
                "names": names,
                "hashes": hashes,
                "model_strengths": ms,
                "clip_strengths": cs,
            }
            _SYNTAX_CACHE[node_id] = {"text": text, "data": data}
            return data
    return {"names": [], "hashes": [], "model_strengths": [], "clip_strengths": []}


def get_rgthree_syntax_names(node_id, *args):
    """Selector for LoRA names from an rgthree Power Prompt node."""
    return _get_syntax(node_id, args[-1])["names"]


def get_rgthree_syntax_hashes(node_id, *args):
    """Selector for LoRA hashes from an rgthree Power Prompt node."""
    return _get_syntax(node_id, args[-1])["hashes"]


def get_rgthree_syntax_model_strengths(node_id, *args):
    """Selector for LoRA model strengths from an rgthree Power Prompt node."""
    return _get_syntax(node_id, args[-1])["model_strengths"]


def get_rgthree_syntax_clip_strengths(node_id, *args):
    """Selector for LoRA CLIP strengths from an rgthree Power Prompt node."""
    return _get_syntax(node_id, args[-1])["clip_strengths"]


CAPTURE_FIELD_LIST = {
    "Power Lora Loader (rgthree)": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_name},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strength},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strength},
    },
    "Lora Loader Stack (rgthree)": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_name},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strength},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strength},
    },
    # Syntax-only prompt nodes
    "Power Prompt (rgthree)": {
        MetaField.LORA_MODEL_NAME: {"selector": get_rgthree_syntax_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_rgthree_syntax_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_rgthree_syntax_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_rgthree_syntax_clip_strengths},
    },
    "SDXL Power Prompt - Positive (rgthree)": {
        MetaField.LORA_MODEL_NAME: {"selector": get_rgthree_syntax_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_rgthree_syntax_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_rgthree_syntax_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_rgthree_syntax_clip_strengths},
    },
}
