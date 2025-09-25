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
    """Parse LoRA tags from the current prompt text and cache by (node_id, text snapshot)."""
    global _NODE_DATA_CACHE

    text_input = input_data[0].get("text", "")
    text_to_parse = coerce_first(text_input)

    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get("text") == text_to_parse:
        return cached["data"]

    names, strengths = [], []
    raw_names, ms_list, _cs_list = parse_lora_syntax(text_to_parse)
    if raw_names:
        names = resolve_lora_display_names(raw_names)
        strengths = ms_list
    # Hashes must be computed from raw_names (not display names)
    hashes = [calc_lora_hash(raw, input_data) for raw in raw_names] if raw_names else []

    result = {"names": names, "hashes": hashes, "strengths": strengths}
    _NODE_DATA_CACHE[node_id] = {"text": text_to_parse, "data": result}
    return result


def get_lora_model_names(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["names"]


def get_lora_model_hashes(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["hashes"]


def get_lora_strengths(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["strengths"]


# We need to update the main capture list with our new definition
CAPTURE_FIELD_LIST = {
    "PCLazyLoraLoader": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strengths},
    },
    "PCLazyLoraLoaderAdvanced": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strengths},
    },
}
