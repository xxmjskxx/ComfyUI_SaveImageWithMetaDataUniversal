"""
Reference examples for user-generated metadata capture rules.

READ ME FIRST
- This file is NOT imported by the loader at runtime. It is provided only as a reference.
- Copy the bits you need into your actual user rules file:
        saveimage_unimeta/defs/ext/generated_user_rules.py
    or manage it via the UI nodes shown in the README.
- Keep your file small and focused on nodes you actually use.

Schema overview (matches the real generated_user_rules.py)
- KNOWN: dict[str, callable] mapping stable names to callables used by rules.
- CAPTURE_FIELD_LIST: dict[str, dict[MetaField, RuleSpec]]
- SAMPLERS: dict[str, dict[str, str]] mapping semantic roles (e.g., "positive"/"negative")
    to the actual input socket names for sampler-like nodes.

RuleSpec keys supported by the capture engine:
- "field_name": single input name to read (e.g., "ckpt_name").
- "fields": list of input names to read uniformly.
- "prefix": dynamic expansion for inputs with numeric suffixes (e.g., "clip_name1", "clip_name2").
- "selector": callable to derive/transform a value before formatting.
- "validate": predicate callable; if it returns False the field is skipped.
- "format": callable to post-process raw values (e.g., compute hashes).
- "value": constant literal to inject when not available from inputs.

Recommended approach
1) Run the Metadata Rule Scanner to generate a baseline generated_user_rules.py.
2) Use these examples to refine or extend capture for special nodes.
3) Save an image and review the parameter string to validate your changes.
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
from .efficiency_nodes import (
    get_lora_model_name_stack,
    get_lora_model_hash_stack,
    get_lora_strength_model_stack,
    get_lora_strength_clip_stack,
)

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

# This file intentionally defines example registries with a distinct suffix and is never imported.
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
