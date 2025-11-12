from ..meta import MetaField
from ..formatters import (
    calc_model_hash, calc_vae_hash, calc_lora_hash, calc_unet_hash,
    convert_skip_clip, get_scaled_width, get_scaled_height,
    extract_embedding_names, extract_embedding_hashes
)
from ..validators import (
    is_positive_prompt, is_negative_prompt
)
from ..selectors import (
    select_stack_by_prefix,
    collect_lora_stack,
    select_lora_names,
    select_lora_model_strengths,
    select_lora_clip_strengths,
)

def _collect_lora_stack(input_data):
    stack = collect_lora_stack(input_data)
    if stack:
        return stack
    names = select_stack_by_prefix(input_data, 'lora_name', counter_key='lora_count')
    if not names:
        return []
    model_strengths = select_stack_by_prefix(input_data, 'model_str', counter_key='lora_count')
    if not model_strengths:
        model_strengths = select_stack_by_prefix(input_data, 'lora_wt', counter_key='lora_count')
    clip_strengths = select_stack_by_prefix(input_data, 'clip_str', counter_key='lora_count')
    if not clip_strengths:
        clip_strengths = select_stack_by_prefix(input_data, 'lora_wt', counter_key='lora_count')
    stack = []
    for idx, name in enumerate(names):
        model = model_strengths[idx] if idx < len(model_strengths) else None
        clip = clip_strengths[idx] if idx < len(clip_strengths) else model
        stack.append((name, model, clip))
    return stack

def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _collect_lora_stack(input_data)
    return [entry[0] for entry in stack]

def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _collect_lora_stack(input_data)
    return [calc_lora_hash(entry[0], input_data) for entry in stack]

def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _collect_lora_stack(input_data)
    return [entry[1] for entry in stack]

def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):
    stack = _collect_lora_stack(input_data)
    return [entry[2] for entry in stack]

KNOWN = {
    'calc_model_hash': calc_model_hash,
    'calc_vae_hash': calc_vae_hash,
    'calc_lora_hash': calc_lora_hash,
    'calc_unet_hash': calc_unet_hash,
    'convert_skip_clip': convert_skip_clip,
    'get_scaled_width': get_scaled_width,
    'get_scaled_height': get_scaled_height,
    'extract_embedding_names': extract_embedding_names,
    'extract_embedding_hashes': extract_embedding_hashes,
    'is_positive_prompt': is_positive_prompt,
    'is_negative_prompt': is_negative_prompt,
    'collect_lora_stack': collect_lora_stack,
    'select_lora_names': select_lora_names,
    'select_lora_model_strengths': select_lora_model_strengths,
    'select_lora_clip_strengths': select_lora_clip_strengths,
    'get_lora_model_name_stack': get_lora_model_name_stack,
    'get_lora_model_hash_stack': get_lora_model_hash_stack,
    'get_lora_strength_model_stack': get_lora_strength_model_stack,
    'get_lora_strength_clip_stack': get_lora_strength_clip_stack,
}

SAMPLERS = {
    "FL_KSamplerXYZPlot": {
        "positive": "positive",
        "negative": "negative"
    }
}

CAPTURE_FIELD_LIST = {
    "ACELoRALoader": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name", "lora_weight"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name", "lora_weight"]},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "lora_weight"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "lora_weight"},
    },
    "ACEModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "text_encoder_checkpoint", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "text_encoder_checkpoint"},
    },
    "ACEPlusLoader": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "AlignYourStepsScheduler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "Automatic CFG - Advanced": {
        MetaField.CFG: {'field_name': "latent_intensity_rescale_cfg"},
    },
    "Automatic CFG - Preset Loader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "BLIP Model Loader": {
        MetaField.MODEL_HASH: {'field_name': "vqa_model_id", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "vqa_model_id"},
    },
    "BNK_NoisyLatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "BNK_Unsampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "BasicScheduler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "BongSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "ByteDanceSeedreamNode": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
        MetaField.SEED: {'field_name': "seed"},
    },
    "CFGGuider": {
        MetaField.CFG: {'field_name': "cfg"},
    },
    "CLIP Positive-Negative (WLSH)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "positive_text", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "positive_text", 'validate': KNOWN["is_positive_prompt"]},
    },
    "CLIP Positive-Negative XL (WLSH)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "negative_g", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "positive_g", 'validate': KNOWN["is_positive_prompt"]},
    },
    "CLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {'field_name': "clip_name"},
    },
    "CLIPLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'field_name': "clip_name"},
    },
    "CLIPSeg Model Loader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "CR Apply LoRA Stack": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_stack", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_stack"},
    },
    "CR Cycle LoRAs": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_list", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_list"},
    },
    "CR Encode Scheduled Prompts": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "current_prompt", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "current_prompt", 'validate': KNOWN["is_positive_prompt"]},
    },
    "CR LoRA List": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name1", "lora_name2", "lora_name3", "lora_list"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name1", "lora_name2", "lora_name3", "lora_list"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_strength_1", "model_strength_1", "clip_strength_2", "model_strength_2", "clip_strength_3", "model_strength_3"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["clip_strength_1", "model_strength_1", "clip_strength_2", "model_strength_2", "clip_strength_3", "model_strength_3"]},
    },
    "CR LoRA Stack": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name_1", "lora_name_2", "lora_name_3", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name_1", "lora_name_2", "lora_name_3", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_weight_1", "model_weight_1", "clip_weight_2", "model_weight_2", "clip_weight_3", "model_weight_3"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["clip_weight_1", "model_weight_1", "clip_weight_2", "model_weight_2", "clip_weight_3", "model_weight_3"]},
    },
    "CR Load LoRA": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "CR Load Scheduled LoRAs": {
        MetaField.LORA_MODEL_HASH: {'fields': ["default_lora", "lora_list"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["default_lora", "lora_list"]},
    },
    "CR Load Scheduled Models": {
        MetaField.MODEL_HASH: {'field_name': "default_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "default_model"},
    },
    "CR Module Pipe Loader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "CR Random LoRA Stack": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name_1", "lora_name_2", "lora_name_3", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name_1", "lora_name_2", "lora_name_3", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_weight_1", "model_weight_1", "clip_weight_2", "model_weight_2", "clip_weight_3", "model_weight_3"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["clip_weight_1", "model_weight_1", "clip_weight_2", "model_weight_2", "clip_weight_3", "model_weight_3"]},
    },
    "CR Random Weight LoRA": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_weight", "weight_max", "weight_min"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["clip_weight", "weight_max", "weight_min"]},
    },
    "CR Seed": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "CR Select Model": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name3", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name3"},
    },
    "Cfg Literal (Image Saver)": {
        MetaField.CFG: {'field_name': "cfg"},
    },
    "CfgScheduleHookProvider": {
        MetaField.CFG: {'field_name': "target_cfg"},
    },
    "Checkpoint Loader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "Checkpoint Loader (Simple)": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "Checkpoint Loader w/Name (WLSH)": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "Checkpoint Loader with Name (Image Saver)": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "CheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "CheckpointLoaderKJ": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "CheckpointLoaderSimple": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "CheckpointLoaderSimpleShared //Inspire": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "CheckpointLoader|pysssss": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "ClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'field_name': "clip_name"},
    },
    "ClownModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "ClownOptions_SwapSampler_Beta": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
    },
    "ClownSampler": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SEED: {'field_name': "noise_seed_sde"},
        MetaField.STEPS: {'field_name': "implicit_steps"},
    },
    "ClownSamplerAdvanced": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SEED: {'field_name': "noise_seed_sde"},
        MetaField.STEPS: {'field_name': "implicit_steps"},
    },
    "ClownSamplerAdvanced_Beta": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SEED: {'field_name': "noise_seed_sde"},
        MetaField.STEPS: {'field_name': "implicit_substeps"},
    },
    "ClownSamplerSelector_Beta": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
    },
    "ClownSampler_Beta": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SEED: {'field_name': "seed"},
    },
    "ClownScheduler": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "total_steps"},
    },
    "ClownsharKSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "ClownsharKSamplerGuide": {
        MetaField.SCHEDULER: {'field_name': "guide_weight_scheduler"},
    },
    "ClownsharKSamplerGuides": {
        MetaField.SCHEDULER: {'field_name': "guide_weight_scheduler"},
    },
    "ClownsharKSamplerOptions": {
        MetaField.SEED: {'field_name': "noise_seed"},
    },
    "ClownsharKSampler_Beta": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "ClownsharkChainsampler_Beta": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.STEPS: {'field_name': "steps_to_run"},
    },
    "CosmosImageToVideoLatent": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "CosmosPredict2ImageToVideoLatent": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "CreateCFGScheduleFloatList": {
        MetaField.CFG: {'field_name': "cfg_scale_start"},
    },
    "CreateHookLora": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "CreateHookLoraModelOnly": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength_model"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength_model"},
    },
    "DetailDaemonSamplerNode": {
        MetaField.CFG: {'field_name': "cfg_scale_override"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "DiTBlockLoraLoader": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name", "opt_lora_path"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name", "opt_lora_path"]},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength_model"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength_model"},
    },
    "DiTCondLabelSelect": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "DiffControlNetLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "Diffusers Model Loader": {
        MetaField.MODEL_HASH: {'field_name': "model_path", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_path"},
    },
    "DiffusersLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_path", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_path"},
    },
    "DiffusionModelLoaderKJ": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "DiffusionModelSelector": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "DitCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "DownloadAndLoadCLIPSeg": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "DownloadAndLoadDepthCrafterModel": {
        MetaField.MODEL_HASH: {'field_name': "enable_model_cpu_offload", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "enable_model_cpu_offload"},
    },
    "DownloadAndLoadGIMMVFIModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "DownloadAndLoadSAM2Model": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "DownloadAndLoadWav2VecModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "DualCFGGuider": {
        MetaField.CFG: {'field_name': "cfg_conds"},
    },
    "DualCLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2"]},
    },
    "DualCLIPLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2"]},
    },
    "DualClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2"]},
    },
    "Eff. Loader SDXL": {
        MetaField.IMAGE_HEIGHT: {'field_name': "empty_latent_height"},
        MetaField.IMAGE_WIDTH: {'field_name': "empty_latent_width"},
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_stack", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_stack"},
        MetaField.MODEL_HASH: {'field_name': "base_ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "base_ckpt_name"},
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
    },
    "Efficient Loader": {
        MetaField.IMAGE_HEIGHT: {'field_name': "empty_latent_height"},
        MetaField.IMAGE_WIDTH: {'field_name': "empty_latent_width"},
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_clip_strength", "lora_model_strength", "lora_name", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_clip_strength", "lora_model_strength", "lora_name", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["lora_clip_strength", "lora_model_strength"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["lora_clip_strength", "lora_model_strength"]},
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
    },
    "Empty Latent by Size (WLSH)": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyChromaRadianceLatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyCosmosLatentVideo": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyDCAELatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyHunyuanImageLatent": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyHunyuanLatentVideo": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyLTXVLatentVideo": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyLatentHunyuan3Dv2": {
        MetaField.IMAGE_HEIGHT: {'field_name': "resolution"},
        MetaField.IMAGE_WIDTH: {'field_name': "resolution"},
    },
    "EmptyLatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyLatentImage64": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyLatentImageCustom": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptyLatentImageCustomPresets": {
        MetaField.IMAGE_HEIGHT: {'field_name': "dimensions"},
        MetaField.IMAGE_WIDTH: {'field_name': "dimensions"},
    },
    "EmptyLatentImagePresets": {
        MetaField.IMAGE_HEIGHT: {'field_name': "dimensions"},
        MetaField.IMAGE_WIDTH: {'field_name': "dimensions"},
    },
    "EmptyMochiLatentVideo": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptySD3LatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EmptySanaLatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "EnhancedLoadDiffusionModel": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "ExtraVAELoader": {
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
    },
    "FBGSampler": {
        MetaField.CFG: {'field_name': "cfg_scale"},
        MetaField.GUIDANCE: {'field_name': "max_guidance_scale"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_mode"},
    },
    "FL_API_Base64_ImageLoader": {
        MetaField.IMAGE_HEIGHT: {'field_name': "resize_height"},
        MetaField.IMAGE_WIDTH: {'field_name': "resize_width"},
    },
    "FL_Fal_Seedance_i2v": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "FL_Fal_Seedream_Edit": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "FL_FractalKSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "FL_HFHubModelUploader": {
        MetaField.MODEL_HASH: {'field_name': "model_file_path", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_file_path"},
    },
    "FL_HF_UploaderAbsolute": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_file", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_file"},
    },
    "FL_KSamplerXYZPlot": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "FL_KsamplerBasic": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "FL_KsamplerPlus": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "FL_KsamplerPlusV2": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "FL_KsamplerSettings": {
        MetaField.CFG: {'field_name': "Pass_1_CFG"},
        MetaField.DENOISE: {'field_name': "Pass_2_denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "Pass_2_steps"},
    },
    "FL_UnloadModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "FaceProcessorLoader": {
        MetaField.MODEL_HASH: {'field_name': "yolo_model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "yolo_model_name"},
    },
    "FantasyPortraitModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "FantasyTalkingModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "FlowEditSampler": {
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "refine_steps"},
    },
    "FluxDeGuidance": {
        MetaField.GUIDANCE: {'field_name': "guidance"},
    },
    "FluxForwardODESampler": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "FluxGuidance": {
        MetaField.GUIDANCE: {'field_name': "guidance"},
    },
    "FluxLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "FluxSampler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "FluxSamplerParams+": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "GGUFLoaderKJ": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "GITSScheduler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "GITSSchedulerFuncProvider": {
        MetaField.DENOISE: {'field_name': "denoise"},
    },
    "GemmaLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "GlobalSampler //Inspire": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "GroundingDinoModelLoader (segment anything)": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "HYDiTCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "HypernetworkLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "ImageOnlyCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "ImpactKSamplerAdvancedBasicPipe": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "ImpactKSamplerBasicPipe": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "ImpactSchedulerAdapter": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "ImpactWildcardEncode": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "populated_text", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "populated_text", 'validate': KNOWN["is_positive_prompt"]},
    },
    "InFluxModelSamplingPred": {
        MetaField.BASE_SHIFT: {'field_name': "base_shift"},
        MetaField.MAX_SHIFT: {'field_name': "max_shift"},
    },
    "Intrinsic_lora_sampling": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
    },
    "KRestartSamplerCustomNoise": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler (Efficient)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler (WAS)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler //Inspire": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler Adv. (Efficient)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler Config (rgthree)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps_total"},
    },
    "KSampler Cycle": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "cycle_denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSampler SDXL (Eff.)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerAdvanced": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerAdvanced (WLSH)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerAdvanced //Inspire": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerAdvancedPipe //Inspire": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerAdvancedProgress //Inspire": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerAdvancedProvider": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "KSamplerPipe //Inspire": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerProgress //Inspire": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerProvider": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerSelect": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
    },
    "KSamplerVariationsStochastic+": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerVariationsWithNoise+": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerWithNAG": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "KSamplerWithNAG (Advanced)": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "LatentCrop": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "LatentNoiseBatch_perlin": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "LayerUtility: LoadJoyCaption2Model": {
        MetaField.LORA_MODEL_HASH: {'field_name': "vlm_lora", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "vlm_lora"},
        MetaField.MODEL_HASH: {'field_name': "llm_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "llm_model"},
    },
    "LayerUtility: LoadJoyCaptionBeta1Model": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "LayerUtility: LoadSmolLM2Model": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "LayerUtility: LoadSmolVLMModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "LayerUtility: LoadVQAModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "LayerUtility: Seed": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "Legacy_ClownSampler": {
        MetaField.CFG: {'field_name': "cfgpp"},
        MetaField.SAMPLER_NAME: {'field_name': "noise_sampler_type"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "implicit_steps"},
    },
    "Legacy_ClownsharKSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "Legacy_ClownsharKSamplerGuides": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "Legacy_SharkSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "LoRA Stack to String converter": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_stack", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_stack"},
    },
    "LoRA Stacker": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name_1", "lora_wt_1", "lora_name_2", "lora_wt_2", "lora_name_3", "lora_wt_3", "lora_name_4", "lora_wt_4", "lora_name_5", "lora_wt_5", "lora_name_6", "lora_wt_6", "lora_name_7", "lora_wt_7", "lora_name_8", "lora_wt_8", "lora_name_9", "lora_wt_9", "lora_name_10", "lora_wt_10", "lora_name_11", "lora_wt_11", "lora_name_12", "lora_wt_12", "lora_name_13", "lora_wt_13", "lora_name_14", "lora_wt_14", "lora_name_15", "lora_wt_15", "lora_name_16", "lora_wt_16", "lora_name_17", "lora_wt_17", "lora_name_18", "lora_wt_18", "lora_name_19", "lora_wt_19", "lora_name_20", "lora_wt_20", "lora_name_21", "lora_wt_21", "lora_name_22", "lora_wt_22", "lora_name_23", "lora_wt_23", "lora_name_24", "lora_wt_24", "lora_name_25", "lora_wt_25", "lora_name_26", "lora_wt_26", "lora_name_27", "lora_wt_27", "lora_name_28", "lora_wt_28", "lora_name_29", "lora_wt_29", "lora_name_30", "lora_wt_30", "lora_name_31", "lora_wt_31", "lora_name_32", "lora_wt_32", "lora_name_33", "lora_wt_33", "lora_name_34", "lora_wt_34", "lora_name_35", "lora_wt_35", "lora_name_36", "lora_wt_36", "lora_name_37", "lora_wt_37", "lora_name_38", "lora_wt_38", "lora_name_39", "lora_wt_39", "lora_name_40", "lora_wt_40", "lora_name_41", "lora_wt_41", "lora_name_42", "lora_wt_42", "lora_name_43", "lora_wt_43", "lora_name_44", "lora_wt_44", "lora_name_45", "lora_wt_45", "lora_name_46", "lora_wt_46", "lora_name_47", "lora_wt_47", "lora_name_48", "lora_wt_48", "lora_name_49", "lora_wt_49", "lora_name_50", "lora_wt_50", "lora_count", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name_1", "lora_wt_1", "lora_name_2", "lora_wt_2", "lora_name_3", "lora_wt_3", "lora_name_4", "lora_wt_4", "lora_name_5", "lora_wt_5", "lora_name_6", "lora_wt_6", "lora_name_7", "lora_wt_7", "lora_name_8", "lora_wt_8", "lora_name_9", "lora_wt_9", "lora_name_10", "lora_wt_10", "lora_name_11", "lora_wt_11", "lora_name_12", "lora_wt_12", "lora_name_13", "lora_wt_13", "lora_name_14", "lora_wt_14", "lora_name_15", "lora_wt_15", "lora_name_16", "lora_wt_16", "lora_name_17", "lora_wt_17", "lora_name_18", "lora_wt_18", "lora_name_19", "lora_wt_19", "lora_name_20", "lora_wt_20", "lora_name_21", "lora_wt_21", "lora_name_22", "lora_wt_22", "lora_name_23", "lora_wt_23", "lora_name_24", "lora_wt_24", "lora_name_25", "lora_wt_25", "lora_name_26", "lora_wt_26", "lora_name_27", "lora_wt_27", "lora_name_28", "lora_wt_28", "lora_name_29", "lora_wt_29", "lora_name_30", "lora_wt_30", "lora_name_31", "lora_wt_31", "lora_name_32", "lora_wt_32", "lora_name_33", "lora_wt_33", "lora_name_34", "lora_wt_34", "lora_name_35", "lora_wt_35", "lora_name_36", "lora_wt_36", "lora_name_37", "lora_wt_37", "lora_name_38", "lora_wt_38", "lora_name_39", "lora_wt_39", "lora_name_40", "lora_wt_40", "lora_name_41", "lora_wt_41", "lora_name_42", "lora_wt_42", "lora_name_43", "lora_wt_43", "lora_name_44", "lora_wt_44", "lora_name_45", "lora_wt_45", "lora_name_46", "lora_wt_46", "lora_name_47", "lora_wt_47", "lora_name_48", "lora_wt_48", "lora_name_49", "lora_wt_49", "lora_name_50", "lora_wt_50", "lora_count", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_str_1", "lora_wt_1", "clip_str_2", "lora_wt_2", "clip_str_3", "lora_wt_3", "clip_str_4", "lora_wt_4", "clip_str_5", "lora_wt_5", "clip_str_6", "lora_wt_6", "clip_str_7", "lora_wt_7", "clip_str_8", "lora_wt_8", "clip_str_9", "lora_wt_9", "clip_str_10", "lora_wt_10", "clip_str_11", "lora_wt_11", "clip_str_12", "lora_wt_12", "clip_str_13", "lora_wt_13", "clip_str_14", "lora_wt_14", "clip_str_15", "lora_wt_15", "clip_str_16", "lora_wt_16", "clip_str_17", "lora_wt_17", "clip_str_18", "lora_wt_18", "clip_str_19", "lora_wt_19", "clip_str_20", "lora_wt_20", "clip_str_21", "lora_wt_21", "clip_str_22", "lora_wt_22", "clip_str_23", "lora_wt_23", "clip_str_24", "lora_wt_24", "clip_str_25", "lora_wt_25", "clip_str_26", "lora_wt_26", "clip_str_27", "lora_wt_27", "clip_str_28", "lora_wt_28", "clip_str_29", "lora_wt_29", "clip_str_30", "lora_wt_30", "clip_str_31", "lora_wt_31", "clip_str_32", "lora_wt_32", "clip_str_33", "lora_wt_33", "clip_str_34", "lora_wt_34", "clip_str_35", "lora_wt_35", "clip_str_36", "lora_wt_36", "clip_str_37", "lora_wt_37", "clip_str_38", "lora_wt_38", "clip_str_39", "lora_wt_39", "clip_str_40", "lora_wt_40", "clip_str_41", "lora_wt_41", "clip_str_42", "lora_wt_42", "clip_str_43", "lora_wt_43", "clip_str_44", "lora_wt_44", "clip_str_45", "lora_wt_45", "clip_str_46", "lora_wt_46", "clip_str_47", "lora_wt_47", "clip_str_48", "lora_wt_48", "clip_str_49", "lora_wt_49", "clip_str_50", "lora_wt_50"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["lora_wt_1", "model_str_1", "lora_wt_2", "model_str_2", "lora_wt_3", "model_str_3", "lora_wt_4", "model_str_4", "lora_wt_5", "model_str_5", "lora_wt_6", "model_str_6", "lora_wt_7", "model_str_7", "lora_wt_8", "model_str_8", "lora_wt_9", "model_str_9", "lora_wt_10", "model_str_10", "lora_wt_11", "model_str_11", "lora_wt_12", "model_str_12", "lora_wt_13", "model_str_13", "lora_wt_14", "model_str_14", "lora_wt_15", "model_str_15", "lora_wt_16", "model_str_16", "lora_wt_17", "model_str_17", "lora_wt_18", "model_str_18", "lora_wt_19", "model_str_19", "lora_wt_20", "model_str_20", "lora_wt_21", "model_str_21", "lora_wt_22", "model_str_22", "lora_wt_23", "model_str_23", "lora_wt_24", "model_str_24", "lora_wt_25", "model_str_25", "lora_wt_26", "model_str_26", "lora_wt_27", "model_str_27", "lora_wt_28", "model_str_28", "lora_wt_29", "model_str_29", "lora_wt_30", "model_str_30", "lora_wt_31", "model_str_31", "lora_wt_32", "model_str_32", "lora_wt_33", "model_str_33", "lora_wt_34", "model_str_34", "lora_wt_35", "model_str_35", "lora_wt_36", "model_str_36", "lora_wt_37", "model_str_37", "lora_wt_38", "model_str_38", "lora_wt_39", "model_str_39", "lora_wt_40", "model_str_40", "lora_wt_41", "model_str_41", "lora_wt_42", "model_str_42", "lora_wt_43", "model_str_43", "lora_wt_44", "model_str_44", "lora_wt_45", "model_str_45", "lora_wt_46", "model_str_46", "lora_wt_47", "model_str_47", "lora_wt_48", "model_str_48", "lora_wt_49", "model_str_49", "lora_wt_50", "model_str_50"]},
    },
    "Load Face Analysis Model (mtb)": {
        MetaField.MODEL_HASH: {'field_name': "faceswap_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "faceswap_model"},
    },
    "Load Face Enhance Model (mtb)": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "Load Face Swap Model (mtb)": {
        MetaField.MODEL_HASH: {'field_name': "faceswap_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "faceswap_model"},
    },
    "Load Lora": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "Load Remote Models": {
        MetaField.MODEL_HASH: {'field_name': "Sort_Models", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "Sort_Models"},
    },
    "Load Whisper (mtb)": {
        MetaField.MODEL_HASH: {'field_name': "model_size", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_size"},
    },
    "Load3D": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
        MetaField.MODEL_HASH: {'field_name': "model_file", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_file"},
    },
    "Load3DAnimation": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
        MetaField.MODEL_HASH: {'field_name': "model_file", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_file"},
    },
    "LoadAudioModel (DD)": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "LoadDiffusionModelShared //Inspire": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "LoadLBW //Inspire": {
        MetaField.MODEL_HASH: {'field_name': "lbw_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "lbw_model"},
    },
    "LoadLoraByName": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "LoadLoraModelOnlyByName": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength_model"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength_model"},
    },
    "LoadLynxResampler": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "LoadResAdapterNormalization": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "LoadVQVAE": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "Lora Loader": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "Lora Loader Stack (rgthree)": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_01", "lora_02", "lora_03", "lora_04"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_01", "lora_02", "lora_03", "lora_04"]},
    },
    "LoraBlockInfo //Inspire": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
    },
    "LoraExtractKJ": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_type", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_type"},
    },
    "LoraLoader": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "LoraLoaderBlockWeight //Inspire": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "LoraLoaderFromString": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength_model"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength_model"},
    },
    "LoraLoaderModelOnly": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength_model"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength_model"},
    },
    "LoraLoader|pysssss": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "LoraModelLoader": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora"},
    },
    "LoraReduceRankKJ": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
    },
    "LoraSave": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_type", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_type"},
    },
    "LorasForFluxParams+": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_1", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_1"},
    },
    "LyingSigmaSampler": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "MiDaS Model Loader": {
        MetaField.MODEL_HASH: {'field_name': "midas_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "midas_model"},
    },
    "MiaoBiCLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {'field_name': "clip_name"},
    },
    "MiaoBiDiffusersLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_path", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_path"},
    },
    "ModelSamplingAdvanced": {
        MetaField.SHIFT: {'field_name': "shift"},
    },
    "ModelSamplingAdvancedResolution": {
        MetaField.BASE_SHIFT: {'field_name': "base_shift"},
        MetaField.MAX_SHIFT: {'field_name': "max_shift"},
    },
    "ModelSamplingAuraFlow": {
        MetaField.SHIFT: {'field_name': "shift"},
    },
    "ModelSamplingFlux": {
        MetaField.BASE_SHIFT: {'field_name': "base_shift"},
        MetaField.MAX_SHIFT: {'field_name': "max_shift"},
    },
    "ModelSamplingLTXV": {
        MetaField.BASE_SHIFT: {'field_name': "base_shift"},
        MetaField.MAX_SHIFT: {'field_name': "max_shift"},
    },
    "ModelSamplingSD3": {
        MetaField.SHIFT: {'field_name': "shift"},
    },
    "ModelSamplingSD3Advanced+": {
        MetaField.SHIFT: {'field_name': "shift"},
    },
    "ModelSamplingStableCascade": {
        MetaField.SHIFT: {'field_name': "shift"},
    },
    "MultiTalkModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "NAGCFGGuider": {
        MetaField.CFG: {'field_name': "cfg"},
    },
    "OffsetLatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "OptimalStepsScheduler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "OutFluxModelSamplingPred": {
        MetaField.BASE_SHIFT: {'field_name': "base_shift"},
        MetaField.MAX_SHIFT: {'field_name': "max_shift"},
    },
    "OverrideVAEDevice": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "OviMMAudioVAELoader": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "PhotoMakerEncode": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "text", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "text", 'validate': KNOWN["is_positive_prompt"]},
    },
    "PhotoMakerLoader": {
        MetaField.MODEL_HASH: {'field_name': "photomaker_model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "photomaker_model_name"},
    },
    "PixArtCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "PixArtCheckpointLoaderSimple": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "PixArtLoraLoader": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength"},
    },
    "PixArtResolutionSelect": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "Power Prompt (rgthree)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "prompt", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "prompt", 'validate': KNOWN["is_positive_prompt"]},
    },
    "Power Prompt - Simple (rgthree)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "prompt", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "prompt", 'validate': KNOWN["is_positive_prompt"]},
    },
    "Prompt (LoraManager)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "text", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "text", 'validate': KNOWN["is_positive_prompt"]},
    },
    "QuadrupleCLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3", "clip_name4"]},
    },
    "QuadrupleCLIPLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3", "clip_name4"]},
    },
    "QuadrupleClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3", "clip_name4"]},
    },
    "QwenLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "RegionalSampler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "base_sampler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "RegionalSamplerAdvanced": {
        MetaField.SAMPLER_NAME: {'field_name': "base_sampler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "RenormCFG": {
        MetaField.CFG: {'field_name': "cfg_trunc"},
    },
    "RestartSamplerCustomNoise": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "SAM Model Loader": {
        MetaField.MODEL_HASH: {'field_name': "model_size", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_size"},
    },
    "SAMLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "SAMModelLoader (segment anything)": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "SD35Loader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "SDTurboScheduler": {
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SDXL Empty Latent Image (rgthree)": {
        MetaField.IMAGE_HEIGHT: {'field_name': "dimensions"},
        MetaField.IMAGE_WIDTH: {'field_name': "dimensions"},
    },
    "SDXL Power Prompt - Positive (rgthree)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "prompt_l", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "prompt_l", 'validate': KNOWN["is_positive_prompt"]},
    },
    "SDXL Power Prompt - Simple / Negative (rgthree)": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "prompt_l", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "prompt_l", 'validate': KNOWN["is_positive_prompt"]},
    },
    "SDXL Quick Empty Latent (WLSH)": {
        MetaField.IMAGE_HEIGHT: {'field_name': "resolution"},
        MetaField.IMAGE_WIDTH: {'field_name': "resolution"},
    },
    "SDXLEmptyLatentSizePicker+": {
        MetaField.IMAGE_HEIGHT: {'field_name': "resolution"},
        MetaField.IMAGE_WIDTH: {'field_name': "resolution"},
    },
    "Sampler Selector (Image Saver)": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
    },
    "SamplerConfigOverride": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "SamplerCustom": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SEED: {'field_name': "noise_seed"},
    },
    "SamplerCustomAdvanced": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "SamplerCustomWithNAG": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SEED: {'field_name': "noise_seed"},
    },
    "SamplerOptions_GarbageCollection": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "SamplerOptions_TimestepScaling": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "SamplerToString (Image Saver)": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
    },
    "SanaCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "SanaResolutionSelect": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "SaveLoRANode": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora"},
    },
    "ScheduledCFGGuidance": {
        MetaField.CFG: {'field_name': "cfg"},
    },
    "ScheduledCFGGuider //Inspire": {
        MetaField.CFG: {'field_name': "from_cfg"},
    },
    "ScheduledPerpNegCFGGuider //Inspire": {
        MetaField.CFG: {'field_name': "from_cfg"},
    },
    "Scheduler Selector (Eff.) (Image Saver)": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "Scheduler Selector (Image Saver)": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "Scheduler Selector (inspire) (Image Saver)": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "SchedulerEfficiencyToString (Image Saver)": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "SchedulerInspireToString (Image Saver)": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "SchedulerToString (Image Saver)": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "SeargeCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "SeargeLoraLoader": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["strength_clip", "strength_model"]},
    },
    "SeargeLoras": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_1", "lora_1_strength", "lora_2", "lora_2_strength", "lora_3", "lora_3_strength", "lora_4", "lora_4_strength", "lora_5", "lora_5_strength"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_1", "lora_1_strength", "lora_2", "lora_2_strength", "lora_3", "lora_3_strength", "lora_4", "lora_4_strength", "lora_5", "lora_5_strength"]},
    },
    "SeargeModelSelector": {
        MetaField.MODEL_HASH: {'field_name': "refiner_checkpoint", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "refiner_checkpoint"},
    },
    "SeargeSDXLImage2ImageSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SeargeSDXLImage2ImageSampler2": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SeargeSDXLSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SeargeSDXLSampler2": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SeargeSDXLSamplerV3": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "noise_seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SeargeSamplerInputs": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "SeargeVAELoader": {
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
    },
    "Seed": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "Seed (rgthree)": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "Seed Generator (Image Saver)": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "Seed and Int (WLSH)": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "SeedExplorer //Inspire": {
        MetaField.SEED: {'field_name': "additional_seed"},
    },
    "SeedGenerator": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "SeedLogger //Inspire": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "SeedVR2LoadDiTModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "SeedVR2LoadVAEModel": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "SharkChainsampler_Beta": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.STEPS: {'field_name': "steps_to_run"},
    },
    "SharkOptions_UltraCascade_Latent_Beta": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "SharkSampler_Beta": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "SigmasSchedulePreview": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
    },
    "SonarLatentOperationSetSeed": {
        MetaField.SEED: {'field_name': "seed"},
    },
    "StableCascade_EmptyLatentImage": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "StyleModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "style_model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "style_model_name"},
    },
    "TiledKSamplerProvider": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "TorchCompileVAE": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "TrainLoraNode": {
        MetaField.LORA_MODEL_HASH: {'fields': ["existing_lora", "lora_dtype"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["existing_lora", "lora_dtype"]},
    },
    "TripleCLIPLoader": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3"]},
    },
    "TripleCLIPLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3"]},
    },
    "TripleClipLoaderGGUF": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3"]},
    },
    "UNETLoader": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "UNet loader with Name (Image Saver)": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "UltraSharkSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SEED: {'field_name': "noise_seed"},
    },
    "UltraSharkSampler Tiled": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler"},
        MetaField.SEED: {'field_name': "noise_seed"},
    },
    "UnetLoaderGGUF": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
    },
    "UnetLoaderGGUFAdvanced": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
    },
    "UnsamplerHookProvider": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.SAMPLER_NAME: {'field_name': "sampler_name"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "VAELoader": {
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
    },
    "VAELoaderKJ": {
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "VAESave": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VAEStyleTransferLatent": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VHS_LoadImagePath": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VHS_LoadVideo": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VHS_LoadVideoFFmpeg": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VHS_LoadVideoFFmpegPath": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VHS_LoadVideoPath": {
        MetaField.VAE_HASH: {'field_name': "vae", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae"},
    },
    "VaeGGUF": {
        MetaField.VAE_HASH: {'field_name': "vae_name", 'format': KNOWN["calc_vae_hash"]},
        MetaField.VAE_NAME: {'field_name': "vae_name"},
    },
    "VelocatorLoadAndQuantizeClip": {
        MetaField.CLIP_MODEL_NAME: {'fields': ["clip_name1", "clip_name2", "clip_name3"]},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "VelocatorLoadAndQuantizeDiffusionModel": {
        MetaField.MODEL_HASH: {'field_name': "unet_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "unet_name"},
        MetaField.WEIGHT_DTYPE: {'field_name': "weight_dtype"},
    },
    "VideoLinearCFGGuidance": {
        MetaField.CFG: {'field_name': "min_cfg"},
    },
    "VideoTriangleCFGGuidance": {
        MetaField.CFG: {'field_name': "min_cfg"},
    },
    "Wan22ImageToVideoLatent": {
        MetaField.IMAGE_HEIGHT: {'field_name': "height"},
        MetaField.IMAGE_WIDTH: {'field_name': "width"},
    },
    "WanVideo Lora Select (LoraManager)": {
        MetaField.LORA_MODEL_HASH: {'field_name': "merge_loras", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "merge_loras"},
    },
    "WanVideoControlnetLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "WanVideoDiffusionForcingSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise_strength"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "WanVideoExtraModelSelect": {
        MetaField.MODEL_HASH: {'field_name': "extra_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "extra_model"},
    },
    "WanVideoFlashVSRDecoderLoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "WanVideoLoraSelect": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora", "merge_loras", "prev_lora"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora", "merge_loras", "prev_lora"]},
    },
    "WanVideoLoraSelectByName": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name", "merge_loras", "prev_lora"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name", "merge_loras", "prev_lora"]},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': "strength"},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': "strength"},
    },
    "WanVideoLoraSelectMulti": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4", "merge_loras", "prev_lora"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4", "merge_loras", "prev_lora"]},
    },
    "WanVideoModelLoader": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora"},
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "WanVideoOviCFG": {
        MetaField.CFG: {'field_name': "ovi_audio_cfg"},
    },
    "WanVideoSampler": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise_strength"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "WanVideoSamplerFromSettings": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_inputs"},
    },
    "WanVideoSamplerSettings": {
        MetaField.CFG: {'field_name': "cfg"},
        MetaField.DENOISE: {'field_name': "denoise_strength"},
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.SEED: {'field_name': "seed"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "WanVideoScheduler": {
        MetaField.SCHEDULER: {'field_name': "scheduler"},
        MetaField.STEPS: {'field_name': "steps"},
    },
    "WanVideoSetLoRAs": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora"},
    },
    "WanVideoTinyVAELoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "WanVideoUni3C_ControlnetLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "WanVideoVACEModelSelect": {
        MetaField.MODEL_HASH: {'field_name': "vace_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "vace_model"},
    },
    "WanVideoVAELoader": {
        MetaField.MODEL_HASH: {'field_name': "model_name", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model_name"},
    },
    "Wav2VecModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "WhisperModelLoader": {
        MetaField.MODEL_HASH: {'field_name': "model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "model"},
    },
    "WildcardEncode //Inspire": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "populated_text", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "populated_text", 'validate': KNOWN["is_positive_prompt"]},
    },
    "XY Input: LoRA": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name_1", "lora_name_2", "lora_name_3", "lora_name_4", "lora_name_5", "lora_name_6", "lora_name_7", "lora_name_8", "lora_name_9", "lora_name_10", "lora_name_11", "lora_name_12", "lora_name_13", "lora_name_14", "lora_name_15", "lora_name_16", "lora_name_17", "lora_name_18", "lora_name_19", "lora_name_20", "lora_name_21", "lora_name_22", "lora_name_23", "lora_name_24", "lora_name_25", "lora_name_26", "lora_name_27", "lora_name_28", "lora_name_29", "lora_name_30", "lora_name_31", "lora_name_32", "lora_name_33", "lora_name_34", "lora_name_35", "lora_name_36", "lora_name_37", "lora_name_38", "lora_name_39", "lora_name_40", "lora_name_41", "lora_name_42", "lora_name_43", "lora_name_44", "lora_name_45", "lora_name_46", "lora_name_47", "lora_name_48", "lora_name_49", "lora_name_50", "lora_count", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name_1", "lora_name_2", "lora_name_3", "lora_name_4", "lora_name_5", "lora_name_6", "lora_name_7", "lora_name_8", "lora_name_9", "lora_name_10", "lora_name_11", "lora_name_12", "lora_name_13", "lora_name_14", "lora_name_15", "lora_name_16", "lora_name_17", "lora_name_18", "lora_name_19", "lora_name_20", "lora_name_21", "lora_name_22", "lora_name_23", "lora_name_24", "lora_name_25", "lora_name_26", "lora_name_27", "lora_name_28", "lora_name_29", "lora_name_30", "lora_name_31", "lora_name_32", "lora_name_33", "lora_name_34", "lora_name_35", "lora_name_36", "lora_name_37", "lora_name_38", "lora_name_39", "lora_name_40", "lora_name_41", "lora_name_42", "lora_name_43", "lora_name_44", "lora_name_45", "lora_name_46", "lora_name_47", "lora_name_48", "lora_name_49", "lora_name_50", "lora_count", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_str_1", "clip_str_2", "clip_str_3", "clip_str_4", "clip_str_5", "clip_str_6", "clip_str_7", "clip_str_8", "clip_str_9", "clip_str_10", "clip_str_11", "clip_str_12", "clip_str_13", "clip_str_14", "clip_str_15", "clip_str_16", "clip_str_17", "clip_str_18", "clip_str_19", "clip_str_20", "clip_str_21", "clip_str_22", "clip_str_23", "clip_str_24", "clip_str_25", "clip_str_26", "clip_str_27", "clip_str_28", "clip_str_29", "clip_str_30", "clip_str_31", "clip_str_32", "clip_str_33", "clip_str_34", "clip_str_35", "clip_str_36", "clip_str_37", "clip_str_38", "clip_str_39", "clip_str_40", "clip_str_41", "clip_str_42", "clip_str_43", "clip_str_44", "clip_str_45", "clip_str_46", "clip_str_47", "clip_str_48", "clip_str_49", "clip_str_50", "clip_strength", "model_strength"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["model_str_1", "model_str_2", "model_str_3", "model_str_4", "model_str_5", "model_str_6", "model_str_7", "model_str_8", "model_str_9", "model_str_10", "model_str_11", "model_str_12", "model_str_13", "model_str_14", "model_str_15", "model_str_16", "model_str_17", "model_str_18", "model_str_19", "model_str_20", "model_str_21", "model_str_22", "model_str_23", "model_str_24", "model_str_25", "model_str_26", "model_str_27", "model_str_28", "model_str_29", "model_str_30", "model_str_31", "model_str_32", "model_str_33", "model_str_34", "model_str_35", "model_str_36", "model_str_37", "model_str_38", "model_str_39", "model_str_40", "model_str_41", "model_str_42", "model_str_43", "model_str_44", "model_str_45", "model_str_46", "model_str_47", "model_str_48", "model_str_49", "model_str_50", "clip_strength", "model_strength"]},
    },
    "XY Input: LoRA Plot": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_name", "lora_stack"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_name", "lora_stack"]},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["clip_strength", "model_strength"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["clip_strength", "model_strength"]},
    },
    "XY Input: LoRA Stacks": {
        MetaField.LORA_MODEL_HASH: {'fields': ["lora_stack_1", "lora_stack_2", "lora_stack_3", "lora_stack_4", "lora_stack_5"], 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'fields': ["lora_stack_1", "lora_stack_2", "lora_stack_3", "lora_stack_4", "lora_stack_5"]},
    },
    "XY Input: Lora Block Weight //Inspire": {
        MetaField.LORA_MODEL_HASH: {'field_name': "lora_name", 'format': KNOWN["calc_lora_hash"]},
        MetaField.LORA_MODEL_NAME: {'field_name': "lora_name"},
        MetaField.LORA_STRENGTH_CLIP: {'fields': ["heatmap_strength", "strength_clip", "strength_model"]},
        MetaField.LORA_STRENGTH_MODEL: {'fields': ["heatmap_strength", "strength_clip", "strength_model"]},
    },
    "XY Input: Sampler/Scheduler": {
        MetaField.SAMPLER_NAME: {'field_name': "sampler_27"},
        MetaField.SCHEDULER: {'field_name': "scheduler_32"},
    },
    "mjsk_Checkpoint_Selector": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "mjsk_MiDaS_Model_Loader": {
        MetaField.MODEL_HASH: {'field_name': "midas_model", 'format': KNOWN["calc_unet_hash"]},
        MetaField.MODEL_NAME: {'field_name': "midas_model"},
    },
    "mjsk_PromptWithTokenCounter": {
        MetaField.NEGATIVE_PROMPT: {'field_name': "text", 'validate': KNOWN["is_negative_prompt"]},
        MetaField.POSITIVE_PROMPT: {'field_name': "text", 'validate': KNOWN["is_positive_prompt"]},
    },
    "unCLIP Checkpoint Loader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
    "unCLIPCheckpointLoader": {
        MetaField.MODEL_HASH: {'field_name': "ckpt_name", 'format': KNOWN["calc_model_hash"]},
        MetaField.MODEL_NAME: {'field_name': "ckpt_name"},
    },
}
