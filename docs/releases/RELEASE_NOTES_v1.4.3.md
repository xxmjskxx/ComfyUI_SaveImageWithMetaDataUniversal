# Release Notes — v1.4.3

**Release Date:** 2026-07-21
**Commits:** 8 merged PRs since v1.4.2
**Tag:** [`v1.4.3`](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/releases/tag/v1.4.3)

## Overview

Version 1.4.3 is a maintenance patch release that bundles LoRA Manager hash and path-resolution fixes,
extra-metadata robustness improvements, several targeted bugfixes, and minor UI/UX enhancements. All changes
are backward-compatible with no migration required.

## Highlights

### LoRA Manager: Hash Detection & Extra Paths

- LoRA Loader (LoraManager) hash calculation now works correctly when structured payloads with active-flag
  fields are present, and scalar fallback strength parsing handles list/tuple widget values. (#128)
- `build_lora_index` now includes LoraManager-configured extra LoRA paths with cross-platform path
  deduplication, preventing double-walks when the same path appears in multiple sources. (#127, #129)
- Extra directory support extended to embeddings, checkpoints, and UNet models — model file resolution now
  searches LoraManager-configured extra paths for all model types. (#133)

### Extra Metadata Robustness

- Extra metadata values no longer have commas silently replaced with slashes, making
  `CreateExtraMetaDataUniversal` usable for storing prompt text that naturally contains commas. (#126)
- `CreateExtraMetaDataUniversal` now uses a configurable `EXTRA_METADATA_PAIR_COUNT` constant to generate
  key/value input fields dynamically, replacing the previous hardcoded 4-pair limit. The node's `FUNCTION`
  accepts variable positional/keyword arguments with normalization and validation. (#63, #137)

### Bugfixes

- `_is_advanced_mode` in `efficiency_nodes.py` now accepts both `list` and `tuple` input batch types,
  matching the same fix pattern already applied to `rgthree.py`. This prevents incorrect LoRA strength
  metadata for Efficiency nodes in workflows where ComfyUI passes tuple batches. (#88, #135)
- Removed redundant duplicate `_find_ci("t5 prompt")` call in capture fallback logic. (#135)
- `is_node_connected` cache in `validators.py` now invalidates stale entries when the prompt graph changes
  between calls, preventing incorrect connection-state results across different workflows. (#135)

### UI & Developer Experience

- Advanced UI toggle (`advanced: True`) added for `suppress_missing_class_log` and `model_hash_log`
  parameters, reducing clutter in the save-node widget panel. (#138)
- Filename prefix tooltip enhanced with subdirectory support documentation and clarified token usage. (#136)
- CI lint-autofix job now correctly checks out the pull request head repository and ref for fork-PR
  workflows, fixing false negatives.

### Testing and Validation

- Added tests for tuple input batch handling in efficiency helpers, connection cache invalidation on prompt
  graph changes, and dynamic extra metadata pair count.
- `python -m pytest -q` passes with existing test suite coverage for all changed modules.
- `python -m ruff check .` passes cleanly.

## Breaking Changes

None.

## Upgrade Notes

No migration is required. Update the node pack and restart ComfyUI — all changes are additive and
backward-compatible. Users of the LoraManager custom node will see improved hash resolution and model-file
discovery without any configuration changes.

## What's Changed
* Stop replacing commas with slashes in extra metadata values by @Copilot in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/126
* Fix Lora Loader (LoraManager) not finding LoRA hashes by @Copilot in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/128
* Fix lora manager hash calculation — extra paths support by @Mossbraker in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/129
* LoraManager extra paths for all model types by @Mossbraker in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/133
* Bugfixes: tuple type check, redundant code, cache invalidation by @Mossbraker in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/135
* Enhance filename prefix tooltip with subdirectory support by @Mossbraker in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/136
* Dynamic key-value pairs for CreateExtraMetaDataUniversal by @Mossbraker in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/137
* Advanced toggle for suppressing missing class/model hash logs by @Mossbraker in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/138

**Full Changelog**: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.4.2...v1.4.3
