"""
Reference examples for user-generated metadata capture rules.

READ ME FIRST
- This file is NOT imported by the loader at runtime. It is provided only as a reference.
- Copy snippets you want into your actual user rules file:
    saveimage_unimeta/defs/ext/generated_user_rules.py
  or generate/edit it via the UI nodes:
    - "Show generated_user_rules.py" (viewer)
    - "Save generated_user_rules.py" (validator + saver)
- Keep your own file minimal and focused on the nodes you actually use.

Rule Structure
- Rules extend two registries:
    CAPTURE_FIELD_LIST: dict[str, dict[MetaField, RuleSpec]]
    SAMPLERS: dict[str, dict[str, str]] (rarely needed for basic usage)
- RuleSpec keys (common):
    { "field_name": <input socket name>, "prefix": <input name prefix>,
      "value": <constant>, "format": <callable>, "validate": <callable> }
- Use MetaField entries from saveimage_unimeta.defs.meta.MetaField to target specific metadata fields.
- Use only keys your nodes actually expose. The scanner can help you discover them.

Recommended approach
1) Run the Metadata Rule Scanner to generate a baseline into generated_user_rules.py.
2) Use these examples to refine or extend capture for special nodes.
3) Keep changes small and test by saving an image and checking the parameter string.

"""
from typing import Any
from collections.abc import Mapping

# Import the MetaField enum for readability
from ..meta import MetaField

# Optional: import formatters used in examples
from ..formatters import (
    calc_lora_hash,
    calc_model_hash,
    calc_unet_hash,
    calc_vae_hash,
)

# This file intentionally defines example registries with a distinct suffix and is never imported.
# Copy specific entries into your live generated_user_rules.py.

CAPTURE_FIELD_LIST_EXAMPLES: dict[str, Mapping[MetaField, Mapping[str, Any]]] = {
    # Example 1: Basic model loader using a single input name
    "CheckpointLoaderSimple": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": calc_model_hash},
    },

    # Example 2: CLIP loaders capturing multiple inputs by prefix (clip_name, clip_name1, clip_name2...)
    "CLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {"prefix": "clip_name"},
    },

    # Example 3: VAE loader with hash calculation
    "VAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },

    # Example 4: Sampler core fields
    "KSampler": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.SCHEDULER: {"field_name": "scheduler"},
    },

    # Example 5: LoRA loader including strengths and hash
    "LoraLoader": {
        MetaField.LORA_MODEL_NAME: {"field_name": "lora_name"},
        MetaField.LORA_MODEL_HASH: {"field_name": "lora_name", "format": calc_lora_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model"},
        MetaField.LORA_STRENGTH_CLIP: {"field_name": "strength_clip"},
    },

    # Example 6: Inline constant value (when node doesn’t expose it directly)
    "SomeCustomNode": {
        MetaField.DENOISE: {"value": 1.0},
    },

    # Example 7: UNet (Flux) loaders
    "UNETLoader": {
        MetaField.MODEL_NAME: {"field_name": "unet_name"},
        MetaField.MODEL_HASH: {"field_name": "unet_name", "format": calc_unet_hash},
    },
}

# Optional sampler name mapping examples (advanced)
# Use only when you need to normalize or alias sampler names for downstream tools.
SAMPLERS_EXAMPLES: dict[str, Mapping[str, str]] = {
    # "sampler_key": {"upstream_value": "display_value"}
    # "KSampler": {"euler": "Euler", "euler_ancestral": "Euler a"},
}

# End of examples. Copy pieces into your real generated_user_rules.py.
