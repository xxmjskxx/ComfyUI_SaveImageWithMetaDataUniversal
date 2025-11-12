# Additional Test Workflow Suggestions

Based on the analysis of the current test workflows in `tests/comfyui_cli_tests/dev_test_workflows/`, here are suggestions for additional workflows that would provide more comprehensive test coverage of the Save Image w/ Metadata Universal node's features.

## Current Coverage Summary

The existing workflows test:
- ✅ PNG, JPEG, and WebP formats
- ✅ Large workflows with JPEG fallback
- ✅ LoRA and embeddings
- ✅ Multiple samplers
- ✅ Guidance as CFG
- ✅ Civitai sampler mode
- ✅ Custom metadata
- ✅ Filename formats
- ✅ Flux models
- ✅ Efficiency nodes integration
- ✅ Style/subject transfer nodes
- ✅ 8. Shift Parameters (Flux-specific)
- ✅ 12. VAE Metadata
- ✅ 13. Embedding Resolution

New workflows have been added, or existing ones modified, which test:
- ✅ 1. LoRA Summary Toggle
- ✅ 2. JPEG Fallback Stages
- ✅ 3. Batch Processing
- ✅ 6. Clip Skip
- ✅ 7. Denoise Strength
- ✅ 10. Multiple Encoder
- ✅ 11. Inline LoRA Tags
- ✅ 16. High Seed Value Test

Existing workflows test this, but not extensively:
- ✅ 9. Scheduler Variations
- ✅ 15. Size Variations Test

Still missing/underrepresented test cases:
- ❌ 4. Sampler Selection Method Test
- ❌ 5. Hash Detail Flag Test
- ❌ 14. No Hash Detail + No LoRA Summary Test
- ❌ 17. Zero Denoise Test
- ❌ 18. Model Hash Caching Test

## Missing/Underrepresented Test Cases

### 1. LoRA Summary Toggle Test
**Purpose:** Test the `include_lora_summary` option

**What to test:**
- Workflow with LoRAs where `include_lora_summary` is `true`
- Should validate that the aggregated LoRA summary line appears in metadata
- Should verify individual LoRA entries still exist

**Expected metadata changes:**
```
LoRAs: lora_name1(strength_model/strength_clip), lora_name2(strength_model/strength_clip)
Lora_1: lora_name1
Lora_1 hash: abc123
...
```

### 2. JPEG Fallback Stages Test
**Purpose:** Test all JPEG metadata fallback stages

**What to test:**
- Create workflows that progressively exceed JPEG EXIF limits
- Test with `max_jpeg_exif_kb` set to lower values (e.g., 8, 16) to force fallback
- Verify each fallback stage:
  - `reduced-exif`: Only parameters, no workflow
  - `minimal`: Essential fields only (Steps, Sampler, CFG, Seed, Model, Hashes, etc.)
  - `com-marker`: Comment marker fallback

**Expected metadata changes:**
```
... Metadata Fallback: reduced-exif
... Metadata Fallback: minimal
... Metadata Fallback: com-marker
```

### 3. Batch Processing Test
**Purpose:** Test batch_index and batch_size metadata fields

**What to test:**
- Workflow with batch_size >= 2
- Should generate multiple images with different batch_index values
- Verify metadata contains:
  - `Batch index: N`
  - `Batch size: M`

### 4. Sampler Selection Method Test
**Purpose:** Test all three sampler selection methods

**What to test:**
- Three variants of a workflow with multiple samplers:
  - `sampler_selection_method: "Farthest"`
  - `sampler_selection_method: "Nearest"`
  - `sampler_selection_method: "By node ID"` with specific `sampler_selection_node_id`
- Verify that the correct sampler's metadata is used

### 5. Hash Detail Flag Test
**Purpose:** Test the `METADATA_NO_HASH_DETAIL` environment flag behavior

**What to test:**
- Same workflow run with and without `METADATA_NO_HASH_DETAIL=1`
- With flag: Should see condensed hashes
- Without flag: Should see detailed hash information

**Note:** This may need to be tested via environment configuration rather than workflow JSON

### 6. Clip Skip Test
**Purpose:** Test clip_skip metadata capture

**What to test:**
- Workflow with CLIP Text Encode nodes that use clip_skip parameter
- Verify metadata contains `Clip skip: N`

### 7. Denoise Strength Test
**Purpose:** Test denoise metadata for img2img workflows

**What to test:**
- Workflow with non-1.0 denoise value
- Verify metadata contains `Denoise: X.XX`

### 8. Shift Parameters Test (Flux-specific)
**Purpose:** Test Flux-specific shift parameters

**What to test:**
- Workflow with ModelSamplingFlux nodes
- Verify metadata captures:
  - `Shift: X.XX`
  - `Max shift: X.XX`
  - `Base shift: X.XX`

### 9. Scheduler Variations Test
**Purpose:** Test different scheduler types

**What to test:**
- Multiple workflows with different schedulers:
  - karras
  - exponential
  - normal
  - simple
  - ddim_uniform
  - etc.
- Verify correct sampler name mapping (e.g., "Euler Karras" vs "Euler")

### 10. Multiple Encoder Test
**Purpose:** Test dual encoder scenarios (Flux T5 + CLIP)

**What to test:**
- Workflow with both T5 and CLIP encoders
- Verify prompt aliasing and deduplication works correctly
- Should not have redundant positive prompts

### 11. Inline LoRA Tags Test
**Purpose:** Test inline LoRA tag parsing

**What to test:**
- Workflow using ComfyUI Prompt Control or LoRA Manager with inline tags:
  - `<lora:name:strength>`
  - `<lora:name:strength_model:strength_clip>`
- Verify LoRAs are extracted and hashed correctly

### 12. VAE Metadata Test
**Purpose:** Test VAE name and hash capture

**What to test:**
- Workflow with explicit VAE loader
- Verify metadata contains:
  - `VAE: vae_name.safetensors`
  - `VAE hash: abc123`

### 13. Embedding Resolution Test
**Purpose:** Test embedding name resolution and hashing

**What to test:**
- Workflow with embeddings in prompts
- Verify metadata contains:
  - `Embedding_1: embedding_name`
  - `Embedding_1 hash: abc123`

### 14. No Hash Detail + No LoRA Summary Test
**Purpose:** Test combined verbosity flags

**What to test:**
- Workflow with both `METADATA_NO_HASH_DETAIL` and `METADATA_NO_LORA_SUMMARY` (or UI toggle)
- Verify minimal verbose output while retaining essential information

### 15. Size Variations Test
**Purpose:** Test different image dimensions

**What to test:**
- Multiple workflows with various sizes:
  - Square: 512x512, 1024x1024
  - Portrait: 768x1344, 832x1216
  - Landscape: 1344x768, 1216x832
  - Unusual: 640x960, 896x1152
- Verify `Size: WxH` metadata is correct

### 16. High Seed Value Test
**Purpose:** Test large seed values

**What to test:**
- Workflow with very large seed values (e.g., 999999999999999)
- Verify seed is captured correctly without truncation

### 17. Zero Denoise Test
**Purpose:** Test edge case of denoise=0

**What to test:**
- Workflow with denoise set to 0.0
- Verify behavior is correct (may not generate denoise field)

### 18. Model Hash Caching Test
**Purpose:** Test .sha256 sidecar file generation and reuse

**What to test:**
- First run: Should generate .sha256 files
- Second run: Should reuse cached hashes (faster)
- Verify hash values are consistent

**Note:** This requires actual model files and may need manual verification

## Priority Recommendations

### High Priority (Most Important for Comprehensive Testing)
1. **LoRA Summary Toggle Test** - Tests a key UI option
2. **JPEG Fallback Stages Test** - Critical for understanding fallback behavior
3. **Batch Processing Test** - Common use case
4. **Sampler Selection Method Test** - Tests selection logic

### Medium Priority (Good Coverage)
5. Scheduler Variations Test
6. Denoise Strength Test
7. Shift Parameters Test
8. VAE Metadata Test
9. Inline LoRA Tags Test

### Lower Priority (Edge Cases/Less Common)
10. Hash Detail Flag Test
11. Multiple Encoder Test
12. Size Variations Test
13. Embedding Resolution Test
14. High Seed Value Test
15. Zero Denoise Test

## Implementation Notes

- Some tests require specific custom nodes to be installed (e.g., ComfyUI Prompt Control, LoRA Manager)
- Environment flag tests may need separate test scripts or documentation
- Model files and their paths need to be configured for your local environment
- Consider creating a separate test folder for specialized tests (e.g., `dev_test_workflows/advanced/`)

## Automated Testing Considerations

For fully automated testing:
- Create minimal test models/VAEs (small file sizes)
- Use consistent seed values for reproducibility
- Document expected metadata output for each workflow
- Consider creating a test fixture with known hashes
- Use small image sizes (e.g., 256x256) to speed up generation
