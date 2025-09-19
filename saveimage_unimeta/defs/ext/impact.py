# ImpactWildcardEncode node: embeds <lora:NAME:strength[:clip]> tags in its wildcard-expanded text.
import logging
import re

from ...utils.lora import find_lora_info
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] impact wildcard LoRA syntax support loaded.")

STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")

_CACHE = {}


def _coerce(v):
    if isinstance(v, list):
        return v[0] if v else ""
    return v if isinstance(v, str) else ""


def _parse(text: str):
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


def _extract(node_id, input_data):
    # Likely text fields produced after wildcard expansion
    candidates = ["text", "prompt", "positive", "combined", "out"]
    for key in candidates:
        raw = input_data[0].get(key)
        if raw:
            text = _coerce(raw)
            cached = _CACHE.get(node_id)
            if cached and cached.get("text") == text:
                return cached["data"]
            names, hashes, ms, cs = _parse(text)
            data = {
                "names": names,
                "hashes": hashes,
                "model_strengths": ms,
                "clip_strengths": cs,
            }
            _CACHE[node_id] = {"text": text, "data": data}
            return data
    return {"names": [], "hashes": [], "model_strengths": [], "clip_strengths": []}


def get_impact_lora_names(node_id, *args):
    return _extract(node_id, args[-1])["names"]


def get_impact_lora_hashes(node_id, *args):
    return _extract(node_id, args[-1])["hashes"]


def get_impact_lora_model_strengths(node_id, *args):
    return _extract(node_id, args[-1])["model_strengths"]


def get_impact_lora_clip_strengths(node_id, *args):
    return _extract(node_id, args[-1])["clip_strengths"]


CAPTURE_FIELD_LIST = {
    "ImpactWildcardEncode": {
        MetaField.LORA_MODEL_NAME: {"selector": get_impact_lora_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_impact_lora_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_impact_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_impact_lora_clip_strengths},
    }
}
