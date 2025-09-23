# https://github.com/willmiao/ComfyUI-Lora-Manager
import logging
import re

from ...utils.lora import find_lora_info
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] Lora Loader (LoraManager) metadata definition file loaded.")

# Strict pattern capturing optional separate clip strength:
# <lora:name:model_strength> OR <lora:name:model_strength:clip_strength>
LORA_REGEX_V2 = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
# Fallback (legacy) pattern capturing anything after the second colon
# (may include :clip) – used only if strict finds nothing
LORA_REGEX_LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")

# Cache LoRA parse results per node_id AND text snapshot to avoid stale data.
_NODE_DATA_CACHE: dict[int, dict] = {}


def _select_text_field(input_data):
    """Choose which field to parse based on availability (priority order)."""
    if input_data[0].get("lora_syntax", ""):
        return "lora_syntax"
    if input_data[0].get("loaded_loras", ""):
        return "loaded_loras"
    return "text"


def _coerce_first(val):
    if isinstance(val, list):
        return val[0] if val else ""
    return val if isinstance(val, str) else ""


def _parse_lora_syntax(text):
    names, hashes, model_strengths, clip_strengths = [], [], [], []
    if not text:
        return names, hashes, model_strengths, clip_strengths

    matches = LORA_REGEX_V2.findall(text)
    if not matches:
        # Try legacy pattern (will lose separate clip; treat combined as model strength if numeric)
        legacy = LORA_REGEX_LEGACY.findall(text)
        for name, strength_blob in legacy:
            try:
                # Attempt to split on ':' if user wrote extended form but regex failed (edge cases)
                parts = strength_blob.split(":")
                if len(parts) == 2:
                    ms = float(parts[0])
                    cs = float(parts[1])
                else:
                    ms = float(parts[0])
                    cs = ms
            except Exception:
                ms = 1.0
                cs = 1.0
            names.append(name)
            hashes.append(calc_lora_hash(name, None))
            model_strengths.append(ms)
            clip_strengths.append(cs)
        return names, hashes, model_strengths, clip_strengths

    for name, model_str, clip_str in matches:
        try:
            ms = float(model_str)
        except Exception:
            ms = 1.0
        try:
            cs = float(clip_str) if clip_str else ms
        except Exception:
            cs = ms
        # Resolve canonical filename (if available) for display consistency
        info = find_lora_info(name)
        display_name = info["filename"] if info else name
        names.append(display_name)
        hashes.append(calc_lora_hash(name, None))
        model_strengths.append(ms)
        clip_strengths.append(cs)
    return names, hashes, model_strengths, clip_strengths


def _get_lora_data_from_node(node_id, input_data):
    """Parse LoRA tags and cache by node id + text snapshot. Supports dual strengths."""
    global _NODE_DATA_CACHE
    field_to_parse = _select_text_field(input_data)
    raw_val = input_data[0].get(field_to_parse, "")
    text_to_parse = _coerce_first(raw_val)

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
