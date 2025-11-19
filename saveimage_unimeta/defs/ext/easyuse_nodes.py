"""Provides metadata definitions for the ComfyUI-Easy-Use custom node pack.

This module is designed to integrate with the `ComfyUI-Easy-Use` custom nodes,
which can be found at: https://github.com/yolain/ComfyUI-Easy-Use

It provides comprehensive metadata capture configurations for a wide range of nodes
from this pack, including loaders, samplers, and the `loraStack` node. The module
defines custom selector functions to handle the specific data structures of these
nodes, particularly for extracting LoRA information.

Attributes:
    SAMPLERS (dict): A mapping of samplers from the Easy-Use pack to their
                     conditioning inputs.
    CAPTURE_FIELD_LIST (dict): A dictionary that defines metadata capture rules for
                               various nodes in the Easy-Use pack. It covers model
                               loading, sampling parameters, and LoRA stack management.
"""
# https://github.com/yolain/ComfyUI-Easy-Use
import re

from ..formatters import calc_lora_hash, calc_model_hash, convert_skip_clip
from ..meta import MetaField


def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to get LoRA model names from an 'easy loraStack' node.

    This function checks if the loraStack is toggled on. If it is, it retrieves
    the names of the active LoRA models.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of active LoRA model names, or an empty list if the stack is off.
    """
    toggled_on = input_data[0]["toggle"][0]

    if toggled_on:
        return get_lora_data_stack(input_data, r"lora_\d_name")
    else:
        return []


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to get LoRA model hashes from an 'easy loraStack' node.

    This function retrieves the names of the active LoRAs and computes a hash for each.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of hashes for the active LoRA models.
    """
    return [calc_lora_hash(model_name, input_data) for model_name in get_lora_data_stack(input_data, r"lora_\d_name")]


def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to get LoRA model strengths from an 'easy loraStack' node.

    This function handles both 'simple' and 'advanced' modes of the loraStack,
    retrieving the appropriate model strength values.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of model strengths for the active LoRAs.
    """
    if input_data[0]["mode"][0] == "advanced":
        return get_lora_data_stack(input_data, r"lora_\d_model_strength")
    return get_lora_data_stack(input_data, r"lora_\d_strength")


def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to get LoRA CLIP strengths from an 'easy loraStack' node.

    This function handles both 'simple' and 'advanced' modes of the loraStack,
    retrieving the appropriate CLIP strength values.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of CLIP strengths for the active LoRAs.
    """
    if input_data[0]["mode"][0] == "advanced":
        return get_lora_data_stack(input_data, r"lora_\d_clip_strength")
    return get_lora_data_stack(input_data, r"lora_\d_strength")


def get_lora_data_stack(input_data, attribute):
    """Helper function to extract data from an 'easy loraStack' node.

    This function iterates through the inputs of the loraStack, matching them
    against a regex pattern for the desired attribute (e.g., name, strength).
    It collects the values for the active LoRAs, up to the number specified
    in the 'num_loras' input.

    Args:
        input_data (dict): The input data for the node.
        attribute (str): A regex pattern for the attribute to extract.

    Returns:
        list: A list of the extracted attribute values.
    """
    lora_count = input_data[0]["num_loras"][0]
    return [v[0] for k, v in input_data[0].items() if re.search(attribute, k) is not None and v[0] != "None"][
        :lora_count
    ]


def get_lora_model_hash(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to get a LoRA model hash from a loader node.

    This function is used for loader nodes that have a single LoRA slot.
    It retrieves the LoRA name and computes its hash.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        str: The hash of the LoRA model, or an empty string if no LoRA is selected.
    """
    if input_data[0]["lora_name"][0] != "None":
        return calc_lora_hash(input_data[0]["lora_name"][0], input_data)
    else:
        return ""


SAMPLERS = {
    "easy fullkSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "easy preSampling": {},
    "easy preSamplingAdvanced": {},
    "easy preSamplingCascade": {},
    "easy preSamplingCustom": {},
    "easy preSamplingDynamicCFG": {},
    "easy preSamplingLayerDiffusion": {},
    "easy preSamplingNoiseIn": {},
    "easy preSamplingSdTurbo": {},
}


CAPTURE_FIELD_LIST = {
    "easy fullLoader": {
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
        MetaField.LORA_MODEL_NAME: {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "lora_model_strength"},
        MetaField.LORA_STRENGTH_CLIP: {"field_name": "lora_clip_strength"},
    },
    "easy comfyLoader": {
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
        MetaField.LORA_MODEL_NAME: {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "lora_model_strength"},
        MetaField.LORA_STRENGTH_CLIP: {"field_name": "lora_clip_strength"},
    },
    "easy fullkSampler": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSampling": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingAdvanced": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingCascade": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingCustom": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingDynamicCFG": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingLayerDiffusion": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingNoiseIn": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy preSamplingSdTurbo": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "easy loraStack": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_name_stack},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash_stack},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strength_model_stack},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strength_clip_stack},
    },
}
