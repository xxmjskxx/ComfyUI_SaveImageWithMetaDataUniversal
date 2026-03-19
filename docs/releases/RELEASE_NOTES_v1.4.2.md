# Release Notes — v1.4.2

**Release Date:** 2026-03-19
**Commits:** 45 since v1.4.1
**Files Changed:** 19 files (+2,290 / -281)
**Tag:** [`v1.4.2`](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/releases/tag/v1.4.2)

## Overview

Version 1.4.2 is a targeted metadata-correctness release. It closes gaps between runtime capture and the workflow validator by improving prompt routing through guider and conditioning nodes, expanding runtime fallback capture for fields commonly missed in real workflows, and tightening validator expectations so they line up with actual saved metadata.

This release also addresses upstream tracker items #87, #89, #92, and #94.

## Highlights

### Prompt Capture and Routing Fixes

- `saveimage_unimeta/defs/validators.py` now routes positive and negative branches generically through guider and conditioning-router nodes instead of relying only on narrow class-specific handling.
- Nodes registered through prompt capture rules are treated as text encoders, which fixes prompt detection for `Prompt (LoraManager)` without adding more brittle class-name checks.
- Added prompt extraction support for `TextEncodeQwenImageEditPlus` and related image-edit workflows.

### Runtime Metadata Fallback Coverage

- `saveimage_unimeta/capture.py` now recovers `Steps`, `Seed`, `Denoise`, `Size`, and `Scheduler` from upstream save-node inputs when sampler-local extraction is missing.
- Base capture definitions now include `Denoise` on `KSampler` and `weight_dtype` on `UNETLoader`.
- Civitai sampler and scheduler normalization is more robust, and weight-dtype handling now accepts values such as `fp8_e4m3fn_fast`.

### Validator Hardening

- `tests/tools/validate_metadata.py` now resolves nested seed/noise chains, route-specific T5/CLIP prompts, prompt-side CLIP model names, `stop_at_clip_layer` clip-skip fields, baked `VAE` / `VAE hash`, `Batch index`, and indexed `CLIP_N Model name` fields.
- LoRA stack extraction now preserves expected ordering between local stack entries and inherited stack references, including structured LoraManager data and linked loader text sources.
- Reverse coverage validation now recognizes grouped field aliases and display-name aliases, which removes several false missing-field reports.
- `Save Custom Metadata Rules` `save_mode` is restored as a proper dropdown choice input.

### Tracked Fixes

- Resolves upstream tracker items #87, #89, #92, and #94 as part of the v1.4.2 metadata and compatibility cleanup.

### Testing and Validation

- Added focused regression coverage for guider prompt routing, conditioning routers, Qwen image-edit prompt extraction, fallback capture paths, reverse-coverage aliases, batch indices, baked-VAE checks, and workflow assignment logic.
- `python -m pytest -q` passes with `1110 passed, 8 warnings`.
- `python -m ruff check .` passes cleanly.
- The metadata-validator flow used by `tests/tools/validate_metadata.py` and its batch wrapper now passes on the current real-output validation set for this release scope.

## Breaking Changes

None.

## Upgrade Notes

No migration is required. If you rely on the workflow validator for regression testing, rerunning your normal metadata-validation batch after updating is enough to pick up the new routing and field-coverage fixes.
