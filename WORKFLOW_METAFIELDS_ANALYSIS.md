# Complete Workflow MetaFields Analysis

Comprehensive table of all MetaFields found in each of the 17 workflows.

| # | Workflow Name | MetaField | Value |
|---|---------------|-----------|-------|
| 1 | efficiency-nodes | CFG | 7 |
| | | CLIP_SKIP | -1 |
| | | DENOISE | 1 |
| | | IMAGE_HEIGHT | 1024 |
| | | IMAGE_WIDTH | 1024 |
| | | MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v50.safetensors |
| | | SAMPLER_NAME | dpmpp_2m |
| | | SCHEDULER | karras |
| | | SEED | 456 |
| | | STEPS | 25 |
| | | VAE_NAME | Baked VAE |
| 2 | embedding_lora_vae_upscale_dual_sampler | CFG | 8 |
| | | DENOISE | 1 |
| | | IMAGE_HEIGHT | 512 |
| | | IMAGE_WIDTH | 512 |
| | | LORA_MODEL_NAME | ['LoRA\\sd15\\berserk\\Guts_05.safetensors', 'LoRA\\sd15\\berserk\\berserk_guts-... |
| | | LORA_STRENGTH_CLIP | [0.5, 0.5] |
| | | LORA_STRENGTH_MODEL | [0.5, 0.5] |
| | | MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v33.safetensors |
| | | POSITIVE_PROMPT | (low quality, worst quality:1.4), embedding:EasyNegative, embedding:FastNegative... |
| | | SAMPLER_NAME | dpmpp_2m |
| | | SCHEDULER | karras |
| | | SEED | 123 |
| | | STEPS | 20 |
| | | VAE_NAME | vae-ft-mse-840000-ema-pruned.ckpt |
| 3 | extra_metadata_clip_skip | CFG | 8 |
| | | DENOISE | 1 |
| | | MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v33.safetensors |
| | | SAMPLER_NAME | euler_ancestral |
| | | SCHEDULER | karras |
| | | SEED | 999999999999999 |
| | | STEPS | 20 |
| 4 | filename_format_denoise | CFG | 8 |
| | | DENOISE | 0.7 |
| | | IMAGE_HEIGHT | 512 |
| | | IMAGE_WIDTH | 512 |
| | | MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v33.safetensors |
| | | POSITIVE_PROMPT | (low quality, worst quality:1.4), embedding:EasyNegative |
| | | SAMPLER_NAME | dpmpp_2m |
| | | SCHEDULER | karras |
| | | SEED | 123 |
| | | STEPS | 20 |
| | | VAE_NAME | vae-ft-mse-840000-ema-pruned.ckpt |
| 5 | flux-CR-LoRA-stack-ClownsharK | CFG | 1 |
| | | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | DENOISE | 1 |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | linear/euler |
| | | SCHEDULER | bong_tangent |
| | | STEPS | 2 |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 6 | flux-PC-LoRA-inline-Inspire-KSampler | CFG | 1 |
| | | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | DENOISE | 1 |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | deis |
| | | SCHEDULER | karras |
| | | STEPS | 1 |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 7 | flux-civsampler-GCFG-lora-summary-batch3-turbo | CLIP_MODEL_NAME | ['flux\\t5xxl_fp16.safetensors', 'flux\\clip_l.safetensors'] |
| | | LORA_MODEL_NAME | ['flux\\turbos\\FLUX.1-Turbo-Alpha.safetensors'] |
| | | LORA_STRENGTH_MODEL | [0.8] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | euler |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn_fast |
| 8 | flux-dual-clip-turbo | CLIP_MODEL_NAME | ['flux\\t5xxl_fp16.safetensors', 'flux\\clip_l.safetensors'] |
| | | CLIP_PROMPT | oil painting, semi realistic, fantasy, anime style, solid color background, tall... |
| | | LORA_MODEL_NAME | ['flux\\turbos\\FLUX.1-Turbo-Alpha.safetensors'] |
| | | LORA_STRENGTH_MODEL | [0.8] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | euler |
| | | T5_PROMPT | In a semi-realistic oil painting style, with bold brushstrokes and vivid colors,... |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn_fast |
| 9 | flux-eff-LoRA-stack-ClownsharK | CFG | 1 |
| | | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | DENOISE | 1 |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | linear/euler |
| | | SCHEDULER | bong_tangent |
| | | STEPS | 2 |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 10 | flux-turbo | CLIP_MODEL_NAME | ['flux\\t5xxl_fp16.safetensors', 'flux\\clip_l.safetensors'] |
| | | LORA_MODEL_NAME | ['flux\\turbos\\FLUX.1-Turbo-Alpha.safetensors'] |
| | | LORA_STRENGTH_MODEL | [0.8] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | euler |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn_fast |
| 11 | large-workflow-jpeg-1kb | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | LORA_MODEL_NAME | ['flux\\artstyle\\style\\m100-style_v.02.safetensors', 'flux\\artstyle\\style\\S... |
| | | LORA_STRENGTH_MODEL | [0.3, 1, 0.15] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | dpmpp_2m |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 12 | large-workflow-jpeg-60kb | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | LORA_MODEL_NAME | ['flux\\artstyle\\style\\m100-style_v.02.safetensors', 'flux\\artstyle\\style\\S... |
| | | LORA_STRENGTH_MODEL | [0.3, 1, 0.15] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | dpmpp_2m |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 13 | large-workflow-png | CFG | 8 |
| | | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | LORA_MODEL_NAME | ['flux\\artstyle\\style\\m100-style_v.02.safetensors', 'flux\\artstyle\\style\\S... |
| | | LORA_STRENGTH_MODEL | [0.3, 1, 0.15] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | dpmpp_2m |
| | | SEED | 258012155729038 |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 14 | large-workflow-webp | CLIP_MODEL_NAME | ['flux\\t5xxl_fp8_e4m3fn_scaled.safetensors', 'flux\\Long-ViT-L-14-REG-TE-only-H... |
| | | LORA_MODEL_NAME | ['flux\\artstyle\\style\\m100-style_v.02.safetensors', 'flux\\artstyle\\style\\S... |
| | | LORA_STRENGTH_MODEL | [0.3, 1, 0.15] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | dpmpp_2m |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn |
| 15 | lora-USO-Style-and-or-Subject-transfer-turbo | CLIP_MODEL_NAME | ['flux\\t5xxl_fp16.safetensors', 'flux\\clip_l.safetensors', 'sigclip_vision_pat... |
| | | LORA_MODEL_NAME | ['flux\\uso\\uso-flux1-dit-lora-v1.safetensors', 'flux\\turbos\\FLUX.1-Turbo-Alp... |
| | | LORA_STRENGTH_MODEL | [1, 0.8] |
| | | MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| | | SAMPLER_NAME | euler |
| | | VAE_NAME | ae.safetensors |
| | | WEIGHT_DTYPE | fp8_e4m3fn_fast |
| 16 | qwen_image_edit_2509 | CFG | 1 |
| | | CLIP_MODEL_NAME | ['qwen_2.5_vl_7b_fp8_scaled.safetensors'] |
| | | DENOISE | 1 |
| | | LORA_MODEL_NAME | ['qwen\\Qwen-Image-Lightning-4steps-V1.0.safetensors'] |
| | | LORA_STRENGTH_MODEL | [1] |
| | | MODEL_NAME | DiffusionModels\qwen_image_edit_2509_fp8_e4m3fn.safetensors |
| | | SAMPLER_NAME | euler |
| | | SCHEDULER | simple |
| | | SEED | 1118877715456453 |
| | | STEPS | 4 |
| | | VAE_NAME | qwen_image_vae.safetensors |
| | | WEIGHT_DTYPE | default |
| 17 | wan21_text_to_image_sage | CFG | 1 |
| | | CLIP_MODEL_NAME | ['umt5_xxl_fp8_e4m3fn_scaled.safetensors'] |
| | | DENOISE | 1 |
| | | IMAGE_HEIGHT | 1504 |
| | | IMAGE_WIDTH | 1344 |
| | | LORA_MODEL_NAME | ['wan\\turbo\\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16_.safetensors... |
| | | LORA_STRENGTH_MODEL | [1] |
| | | MODEL_NAME | flux\wan\Wan2_1-T2V-14B_fp8_e4m3fn_scaled_KJ.safetensors |
| | | SAMPLER_NAME | dpmpp_2m |
| | | SCHEDULER | karras |
| | | SEED | 706190577933098 |
| | | STEPS | 4 |
| | | VAE_NAME | wan_2.1_vae.safetensors |
| | | WEIGHT_DTYPE | default |


## Detailed Analysis by Workflow

### 1. efficiency-nodes

| MetaField | Value |
|-----------|-------|
| CFG | 7 |
| CLIP_SKIP | -1 |
| DENOISE | 1 |
| IMAGE_HEIGHT | 1024 |
| IMAGE_WIDTH | 1024 |
| MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v50.safetensors |
| SAMPLER_NAME | dpmpp_2m |
| SCHEDULER | karras |
| SEED | 456 |
| STEPS | 25 |
| VAE_NAME | Baked VAE |

### 2. embedding_lora_vae_upscale_dual_sampler

| MetaField | Value |
|-----------|-------|
| CFG | 8 |
| DENOISE | 1 |
| IMAGE_HEIGHT | 512 |
| IMAGE_WIDTH | 512 |
| LORA_MODEL_NAME | LoRA\sd15\berserk\Guts_05.safetensors, LoRA\sd15\berserk\berserk_guts-10.safetensors |
| LORA_STRENGTH_CLIP | 0.5, 0.5 |
| LORA_STRENGTH_MODEL | 0.5, 0.5 |
| MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v33.safetensors |
| POSITIVE_PROMPT | (low quality, worst quality:1.4), embedding:EasyNegative, embedding:FastNegativeV2,  |
| SAMPLER_NAME | dpmpp_2m |
| SCHEDULER | karras |
| SEED | 123 |
| STEPS | 20 |
| VAE_NAME | vae-ft-mse-840000-ema-pruned.ckpt |

### 3. extra_metadata_clip_skip

| MetaField | Value |
|-----------|-------|
| CFG | 8 |
| DENOISE | 1 |
| MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v33.safetensors |
| SAMPLER_NAME | euler_ancestral |
| SCHEDULER | karras |
| SEED | 999999999999999 |
| STEPS | 20 |

### 4. filename_format_denoise

| MetaField | Value |
|-----------|-------|
| CFG | 8 |
| DENOISE | 0.7 |
| IMAGE_HEIGHT | 512 |
| IMAGE_WIDTH | 512 |
| MODEL_NAME | StableDiffusion\Originals\sd1.5\cyberrealistic_v33.safetensors |
| POSITIVE_PROMPT | (low quality, worst quality:1.4), embedding:EasyNegative |
| SAMPLER_NAME | dpmpp_2m |
| SCHEDULER | karras |
| SEED | 123 |
| STEPS | 20 |
| VAE_NAME | vae-ft-mse-840000-ema-pruned.ckpt |

### 5. flux-CR-LoRA-stack-ClownsharK

| MetaField | Value |
|-----------|-------|
| CFG | 1 |
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| DENOISE | 1 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | linear/euler |
| SCHEDULER | bong_tangent |
| STEPS | 2 |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 6. flux-PC-LoRA-inline-Inspire-KSampler

| MetaField | Value |
|-----------|-------|
| CFG | 1 |
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| DENOISE | 1 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | deis |
| SCHEDULER | karras |
| STEPS | 1 |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 7. flux-civsampler-GCFG-lora-summary-batch3-turbo

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp16.safetensors, flux\clip_l.safetensors |
| LORA_MODEL_NAME | flux\turbos\FLUX.1-Turbo-Alpha.safetensors |
| LORA_STRENGTH_MODEL | 0.8 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | euler |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn_fast |

### 8. flux-dual-clip-turbo

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp16.safetensors, flux\clip_l.safetensors |
| CLIP_PROMPT | oil painting, semi realistic, fantasy, anime style, solid color background, tall thin character, beautiful lush vibrant forest, backlighting, dramatic atmospheric glow, countless small tiny clumsy gen... |
| LORA_MODEL_NAME | flux\turbos\FLUX.1-Turbo-Alpha.safetensors |
| LORA_STRENGTH_MODEL | 0.8 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | euler |
| T5_PROMPT | In a semi-realistic oil painting style, with bold brushstrokes and vivid colors, a tall and thin character stands majestically in a beautiful, lush, and vibrant forest, set against a solid color backg... |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn_fast |

### 9. flux-eff-LoRA-stack-ClownsharK

| MetaField | Value |
|-----------|-------|
| CFG | 1 |
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| DENOISE | 1 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | linear/euler |
| SCHEDULER | bong_tangent |
| STEPS | 2 |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 10. flux-turbo

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp16.safetensors, flux\clip_l.safetensors |
| LORA_MODEL_NAME | flux\turbos\FLUX.1-Turbo-Alpha.safetensors |
| LORA_STRENGTH_MODEL | 0.8 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | euler |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn_fast |

### 11. large-workflow-jpeg-1kb

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| LORA_MODEL_NAME | flux\artstyle\style\m100-style_v.02.safetensors, flux\artstyle\style\Style_Calligraphy_ART.safetensors, flux\artstyle\style\lnrnr_flux_EliPot.safetensors |
| LORA_STRENGTH_MODEL | 0.3, 1, 0.15 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | dpmpp_2m |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 12. large-workflow-jpeg-60kb

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| LORA_MODEL_NAME | flux\artstyle\style\m100-style_v.02.safetensors, flux\artstyle\style\Style_Calligraphy_ART.safetensors, flux\artstyle\style\lnrnr_flux_EliPot.safetensors |
| LORA_STRENGTH_MODEL | 0.3, 1, 0.15 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | dpmpp_2m |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 13. large-workflow-png

| MetaField | Value |
|-----------|-------|
| CFG | 8 |
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| LORA_MODEL_NAME | flux\artstyle\style\m100-style_v.02.safetensors, flux\artstyle\style\Style_Calligraphy_ART.safetensors, flux\artstyle\style\lnrnr_flux_EliPot.safetensors |
| LORA_STRENGTH_MODEL | 0.3, 1, 0.15 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | dpmpp_2m |
| SEED | 258012155729038 |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 14. large-workflow-webp

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp8_e4m3fn_scaled.safetensors, flux\Long-ViT-L-14-REG-TE-only-HF-format.safetensors |
| LORA_MODEL_NAME | flux\artstyle\style\m100-style_v.02.safetensors, flux\artstyle\style\Style_Calligraphy_ART.safetensors, flux\artstyle\style\lnrnr_flux_EliPot.safetensors |
| LORA_STRENGTH_MODEL | 0.3, 1, 0.15 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | dpmpp_2m |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn |

### 15. lora-USO-Style-and-or-Subject-transfer-turbo

| MetaField | Value |
|-----------|-------|
| CLIP_MODEL_NAME | flux\t5xxl_fp16.safetensors, flux\clip_l.safetensors, sigclip_vision_patch14_384.safetensors |
| LORA_MODEL_NAME | flux\uso\uso-flux1-dit-lora-v1.safetensors, flux\turbos\FLUX.1-Turbo-Alpha.safetensors |
| LORA_STRENGTH_MODEL | 1, 0.8 |
| MODEL_NAME | flux\flux1-dev-fp8-e4m3fn.safetensors |
| SAMPLER_NAME | euler |
| VAE_NAME | ae.safetensors |
| WEIGHT_DTYPE | fp8_e4m3fn_fast |

### 16. qwen_image_edit_2509

| MetaField | Value |
|-----------|-------|
| CFG | 1 |
| CLIP_MODEL_NAME | qwen_2.5_vl_7b_fp8_scaled.safetensors |
| DENOISE | 1 |
| LORA_MODEL_NAME | qwen\Qwen-Image-Lightning-4steps-V1.0.safetensors |
| LORA_STRENGTH_MODEL | 1 |
| MODEL_NAME | DiffusionModels\qwen_image_edit_2509_fp8_e4m3fn.safetensors |
| SAMPLER_NAME | euler |
| SCHEDULER | simple |
| SEED | 1118877715456453 |
| STEPS | 4 |
| VAE_NAME | qwen_image_vae.safetensors |
| WEIGHT_DTYPE | default |

### 17. wan21_text_to_image_sage

| MetaField | Value |
|-----------|-------|
| CFG | 1 |
| CLIP_MODEL_NAME | umt5_xxl_fp8_e4m3fn_scaled.safetensors |
| DENOISE | 1 |
| IMAGE_HEIGHT | 1504 |
| IMAGE_WIDTH | 1344 |
| LORA_MODEL_NAME | wan\turbo\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16_.safetensors |
| LORA_STRENGTH_MODEL | 1 |
| MODEL_NAME | flux\wan\Wan2_1-T2V-14B_fp8_e4m3fn_scaled_KJ.safetensors |
| SAMPLER_NAME | dpmpp_2m |
| SCHEDULER | karras |
| SEED | 706190577933098 |
| STEPS | 4 |
| VAE_NAME | wan_2.1_vae.safetensors |
| WEIGHT_DTYPE | default |

