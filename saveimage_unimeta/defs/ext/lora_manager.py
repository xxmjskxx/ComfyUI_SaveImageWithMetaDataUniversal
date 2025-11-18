"""Provides metadata definitions for the ComfyUI-Lora-Manager custom nodes.

This module is designed to integrate with the `ComfyUI-Lora-Manager` custom node pack,
which can be found at: https://github.com/willmiao/ComfyUI-Lora-Manager

It specializes in parsing LoRA syntax (e.g., `<lora:name:model_strength:clip_strength>`)
from various text fields within the LoraManager nodes. This allows for the capture
of detailed LoRA information, including names, hashes, and separate model/CLIP strengths.

The module includes a caching mechanism to avoid re-parsing the same LoRA syntax,
improving performance on repeated workflow executions. It defines a set of selector
functions that are mapped to several nodes from the LoraManager pack in the
`CAPTURE_FIELD_LIST`.

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary mapping various LoraManager nodes to their
                               metadata capture configurations, utilizing custom
                               selectors to parse and extract LoRA data.
"""
# https://github.com/willmiao/ComfyUI-Lora-Manager
import json
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
_STACK_FIELD_CANDIDATES: tuple[str, ...] = (
    "lora_stack",
    "loras",
    "loaded_loras",
    "scheduled_loras",
    "lora_queue",
)
_TEXT_FIELD_CANDIDATES: tuple[str, ...] = (
    "lora_syntax",
    "loaded_loras",
    "text",
)


def _select_text_field(input_data):
    """Select the first populated text-style field available on the node."""

    if not input_data or not input_data[0]:
        return "text"
    batch = input_data[0]
    for field in _TEXT_FIELD_CANDIDATES:
        try:
            if batch.get(field, ""):
                return field
        except AttributeError:
            continue
    return "text"


def _parse_lora_syntax(text):
    """Parses a string containing LoRA syntax and extracts relevant data.

    This function takes a text string, identifies all LoRA tags within it, and
    extracts their display names, hashes, model strengths, and CLIP strengths.

    Args:
        text (str): The string containing LoRA syntax.

    Returns:
        tuple: A tuple of four lists: display names, hashes, model strengths,
               and CLIP strengths.
    """
    display_names: list[str] = []
    hashes: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    raw_names, ms_list, cs_list = parse_lora_syntax(text)
    if not raw_names:
        return display_names, hashes, model_strengths, clip_strengths
    resolved_names = resolve_lora_display_names(raw_names)
    filtered_names: list[str] = []
    filtered_hashes: list[str] = []
    filtered_model_strengths: list[float] = []
    filtered_clip_strengths: list[float] = []
    for raw, disp, ms_val, cs_val in zip(raw_names, resolved_names, ms_list, cs_list):
        if raw is None:
            continue
        filtered_names.append(disp)
        filtered_hashes.append(calc_lora_hash(raw, []))
        filtered_model_strengths.append(ms_val)
        filtered_clip_strengths.append(cs_val)
    return filtered_names, filtered_hashes, filtered_model_strengths, filtered_clip_strengths


def _coerce_float(value):
    try:
        if value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            return float(stripped)
    except Exception:
        return None
    return None


def _flatten_singleton(value):
    while isinstance(value, list | tuple) and len(value) == 1:
        value = value[0]
    return value


def _parse_stack_entries_from_value(value):
    entries: list[tuple[str | None, float | None, float | None]] = []
    value = _flatten_singleton(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except Exception:
                return []
            return _parse_stack_entries_from_value(parsed)
        return []
    if isinstance(value, dict):
        name = value.get("name") or value.get("model")
        if name is not None and any(k in value for k in ("strength", "clipStrength", "clip_strength")):
            ms = value.get("strength") or value.get("model_strength") or value.get("weight")
            cs = value.get("clipStrength") or value.get("clip_strength") or ms
            entries.append((name, _coerce_float(ms), _coerce_float(cs)))
            return entries
        for candidate in value.values():
            entries.extend(_parse_stack_entries_from_value(candidate))
        return entries
    if isinstance(value, list | tuple):
        if value and all(isinstance(item, list | tuple | dict) for item in value):
            for item in value:
                entries.extend(_parse_stack_entries_from_value(item))
            return entries
        if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
            token = value[0].replace(":", "")
            if token.isdigit():
                return []
        if value:
            name = value[0]
            ms = value[1] if len(value) > 1 else None
            cs = value[2] if len(value) > 2 else ms
            entries.append((name, _coerce_float(ms), _coerce_float(cs)))
        return entries
    return entries


def _build_result_from_entries(raw_entries):
    filtered = [(name, ms, cs if cs is not None else ms) for name, ms, cs in raw_entries if name]
    if not filtered:
        return None
    raw_names = [entry[0] for entry in filtered]
    resolved_names = resolve_lora_display_names(raw_names)
    names: list[str] = []
    hashes: list[str] = []
    model_strengths: list[float] = []
    clip_strengths: list[float] = []
    for raw, disp, (name, ms, cs) in zip(raw_names, resolved_names, filtered):
        try:
            names.append(disp)
            hashes.append(calc_lora_hash(raw, []))
            ms_val = ms if ms is not None else 1.0
            cs_val = cs if cs is not None else ms_val
            model_strengths.append(ms_val)
            clip_strengths.append(cs_val)
        except Exception:
            continue
    if not names:
        return None
    return {
        "names": names,
        "hashes": hashes,
        "model_strengths": model_strengths,
        "clip_strengths": clip_strengths,
    }


def _extract_structured_entries(batch: dict) -> tuple[str | None, tuple[tuple[str | None, float | None, float | None], ...]]:
    """Return the first stack-like field that yields concrete entries."""

    for field in _STACK_FIELD_CANDIDATES:
        if field not in batch:
            continue
        entries = _parse_stack_entries_from_value(batch[field])
        if entries:
            return field, tuple(entries)
    return None, ()


def _build_result_from_text(text: str | None):
    if not text:
        return None
    names, hashes, model_strengths, clip_strengths = _parse_lora_syntax(text)
    if not names:
        return None
    return {
        "names": names,
        "hashes": hashes,
        "model_strengths": model_strengths,
        "clip_strengths": clip_strengths,
    }


def _merge_lora_results(primary, extra):
    if not primary and not extra:
        return {
            "names": [],
            "hashes": [],
            "model_strengths": [],
            "clip_strengths": [],
        }
    if primary and not extra:
        return primary
    if extra and not primary:
        return extra
    names = list(primary["names"])
    hashes = list(primary["hashes"])
    model_strengths = list(primary["model_strengths"])
    clip_strengths = list(primary["clip_strengths"])
    seen = {str(name).lower() for name in names if name}
    for idx, name in enumerate(extra["names"]):
        if not name:
            continue
        key = str(name).lower()
        if key in seen:
            continue
        names.append(name)
        hashes.append(extra["hashes"][idx])
        model_strengths.append(extra["model_strengths"][idx])
        clip_strengths.append(extra["clip_strengths"][idx])
        seen.add(key)
    return {
        "names": names,
        "hashes": hashes,
        "model_strengths": model_strengths,
        "clip_strengths": clip_strengths,
    }


def _get_lora_data_from_node(node_id, input_data):
    """Extracts LoRA data from a node's input, utilizing a cache.

    This function orchestrates the process of selecting the correct text field,
    parsing the LoRA syntax from it, and caching the result. If the same node
    is processed with identical text input, the cached data is returned.

    Args:
        node_id (int): The ID of the node.
        input_data (dict): The input data for the node.

    Returns:
        dict: A dictionary containing the parsed LoRA data (names, hashes, etc.).
    """
    global _NODE_DATA_CACHE

    batch = input_data[0] if input_data and input_data[0] else None
    stack_field = None
    stack_payload: tuple[tuple[str | None, float | None, float | None], ...] = ()
    if isinstance(batch, dict):
        stack_field, stack_payload = _extract_structured_entries(batch)
    structured_result = _build_result_from_entries(list(stack_payload)) if stack_payload else None

    text_field = None
    text_to_parse = None
    if input_data and input_data[0]:
        field_choice = _select_text_field(input_data)
        candidate = input_data[0].get(field_choice, "")
        coerced = coerce_first(candidate)
        if coerced:
            text_field = field_choice
            text_to_parse = coerced
    text_result = _build_result_from_text(text_to_parse)

    cache_signature = (stack_field, stack_payload, text_field, text_to_parse)
    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get("signature") == cache_signature:
        return cached["data"]

    result = _merge_lora_results(structured_result, text_result)
    _NODE_DATA_CACHE[node_id] = {
        "signature": cache_signature,
        "data": result,
    }
    return result


# Selectors (note: *args[-1] is input_data structure from capture pipeline)
def get_lora_model_names(node_id, *args):
    """Selector to get LoRA model names from a LoraManager node."""
    return _get_lora_data_from_node(node_id, args[-1])["names"]


def get_lora_model_hashes(node_id, *args):
    """Selector to get LoRA model hashes from a LoraManager node."""
    return _get_lora_data_from_node(node_id, args[-1])["hashes"]


def get_lora_model_strengths(node_id, *args):
    """Selector to get LoRA model strengths from a LoraManager node."""
    return _get_lora_data_from_node(node_id, args[-1])["model_strengths"]


def get_lora_clip_strengths(node_id, *args):
    """Selector to get LoRA CLIP strengths from a LoraManager node."""
    return _get_lora_data_from_node(node_id, args[-1])["clip_strengths"]


# Legacy selector (kept for backward compatibility) returns model strengths
def get_lora_strengths(node_id, *args):
    """Legacy selector for LoRA strengths, returning model strengths."""
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
