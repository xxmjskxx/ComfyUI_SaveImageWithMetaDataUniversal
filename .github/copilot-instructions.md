# AI Assistant Project Instructions
Concise guide for AI agents working on `ComfyUI_SaveImageWithMetaDataUniversal`. Favor minimal diffs, reference concrete files, avoid speculative refactors.

## Architecture (What Lives Where)
`saveimage_unimeta/nodes/node.py`: Save node + auxiliary nodes; builds PNGInfo/EXIF, handles JPEG fallback, filename tokens.
`saveimage_unimeta/defs/`: Capture definitions (`captures.py` = `CAPTURE_FIELD_LIST`, `meta.py` = `MetaField`, `samplers.py`, `combo.py`).
`saveimage_unimeta/trace.py`: BFS trace + sampler heuristics.
`Capture` (imported): Generates ordered metadata dict + parameter string using loaded rules.
Forced include + rule generation handled by separate nodes; merged via `FORCED_INCLUDE_CLASSES` before capture. Hash helpers & embedding/lora utilities in `saveimage_unimeta/utils/` (hash, lora, embedding).

## External Dependencies
Relies on ComfyUI runtime (`folder_paths`, sampler nodes), Pillow (`PIL`), optional `piexif`. Provide stubs when unavailable (tests).
Avoid adding heavy deps; prefer extending formatters.

## Dev Workflows
Run lint: `ruff check .`  (keep code style consistent).
Run tests (if present): `pytest -q` (multiline parameter mode via `METADATA_TEST_MODE=1`).
Keep all test scripts in 'tests'.
Write any test file outputs to '_test_outputs'.
Manual debug: set `METADATA_DEBUG_PROMPTS=1` or temporarily raise logger level for module.
Validate JPEG fallback: lower `max_jpeg_exif_kb` (e.g. 8) and confirm staged marker progression.

## Core Flow
1. Trace upstream (`Trace.trace`). 
2. Pick sampler (`Trace.find_sampler_node_id`). 
3. Build dict (`Capture.gen_pnginfo_dict`).
4. Render parameters (`Capture.gen_parameters_str`). 
5. Save PNG (PNGInfo) or JPEG/WebP (EXIF → fallback if oversize).

## JPEG Fallback Logic
APP1 limit ~64KB. Stages: full → `reduced-exif` (params only) → `minimal` (trim allowlist) → `com-marker` (no EXIF, comment marker). Append `, Metadata Fallback: <stage>` once.
Allowlist in `_build_minimal_parameters`: prompts header + {Steps, Sampler, CFG scale, Seed, Model, Model hash, VAE, VAE hash, Hashes, Metadata generator version, all Lora_*}.
Per-image stage logged + stored in `_last_fallback_stages`.

## Sampler Detection
Exact match in `SAMPLERS` else heuristic: rule includes `MetaField.SAMPLER_NAME` or both `STEPS` & `CFG`.
Selection method (`SAMPLER_SELECTION_METHOD`): Farthest | Nearest | By node ID.

## Environment Flags (Runtime Evaluated)
`METADATA_NO_HASH_DETAIL`, `METADATA_NO_LORA_SUMMARY`, `METADATA_TEST_MODE`, `METADATA_DEBUG_PROMPTS`,
`METADATA_HASH_LOG_MODE`, `METADATA_HASH_LOG_PROPAGATE`, `METADATA_FORCE_REHASH`, `METADATA_DUMP_LORA_INDEX`.
UI param `include_lora_summary` overrides env. Test mode switches to multiline parameters.
Hash log modes: none|filename|path|detailed|debug. Propagate off with `METADATA_HASH_LOG_PROPAGATE=0` to keep noise local. `METADATA_FORCE_REHASH=1` bypasses sidecar reuse for mismatch debugging. `METADATA_DUMP_LORA_INDEX` dumps LoRA index JSON (value `1` → `_lora_index_dump.json`).

## Hashing & Caching
Model / VAE / LoRA hashes via helpers in `formatters.py`; truncated sha256 (10 chars). Sidecar `.sha256` reused if present; create if absent. Full 64‑char digest only in sidecar / debug log. Force recompute with `METADATA_FORCE_REHASH=1`.

## Filename Tokens
`%seed%`, `%width%`, `%height%`, `%pprompt%[:n]`, `%nprompt%[:n]`, `%model%[:n]`, `%date%` or `%date:pattern%` (yyyy, MM, dd, hh, mm, ss).

## Conventions
No raw `print`; use module logger.
Wrap tooltips ≤ ~140 chars (exclude the description field in pyproject.toml from this rule).
Replace commas in extra metadata values with `/` to avoid downstream split issues.
Keep ordering stable; only append new fields.

## Safe Edit Rules
Do not raise 64KB JPEG EXIF cap without updating README.
Preserve fallback marker semantics.
Keep `_last_fallback_stages` contract.
Document new env flags immediately (README Environment Flags + this file). Keep runtime evaluation (no restart).

## Adding Metadata Fields
Add rule in `captures.py` (or extension file). If it should survive minimal trimming, add its key to `_build_minimal_parameters` allowlist. Regenerate parameters; test with low `max_jpeg_exif_kb`.

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

---
Always return minimal diffs; ask only when blocked by missing context.