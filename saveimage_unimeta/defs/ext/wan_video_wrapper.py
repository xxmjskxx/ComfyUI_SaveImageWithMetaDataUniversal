"""Capture rules for ComfyUI-WanVideoWrapper.

Ref: https://github.com/kijai/ComfyUI-WanVideoWrapper

Coverage summary:
- Model/UNet: `WanVideoModelLoader` (supports up to two models; capture primary and
    secondary when present).
- VAE: `WanVideoVAELoader` and `WanVideoTinyVAELoader` capture VAE name and VAE hash.
- Extra model selectors: `WanVideoVACEModelSelect`, `WanVideoExtraModelSelect` capture
    model name and UNet hash.
- LoRA: `WanVideoLoraSelect`, `WanVideoLoraSelectByName`, `WanVideoLoraSelectMulti`
    capture model names, hashes, and model strengths.
- CLIP encoders: `LoadWanVideoT5TextEncoder` and `LoadWanVideoClipTextEncoder` capture
    CLIP model name.
- Prompts: `WanVideoTextEncode`, `WanVideoTextEncodeCached`, `WanVideoTextEncodeSingle`
    capture positive/negative or single prompt as appropriate.
"""

import logging

from ..validators import is_negative_prompt, is_positive_prompt
from ..formatters import calc_lora_hash, calc_vae_hash, calc_unet_hash
from ..meta import MetaField

logger = logging.getLogger(__name__)
logger.debug("[Meta DBG] Wan Video Wrapper extension definitions loaded.")


CAPTURE_FIELD_LIST = {
    "WanVideoModelLoader": {
        # Capture primary and optional secondary model fields if present.
        MetaField.MODEL_NAME: {"fields": ["model", "model_b", "model2"]},
        MetaField.MODEL_HASH: {"fields": ["model", "model_b", "model2"], "format": calc_unet_hash},
    },
    "WanVideoVAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },
    "WanVideoLoraSelect": {
        MetaField.LORA_MODEL_NAME: {"fields": ["lora", "merge_loras", "prev_lora"]},
        MetaField.LORA_MODEL_HASH: {"fields": ["lora", "merge_loras", "prev_lora"], "format": calc_lora_hash},
    },
    "WanVideoLoraSelectByName": {
        MetaField.LORA_MODEL_NAME: {"fields": ["lora_name"]},
        MetaField.LORA_MODEL_HASH: {"fields": ["lora_name"], "format": calc_lora_hash},
        MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength"},
    },
    "WanVideoTinyVAELoader": {
        MetaField.VAE_NAME: {"field_name": "vae_name"},
        MetaField.VAE_HASH: {"field_name": "vae_name", "format": calc_vae_hash},
    },
    "WanVideoVACEModelSelect": {
        MetaField.MODEL_NAME: {"field_name": "vace_model"},
        MetaField.MODEL_HASH: {"field_name": "vace_model", "format": calc_unet_hash},
    },
    "WanVideoExtraModelSelect": {
        MetaField.MODEL_NAME: {"field_name": "extra_model"},
        MetaField.MODEL_HASH: {"field_name": "extra_model", "format": calc_unet_hash},
    },
    "WanVideoLoraSelectMulti": {
        MetaField.LORA_MODEL_NAME: {"fields": ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4"]},
        MetaField.LORA_MODEL_HASH: {
            "fields": ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4"],
            "format": calc_lora_hash,
        },
        MetaField.LORA_STRENGTH_MODEL: {
            "fields": ["strength_0", "strength_1", "strength_2", "strength_3", "strength_4"],
        },
    },
    "LoadWanVideoT5TextEncoder": {
        MetaField.CLIP_MODEL_NAME: {"field_name": "clip_name"},
    },
    "LoadWanVideoClipTextEncoder": {
        MetaField.CLIP_MODEL_NAME: {"field_name": "clip_name"},
    },
    "WanVideoTextEncode": {
        MetaField.POSITIVE_PROMPT: {"field_name": "positive_prompt", "validate": is_positive_prompt},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative_prompt", "validate": is_negative_prompt},
    },
    "WanVideoTextEncodeCached": {
        MetaField.POSITIVE_PROMPT: {"field_name": "positive_prompt", "validate": is_positive_prompt},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative_prompt", "validate": is_negative_prompt},
        MetaField.CLIP_MODEL_NAME: {"field_name": "model_name"},
    },
    "WanVideoTextEncodeSingle": {
        MetaField.POSITIVE_PROMPT: {"field_name": "prompt", "validate": is_positive_prompt},
        MetaField.NEGATIVE_PROMPT: {"field_name": "prompt", "validate": is_negative_prompt},
    },
    # Sampler: captures steps, cfg, shift, seed, denoise; splits combined scheduler field
    # which may carry both sampler and scheduler information.
    # Wan2.2 MoE support: also captures start_step and end_step for segment-aware rendering.
    "WanVideo Sampler": {
        MetaField.SEED: {"field_name": "seed"},
        MetaField.STEPS: {"field_name": "steps"},
        MetaField.CFG: {"field_name": "cfg"},
        MetaField.SHIFT: {"field_name": "shift"},
        MetaField.DENOISE: {"field_name": "denoise"},
        MetaField.START_STEP: {"field_name": "start_step"},
        MetaField.END_STEP: {"field_name": "end_step"},
        MetaField.SAMPLER_NAME: {
            "selector": (
                lambda node_id, obj, prompt, extra_data, outputs, input_data: _wan_sampler_from_scheduler(input_data)
            )
        },
        MetaField.SCHEDULER: {
            "selector": (
                lambda node_id, obj, prompt, extra_data, outputs, input_data: _wan_scheduler_from_scheduler(input_data)
            )
        },
    },
}


def _wan_get_input(input_data, key):
    try:
        return input_data[0][key][0]
    except Exception:
        return None


def _split_sampler_scheduler(value):
    """Best-effort extraction of (sampler, scheduler) from a combined value.

    Accepts dict-like (keys: sampler/scheduler), tuple/list (first, second),
    or string forms such as "Euler a (Karras)", "Euler a / Karras", or "Euler, Karras".
    Returns a tuple (sampler: str, scheduler: str), defaulting to empty strings when unknown.
    """
    sampler = ""
    scheduler = ""
    try:
        # Dict-like
        if isinstance(value, dict):
            sampler = str(value.get("sampler") or value.get("sampler_name") or value.get("name") or "")
            scheduler = str(value.get("scheduler") or value.get("schedule") or "")
            return sampler, scheduler
        # Tuple/list-like
        if isinstance(value, list | tuple):
            if len(value) >= 1 and value[0] is not None:
                sampler = str(value[0])
            if len(value) >= 2 and value[1] is not None:
                scheduler = str(value[1])
            return sampler, scheduler
        # String-like
        if value is None:
            return sampler, scheduler
        s = str(value)
        # Pattern: "Sampler (Scheduler)"
        if "(" in s and ")" in s and s.index("(") < s.index(")"):
            pre = s[: s.index("(")].strip()
            inside = s[s.index("(") + 1 : s.index(")")].strip()
            return pre, inside
        # Pattern: "Sampler / Scheduler" or "Sampler | Scheduler" or "Sampler - Scheduler"
        for sep in [" / ", " | ", " - "]:
            if sep in s:
                parts = [p.strip() for p in s.split(sep, 1)]
                if len(parts) == 2:
                    return parts[0], parts[1]
        # Fallback: comma separated
        if "," in s:
            parts = [p.strip() for p in s.split(",", 1)]
            if len(parts) == 2:
                return parts[0], parts[1]
        # Unknown: treat as scheduler-only text
        return "", s
    except Exception:
        return sampler, scheduler


def _wan_sampler_from_scheduler(input_data):
    val = _wan_get_input(input_data, "scheduler")
    sampler, _ = _split_sampler_scheduler(val)
    return sampler


def _wan_scheduler_from_scheduler(input_data):
    val = _wan_get_input(input_data, "scheduler")
    _, scheduler = _split_sampler_scheduler(val)
    return scheduler
