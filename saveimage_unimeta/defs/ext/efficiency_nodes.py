# https://github.com/jags111/efficiency-nodes-comfyui
from ..formatters import calc_lora_hash, calc_model_hash, convert_skip_clip
from ..meta import MetaField
from ..selectors import select_stack_by_prefix


def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    return select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")


def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    names = select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")
    return [calc_lora_hash(model_name, input_data) for model_name in names]


def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    if input_data[0]["input_mode"][0] == "advanced":
        return select_stack_by_prefix(input_data, "model_str", counter_key="lora_count")
    return select_stack_by_prefix(input_data, "lora_wt", counter_key="lora_count")


def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    if input_data[0]["input_mode"][0] == "advanced":
        return select_stack_by_prefix(input_data, "clip_str", counter_key="lora_count")
    return select_stack_by_prefix(input_data, "lora_wt", counter_key="lora_count")


def get_lora_data_stack(input_data, attribute):
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

CAPTURE_FIELD_LIST = {
    "Efficient Loader": {
        MetaField.MODEL_NAME: {"field_name": "ckpt_name"},
        MetaField.MODEL_HASH: {"field_name": "ckpt_name", "format": calc_model_hash},
        MetaField.CLIP_SKIP: {"field_name": "clip_skip", "format": convert_skip_clip},
        MetaField.POSITIVE_PROMPT: {"field_name": "positive"},
        MetaField.NEGATIVE_PROMPT: {"field_name": "negative"},
        MetaField.IMAGE_WIDTH: {"field_name": "empty_latent_width"},
        MetaField.IMAGE_HEIGHT: {"field_name": "empty_latent_height"},
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
