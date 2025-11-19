"""Provides metadata definitions for the XTNodes custom node pack.

This module is designed to integrate with the `LoraLoaderWithPreviews` node from the
`ComfyUI-EasyCivitai-XTNodes` custom node pack, which can be found at:
https://github.com/X-T-E-R/ComfyUI-EasyCivitai-XTNodes

It defines selector functions to extract data from the node's inputs, specifically
targeting active LoRA models and their corresponding strengths. The data is retrieved
by iterating through input keys that are prefixed with "lora_".

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary that maps the `LoraLoaderWithPreviews`
                               node to its metadata capture configurations. It uses
                               custom selector functions to extract LoRA names,
                               hashes, and strengths.
"""
# LoraLoaderWithPreviews - https://github.com/X-T-E-R/ComfyUI-EasyCivitai-XTNodes
from ..meta import MetaField
from ..formatters import calc_lora_hash

import logging


logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] rgthree extension definitions loaded.")


def get_lora_model_name(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to retrieve the names of active LoRA models.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of active LoRA model names.
    """
    return get_lora_data(input_data, "lora")


def get_lora_model_hash(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to retrieve the hashes of active LoRA models.

    This function first retrieves the names of the active LoRAs and then calculates
    a hash for each one.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of calculated hashes for the active LoRA models.
    """
    return [calc_lora_hash(model_name, input_data) for model_name in get_lora_data(input_data, "lora")]


def get_lora_strength(node_id, obj, prompt, extra_data, outputs, input_data):
    """Selector function to retrieve the strengths of active LoRA models.

    Args:
        node_id: The ID of the node.
        obj: The node object.
        prompt: The workflow prompt.
        extra_data: Additional data associated with the workflow.
        outputs: The node's output data.
        input_data: The node's input data.

    Returns:
        list: A list of strengths for the active LoRA models.
    """
    return get_lora_data(input_data, "strength")


def get_lora_data(input_data, attribute):
    """Helper function to extract specific attributes from active LoRA inputs.

    This function iterates through the input data of the node, identifying inputs
    that correspond to LoRAs (i.e., keys starting with "lora_"). It filters for
    LoRAs that are currently active ("on" is True) and extracts the specified
    attribute (e.g., "lora" for the name, "strength" for the strength).

    Args:
        input_data (dict): The input data for the node.
        attribute (str): The name of the attribute to extract from the LoRA data.

    Returns:
        list: A list of the extracted attribute values from all active LoRAs.
    """
    return [v[0][attribute] for k, v in input_data[0].items() if k.startswith("lora_") and v[0]["on"]]


CAPTURE_FIELD_LIST = {
    "LoraLoaderWithPreviews": {
        MetaField.LORA_MODEL_NAME: {"selector": get_lora_model_name},
        MetaField.LORA_MODEL_HASH: {"selector": get_lora_model_hash},
        MetaField.LORA_STRENGTH_MODEL: {"selector": get_lora_strength},
        MetaField.LORA_STRENGTH_CLIP: {"selector": get_lora_strength},
    },
}
