"""Provides metadata definitions for the ComfyUI-ZImagePowerNodes custom nodes.

This module contains configurations for integrating the `ComfyUI-ZImagePowerNodes`
pack, available at: https://github.com/martin-rizzo/ComfyUI-ZImagePowerNodes

It defines the necessary mappings for the Z-Sampler Turbo and Z-Sampler Turbo
(Advanced) sampler nodes, allowing the metadata save node to correctly trace
conditioning inputs and capture sampling parameters from workflows using these
nodes.

Attributes:
    SAMPLERS (dict): A dictionary mapping Z-Sampler nodes to their conditioning
                     inputs. These samplers only have a positive conditioning
                     input (no negative).
    CAPTURE_FIELD_LIST (dict): A dictionary that specifies how to capture metadata
                               fields from the Z-Sampler nodes. These samplers
                               expose seed, steps, and denoise but not cfg,
                               sampler_name, or scheduler (those are hardcoded
                               internally).
"""
# https://github.com/martin-rizzo/ComfyUI-ZImagePowerNodes
from ..meta import MetaField

SAMPLERS = {
    "ZSamplerTurbo //ZImagePowerNodes": {
        "positive": "positive",
    },
    "ZSamplerTurboAdvanced //ZImagePowerNodes": {
        "positive": "positive",
    },
}

CAPTURE_FIELD_LIST = {
    "ZSamplerTurbo //ZImagePowerNodes": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.DENOISE: {"field_name": "denoise"},
    },
    "ZSamplerTurboAdvanced //ZImagePowerNodes": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.DENOISE: {"field_name": "denoise"},
    },
}
