# https://github.com/willmiao/ComfyUI-Lora-Manager
import logging

from ...utils.lora import (
    coerce_first,
    parse_lora_syntax,
    resolve_lora_display_names,
)
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] Lora Loader (LoraManager) metadata definition file loaded.")

# Cache LoRA parse results per node_id AND text snapshot to avoid stale data.
_NODE_DATA_CACHE: dict[int, dict] = {}


def _select_text_field(input_data):
    """Choose which field to parse based on availability (priority order)."""
    if input_data[0].get("lora_syntax", ""):
        return "lora_syntax"
    if input_data[0].get("loaded_loras", ""):
        return "loaded_loras"
    return "text"


def _parse_lora_syntax(text):
    """Return (display_names, hashes, model_strengths, clip_strengths).

    Behavior preserved:
    - Hashes computed from raw name (pre-resolution) with calc_lora_hash(raw, None).
    - Display names resolved via indexed filename when available.
    """
    display_names: list[str] = []
    hashes: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    raw_names, ms_list, cs_list = parse_lora_syntax(text)
    if not raw_names:
        return display_names, hashes, model_strengths, clip_strengths
    display_names = resolve_lora_display_names(raw_names)
    hashes = [calc_lora_hash(raw, None) for raw in raw_names]
    model_strengths = ms_list
    clip_strengths = cs_list
    return display_names, hashes, model_strengths, clip_strengths


def _get_lora_data_from_node(node_id, input_data):
    """Parse LoRA tags and cache by node id + text snapshot. Supports dual strengths."""
    global _NODE_DATA_CACHE
    field_to_parse = _select_text_field(input_data)
    raw_val = input_data[0].get(field_to_parse, "")
    text_to_parse = coerce_first(raw_val)

    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get(field_to_parse) == text_to_parse:
        return cached["data"]

    names, hashes, model_strengths, clip_strengths = _parse_lora_syntax(text_to_parse)
    result = {
        "names": names,
        "hashes": hashes,
        "model_strengths": model_strengths,
        "clip_strengths": clip_strengths,
    }
    _NODE_DATA_CACHE[node_id] = {field_to_parse: text_to_parse, "data": result}
    return result


# Selectors (note: *args[-1] is input_data structure from capture pipeline)
def get_lora_model_names(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["names"]


def get_lora_model_hashes(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["hashes"]


def get_lora_model_strengths(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["model_strengths"]


def get_lora_clip_strengths(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["clip_strengths"]


# Legacy selector (kept for backward compatibility) returns model strengths
def get_lora_strengths(node_id, *args):
    return _get_lora_data_from_node(node_id, args[-1])["model_strengths"]


# We need to update the main capture list with our new definition
CAPTURE_FIELD_LIST = {
    "Lora Loader (LoraManager)": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
    "LoRA Text Loader (LoraManager)": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
    "Lora Stacker (LoraManager)": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
    "WanVideo Lora Select (LoraManager)": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
    "WanVideo Lora Select From Text (LoraManager)": {
        # The 'validate' key is now correctly placed inside each field's definition.
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
}
