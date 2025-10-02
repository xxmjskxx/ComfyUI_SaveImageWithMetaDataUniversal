# AI Assistant Project Instructions
ComfyUI extension for saving images with metadata. Focus on tested patterns, minimal diffs.

## Core Architecture
**Pipeline**: `Trace.trace()` → `Capture.get_inputs()` → `Capture.gen_pnginfo_dict()` → `Capture.gen_parameters_str()` → `SaveImageWithMetaDataUniversal.save_images()`

**Key Files**:
- `saveimage_unimeta/capture.py`: Metadata extraction + parameter formatting
- `saveimage_unimeta/trace.py`: Graph traversal + sampler detection  
- `saveimage_unimeta/nodes/save_image.py`: Main save node + JPEG fallback
- `saveimage_unimeta/defs/meta.py`: MetaField enum + field definitions
- `saveimage_unimeta/nodes/scanner.py`: Dynamic rule discovery

## Development Workflow
```bash
# Lint before commits
ruff check . --fix

# Test with deterministic output
set METADATA_TEST_MODE=1
pytest -q
```

## JPEG Fallback System (Critical)
**4 Stages**: `full` → `reduced-exif` → `minimal` → `com-marker`
- Trigger: EXIF size > `max_jpeg_exif_kb` (UI capped at 64KB)
- **Always append** `, Metadata Fallback: <stage>` exactly once to parameter string
- Minimal stage keeps: prompts + core generation + LoRAs + hashes only
- Implementation: `saveimage_unimeta/nodes/save_image.py` → `save_images()`

## Rule System Patterns
```python
# Single field capture
MetaField.MODEL_NAME: {
    "field_name": "ckpt_name",
    "format": "calc_model_hash"
}

# Multi-field pattern  
MetaField.LORA_MODEL_NAME: {
    "prefix": "lora_name",  # matches lora_name1, lora_name2...
    "format": "calc_lora_hash"
}
```

## Environment Flags (Debug/Test)
```bash
set METADATA_TEST_MODE=1      # Multiline deterministic parameters
set METADATA_DEBUG_PROMPTS=1  # Verbose trace logging
set METADATA_NO_HASH_DETAIL=1 # Hide JSON hash blocks
```

## Testing Conventions
- Use `METADATA_TEST_MODE=1` for reproducible output
- Mock ComfyUI: `conftest.py` provides stubs for `folder_paths`, `nodes`
- JPEG tests: Mock `piexif.dump()` returning oversized bytes triggers fallback stages
- Test isolation: `generated_user_rules.py` uses `_test_outputs/user_rules/` in test mode

## Error Handling Rules
- **Metadata failures never abort image saving**
- Wrap risky operations in `try/except` with graceful degradation
- Use `logger.warning()` with context (node ID, field name)
- Skip malformed fields rather than emit placeholders (except `"error: see log"` for recoverable issues)

## Common Tasks
- **Add MetaField**: Edit `saveimage_unimeta/defs/meta.py`
- **Modify sampler detection**: Edit `saveimage_unimeta/trace.py` → `is_sampler_like()`
- **Change parameter format**: Edit `saveimage_unimeta/capture.py` → `gen_parameters_str()`
- **Update JPEG fallback**: Edit `saveimage_unimeta/nodes/save_image.py` → `save_images()`

## Critical DON'Ts
- Never reorder stable metadata keys (breaks downstream parsers)
- Never duplicate `Metadata Fallback:` markers
- Never modify `CAPTURE_FIELD_LIST` directly (use rule loading system)
- Never use `print()` (use module logger)

Always return minimal diffs; maintain stable field ordering; test with `METADATA_TEST_MODE=1`.

### Conditional Imports (Testing)
```python
try:
    import piexif
except ImportError:
    # Provide stub for tests
```

### Hashing & Caching
- Model/VAE/LoRA hashes: SHA256 truncated to 10 chars
- `.sha256` sidecar files cached; create if missing
- Hash formatters guard expensive operations with path-like detection

## Performance & Memory Patterns

### Trace Optimization
- BFS limited to reachable nodes from save node backward
- Sampler detection: exact match in `SAMPLERS` → heuristic (has `SAMPLER_NAME` field) → fallback (has both `STEPS` + `CFG`)
- Distance-based selection: Farthest | Nearest | By node ID

### Scanner Caching
- Baseline cache keyed by user rule file mtimes (avoids full reload on repeated scans)
- "Missing-only lens" filters already-captured fields for UX focus

## Common Patterns & Anti-Patterns

### DO
- Use `Capture._extract_value()` to handle varied capture tuple shapes
- Append new fields to maintain stable ordering (never reorder existing)
- Replace commas with `/` in metadata values to avoid downstream split issues
- Test both single and multi-sampler scenarios

### DON'T
- Reorder stable metadata keys (breaks downstream parsers)
- Duplicate `Metadata Fallback:` markers in parameter strings
- Use raw `print()` statements (use module logger)
- Modify `CAPTURE_FIELD_LIST` directly in production (use rule loading system)

## Error Handling & Resilience
- Metadata failures must not abort image saving: wrap risky sections in `try/except` with guarded fallback.
- Use logging rather than silent failure; include context (node id, field name).
- Use colored logging for visibility during debug runs (use `cstr` and message templates from `saveimage_unimeta/utils/color.py`).
- Fallback strategy: skip field (omit) rather than emit malformed placeholder—except where placeholders signal recoverable parsing issues (`error: see log`).

## Workflow Compression (Future)
Planned: gzip+base64 workflow JSON pre-EXIF; fallback logic unchanged; add detection marker. Leave placeholder only—don’t implement silently.

## Do / Don't
Do: use existing Capture/Trace pipeline; small diffs; update docs with behavior changes.
Don't: reorder stable keys, duplicate `Metadata Fallback:` marker, add multi-segment EXIF hacks.

## Key Files for Common Tasks
- **Add new MetaField**: `saveimage_unimeta/defs/meta.py`
- **Scanner heuristics**: `saveimage_unimeta/nodes/scanner.py` → `HEURISTIC_RULES`
- **Sampler detection**: `saveimage_unimeta/trace.py` → `is_sampler_like()`
- **Parameter formatting**: `saveimage_unimeta/capture.py` → `gen_parameters_str()`
- **JPEG fallback logic**: `saveimage_unimeta/nodes/save_image.py` → `save_images()`

Always return minimal diffs; ask for clarification only when blocked by missing domain context.