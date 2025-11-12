# https://github.com/jags111/efficiency-nodes-comfyui
import logging
from ..formatters import calc_lora_hash, calc_model_hash, convert_skip_clip
from ..meta import MetaField
from ..selectors import collect_lora_stack, select_stack_by_prefix


logger = logging.getLogger(__name__)
# Guard to avoid repeating the same deprecation message on every call.
_LORA_STACK_SHIM_WARNED = False


def _stack_from_outputs(node_id, outputs):
    """Return normalized `(name, model_strength, clip_strength)` tuples from node outputs."""
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


def _is_advanced_mode(input_data) -> bool:
    """Safely detect Efficiency Nodes 'advanced' mode from input_data."""
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


def _get_unified_stack(node_id, outputs, input_data):
    """Get unified LoRA stack, trying outputs first, then input_data.

    Returns:
        list[tuple]: List of (name, model_strength, clip_strength) tuples, or empty list.
    """
    stack = _stack_from_outputs(node_id, outputs)
    if stack is None:
        stack = collect_lora_stack(input_data)
    return stack if stack else []


def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _get_unified_stack(node_id, outputs, input_data)
    return [entry[0] for entry in stack]


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _get_unified_stack(node_id, outputs, input_data)
    names = [entry[0] for entry in stack]
    return [calc_lora_hash(model_name, input_data) for model_name in names]


def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _get_unified_stack(node_id, outputs, input_data)
    return [entry[1] for entry in stack]


def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _get_unified_stack(node_id, outputs, input_data)
    return [entry[2] for entry in stack]


def get_lora_data_stack(input_data, attribute):
    """Deprecated shim for older rules using get_lora_data_stack.

    Prefer select_stack_by_prefix(input_data, attr, counter_key="lora_count").
    Scheduled for removal no earlier than v1.3.0 (and at least 60 days after
    a v1.2.0 release), pending downstream adoption.
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

def _get_efficient_loader_lora_name(node_id, obj, prompt, extra_data, outputs, input_data):
    """Get lora name from Efficient Loader, filtering out None values."""
    if not input_data or not isinstance(input_data, list) or not input_data[0]:
        return []
    lora_name = input_data[0].get("lora_name", [None])[0]
    if lora_name is None or str(lora_name).strip() == "" or str(lora_name).strip().lower() == "none":
        return []
    return [lora_name]


def _get_efficient_loader_lora_hash(node_id, obj, prompt, extra_data, outputs, input_data):
    """Get lora hash from Efficient Loader, filtering out None values."""
    names = _get_efficient_loader_lora_name(node_id, obj, prompt, extra_data, outputs, input_data)
    return [calc_lora_hash(name, input_data) for name in names]


def _get_efficient_loader_lora_model_strength(node_id, obj, prompt, extra_data, outputs, input_data):
    """Get lora model strength from Efficient Loader, filtering out None values."""
    names = _get_efficient_loader_lora_name(node_id, obj, prompt, extra_data, outputs, input_data)
    if not names:
        return []
    if not input_data or not isinstance(input_data, list) or not input_data[0]:
        return []
    return [input_data[0].get("lora_wt", [None])[0]]


def _get_efficient_loader_lora_clip_strength(node_id, obj, prompt, extra_data, outputs, input_data):
    """Get lora clip strength from Efficient Loader, filtering out None values."""
    names = _get_efficient_loader_lora_name(node_id, obj, prompt, extra_data, outputs, input_data)
    if not names:
        return []
    if not input_data or not isinstance(input_data, list) or not input_data[0]:
        return []
    return [input_data[0].get("lora_wt", [None])[0]]


CAPTURE_FIELD_LIST = {
    "Efficient Loader": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": calc_model_hash},
        MetaField.CLIP_SKIP: {"field_name": "clip_skip", "format": convert_skip_clip},
        MetaField.POSITIVE_PROMPT: {"field_name": "positive"},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative"},
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
        MetaField.LORA_MODEL_NAME: {"selector": _get_efficient_loader_lora_name},
        MetaField.LORA_MODEL_HASH: {"selector": _get_efficient_loader_lora_hash},
        MetaField.LORA_STRENGTH_MODEL: {"selector": _get_efficient_loader_lora_model_strength},
        MetaField.LORA_STRENGTH_CLIP: {"selector": _get_efficient_loader_lora_clip_strength},
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
        MetaField.POSITIVE_PROMPT: {"field_name": "positive"},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative"},
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
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
