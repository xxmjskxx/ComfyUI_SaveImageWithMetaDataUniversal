"""Provides metadata definitions for EreNodes' Prompt Lora Loader.

The selectors mirror the syntax, filename resolution, prefix-first apply order,
and optional model/CLIP behavior of ComfyUI-EreNodes:
https://github.com/Erehr/ComfyUI-EreNodes

A resolved LoRA is considered only once, even if its first occurrence is disabled.
Missing files and tags passed through without a model are excluded. Runtime file
loading errors cannot be inferred from the node's inputs.

Attributes:
    CAPTURE_FIELD_LIST (dict): LoRA capture rules for ErePromptLoraLoader.
"""

import logging
import os
import re

import folder_paths

from ...utils.lora import coerce_first
from ..formatters import calc_lora_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] EreNodes metadata definition file loaded.")

_NODE_DATA_CACHE: dict = {}
_TEXT_FIELDS = ("prefix", "text")
_LORA_EXTENSIONS = (".safetensors", ".pt", ".ckpt", ".lora")
# EreNodes also accepts bare names, negative strengths, and malformed numeric
# strings (with a float-conversion fallback). Do not use the shared strict parser.
_LORA_REGEX = re.compile(r"<lora:([^:>]+)(?::(-?[0-9.]+))?(?::(-?[0-9.]+))?>")


def _has_input(batch, field):
    """Check whether a resolved optional input contains an object.

    Args:
        batch (dict): ComfyUI's resolved input values.
        field (str): Optional input name.

    Returns:
        bool: Whether the first input value is present and not None.
    """
    value = batch.get(field)
    if isinstance(value, list | tuple):
        value = value[0] if value else None
    return value is not None


def _resolve_lora_name(name, available):
    """Resolve a tag to a registered filename using EreNodes' matching order.

    Args:
        name (str): Raw LoRA tag name.
        available (tuple[str, ...]): Registered LoRA filenames in ComfyUI order.

    Returns:
        str | None: Registered filename, or None when no file matches.
    """
    wanted = {name.replace("\\", "/").lower(), os.path.splitext(name)[0].replace("\\", "/").lower()}
    # Full relative paths take precedence over basename-only matches.
    for entry in available:
        flat = entry.replace("\\", "/").lower()
        if flat in wanted or os.path.splitext(flat)[0] in wanted:
            return entry
    for entry in available:
        base = os.path.basename(entry.replace("\\", "/")).lower()
        if base in wanted or os.path.splitext(base)[0] in wanted:
            return entry
    return None


def _strength(value, fallback):
    """Convert an EreNodes strength token, falling back if it is malformed.

    Args:
        value (str): Captured numeric token, possibly empty.
        fallback (float): Default strength.

    Returns:
        float: Parsed strength or the fallback.
    """
    try:
        return float(value)
    except ValueError:
        return fallback


def _collect_entries(batch, available):
    """Collect resolved names and effective strengths in EreNodes apply order.

    Args:
        batch (dict): Resolved text, prefix, model, and CLIP input values.
        available (tuple[str, ...]): Registered LoRA filenames.

    Returns:
        list[tuple[str, float, float]]: Names and model/CLIP strengths.
    """
    if not _has_input(batch, "model"):
        return []
    has_clip = _has_input(batch, "clip")
    entries = []
    seen = set()
    for field in _TEXT_FIELDS:
        for raw_name, model_token, clip_token in _LORA_REGEX.findall(coerce_first(batch.get(field, ""))):
            name = _resolve_lora_name(raw_name, available)
            if name is None:
                # EreNodes normalizes unresolved names and supplies the default
                # extension before its apply step tries resolution again.
                name = os.path.normpath(raw_name)
                if not name.lower().endswith(_LORA_EXTENSIONS):
                    name += ".safetensors"
            if name in seen:
                continue
            # EreNodes marks the parsed row name seen before checking strengths.
            seen.add(name)
            ms = _strength(model_token, 1.0)
            cs = _strength(clip_token, ms) if has_clip else 0.0
            if ms == 0 and cs == 0:
                continue
            resolved_name = _resolve_lora_name(name, available)
            if resolved_name is not None:
                entries.append((resolved_name, ms, cs))
    return entries


def _get_lora_data_from_node(node_id, input_data):
    """Parse and cache LoRA data using all inputs that affect capture.

    Args:
        node_id (str | int): Node ID.
        input_data (tuple): ComfyUI input data; the first item holds input values.

    Returns:
        dict: Aligned names, hashes, and model/CLIP strengths.
    """
    batch = input_data[0] if input_data and input_data[0] else {}
    try:
        available = tuple(folder_paths.get_filename_list("loras"))
    except (AttributeError, OSError):
        available = ()
    snapshot = (
        *(coerce_first(batch.get(field, "")) for field in _TEXT_FIELDS),
        _has_input(batch, "model"),
        _has_input(batch, "clip"),
        available,
    )
    cached = _NODE_DATA_CACHE.get(node_id)
    if cached and cached.get("snapshot") == snapshot:
        return cached["data"]

    entries = _collect_entries(batch, available)
    # Keep registered relative filenames for both display and hashing so files
    # with the same basename in different folders retain their identity.
    names = [name for name, _ms, _cs in entries]
    result = {
        "names": names,
        "hashes": [calc_lora_hash(name, input_data) for name in names],
        "model_strengths": [ms for _name, ms, _cs in entries],
        "clip_strengths": [cs for _name, _ms, cs in entries],
    }
    _NODE_DATA_CACHE[node_id] = {"snapshot": snapshot, "data": result}
    return result


# *args[-1] is the input_data structure from the capture pipeline.
def get_lora_model_names(node_id, *args):
    """Select LoRA filenames.

    Args:
        node_id (str | int): Node ID.
        *args: Capture context ending with resolved input data.

    Returns:
        list[str]: Registered LoRA filenames.
    """
    return _get_lora_data_from_node(node_id, args[-1])["names"]


def get_lora_model_hashes(node_id, *args):
    """Select LoRA hashes.

    Args:
        node_id (str | int): Node ID.
        *args: Capture context ending with resolved input data.

    Returns:
        list[str]: LoRA hashes in apply order.
    """
    return _get_lora_data_from_node(node_id, args[-1])["hashes"]


def get_lora_model_strengths(node_id, *args):
    """Select LoRA model strengths.

    Args:
        node_id (str | int): Node ID.
        *args: Capture context ending with resolved input data.

    Returns:
        list[float]: Model strengths in apply order.
    """
    return _get_lora_data_from_node(node_id, args[-1])["model_strengths"]


def get_lora_clip_strengths(node_id, *args):
    """Select effective LoRA CLIP strengths.

    Args:
        node_id (str | int): Node ID.
        *args: Capture context ending with resolved input data.

    Returns:
        list[float]: CLIP strengths in apply order.
    """
    return _get_lora_data_from_node(node_id, args[-1])["clip_strengths"]


CAPTURE_FIELD_LIST = {
    "ErePromptLoraLoader": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_model_strengths},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_clip_strengths},
    },
}
