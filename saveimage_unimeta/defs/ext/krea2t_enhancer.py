"""Provides metadata definitions for the ComfyUI-Krea2T-Enhancer LoRA loaders.

Source: https://github.com/capitan01R/ComfyUI-Krea2T-Enhancer

Both loaders take the same ``lora_name`` / ``strength_model`` inputs as the core
``LoraLoaderModelOnly``, so they reuse its field mapping. The validator skips a
loader that the node itself bypasses (``enabled`` off or ``strength_model`` 0),
so a disabled LoRA is not written into the metadata.
"""
# https://github.com/capitan01R/ComfyUI-Krea2T-Enhancer
from ..formatters import calc_lora_hash
from ..meta import MetaField


def _first(value):
    return value[0] if isinstance(value, list) and value else value


def is_lora_applied(node_id, obj, prompt, extra_data, outputs, input_data):
    """Return False when the loader bypasses its LoRA (mirrors the nodes' own checks)."""
    try:
        inputs = input_data[0]
        if _first(inputs.get("enabled", True)) is False:
            return False
        return float(_first(inputs.get("strength_model", 1.0))) != 0
    except (IndexError, KeyError, TypeError, ValueError, AttributeError):
        return True


_MODEL_ONLY_LORA_RULE = {
    MetaField.LORA_MODEL_NAME: {"field_name": "lora_name", "validate": is_lora_applied},
    MetaField.LORA_MODEL_HASH: {"field_name": "lora_name", "format": calc_lora_hash, "validate": is_lora_applied},
    MetaField.LORA_STRENGTH_MODEL: {"field_name": "strength_model", "validate": is_lora_applied},
}

CAPTURE_FIELD_LIST = {
    "Krea2TCharacterLoraImageOnly": _MODEL_ONLY_LORA_RULE,
    "Krea2SelectiveLoraLoaderModelOnlyProjection": _MODEL_ONLY_LORA_RULE,
}
