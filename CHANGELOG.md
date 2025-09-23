# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- (placeholder)

### Added
- README section detailing JPEG EXIF size limits & staged fallback behavior.
- Enhanced tooltip for `max_jpeg_exif_kb` with recommendations and fallback stage explanation.

### Changed
- Clarified documentation for `force_include_node_class` (scanner) vs global `MetadataForceInclude` node.

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

