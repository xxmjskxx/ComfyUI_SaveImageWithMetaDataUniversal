# https://github.com/rgthree/rgthree-comfy
import logging
import re

from ...utils.lora import find_lora_info
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] rgthree extension definitions loaded.")


def get_lora_model_name(node_id, obj, prompt, extra_data, outputs, input_data):
    return get_lora_data(input_data, "lora")


def get_lora_model_hash(node_id, obj, prompt, extra_data, outputs, input_data):
    return [calc_lora_hash(model_name, input_data) for model_name in get_lora_data(input_data, "lora")]


def get_lora_strength(node_id, obj, prompt, extra_data, outputs, input_data):
    return get_lora_data(input_data, "strength")


def get_lora_data(input_data, attribute):
    return [v[0][attribute] for k, v in input_data[0].items() if k.startswith("lora_") and v[0]["on"]]


def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    return get_lora_data_stack(input_data, "lora")


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    return [calc_lora_hash(model_name, input_data) for model_name in get_lora_data_stack(input_data, "lora")]


def get_lora_strength_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    return get_lora_data_stack(input_data, "strength")


def get_lora_data_stack(input_data, attribute):
    return [v[0] for k, v in input_data[0].items() if k.startswith(attribute + "_") and v[0] != "None"]


STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")
_SYNTAX_CACHE = {}


def _coerce_first(v):
    if isinstance(v, list):
        return v[0] if v else ""
    return v if isinstance(v, str) else ""


def _parse_syntax(text: str):
    names, hashes, model_strengths, clip_strengths = [], [], [], []
    if not text:
        return names, hashes, model_strengths, clip_strengths
    matches = STRICT.findall(text)
    if not matches:
        legacy = LEGACY.findall(text)
        for name, blob in legacy:
            try:
                parts = blob.split(":")
                if len(parts) == 2:
                    ms = float(parts[0])
                    cs = float(parts[1])
                else:
                    ms = float(parts[0])
                    cs = ms
            except Exception:
                ms = cs = 1.0
            info = find_lora_info(name)
            display = info["filename"] if info else name
            names.append(display)
            hashes.append(calc_lora_hash(name, None))
            model_strengths.append(ms)
            clip_strengths.append(cs)
        return names, hashes, model_strengths, clip_strengths
    for name, ms_s, cs_s in matches:
        try:
            ms = float(ms_s)
        except Exception:
            ms = 1.0
        try:
            cs = float(cs_s) if cs_s else ms
        except Exception:
            cs = ms
        info = find_lora_info(name)
        display = info["filename"] if info else name
        names.append(display)
        hashes.append(calc_lora_hash(name, None))
        model_strengths.append(ms)
        clip_strengths.append(cs)
    return names, hashes, model_strengths, clip_strengths


def _get_syntax(node_id, input_data):
    # Candidate textual fields used by rgthree prompt nodes
    candidates = ["prompt", "text", "positive", "clip", "t5", "combined"]
    for key in candidates:
        raw = input_data[0].get(key)
        if raw:
            text = _coerce_first(raw)
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
    return _get_syntax(node_id, args[-1])["names"]


def get_rgthree_syntax_hashes(node_id, *args):
    return _get_syntax(node_id, args[-1])["hashes"]


def get_rgthree_syntax_model_strengths(node_id, *args):
    return _get_syntax(node_id, args[-1])["model_strengths"]


def get_rgthree_syntax_clip_strengths(node_id, *args):
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
