"""Provides a comprehensive set of reference examples for user-generated metadata capture rules.

This module serves as a detailed guide and a source of copy-pasteable examples for users who wish
to customize their metadata capture by creating or editing the `generated_user_rules.py` file.

**Important:** This file itself is not loaded at runtime. Its purpose is purely educational.
Users are expected to transfer the relevant snippets to their live `generated_user_rules.py` file.

The module is structured to mirror the actual user rules file, with sections for:
- `KNOWN`: A dictionary for registering callable functions (formatters, validators, selectors)
  that can be referenced in the capture rules.
- `CAPTURE_FIELD_LIST_EXAMPLES`: A dictionary containing a variety of rule examples for different
  types of nodes, demonstrating various features of the rule engine such as simple field mapping,
  use of formatters, validators, prefix-based matching, and injection of constant values.
- `SAMPLERS_EXAMPLES`: A dictionary illustrating how to map the conceptual roles of "positive"
  and "negative" prompts to the actual input names of custom sampler nodes.

The examples cover a range of common use cases, from basic model and VAE loaders to more complex
scenarios involving LoRA stacks and custom samplers. Each example is commented to explain the
purpose and mechanics of the rule.

The recommended workflow for users is to first generate a baseline `generated_user_rules.py` using
the built-in Metadata Rule Scanner, and then to use the examples in this file to refine and
extend the generated rules to suit their specific needs and custom nodes.
"""

from typing import Any
from collections.abc import Mapping

# Import the MetaField enum for readability
from ..meta import MetaField

# Import functions used in examples, then register them in KNOWN just like the real file
from ..formatters import (
    calc_model_hash,
    calc_vae_hash,
    calc_lora_hash,
    calc_unet_hash,
)
from ..validators import (
    is_positive_prompt,
    is_negative_prompt,
)
from ..selectors import select_stack_by_prefix


# Self-contained LoRA stack helpers to mirror the generator output.
# These avoid importing from other extension modules.
def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    return select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    names = select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")
    return [calc_lora_hash(n, input_data) for n in names]


def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    # Advanced mode switches the source key to 'model_str' to match Efficiency Nodes behavior.
    try:
        if input_data[0].get("input_mode", [""])[0] == "advanced":
            return select_stack_by_prefix(input_data, "model_str", counter_key="lora_count")
    except Exception:
        pass  # Fall back to simple mode if advanced mode check fails
    return select_stack_by_prefix(input_data, "lora_wt", counter_key="lora_count")


def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    # Advanced mode uses 'clip_str' for clip strength.
    try:
        if input_data[0].get("input_mode", [""])[0] == "advanced":
            return select_stack_by_prefix(input_data, "clip_str", counter_key="lora_count")
    except Exception:
        pass  # Fall back to simple mode if advanced mode check fails
    return select_stack_by_prefix(input_data, "lora_wt", counter_key="lora_count")


# This mirrors the indirection used by generated_user_rules.py
KNOWN = {
    "calc_model_hash": calc_model_hash,
    "calc_vae_hash": calc_vae_hash,
    "calc_lora_hash": calc_lora_hash,
    "calc_unet_hash": calc_unet_hash,
    "is_positive_prompt": is_positive_prompt,
    "is_negative_prompt": is_negative_prompt,
    "get_lora_model_name_stack": get_lora_model_name_stack,
    "get_lora_model_hash_stack": get_lora_model_hash_stack,
    "get_lora_strength_model_stack": get_lora_strength_model_stack,
    "get_lora_strength_clip_stack": get_lora_strength_clip_stack,
}

# This file intentionally defines example registries with an '_EXAMPLES' suffix and is never imported.
# Copy specific entries into your live generated_user_rules.py.

CAPTURE_FIELD_LIST_EXAMPLES: dict[str, Mapping[MetaField, Mapping[str, Any]]] = {
    # Example 1: Basic model loader using a single input name
    "CheckpointLoaderSimple": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": KNOWN["calc_model_hash"]},
    },
    # Example 2: CLIP text encoders with validation for prompt roles
    "CLIPTextEncode": {
        MetaField.POSITIVE_PROMPT: {"field_name": "text", "validate": KNOWN["is_positive_prompt"]},
        MetaField.NEGATIVE_PROMPT: {"field_name": "text", "validate": KNOWN["is_negative_prompt"]},
    },
    # Example 3: CLIP loaders capturing multiple inputs by prefix (clip_name, clip_name1, clip_name2, ...)
    "CLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },
    # Example 4: VAE loader with hash calculation
    "VAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": KNOWN["calc_vae_hash"]},
    },
    # Example 5: Sampler core fields
    "KSampler": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },
    # Example 6: LoRA loader including strengths and hash
    "LoraLoader": {
        MetaField.LORA_MODEL_NAME: {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH: {"field_name": "lora_name", "format": KNOWN["calc_lora_hash"]},
        # You can either capture individual fields ...
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model"},
        MetaField.LORA_STRENGTH_CLIP: {"field_name": "strength_clip"},
        # ...or capture pairs uniformly with a list:
        # MetaField.LORA_STRENGTH_MODEL: {"fields": ["strength_clip", "strength_model"]},
        # MetaField.LORA_STRENGTH_CLIP: {"fields": ["strength_clip", "strength_model"]},
    },
    # Example 7: Inline constant value (when the node doesn’t expose it)
    "SomeCustomNode": {
        MetaField.DENOISE: {"value": 1.0},
    },
    # Example 8: UNet loaders
    "UNETLoader": {
        MetaField.MODEL_NAME: {"field_name": "unet_name"},
        MetaField.MODEL_HASH: {"field_name": "unet_name", "format": KNOWN["calc_unet_hash"]},
    },
}

# Sampler role mapping examples (advanced)
# Map semantic roles to the actual input socket names of sampler-like nodes.
SAMPLERS_EXAMPLES: dict[str, Mapping[str, str]] = {
    "KSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    # Example: a custom sampler whose "positive" input socket is called "cond"
    # "MyCustomSampler": {
    #     "positive": "cond",
    #     "negative": "uncond",
    # },
}

# End of examples. Copy pieces (including KNOWN entries you rely on) into your real generated_user_rules.py.
