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

from ..formatters import calc_lora_hash, calc_model_hash, convert_skip_clip, calc_vae_hash
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


def _normalize_connection_target(value):
    """Return the upstream node id referenced by a connection field."""

    if isinstance(value, list | tuple):  # noqa: UP038 - explicit modern union syntax
        if not value:
            return None
        value = value[0]
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    if not text or text.lower() == "none":
        return None
    return text


def _collect_stack_from_connection(node_inputs, prompt, outputs, key="lora_stack"):
    """Resolve a connected LoRA stack by inspecting upstream node outputs."""

    if not isinstance(node_inputs, dict):
        return []
    target = _normalize_connection_target(node_inputs.get(key))
    if not target:
        return []
    stack = _stack_from_outputs(target, outputs)
    if stack is None:
        upstream = prompt.get(target)
        if upstream:
            pseudo_input = [upstream.get("inputs", {})]
            stack = collect_lora_stack(pseudo_input)
    return stack or []


def _first_input_value(input_data, field_name):
    """Extract the first value for ``field_name`` from ``get_input_data`` output."""

    if not field_name or not input_data:
        return None
    try:
        value = input_data[0].get(field_name)
    except Exception:
        return None
    if isinstance(value, list | tuple):  # noqa: UP038
        return value[0] if value else None
    return value


def _normalize_lora_name(name):
    if name is None:
        return None
    if isinstance(name, list | tuple):  # noqa: UP038
        if not name:
            return None
        name = name[0]
    try:
        text = str(name).strip()
    except Exception:
        return None
    if not text or text.lower() == "none":
        return None
    return text


def _build_loader_lora_entries(
    node_id,
    prompt,
    outputs,
    input_data,
    inline_spec=None,
    stack_key="lora_stack",
):
    """Collect LoRA tuples (name, model_strength, clip_strength) for loader nodes."""

    entries: list[tuple[str, float | None, float | None]] = []
    if inline_spec:
        inline_name = _normalize_lora_name(_first_input_value(input_data, inline_spec.get("name")))
        if inline_name:
            sm = _first_input_value(input_data, inline_spec.get("strength_model"))
            sc = _first_input_value(input_data, inline_spec.get("strength_clip"))
            if sc is None:
                sc = sm
            entries.append((inline_name, sm, sc))
    node_inputs = (prompt.get(node_id) or {}).get("inputs", {})
    entries.extend(_collect_stack_from_connection(node_inputs, prompt, outputs, key=stack_key))
    return entries


def _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=True):
    inline_spec = None
    if inline:
        inline_spec = {
            "name": "lora_name",
            "strength_model": "lora_model_strength",
            "strength_clip": "lora_clip_strength",
        }
    return _build_loader_lora_entries(
        node_id,
        prompt,
        outputs,
        input_data,
        inline_spec=inline_spec,
        stack_key="lora_stack",
    )


def get_eff_loader_lora_model_names(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=True)
    return [entry[0] for entry in entries]


def get_eff_loader_lora_model_hashes(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=True)
    return [calc_lora_hash(entry[0], input_data) for entry in entries]


def get_eff_loader_lora_strength_model(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=True)
    return [entry[1] for entry in entries]


def get_eff_loader_lora_strength_clip(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=True)
    return [entry[2] for entry in entries]


def get_eff_loader_sdxl_lora_model_names(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=False)
    return [entry[0] for entry in entries]


def get_eff_loader_sdxl_lora_model_hashes(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=False)
    return [calc_lora_hash(entry[0], input_data) for entry in entries]


def get_eff_loader_sdxl_lora_strength_model(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=False)
    return [entry[1] for entry in entries]


def get_eff_loader_sdxl_lora_strength_clip(node_id, obj, prompt, extra_data, outputs, input_data):
    entries = _gather_eff_loader_entries(node_id, prompt, outputs, input_data, inline=False)
    return [entry[2] for entry in entries]


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
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "negative",
        },
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
        MetaField.LORA_MODEL_NAME: {"selector": get_eff_loader_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_eff_loader_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_eff_loader_lora_strength_model},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_eff_loader_lora_strength_clip},
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
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
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "negative",
        },
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
        MetaField.LORA_MODEL_NAME: {"selector": get_eff_loader_sdxl_lora_model_names},
        MetaField.LORA_MODEL_HASH: {"selector": get_eff_loader_sdxl_lora_model_hashes},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_eff_loader_sdxl_lora_strength_model},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_eff_loader_sdxl_lora_strength_clip},
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
