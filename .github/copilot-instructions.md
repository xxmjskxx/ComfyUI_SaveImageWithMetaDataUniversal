# AI Assistant Project Instructions
Concise guide for AI agents working on `ComfyUI_SaveImageWithMetaDataUniversal`. Fadiffs, reference concrete files, avoid speculative refactors.

## Architecture (What Lives Where)
**Core Pipeline**: `Trace.trace()` → `Capture.get_inputs()` → `Capture.gen_pnginfo_dict()` → `Capture.gen_parameters_str()` → `SaveImageWithMetaDataUniversal.save_images()`

**Key Modules**:
- `saveimage_unimeta/nodes/save_image.py`: Main save node + JPEG fallback handling + filename tokens
- `saveimage_unimeta/capture.py`: Metadata extraction engine + parameter string formatting
- `saveimage_unimeta/trace.py`: BFS graph traversal + sampler node detection heuristics
- `saveimage_unimeta/defs/`: Rule definitions (`captures.py`, `meta.py`, `samplers.py`, `formatters.py`)
- `saveimage_unimeta/nodes/scanner.py`: Dynamic rule discovery from installed nodes

**Rule System**: `CAPTURE_FIELD_LIST` (defaults + extensions + user JSON) merged at runtime. Scanner generates `generated_user_rules.py` from heuristic analysis.

## Critical Workflows

### Development Commands
```bash
# Lint (required before commits)
ruff check .
ruff check . --fix

# Test with proper environment
set METADATA_TEST_MODE=1
pytest -q
```

### Debug Modes (Runtime Environment Flags)
```bash
set METADATA_DEBUG_PROMPTS=1  # Verbose trace/sampler logging
set METADATA_TEST_MODE=1      # Multiline deterministic parameters
set METADATA_NO_HASH_DETAIL=1 # Suppress structured JSON hash blocks
```

### Testing Patterns
- Always use `METADATA_TEST_MODE=1` for deterministic multiline parameters
- Mock ComfyUI runtime: `conftest.py` provides stubs for `folder_paths`, `nodes`
- Test isolation: `generated_user_rules.py` uses `_test_outputs/user_rules/` directory in test mode
- JPEG fallback tests: Mock `piexif.dump()` to return oversized bytes to trigger stages

## Project-Specific Conventions

### JPEG Metadata Fallback (Critical Business Logic)
**4-Stage System**: `full` → `reduced-exif` → `minimal` → `com-marker`
- Controlled by `max_jpeg_exif_kb` (UI hard cap: 64KB)
- Stage progression triggered by EXIF size vs limit
- **Minimal allowlist** in `_build_minimal_parameters()`: prompts + core generation + LoRAs + hashes only
- Always append `, Metadata Fallback: <stage>` **exactly once** to parameter string
- Store per-image stages in `_last_fallback_stages` for testing/diagnostics

### Rule Definition Patterns
```python
# In captures.py or generated_user_rules.py
MetaField.MODEL_NAME: {
    "field_name": "ckpt_name",           # Single field
    "format": "calc_model_hash",         # Post-processor
    "validate": "lambda x: x is not None" # Skip condition
}
MetaField.LORA_MODEL_NAME: {
    "prefix": "lora_name",               # Multi-field pattern (lora_name1, lora_name2...)
    "format": "calc_lora_hash"
}
```

### Environment Flag Precedence
UI params > environment flags > defaults (e.g., `include_lora_summary` UI param overrides `METADATA_NO_LORA_SUMMARY`)

### Error Handling Philosophy
- **Metadata failures must never abort image saving**
- Wrap risky capture operations in `try/except` with graceful degradation
- Use `logger.warning()` with context rather than silent failures
- Emit `"error: see log"` placeholders for recoverable parsing issues

## External Dependencies & Integration

### ComfyUI Runtime Boundaries
- `folder_paths.get_output_directory()` / `get_save_image_path()` for file operations
- `nodes.NODE_CLASS_MAPPINGS` for scanner discovery
- Global `hook.current_prompt` / `hook.current_save_image_node_id` for graph context
- Tests provide stubs; production requires ComfyUI runtime

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