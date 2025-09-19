# https://github.com/asagi4/comfyui-prompt-control
# from ..validators import is_node_connected
import logging
import re

from ...utils.lora import find_lora_info
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[PC Meta DBG] PC metadata definition file loaded.")

LORA_REGEX = re.compile(r"<lora:([^:]+):([^>]+)>")
# Cache LoRA parse results per node_id AND prompt text snapshot to avoid stale data
_NODE_DATA_CACHE: dict[int, dict] = {}


def _get_lora_data_from_node(node_id, input_data):
    """Parse LoRA tags from the current prompt text and cache by (node_id, text snapshot).
    This ensures updates to LoRA names/weights are reflected immediately when the text changes.
    """
    global _NODE_DATA_CACHE

    # Extract the text to parse from input_data
    text_input = input_data[0].get("text", "")
    if isinstance(text_input, list):
        text_to_parse = text_input[0] if text_input else ""
    elif isinstance(text_input, str):
        text_to_parse = text_input
    else:
        text_to_parse = ""

    # Return cached result only if the text snapshot matches
    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get("text") == text_to_parse:
        return cached["data"]

    names, hashes, strengths = [], [], []
    if text_to_parse:
        matches = LORA_REGEX.findall(text_to_parse)
        for name, strength_str in matches:
            hashes.append(calc_lora_hash(name, input_data))
            info = find_lora_info(name)
            names.append(info["filename"] if info else name)
            try:
                strengths.append(float(strength_str))
            except (ValueError, TypeError):
                strengths.append(1.0)

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
