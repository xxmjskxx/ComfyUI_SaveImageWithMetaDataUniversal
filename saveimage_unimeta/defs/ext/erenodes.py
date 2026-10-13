"""Provides metadata definitions for the EreNodes custom node pack.

This module is designed to integrate with `ComfyUI-EreNodes`, specifically its
`Prompt Lora Loader` node (`ErePromptLoraLoader`). The original implementation
can be found at: https://github.com/erehr/ComfyUI-EreNodes

The node applies every LoRA written as `<lora:name:model_strength:clip_strength>`
in two places: its own `text` widget and its optional `prefix` input, which is
usually the prompt of an upstream EreNodes prompt node. The prefix is applied
first, a LoRA named in both is applied once, and a LoRA whose model and CLIP
strengths are both zero is skipped. The selectors here mirror that, so the
captured LoRAs are the ones the node actually loaded.

Attributes:
    CAPTURE_FIELD_LIST (dict): Maps `ErePromptLoraLoader` to its LoRA capture
                               configuration.
"""

# https://github.com/erehr/ComfyUI-EreNodes
import logging

from ...utils.lora import (
    coerce_first,
    parse_lora_syntax,
    resolve_lora_display_names,
)
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] EreNodes metadata definition file loaded.")

# Cache LoRA parse results per node_id AND input snapshot to avoid stale data.
_NODE_DATA_CACHE: dict = {}

# In the order the node applies them.
_TEXT_FIELDS = ("prefix", "text")


def _collect_entries(batch):
    """Return (raw_name, model_strength, clip_strength) for each LoRA the node applies."""
    entries = []
    seen = set()
    for field in _TEXT_FIELDS:
        names, model_strengths, clip_strengths = parse_lora_syntax(coerce_first(batch.get(field, "")))
        for name, ms, cs in zip(names, model_strengths, clip_strengths):
            key = str(name).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            if ms == 0 and cs == 0:
                continue
            entries.append((name, ms, cs))
    return entries


def _get_lora_data_from_node(node_id, input_data):
    """Parses LoRA tags from the node's `prefix` and `text` inputs, utilizing a cache.

    Args:
        node_id (int): The ID of the node.
        input_data (tuple): The node's input data, where the first element is a
                            dictionary holding the `prefix` and `text` values.

    Returns:
        dict: A dictionary containing the parsed LoRA data (names, hashes, etc.).
    """
    batch = input_data[0] if input_data and input_data[0] else {}
    snapshot = tuple(coerce_first(batch.get(field, "")) for field in _TEXT_FIELDS)
    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get("snapshot") == snapshot:
        return cached["data"]

    entries = _collect_entries(batch)
    raw_names = [name for name, _ms, _cs in entries]
    result = {
        "names": resolve_lora_display_names(raw_names) if raw_names else [],
        # Hashes must be computed from raw names (not display names)
        "hashes": [calc_lora_hash(name, input_data) for name in raw_names],
        "model_strengths": [ms for _name, ms, _cs in entries],
        "clip_strengths": [cs for _name, _ms, cs in entries],
    }
    _NODE_DATA_CACHE[node_id] = {"snapshot": snapshot, "data": result}
    return result


# Selectors (note: *args[-1] is input_data structure from capture pipeline)
def get_lora_model_names(node_id, *args):
    """Selector to get LoRA model names from an EreNodes Prompt Lora Loader."""
    return _get_lora_data_from_node(node_id, args[-1])["names"]


def get_lora_model_hashes(node_id, *args):
    """Selector to get LoRA model hashes from an EreNodes Prompt Lora Loader."""
    return _get_lora_data_from_node(node_id, args[-1])["hashes"]


def get_lora_model_strengths(node_id, *args):
    """Selector to get LoRA model strengths from an EreNodes Prompt Lora Loader."""
    return _get_lora_data_from_node(node_id, args[-1])["model_strengths"]


def get_lora_clip_strengths(node_id, *args):
    """Selector to get LoRA CLIP strengths from an EreNodes Prompt Lora Loader."""
    return _get_lora_data_from_node(node_id, args[-1])["clip_strengths"]


CAPTURE_FIELD_LIST = {
    "ErePromptLoraLoader": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
}
