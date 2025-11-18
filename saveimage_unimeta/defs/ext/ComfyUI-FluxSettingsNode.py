"""Provides metadata definitions for the ComfyUI-FluxSettingsNode custom node.

This module contains configurations for integrating the `ComfyUI-FluxSettingsNode`,
which can be found at: https://github.com/Light-x02/ComfyUI-FluxSettingsNode

It defines the necessary mappings for samplers and metadata capture fields, allowing
the `saveimage_unimeta` node to correctly interpret and record data from workflows
that utilize this custom node.

Attributes:
    SAMPLERS (dict): A dictionary that maps the `FluxSettingsNode` to its positive and
                     negative conditioning inputs. This enables the system to trace
                     and identify the prompts used in the generation process.
    CAPTURE_FIELD_LIST (dict): A dictionary that specifies how to capture metadata
                               fields from the `FluxSettingsNode`. Each entry maps a
                               standard metadata field (e.g., `MetaField.MODEL_NAME`)
                               to the corresponding field name within the node's
                               widget values.
"""
# https://github.com/Light-x02/ComfyUI-FluxSettingsNode
from ..meta import MetaField

SAMPLERS = {
    "FluxSettingsNode": {
        "positive": "conditioning.positive",
        "negative": "conditioning.negative",
    },
}


CAPTURE_FIELD_LIST = {
    "FluxSettingsNode": {
        MetaField.MODEL_NAME: {"field_name": "model"},
        MetaField.GUIDANCE: {"field_name": "guidance"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.SEED: {"field_name": "noise_seed"},
        MetaField.POSITIVE_PROMPT: {
            "field_name": "conditioning.positive",
            "inline_lora_candidate": True,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "conditioning.negative",
            "inline_lora_candidate": True,
        },
    },
}
