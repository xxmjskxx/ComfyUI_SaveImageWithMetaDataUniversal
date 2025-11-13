# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
_No changes yet._

## [1.2.3] - 2025-11-13
### Fixed
- Resolved AttributeError in ComfyUI 0.3.65+ cache flows (compat wrapper + capture robustness).
- Added missing `get_cache` alias ensuring forward compatibility (Issue #29 continuity from prior groundwork).
- Minor README clarifications (rerun nodes note) and typo corrections.

### Changed
- Path normalization (`_test_outputs` → `tests/_test_outputs`) carried forward; documentation note on workflow rerun behavior.

### Internal
- Merge PR #51 and #52 consolidated compatibility work introduced earlier but not present in v1.2.2 tag.
- Backfills release notes accuracy for earlier mistaken attribution.

### Notes
- This release contains the compatibility fix previously (incorrectly) listed under 1.2.2. See 1.2.2 Errata.

## [1.2.2] - 2025-11-12
### Fixed
- Lint compliance adjustments to test metadata validation script (`validate_metadata.py`) for ruff 120 char limit.
- Minor sampler name recovery heuristics documented (no breaking changes).

### Changed
- Improved error message formatting for LoRA name mismatches and missing LoRAs.
- Structured internal functions now use wrapped long lines for readability within tooling constraints.
- Added ComfyUI cli test scripts and workflows to `tests\comfyui_cli_tests`.
- Changed all references of `_test_outputs` to `tests/_test_outputs`.
- Update version in `saveimage_unimeta/capture.py` to 1.2.2.

### Internal
- Follow‑up to undocumented 1.2.1; consolidates sampler fallback and validation script lint compliance.
### Errata
- The ComfyUI 0.3.65+ AttributeError fix and `get_cache` alias were not in the v1.2.2 tag; they landed later and are correctly part of 1.2.3.

## [1.2.1] - 2025-10-15
### Added
- Compatibility wrapper `_OutputCacheCompat` for evolving ComfyUI API (supports `get_output_cache`).
- Expanded CLI workflow validation utilities (`tests/comfyui_cli_tests/validate_metadata.py`, workflow JSON fixtures) covering sampler, prompt, LoRA, embedding, size, and fallback scenarios.
- Additional workflow test JSONs for large JPEG/WebP metadata fallback edge cases and dual‑prompt Flux variants.
- Test `test_output_cache_compat.py` ensuring wrapper behavior.

### Changed
- Refined capture traversal to gracefully skip absent prompt executer caches without aborting image save.
- Improved sampler name recovery heuristics (graph introspection + token scan) prior to 1.2.2 robustness tweaks.
- Cleaned test imports & trimmed legacy artifacts for faster CI feedback.

### Fixed
- Minor path and casing inconsistencies in workflow test fixtures.
- Early fallback handling for missing Flux dual prompts (T5 / CLIP) in validation paths.

### Internal
- Foundation work preparing for 1.2.2 capture robustness; this release documents previously unrecorded changes between v1.2.0 and v1.2.2.

## [1.2.0] - 2025-09-26
### Added
- Tests: missing-only lens behavior, forced sampler role retention, scanner cache path parity.
- Dummy `KSampler` test shim for stable sampler detection under test mode.
- Benchmark relocated to `tests/bench/bench_merge_performance.py` (no runtime surface impact).
- Initial coverage threshold enforcement (fail-under 35%) with multi-version matrix (3.10–3.12).
- Baseline rule cache in `Metadata Rule Scanner` (diff report: `BaselineCache=hit:X|miss:Y`).
- Dropdown backup restore selector for `Save Custom Metadata Rules` (`restore_backup_set`).
- Central diff parsing helper (`tests/diff_utils.parse_diff_report`).
- Scanner tests for forced metafield retention and cache hit accounting.

### Changed
- Scanner semantics clarified: `include_existing=False` activates missing-only lens (documentation + logs). (Interim experiment to default True was reverted before release; final default remains False — no breaking change to prior public behavior.)
- Unified test artifact isolation: writer, loader, and scanner prefer `_test_outputs/user_rules` in `METADATA_TEST_MODE`.
- Path parity updates for user rule JSON (writer + scanner mtime cache logic).
- Moved `MIGRATIONS.md` to `docs/`.
- Consolidated dual CI workflows into single `unimeta-ci.yml` (matrix tests, coverage, strict & autofix lint jobs).
- Clarified scanner `include_existing` tooltip (explicit include vs missing-only lens when disabled) and expanded `rules_json_string` tooltip (schema guidance, allowed rule keys).

### Removed
- Root `folder_paths.py` test stub (tests supply their own stub early).
- Legacy example user rule JSON files and obsolete design scratch file.

### Fixed
- Loader runtime test-mode path detection (ensures user JSON merges correctly under coverage import order).
- Coverage “No source for code” error: placeholder `generated_user_rules.py` + coverage omit.
- Timestamp helper now validates optional `-N` suffix correctly.
- Failing append placeholder test due to path mismatch after isolation changes.
- Potential stale baseline in scanner cache when isolated test directory used.
- Narrowed broad `Exception` catches in migration fallback to `OSError` (reduces risk of swallowing logic errors).
- Removed duplicate registration block in missing-lens sampler roles test.
- Minor tooltip long-line wrapping & consistency adjustments across nodes.

## [1.1.2] - 2025-09-26
### Added
- Collapsible README section pattern unified ("More:" details blocks) for improved scanability.
- Migration guide relocated to `docs/MIGRATIONS.md` (clearer docs structure).
### Changed
- README Quick Start simplified (heading outside collapsible + consistent details styling).
- Refined documentation anchors & internal links for fallback tips and parameters.
### Fixed
- Benchmark script now ensures `_test_outputs` directory exists before writing JSON output.
- Eliminated duplicated `METADATA_TEST_MODE` parsing in tests via new `metadata_test_mode` fixture (reduces drift risk).

## [1.1.1] - 2025-09-25
### Added
- Benchmark script `bench_merge_performance.py` (verifies sampler merge helper adds <5% overhead; ~4.8% in synthetic test).
- Negative tests for malformed capture and sampler user JSON structures (ignored safely without clobbering).
- CI matrix expanded to run with and without `METADATA_TEST_MODE` across supported Python versions.
### Changed
- Refactored loader merge logic: extracted `_merge_user_sampler_entry`, `_merge_extension_capture_entry`, `_merge_user_capture_entry` for clarity & maintainability.
- Simplified sampler per-key merge with validation and shallow update semantics encapsulated in helper.
- Clarified `METADATA_TEST_MODE` parsing (only explicit truthy tokens enable test mode; "0" no longer truthy).
- Improved readability of selector utilities (updated `selectors.py`).
### Fixed
- Loader now skips non-mapping sampler entries instead of overwriting with invalid data.
- Conditional tests now skip gracefully when baseline definitions intentionally empty under test mode.

## [1.1.0] - 2025-09-24
Note: 1.0.0 was the first public registry release; this minor release formalizes post‑1.0 refactor cleanup (shim removal) and new UI/node enhancements.

### Added
- Node: `Show Any (Any to String)` — accepts any input, converts to STRING, displays on canvas; supports batching.
- Frontend: `web/show_text_unimeta.js` extended to handle `ShowAny|unimeta` and `ShowText|unimeta` with robust payload parsing.
- Frontend: Dynamic textarea sizing and node recompute to reduce overlap at small zoom levels.
- Tests: `tests/test_show_any.py` covering `_safe_to_str`, UI/result shapes, workflow widget persistence, and wildcard `AnyType` semantics.
- Docs: Expanded README sections (ToC sync, sampler selection, metadata list, JPEG fallback tips). Japanese README aligned to English.
- Save node option `suppress_missing_class_log` to suppress informational missing class list log (reduces noise in large graphs).

### Changed
- Frontend separation: `web/show_text.js` now targets base `ShowText` only to avoid double initialization with UniMeta variants.
- Improved truncation suffix documentation and test expectations for `_safe_to_str`.
- Removed legacy compatibility shim `saveimage_unimeta/nodes/node.py`; direct imports now required:
	- `SaveImageWithMetaDataUniversal` → `saveimage_unimeta.nodes.save_image`
	- `SaveCustomMetadataRules` → `saveimage_unimeta.nodes.rules_writer`
	- `MetadataRuleScanner` → `saveimage_unimeta.nodes.scanner`
	- Centralized EXIF test monkeypatch target: `saveimage_unimeta.piexif_alias.piexif`.

### Fixed
- Prevented double widget injection causing textarea overlap in UniMeta nodes.
- UI display not updating for `ShowAny|unimeta` in certain payload shapes (now reads `message.ui.text`).
- Readme anchor correction for `Format & Fallback Quick Tips`.

## [0.2.0] - 2025-09-19
### Added
- `MetadataRuleScanner` scanning node (rule suggestion) separate from force include config.
- `MetadataForceInclude` node to manage globally forced node class names.
- Global registry `FORCED_INCLUDE_CLASSES` with helpers: `set_forced_include`, `clear_forced_include`.

### Changed
- Split concerns: scanning vs forced class configuration (previous single scanner responsibilities divided into two nodes).
- Improved description wrapping for `SaveImageWithMetaDataUniversal` to satisfy style guidance.

### Metadata Fallback
- Maintained multi-stage JPEG metadata fallback: full EXIF → reduced-exif → minimal → COM marker with fallback annotation.

### Notes
- Remaining long lines in `node.py` are legacy and will be incrementally cleaned.

---

[Unreleased]: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.2.2...HEAD
[1.2.3]: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.1.2...v1.2.0

## [0.1.0] - 2025-09-20 (Initial Internal Release)
Baseline derived from upstream [`nkchocoai/ComfyUI-SaveImageWithMetaData`](https://github.com/nkchocoai/ComfyUI-SaveImageWithMetaData/) with extensive architectural and feature expansion aggregated prior to release.

### Nodes Introduced
| Node | Purpose |
| ---- | ------- |
| `SaveImageWithMetaDataUniversal` | Core image save + enriched metadata & parameters (PNGInfo / EXIF / WebP). |
| `Metadata Rule Scanner` | Analyze installed nodes, suggest capture rules & sampler associations. |
| `Save Custom Metadata Rules` | Persist accepted rule suggestions to user rules file. |
| `Metadata Force Include` | Manage globally forced node class names for guaranteed capture. |
| `Create Extra MetaData` | Inject arbitrary additional key-value pairs. |
| `Show generated_user_rules.py` | Display merged user rules for review/edit. |
| `Save generated_user_rules.py` | Validate and write edited rules back to disk. |
| `Show Text (UniMeta)` | Display connected text outputs (local variant). |

### Core Additions
- Universal capture pipeline (`Capture` + dynamic rule loading) covering prompts, models, VAEs, LoRAs, embeddings, samplers, guidance, shift, clip models.
- Multi-format save: PNG (PNGInfo), lossless WebP, JPEG (EXIF) with staged fallback and parameter string annotation.
- Dynamic rule generation workflow: `Metadata Rule Scanner` + `Save Custom Metadata Rules` nodes; persisted user rule file merge logic.
- Global forced include management via `Metadata Force Include` node and `FORCED_INCLUDE_CLASSES` registry.
- Parameter string generation aligned with Automatic1111 style (single-line) plus test mode (multiline) for deterministic snapshots.
- Hash caching using `.sha256` sidecars for model, VAE, LoRA (truncated SHA256 display, reused once computed).
- LoRA detection (single, stacked loaders, inline prompt tags) with optional summary + per-item detail lines.
- Filename token system with truncation (`%pprompt:[n]%`, `%model:[n]%`, timestamp patterning).
- Environment flag system (runtime evaluated) for hash detail suppression, LoRA summary suppression, test mode formatting, and prompt debug logging.

### JPEG Metadata Fallback System
- Size-aware staged degradation: full → reduced-exif → minimal → com-marker.
- Minimal stage allowlist retains prompts, sampler core settings, seed, model/vae names+hashes, hash summary, generator version, LoRAs.
- Automatic annotation `Metadata Fallback: <stage>` appended only once to parameter string.
- Configurable UI cap `max_jpeg_exif_kb` (hard limit 64KB) with recommendations.

### Sampler & Graph Intelligence
- BFS trace + sampler heuristic selection (`Trace`) with distance-based selection modes (Farthest, Nearest, By node ID).
- Heuristic fallback when sampler not explicitly matched (based on presence of key metafields like Steps/CFG).

### Metadata Integrity & Ordering
- Stable key ordering; only append new fields to avoid churn.
- Consistent trimming rules for minimal fallback to preserve downstream parsing reliability.
- Comma replacement with `/` in extra metadata values to avoid downstream naive split issues.

### Developer / Maintenance Enhancements
- Central AI assistant instructions (`.github/copilot-instructions.md`) describing architecture, constraints, safe-edit rules.
- Expanded README with quick tips, fallback behavior explanation, environment flags table, filename token reference.
- Logging over raw prints; debug flags for prompt capture.
- Testing support: multiline deterministic parameters under `METADATA_TEST_MODE`.

### Archived / Deferred (Documented Separately)
- Archived prototype in `web/disabled/metadata_rule_scanner/` (editor UI) documented in `docs/FUTURE_AND_PROTOTYPES.md`.
- Workflow compression placeholder design (`docs/WORKFLOW_COMPRESSION_DESIGN.md`).

### Compatibility / Interop
- Civitai-aligned sampler & CFG mapping option (`guidance_as_cfg`, `civitai_sampler`).
- Lossless WebP parity with PNG for workflow embedding.

### Security / Performance
- Avoid repeated hashing by sidecar reuse; truncated display for readability.
- No multi-segment EXIF writes (explicitly out-of-scope for simplicity & compatibility).

### Breaks / Differences From Upstream
- Separation of scanning vs forced include responsibilities into dedicated nodes.
- JPEG fallback semantics and parameter string marker (not present upstream).
- Extended LoRA and embedding hashing & display structures.
- Environment flag driven runtime behavior toggles (no restart required).

---

