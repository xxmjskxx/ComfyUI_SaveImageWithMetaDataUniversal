# Validate Metadata Script Fixes

## Summary

This document describes the fixes applied to `validate_metadata.py` and related components to address metadata parsing issues reported during development testing.

## Issues Fixed

### 1. Metadata Parser Not Detecting Required Fields

**Problem**: The `parse_parameters_string` method was only handling newline-separated metadata format. When metadata was in comma-separated format (the default for non-test mode), fields like "Steps", "Sampler", "CFG scale", and "Seed" were not being detected.

**Solution**: Updated the parser to detect and handle both formats:
- **Comma-separated format**: `"Steps: 2, Sampler: euler, CFG scale: 7, ..."`
- **Newline-separated format**: `"Steps: 2\nSampler: euler\nCFG scale: 7\n..."`

The parser now:
1. Analyzes the metadata to determine which format is being used
2. Uses appropriate splitting logic for each format
3. Correctly handles LoRA fields like "Lora_0 Model name", "Lora_0 Model hash", etc.
4. Properly distinguishes between prompt headers (T5 Prompt, CLIP Prompt, Negative prompt) and actual metadata fields

### 2. Complex Filename Pattern Matching

**Problem**: The workflow `filename_format_denoise.json` uses a complex filename pattern:
```
Test\siwm-%model:10%/%pprompt:20%-%nprompt:20%/%seed%-%width%x%height%_%date:yyyyMMdd-hhmmss%
```

The old pattern extraction logic wasn't properly extracting "siwm" from this complex path with subdirectories and multiple tokens.

**Solution**: Improved `extract_filename_patterns` to:
- Split paths by both forward slash (`/`) and backslash (`\`)
- Remove all token patterns (`%...%`) from each path component
- Clean up remaining separators (hyphens, underscores, slashes)
- Extract meaningful pattern identifiers like "siwm"

### 3. Special Workflow Handling

**Problem**: The workflow `1-scan-and-save-custom-metadata-rules.json` doesn't create images—it only generates metadata rules. The validator was incorrectly warning about missing Save Image nodes.

**Solution**: Added special case handling to skip this workflow with an informational message explaining that it generates rules, not images.

### 4. Missing Test Workflow Files

**Problem**: The problem statement mentioned `large-workflow-jpeg-4kb.json`, but this file didn't exist in the repository.

**Solution**: Created the missing workflow file by copying and modifying `large-workflow-jpeg-8kb.json` with the appropriate `max_jpeg_exif_kb` setting.

### 5. JPEG Fallback Stage Testing

**Problem**: The minimum value for `max_jpeg_exif_kb` was 4KB, but even at 4KB the metadata only reached the "reduced-exif" fallback stage. The reduced-exif metadata is only about 2KB, so lower thresholds were needed to test "minimal" and "com-marker" fallback stages.

**Solution**:
1. Reduced minimum `max_jpeg_exif_kb` from 4 to 1 in `save_image.py`
2. Created additional test workflow files:
   - `large-workflow-jpeg-4kb.json` (tests reduced-exif stage)
   - `large-workflow-jpeg-2kb.json` (tests minimal stage)
   - `large-workflow-jpeg-1kb.json` (tests com-marker stage)

## Files Modified

### `validate_metadata.py`
- Rewrote `parse_parameters_string` method to handle both comma-separated and newline-separated formats
- Enhanced `extract_filename_patterns` to handle complex paths with tokens
- Added special case handling for `1-scan-and-save-custom-metadata-rules.json`
- Updated `KNOWN_KEY_PATTERNS` to include LoRA and Embedding field patterns

### `saveimage_unimeta/nodes/save_image.py`
- Changed `max_jpeg_exif_kb` minimum from 4 to 1

## New Files Created

### Test Workflow Files
- `tests/comfyui_cli_tests/dev_test_workflows/large-workflow-jpeg-4kb.json`
- `tests/comfyui_cli_tests/dev_test_workflows/large-workflow-jpeg-2kb.json`
- `tests/comfyui_cli_tests/dev_test_workflows/large-workflow-jpeg-1kb.json`

### Test Files
- `tests/test_validate_metadata.py` - Unit tests for the validator components
- `tests/test_validate_metadata_integration.py` - Integration tests with real workflows

## Test Coverage

All new functionality is covered by tests:
- ✅ Comma-separated metadata format parsing
- ✅ Newline-separated metadata format parsing
- ✅ LoRA field parsing
- ✅ Dual-encoder prompt (T5 + CLIP) handling
- ✅ Complex filename pattern extraction
- ✅ Image to workflow matching logic
- ✅ Special workflow skip behavior
- ✅ JPEG workflow configurations

## Usage

The `validate_metadata.py` script now correctly validates:

```bash
# Validate test outputs
python tests/tools/validate_metadata.py --output-folder "/path/to/ComfyUI/output/Test"

# With custom workflow directory
python tests/tools/validate_metadata.py --output-folder "./output/Test" --workflow-dir "./my_workflows"

# With log file
python tests/tools/validate_metadata.py --output-folder "./output/Test" --log-file "./validation.log"
```

### Validation Summary

The script now provides a comprehensive summary including:

```
======================================================================
Validation Summary:
  Total Images Validated: 21
  ✓ Passed:               21
  ✗ Failed:               0
  ⚠ Unmatched Images:     0
  ⚠ Unmatched Workflows:  0
======================================================================
```

- **Total Images Validated**: Number of images successfully matched to workflows and validated
- **Passed**: Images with valid metadata matching workflow expectations
- **Failed**: Images with metadata issues or missing required fields
- **Unmatched Images**: Images in the output folder that don't match any workflow pattern
- **Unmatched Workflows**: Workflows with save nodes but no matching output images

## Known Limitations

### Wan21 Workflow - METADATA GENERATION ISSUES IDENTIFIED ⚠️

**Important Update**: The wan21 workflow includes **metadata generation issues** (not parsing issues):

**Issues Found**:
1. **Phantom embeddings**: The workflow contains NO embedding nodes, yet 2 embeddings are being recorded
2. **Prompts as embedding data**: The positive and negative prompts are being incorrectly recorded as embedding names and hashes
3. **Wrong Hashes indexing**: Embeddings appear as "embed:3" and "embed:4" instead of "embed:EmbeddingName"
4. **Trailing punctuation**: Embedding names with trailing commas (e.g., "EasyNegative,,") cause hash computation failures

These are **saveimage_unimeta metadata generation bugs**, not validation script issues.

**Validation Script Enhancements**:
To help catch these issues, the validation script now detects:
- ✅ **N/A values**: Any field containing "N/A" is flagged as an error
- ✅ **Prompts as embeddings**: Embedding names/hashes longer than 100/70 characters (suggests prompts)
- ✅ **Trailing punctuation**: Embedding names ending with commas or other punctuation
- ✅ **Missing Hashes entries**: Models/LoRAs/embeddings with metadata but missing from Hashes summary
- ✅ **Wrong Hashes keys**: Embeddings with numeric keys (e.g., "embed:10") instead of name-based keys

The image `tests/comfyui_cli_tests/dev_test_workflows/Wan21_00001_.png` demonstrates these issues. The validation script successfully detects all the problems listed above.

### Flux LoRA Manager Workflow
The problem statement mentions difficulty exporting a working API version of `flux-LoRA-Manager.json`. This is a ComfyUI UI/API export issue, not a validation script issue. Users should ensure:
1. Dev Mode is enabled in ComfyUI settings
2. Using "Save (API format)" instead of regular save
3. The workflow is fully connected and has no missing nodes

## Testing Recommendations

To fully validate these fixes with actual images:

1. Run the dev workflows:
   ```bash
   python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "/path/to/ComfyUI" \
     --output-folder "/path/to/output/Test"
   ```

2. Validate the generated images:
   ```bash
   python tests/comfyui_cli_tests/validate_metadata.py --output-folder "/path/to/output/Test"
   ```

3. Expected results:
   - ✅ `1-scan-and-save-custom-metadata-rules.json` - Skipped with info message
   - ✅ `extra_metadata_clip_skip.json` - All fields detected
   - ✅ `filename_format_denoise.json` - Images matched to workflow
   - ✅ `flux-CR-LoRA-stack-ClownsharK.json` - CFG scale (or Guidance) detected
   - ✅ `flux-PC-LoRA-inline-Inspire-KSampler.json` - CFG scale (or Guidance) detected
   - ✅ `large-workflow-jpeg-4kb.json` - Fallback: reduced-exif
   - ✅ `large-workflow-jpeg-2kb.json` - Fallback: minimal
   - ✅ `large-workflow-jpeg-1kb.json` - Fallback: com-marker
   - ✅ Other workflows - Metadata validated correctly

## Future Improvements

1. **Workflow Export Tool**: Consider creating a helper tool to ensure workflows are properly exported in API format
2. **Validation Report**: Add option to generate HTML/JSON validation reports
3. **Image Metadata Viewer**: Create a companion tool to view and verify metadata in individual images
