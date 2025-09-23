import json
import logging

from ..defs.formatters import (
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
from ..defs.meta import MetaField
from ..defs.validators import is_negative_prompt, is_positive_prompt

# Logging setup
logger = logging.getLogger(__name__)

# --- Lookup Tables for Deserialization ---
# This table maps function names from the JSON to actual callable Python functions.
FUNCTIONS = {
    "calc_model_hash": calc_model_hash,
    "calc_vae_hash": calc_vae_hash,
    "calc_lora_hash": calc_lora_hash,
    "calc_unet_hash": calc_unet_hash,
    "convert_skip_clip": convert_skip_clip,
    "get_scaled_width": get_scaled_width,
    "get_scaled_height": get_scaled_height,
    "extract_embedding_names": extract_embedding_names,
    "extract_embedding_hashes": extract_embedding_hashes,
    "is_positive_prompt": is_positive_prompt,
    "is_negative_prompt": is_negative_prompt,
}

# This table maps enum names from the JSON to the actual MetaField enum members.
ENUMS = {f.name: f for f in MetaField}

# --- Global warning toggle ---
WARNINGS_ENABLED = False  # <--- flip this to False to silence warnings


def log_warning(msg: str):
    if WARNINGS_ENABLED:
        logger.warning("[Metadata Loader] %s", msg)


# --- Recursive fixer with validation ---
def restore_values(obj):
    """
    Recursively traverses a dictionary or list loaded from JSON and restores
    the string representations of enums and functions back to their proper
    Python objects. Logs warnings if unknown names are encountered (non-fatal).
    """
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            # Restore the key if it's an enum name
            if isinstance(k, str) and k in ENUMS:
                k = ENUMS[k]
            elif isinstance(k, str) and k not in ENUMS:
                log_warning(f"Unknown enum key '{k}' in captures file.")

            # Try enum for key (by int value)
            elif isinstance(k, int) and k in MetaField._value2member_map_:
                k = MetaField(k)
            elif isinstance(k, int):
                log_warning(f"Unknown enum int '{k}' in captures file.")

            # Recurse into the value
            new_dict[k] = restore_values(v)
        return new_dict

    elif isinstance(obj, list):
        return [restore_values(i) for i in obj]

    elif isinstance(obj, str):
        # Restore function names
        if obj in FUNCTIONS:
            return FUNCTIONS[obj]
        elif obj.endswith("()") and obj[:-2] in FUNCTIONS:
            # allow "func()" shorthand
            return FUNCTIONS[obj[:-2]]
        elif obj in ENUMS:  # allow enums as values too
            return ENUMS[obj]
        else:
            # Unknown string → log warning but keep string
            if obj not in ("", None):
                log_warning(f"Unknown function or enum value '{obj}' in captures file.")
            return obj

    elif isinstance(obj, int) and obj in MetaField._value2member_map_:
        return MetaField(obj)

    return obj


# --- Pretty-printer (optional, for debugging) ---
def format_config(obj, indent=0):
    pad = "    " * indent
    if isinstance(obj, dict):
        lines = ["{"]
        for k, v in obj.items():
            if isinstance(k, MetaField):
                key_str = f"{k.__class__.__name__}.{k.name}"
            else:
                key_str = f'"{k}"' if isinstance(k, str) else repr(k)

            val_str = format_config(v, indent + 1)
            lines.append(f"{pad}    {key_str}: {val_str},")
        lines.append(pad + "}")
        return "\n".join(lines)

    elif isinstance(obj, list):
        return "[ " + ", ".join(format_config(v, indent + 1) for v in obj) + " ]"

    elif callable(obj):
        return obj.__name__

    elif isinstance(obj, MetaField):
        return f"{obj.__class__.__name__}.{obj.name}"

    elif isinstance(obj, str):
        return f'"{obj}"'

    else:
        return repr(obj)


# --- Main function with validation ---
def deserialize_input(json_path):
    with open(json_path) as f:
        raw = json.load(f)
    # Restore JSON into real Python objects (enums/functions) and return the dict
    deserialized = restore_values(raw)

    if not isinstance(deserialized, dict):
        # Helpful debug hint: pretty-print what we did parse
        pretty = format_config(deserialized) if deserialized is not None else "<none>"
        raise ValueError(
            "[Metadata Loader] Captures file must deserialize to a dict at top level."
            f" Parsed type: {type(deserialized).__name__}. Content: {pretty}"
        )

    return deserialized
