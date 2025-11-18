"""Provides metadata definitions for the efficiency-nodes-comfyui custom nodes.

This module is designed to integrate with the `efficiency-nodes-comfyui` custom
node pack, available at: https://github.com/jags111/efficiency-nodes-comfyui

It includes configurations for various nodes from this pack, such as loaders,
samplers, and the `LoRA Stacker`. A key feature of this module is its ability
to parse LoRA stack data, which can be provided either through the node's inputs
or its outputs. This dual approach ensures compatibility with different versions
and configurations of the Efficiency Nodes.

The module defines custom selector functions to handle the extraction of LoRA
names, hashes, and strengths, accommodating both simple and advanced modes of
the `LoRA Stacker`.

Attributes:
    SAMPLERS (dict): A mapping of samplers from the Efficiency Nodes pack to their
                     conditioning inputs.
    CAPTURE_FIELD_LIST (dict): A dictionary that defines metadata capture rules for
                               various nodes in the pack, covering model loading,
                               sampling parameters, and LoRA stack management.
"""
# https://github.com/jags111/efficiency-nodes-comfyui
import logging
from ..formatters import calc_lora_hash, calc_model_hash, convert_skip_clip
from ..meta import MetaField
from ..selectors import collect_lora_stack, select_stack_by_prefix, _aligned_strengths_for_prefix


logger = logging.getLogger(__name__)
# Guard to avoid repeating the same deprecation message on every call.
_LORA_STACK_SHIM_WARNED = False


def _stack_from_outputs(node_id, outputs):
    """Parses and normalizes LoRA stack data from a node's outputs.

    This function attempts to find and interpret LoRA stack information that is
    passed through the outputs of a node (e.g., `LoRA Stacker`). It searches for
    keys like "lora_stack" and normalizes the data into a consistent format of
    `(name, model_strength, clip_strength)` tuples.

    Args:
        node_id (int): The ID of the node being processed.
        outputs (dict): The outputs dictionary from the workflow execution.

    Returns:
        list | None: A list of normalized LoRA stack tuples, or None if no valid
                      stack data could be found in the outputs.
    """
    if not isinstance(outputs, dict):
        return None

    raw = outputs.get(node_id)
    if raw is None:
        return None

    candidates = []
    if isinstance(raw, dict):
        for key in ("lora_stack", "LORA_STACK", 0, "0"):
            if key in raw:
                candidates.append(raw[key])
        if not candidates:
            candidates.extend(raw.values())
    elif isinstance(raw, list | tuple):
        candidates.extend(raw)
    else:
        candidates.append(raw)

    for candidate in candidates:
        stack = candidate
        if isinstance(stack, tuple) and len(stack) == 1 and isinstance(stack[0], list):
            stack = stack[0]
        if not isinstance(stack, list):
            continue
        if not stack:
            return []

        normalized = []
        saw_tuple = False
        for entry in stack:
            if not isinstance(entry, list | tuple):
                continue
            saw_tuple = True
            if not entry:
                continue
            name = entry[0]
            name_str = "" if name is None else str(name).strip()
            if name_str == "" or name_str.lower() == "none":
                continue
            model_strength = entry[1] if len(entry) > 1 else None
            clip_strength = entry[2] if len(entry) > 2 else model_strength
            normalized.append((name, model_strength, clip_strength))
        if saw_tuple:
            return normalized

    return None


def _is_advanced_mode(input_data) -> bool:
    """Detects if a 'LoRA Stacker' node is in 'advanced' mode.

    This function checks the input data of a node to determine if it is configured
    to use the 'advanced' input mode, which affects how LoRA strengths are specified.

    Args:
        input_data (dict): The input data for the node.

    Returns:
        bool: True if the node is in 'advanced' mode, False otherwise.
    """
    try:
        return (
            isinstance(input_data, list)
            and input_data
            and isinstance(input_data[0], dict)
            and isinstance(input_data[0].get("input_mode"), list)
            and input_data[0]["input_mode"]
            and input_data[0]["input_mode"][0] == "advanced"
        )
    except Exception:
        return False


def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector to get LoRA model names from a 'LoRA Stacker' node.

    This function first attempts to get the LoRA stack from the node's outputs.
    If that fails, it falls back to parsing the stack from the node's inputs.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of LoRA model names.
    """
    stack = _stack_from_outputs(node_id, outputs)
    if stack is None:
        stack = collect_lora_stack(input_data)
    if stack:
        return [entry[0] for entry in stack]
    return select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector to get LoRA model hashes from a 'LoRA Stacker' node.

    This function retrieves the LoRA names and then computes a hash for each one.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of hashes for the LoRA models.
    """
    stack = _stack_from_outputs(node_id, outputs)
    if stack is None:
        stack = collect_lora_stack(input_data)
    if stack:
        names = [entry[0] for entry in stack]
    else:
        names = select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")
    return [calc_lora_hash(model_name, input_data) for model_name in names]


def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector to get LoRA model strengths from a 'LoRA Stacker' node.

    This function handles both simple and advanced modes for specifying strengths.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of model strengths for the LoRAs.
    """
    stack = _stack_from_outputs(node_id, outputs)
    if stack is None:
        stack = collect_lora_stack(input_data)
    if stack:
        return [entry[1] for entry in stack]
    if _is_advanced_mode(input_data):
        return _aligned_strengths_for_prefix(input_data, "model_str")
    return _aligned_strengths_for_prefix(input_data, "lora_wt")


def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector to get LoRA CLIP strengths from a 'LoRA Stacker' node.

    This function handles both simple and advanced modes for specifying strengths.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of CLIP strengths for the LoRAs.
    """
    stack = _stack_from_outputs(node_id, outputs)
    if stack is None:
        stack = collect_lora_stack(input_data)
    if stack:
        return [entry[2] for entry in stack]
    if _is_advanced_mode(input_data):
        return _aligned_strengths_for_prefix(input_data, "clip_str")
    return _aligned_strengths_for_prefix(input_data, "lora_wt")


def get_lora_data_stack(input_data, attribute):
    """Provides a deprecated shim for backward compatibility with older rules.

    This function was used in older versions to extract LoRA data. It is now
    superseded by `select_stack_by_prefix`, which offers more flexibility. A
    warning is logged when this shim is used.

    Args:
        input_data (dict): The input data for the node.
        attribute (str): The attribute to extract.

    Returns:
        list: A list of the extracted attribute values.
    """
    global _LORA_STACK_SHIM_WARNED
    if not _LORA_STACK_SHIM_WARNED:
        logger.warning("get_lora_data_stack is deprecated; use select_stack_by_prefix(..., counter_key='lora_count').")
        _LORA_STACK_SHIM_WARNED = True
    # Backward compatibility shim; prefer select_stack_by_prefix above.
    return select_stack_by_prefix(input_data, attribute, counter_key="lora_count")


SAMPLERS = {
    "KSampler (Efficient)": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSampler Adv. (Efficient)": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSampler SDXL (Eff.)": {
        "positive": "positive",
        "negative": "negative",
    },
}

CAPTURE_FIELD_LIST = {
    "Efficient Loader": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": calc_model_hash},
        MetaField.CLIP_SKIP: {"field_name": "clip_skip", "format": convert_skip_clip},
        MetaField.POSITIVE_PROMPT: {
            "field_name": "positive",
            "inline_lora_candidate": True,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "negative",
            "inline_lora_candidate": True,
        },
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
    },
    "Eff. Loader SDXL": {
        MetaField.MODEL_NAME: {"field_name": "base_ckpt_name"},
        MetaField.MODEL_HASH: {
            "field_name": "base_ckpt_name",
            "format": calc_model_hash,
        },
        MetaField.CLIP_SKIP: {
            "field_name": "base_clip_skip",
            "format": convert_skip_clip,
        },
        MetaField.POSITIVE_PROMPT: {
            "field_name": "positive",
            "inline_lora_candidate": True,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "negative",
            "inline_lora_candidate": True,
        },
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
    },
    "KSampler (Efficient)": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "KSampler Adv. (Efficient)": {
        MetaField.SEED: {"field_name": "noise_seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "KSampler SDXL (Eff.)": {
        MetaField.SEED: {"field_name": "noise_seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "LoRA Stacker": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_name_stack},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash_stack},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strength_model_stack},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strength_clip_stack},
    },
}
