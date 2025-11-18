"""Defines the baseline metadata capture rules for various ComfyUI nodes.

This module contains the `CAPTURE_FIELD_LIST`, a dictionary that maps node
class types to a set of rules for capturing metadata from their inputs. Each
rule specifies which `MetaField` to populate, which input field to read from,
and optional formatting or validation functions to apply.

These baseline rules provide out-of-the-box support for a wide range of common
nodes, and they can be extended or overridden by user-defined rules.
"""
from .formatters import (
    calc_lora_hash,
    calc_model_hash,
    calc_unet_hash,
    calc_vae_hash,
    convert_skip_clip,
    extract_embedding_hashes,
    extract_embedding_names,
    get_scaled_height,
    get_scaled_width,
)
from .meta import MetaField
from .validators import is_negative_prompt, is_positive_prompt


def _passthrough(value, *_):
    """A passthrough formatter that returns the input value unchanged (helper for pre-hashed stub inputs).

    This function is used as a formatter in capture rules where the input
    value is already in the desired format and does not require any
    transformation. It is particularly useful for test nodes that provide
    pre-hashed or pre-formatted values.

    Args:
        value: The input value.
        *_ A catch-all for any additional arguments.

    Returns:
        The input value, unchanged.
    """
    return value


# import os
# import json

CAPTURE_FIELD_LIST = {
    "CheckpointLoaderSimple": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": calc_model_hash},
    },
    "CLIPSetLastLayer": {
        MetaField.CLIP_SKIP: {
            "field_name": "stop_at_clip_layer",
            "format": convert_skip_clip,
        },
    },
    "VAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },
    # CLIP loaders: capture one or more clip_name* inputs where present
    "CLIPLoader": {
        # Collects inputs starting with 'clip_name', e.g. 'clip_name', 'clip_name1', 'clip_name2'...
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "DualCLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "TripleClipLoader": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "QuadrupleClipLoader": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "ClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "DualClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "TripleClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "QuadrupleClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    "EmptyLatentImage": {
        MetaField.IMAGE_WIDTH: {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },
    "CLIPTextEncode": {
        MetaField.POSITIVE_PROMPT: {
            "field_name": "text",
            "validate": is_positive_prompt,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "text",
            "validate": is_negative_prompt,
        },
        MetaField.EMBEDDING_NAME: {
            "field_name": "text",
            "format": extract_embedding_names,
        },
        MetaField.EMBEDDING_HASH: {
            "field_name": "text",
            "format": extract_embedding_hashes,
        },
    },
    "KSampler": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "KSamplerAdvanced": {
        MetaField.SEED: {"field_name": "noise_seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "SamplerCustomAdvanced": {
        MetaField.SEED: {"field_name": "noise_seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    "LatentUpscale": {
        MetaField.IMAGE_WIDTH: {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },
    "LatentUpscaleBy": {
        MetaField.IMAGE_WIDTH: {"field_name": "scale_by", "format": get_scaled_width},
        MetaField.IMAGE_HEIGHT: {
            "field_name": "scale_by",
            "format": get_scaled_height,
        },
    },
    "LoraLoader": {
        MetaField.LORA_MODEL_NAME: {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH: {
            "field_name": "lora_name",
            "format": calc_lora_hash,
        },
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model"},
        MetaField.LORA_STRENGTH_CLIP: {"field_name": "strength_clip"},
    },
    "LoraLoaderModelOnly": {
        MetaField.LORA_MODEL_NAME: {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH: {
            "field_name": "lora_name",
            "format": calc_lora_hash,
        },
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model"},
        MetaField.LORA_STRENGTH_CLIP: {"value": 0},
    },
    # Flux - https://comfyanonymous.github.io/ComfyUI_examples/flux/
    "UNETLoader": {
        MetaField.MODEL_NAME: {"field_name": "unet_name"},
        MetaField.MODEL_HASH: {"field_name": "unet_name", "format": calc_unet_hash},
    },
    "RandomNoise": {
        MetaField.SEED: {"field_name": "noise_seed"},
    },
    "KSamplerSelect": {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
    },
    "CLIPTextEncodeFlux": {
        MetaField.T5_PROMPT: {
            "field_name": "t5xxl",
            "validate": is_positive_prompt,
        },
        MetaField.CLIP_PROMPT: {
            "field_name": "clip_l",
            "validate": is_positive_prompt,
        },
        MetaField.GUIDANCE: {
            "field_name": "guidance",
        },
    },
    # Fallback for other flux encoders that expose similar fields without validator
    # "CLIPTextEncodeFluxAdvanced": {
    #     MetaField.T5_PROMPT: {"field_name": "t5xxl"},
    #     MetaField.CLIP_PROMPT: {"field_name": "clip_l"},
    # },
    "FluxGuidance": {
        MetaField.GUIDANCE: {"field_name": "guidance"},
    },
    "BasicScheduler": {
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
        MetaField.DENOISE: {"field_name": "denoise"},
    },
    "Load Diffusion Model": {
        MetaField.WEIGHT_DTYPE: {"field_name": "weight_dtype"},
        MetaField.MODEL_NAME: {"field_name": "unet_name"},
        MetaField.MODEL_HASH: {"field_name": "unet_name", "format": calc_unet_hash},
    },
    "ModelSamplingFlux": {
        MetaField.MAX_SHIFT: {"field_name": "max_shift"},
        MetaField.BASE_SHIFT: {"field_name": "base_shift"},
    },
    "TextEncodeQwenImageEdit": {
        MetaField.POSITIVE_PROMPT: {
            "field_name": "prompt",
            "validate": is_positive_prompt,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "prompt",
            "validate": is_negative_prompt,
        },
    },
    "MetadataTestSampler": {
        MetaField.POSITIVE_PROMPT: {
            "field_name": "positive_prompt",
            "inline_lora_candidate": True,
        },
        MetaField.NEGATIVE_PROMPT: {
            "field_name": "negative_prompt",
            "inline_lora_candidate": True,
        },
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
        MetaField.GUIDANCE: {"field_name": "guidance"},
        MetaField.MODEL_NAME: {"field_name": "model_name"},
        MetaField.MODEL_HASH: {"field_name": "model_hash", "format": _passthrough},
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_hash", "format": _passthrough},
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
        MetaField.IMAGE_WIDTH: {"field_name": "width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "height"},
    },
}


# "DualCLIPLoader": {
#     MetaField.CLIP_1: {"field_name": "clip_1"},
#     MetaField.CLIP_2: {"field_name": "clip_2"},
# },
#     "DualCLIPLoader": {
#     MetaField.CLIP_MODEL_NAME: {"field_name": "clip_name1"},
#     MetaField.CLIP_MODEL_NAME: {"field_name": "clip_name2"},
# },
