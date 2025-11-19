"""Provides metadata definitions for the Impact Pack's Wildcard nodes.

This module is specifically designed to handle the `ImpactWildcardEncode` node, which allows
for the embedding of LoRA tags (e.g., `<lora:NAME:strength[:clip]>`) directly within
wildcard-expanded text prompts.

The core functionality involves parsing the output text from the node to find and extract
these LoRA tags. It supports both a strict format and a legacy format for the tags.
The extracted information, including LoRA names, hashes, and strengths, is then made
available for metadata capture through a set of custom selector functions.

To improve performance, the parsed data from a given text input is cached, preventing
redundant parsing if the same text is processed multiple times.

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary that maps the `ImpactWildcardEncode` node to
                               its metadata capture configurations, using custom selectors
                               to extract the parsed LoRA data.
"""
# ImpactWildcardEncode node: embeds <lora:NAME:strength[:clip]> tags in its wildcard-expanded text.
import logging
import re
from typing import TypedDict

from ...utils.lora import find_lora_info
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] impact wildcard LoRA syntax support loaded.")

STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")


class _ImpactData(TypedDict):
    names: list[str]
    hashes: list[str]
    model_strengths: list[float]
    clip_strengths: list[float]


class _ImpactCacheEntry(TypedDict):
    text: str
    data: _ImpactData


_CACHE: dict[int, _ImpactCacheEntry] = {}


def _coerce(v):
    """Coerces an input value into a string.

    If the input is a list, it returns the first element or an empty string.
    If it's already a string, it's returned as is. Otherwise, an empty string is returned.

    Args:
        v: The value to coerce.

    Returns:
        str: The coerced string value.
    """
    if isinstance(v, list):
        return v[0] if v else ""
    return v if isinstance(v, str) else ""


def _parse(text: str) -> _ImpactData:
    """Parses a string to find and extract LoRA tags.

    This function searches for LoRA tags in both a strict and a legacy format.
    For each tag found, it extracts the LoRA name, calculates its hash, and
    determines the model and CLIP strengths.

    Args:
        text (str): The text to parse.

    Returns:
        tuple: A tuple containing four lists: names, hashes, model_strengths,
               and clip_strengths.
    """
    names: list[str] = []
    hashes: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    if not text:
        return {
            "names": names,
            "hashes": hashes,
            "model_strengths": model_strengths,
            "clip_strengths": clip_strengths,
        }
    matches = STRICT.findall(text)
    if not matches:
        legacy = LEGACY.findall(text)
        for name, blob in legacy:
            if not name:
                continue
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
            hashes.append(calc_lora_hash(name, []))
            model_strengths.append(ms)
            clip_strengths.append(cs)
        return {
            "names": names,
            "hashes": hashes,
            "model_strengths": model_strengths,
            "clip_strengths": clip_strengths,
        }
    for name, ms_s, cs_s in matches:
        if not name:
            continue
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
        hashes.append(calc_lora_hash(name, []))
        model_strengths.append(ms)
        clip_strengths.append(cs)
    return {
        "names": names,
        "hashes": hashes,
        "model_strengths": model_strengths,
        "clip_strengths": clip_strengths,
    }


def _extract(node_id, input_data) -> _ImpactData:
    """Extracts and parses text from a node's input to find LoRA data.

    This function searches for text in likely input fields of a wildcard node.
    It uses a cache to avoid re-parsing the same text for the same node.

    Args:
        node_id (int): The ID of the node.
        input_data (dict): The input data for the node.

    Returns:
        dict: A dictionary containing the extracted LoRA data (names, hashes, etc.).
    """
    # Likely text fields produced after wildcard expansion
    candidates = ["text", "prompt", "positive", "combined", "out"]
    if not isinstance(input_data, list) or not input_data:
        return {"names": [], "hashes": [], "model_strengths": [], "clip_strengths": []}
    batch = input_data[0]
    if not isinstance(batch, dict):
        return {"names": [], "hashes": [], "model_strengths": [], "clip_strengths": []}
    for key in candidates:
        raw = batch.get(key)
        if raw:
            text = _coerce(raw)
            cached = _CACHE.get(node_id)
            if cached and cached.get("text") == text:
                return cached["data"]
            data = _parse(text)
            _CACHE[node_id] = {"text": text, "data": data}
            return data
    return {"names": [], "hashes": [], "model_strengths": [], "clip_strengths": []}


def get_impact_lora_names(node_id, *args):
    """Selector to get LoRA names from an Impact Wildcard node."""
    return _extract(node_id, args[-1])["names"]


def get_impact_lora_hashes(node_id, *args):
    """Selector to get LoRA hashes from an Impact Wildcard node."""
    return _extract(node_id, args[-1])["hashes"]


def get_impact_lora_model_strengths(node_id, *args):
    """Selector to get LoRA model strengths from an Impact Wildcard node."""
    return _extract(node_id, args[-1])["model_strengths"]


def get_impact_lora_clip_strengths(node_id, *args):
    """Selector to get LoRA CLIP strengths from an Impact Wildcard node."""
    return _extract(node_id, args[-1])["clip_strengths"]


CAPTURE_FIELD_LIST = {
    "ImpactWildcardEncode": {
        MetaField.LORA_MODEL_NAME: {"selector": get_impact_lora_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_impact_lora_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_impact_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_impact_lora_clip_strengths},
    }
}
