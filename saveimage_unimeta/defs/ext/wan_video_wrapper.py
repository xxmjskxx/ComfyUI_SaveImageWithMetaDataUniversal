# https://github.com/kijai/ComfyUI-WanVideoWrapper

import logging
import re

from ..validators import is_negative_prompt, is_positive_prompt

from ...utils.lora import find_lora_info
from ..formatters import calc_lora_hash, calc_vae_hash, calc_unet_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] Wan Video Wrapper extension definitions loaded.")


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
    # Candidate textual fields used by WanVideo prompt/encode nodes
    candidates = [
        "prompt",
        "text",
        "positive",
        "clip",
        "t5",
        "combined",
        "positive_prompt",
        "negative_prompt",
    ]
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

# WanVideoModelLoader may load up to 2 models and both should be recorded if present.
# Possible name formats for WanVideoLoraSelectByName:
#   Wan2.2-Lightning_T2V-A14B-4steps-lora_HIGH_fp16
#   wan\\turbo\\Wan2.2-Lightning_T2V-A14B-4steps-lora_HIGH_fp16
# Wan can also use additional models like the one's loaded with the VACE and ExtraModel nodes
# Wan lora models have no clip strengths, only model strengths.
# WanVideoLoraSelectMulti can load up to 5 loras at once
# LoadWanVideoT5TextEncoder and LoadWanVideoClipTextEncoder load CLIP models
# WanVideo TextEncode has a positive_prompt and negative_prompt field
# WanVideo TextEncode Cached has a positive_prompt and negative_prompt field,
# and a model_name field for loading a clip model
# WanVideo TextEncodeSingle has a prompt field

CAPTURE_FIELD_LIST = {
    "WanVideoModelLoader": {
        MetaField.MODEL_NAME: {"field_name": "model"},
        MetaField.MODEL_HASH: {"field_name": "model", "format": calc_unet_hash},
        # Some variants expose two models; if present, the active one is exposed via 'model'.
    },
    "WanVideoVAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },
    "WanVideoLoraSelect": {
        MetaField.LORA_MODEL_NAME: {"fields": ["lora", "merge_loras", "prev_lora"]},
        MetaField.LORA_MODEL_HASH: {"fields": ["lora", "merge_loras", "prev_lora"], "format": calc_lora_hash},
    },
    "WanVideoLoraSelectByName": {
        MetaField.LORA_MODEL_NAME: {"fields": ["lora_name"]},
        MetaField.LORA_MODEL_HASH: {"fields": ["lora_name"], "format": calc_lora_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength"},
    },
    "WanVideoTinyVAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },
    "WanVideoVACEModelSelect": {
        MetaField.MODEL_NAME: {"field_name": "vace_model"},
        MetaField.MODEL_HASH: {"field_name": "vace_model", "format": calc_unet_hash},
    },
    "WanVideoExtraModelSelect": {
        MetaField.MODEL_NAME: {"field_name": "extra_model"},
        MetaField.MODEL_HASH: {"field_name": "extra_model", "format": calc_unet_hash},
    },
    "WanVideoLoraSelectMulti": {
        MetaField.LORA_MODEL_NAME: {"fields": ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4"]},
        MetaField.LORA_MODEL_HASH: {
            "fields": ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4"],
            "format": calc_lora_hash,
        },
        MetaField.LORA_STRENGTH_MODEL: {
            "fields": ["strength_0", "strength_1", "strength_2", "strength_3", "strength_4"],
        },
    },
    "LoadWanVideoT5TextEncoder": {
        MetaField.CLIP_MODEL_NAME: {"field_name": "clip_name"},
    },
    "LoadWanVideoClipTextEncoder": {
        MetaField.CLIP_MODEL_NAME: {"field_name": "clip_name"},
    },
    "WanVideoTextEncode": {
        MetaField.POSITIVE_PROMPT: {"field_name": "positive_prompt", "validate": is_positive_prompt},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative_prompt", "validate": is_negative_prompt},
    },
    "WanVideoTextEncodeCached": {
        MetaField.POSITIVE_PROMPT: {"field_name": "positive_prompt", "validate": is_positive_prompt},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative_prompt", "validate": is_negative_prompt},
        MetaField.CLIP_MODEL_NAME: {"field_name": "model_name"},
    },
    "WanVideoTextEncodeSingle": {
        MetaField.POSITIVE_PROMPT: {"field_name": "prompt", "validate": is_positive_prompt},
        MetaField.NEGATIVE_PROMPT: {"field_name": "prompt", "validate": is_negative_prompt},
    },
}
