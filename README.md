# ComfyUI-SaveImageWithMetaDataUniversal
![SaveImageWithMetaData Preview](img/save_image_with_metadata_universal.png)
> Enhanced Automatic1111‑style, Civitai-compatible metadata capture with extendend support for prompt encoders, lora and model loaders, embeddings, samplers, clip models, guidance, shift, and more.

- Extensive rework of [ComfyUI-SaveImageWithMetaData](https://github.com/nkchocoai/ComfyUI-SaveImageWithMetaData/), a custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI), that attempts to add universal support for all custom node packs, while also adding explicit support for a few custom nodes.
- The `Save Image w/ Metadata Universal` node saves images with metadata extracted from the input values of each node.
- Adds full support for saving workflows and metadata to WEBP images.
- Adds support for for saving workflows and metadata to JPEGs (limited to 64KB—only smaller workflows can be saved to JPEGs).
- Adds two new nodes `Metadata Rule Scanner` and `Save Custom Metadata Rules` which scan all installed nodes and create and save new rules for extracting their input values (I can't test with every custom node pack, but it has been working well so far).
- Since the value extraction rules are created dynamically, values output by various extension nodes can be added to metadata.

## Table of Contents
* [Quick Start](#quick-start)
* [Quick Feature Overview](#quick-feature-overview-added--extended)
* [Nodes Provided](#nodes-provided)
* [Node UI Parameters](#node-ui-parameters-key-additions)
* [JPEG Metadata Size & Fallback Behavior](#jpeg-metadata-size--fallback-behavior)
* [Metadata Rule Scanner vs Metadata Force Include](#metadata-rule-scanner-vs-metadata-force-include)
* [New Input (Scanner): force_include_node_class](#new-input-scanner-force_include_node_class)
* [Fallback Stages & Indicator](#fallback-stages--indicator)
* [Troubleshooting / FAQ](#troubleshooting--faq)
* [Design / Future Ideas](#design--future-ideas)
* [Environment Flags](#environment-flags)
* [Parameter String Formatting Modes](#parameter-string-formatting-modes)
* [Ordering Guarantees](#ordering-guarantees)
* [Contributing](#contributing-summary)
* [Filename Token Reference](#filename-token-reference)

## Installation
```
cd <ComfyUI directory>/custom_nodes
git clone https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal.git
```

## Quick Start
- Use the `Metadata Rule Scanner` and `Save Custom Metadata Rules` nodes to create and and save new rules for metadata capture. Examples can be found in the workflow `scan-and-save-custom-metadata-rules.json` in the examples folder. 
- Start using the `Save Image w/ Metadata Universal` node to save your images.
- Set both civitai_sampler and guidance_as_cfg to true in the `Save Image w/ Metadata Universal` node for complete Civitai compatibility.

5. JPEG vs PNG:
  * Use PNG (or WebP lossless) for guaranteed full workflow + parameters.
  * JPEG has a hard ~64KB EXIF limit; large workflows trigger fallback trimming.
6. Control size:
  * `max_jpeg_exif_kb` (default 60, hard UI max 64) governs how much EXIF the node tries before fallback.
7. Read fallback stage: If parameters end with `Metadata Fallback: <stage>`, trimming occurred.
8. LoRA summary: Toggle with `include_lora_summary` or env `METADATA_NO_LORA_SUMMARY`.
## Quick Feature Overview (Added / Extended)
* Automatic1111‑style parameter string generation (single-line in production; multiline when `METADATA_TEST_MODE=1`).
* Dual Flux encoder prompt handling: captures / aliases T5 + CLIP prompts, suppressing unified positive when both present.
* LoRA handling:
  * Loader + inline `<lora:name:sm[:sc]>` syntax parsing (dual strengths supported).
  * Aggregated summary line `LoRAs: name(strength_model/strength_clip), ...` (UI & env toggles).
  * Per-LoRA model name, hash, strengths always retained.
* Embedding resolution with secure path normalization and hashing.
* Hash detail (structured JSON) optionally included (suppressed via `METADATA_NO_HASH_DETAIL`).
* Sampler normalization limited to specific cases (e.g. `euler_karras`) to avoid unwanted renames.
* Dynamic (call-time) evaluation of all environment flags—changes take effect without restart.
## Quick Feature Overview
* Clean Automatic1111‑style parameter line (optional multi‑line test mode).
* Works with multiple prompt encoder styles automatically.
* LoRA support: detects loaders & inline tags; optional summary line.
* Captures model / LoRA hashes for reproducibility.
* Can shorten output (hide hash detail or summary line).
* Stable ordering for predictable diffs.
* Plays nicely with most custom node packs out‑of‑the‑box.

## Node UI Parameters (Key Additions)
Key quality‑of‑life and compatibility controls exposed by the primary save node:

* `include_lora_summary` (BOOLEAN, default True): Toggles the aggregated `LoRAs:` summary line; when False only individual `Lora_*` entries are emitted. UI setting overrides env flags.
* `guidance_as_cfg` (BOOLEAN, default False): Substitutes the captured `Guidance` value into `CFG scale` and omits the separate `Guidance:` field for better A1111 / Civitai parity when models expose guidance separately.
* `max_jpeg_exif_kb` (INT, default 60, min 4, max 64): UI‑enforced ceiling for attempted JPEG EXIF payload. Real-world single APP1 EXIF segment limit is ~64KB; exceeding it triggers staged fallback (reduced-exif → minimal → com-marker). For large workflows prefer PNG / lossless WebP.

### JPEG Metadata Size & Fallback Behavior
JPEG metadata is constrained by a single APP1 (EXIF) segment (~64KB). This repository now enforces a hard UI cap of 64KB for `max_jpeg_exif_kb`; values above this provide no benefit and are rejected by Pillow or stripped by consumers. Large prompt + workflow JSON + hash detail can exceed the limit quickly.

When saving JPEG, the node evaluates total EXIF size vs `max_jpeg_exif_kb` (<=64) and applies staged fallback:
1. full (no message) — Full EXIF (workflow + parameters) fits.
2. reduced-exif — EXIF shrunk to parameters-only `UserComment`.
3. minimal — Trimmed parameter string (core fields + LoRAs + hashes) embedded as EXIF.
4. com-marker — EXIF dropped entirely; trimmed parameters stored in a JPEG COM marker.

If a fallback stage is used the parameters string gets an appended token: `Metadata Fallback: <stage>`.

Recommendations:
* Keep `max_jpeg_exif_kb` between 48–64 (the upper bound is enforced).
* Prefer PNG or lossless WebP when you require guaranteed full workflow embedding.
* Treat JPEG as delivery/export; archive originals as PNG if full metadata fidelity matters.

Limitations:
* Social platforms often strip both EXIF and COM markers; consider sidecar archival if critical.
* COM marker text has no structure; downstream tooling must parse the plain parameter string.
* Multi-segment APPn fragmentation (splitting across several EXIF/APP markers) is not implemented (deferred; see `docs/WORKFLOW_COMPRESSION_DESIGN.md`).

NOTE: The previous `force_include_node_class` input moved to the dedicated `Metadata Rule Scanner` node.

### Metadata Rule Scanner vs Metadata Force Include

Two separate nodes now handle scanning vs global class forcing:

1. `Metadata Rule Scanner` (defined in `node.py`):
  * Inputs: `exclude_keywords`, `include_existing`, `mode`, `force_include_metafields`.
  * Scans installed nodes and suggests capture rules + sampler mappings.
  * Produces JSON rules suggestion + a human-readable diff summary.

2. `Metadata Force Include` (new helper):
  * Inputs: `force_include_node_class` (multiline), `reset_forced` (bool), `dry_run` (optional bool).
  * Maintains a global set of node class names treated as required when loading user metadata definitions.
  * Output: Comma-joined list of currently forced classes (`FORCED_CLASSES`).

`SaveImageWithMetaDataUniversal` automatically merges the forced class set before deciding whether to load user JSON definition files.

> Experimental UI Notice: An earlier experimental auto-populated editable JSON rules textarea for the `Metadata Rule Scanner` has been disabled and archived under `web/disabled/metadata_rule_scanner/` for potential future iteration. It was removed to simplify maintenance and avoid layout instability concerns.

#### New Input (Scanner): `force_include_node_class`

`Metadata Rule Scanner` now exposes an optional multiline `force_include_node_class` field. Provide exact class names (comma or newline separated) to forcibly include those nodes in the scan results even when they:
* Match one of the `exclude_keywords`, or
* Would normally be omitted by `mode` (e.g. `existing_only` skipping new nodes).

Output Effects:
* `summary.forced_node_classes` lists them.
* `diff_report` appends a `Forced node classes=` segment.
* If a forced class yields no heuristic suggestions, an empty object is emitted so tooling can still merge or annotate it.

### Fallback Stages & Indicator
JPEG saves now record a `Metadata Fallback:` stage when size constraints trigger progressive trimming:

| Stage | Meaning |
| ----- | ------- |
| `none` | Full EXIF (workflow + parameters) written within limit (stage not emitted) |
| `reduced-exif` | EXIF shrunk to parameters-only UserComment |
| `minimal` | Parameters string trimmed to minimal allowlist (prompt, negative prompt, core generation fields, LoRA entries, hashes) and embedded as EXIF |
| `com-marker` | All EXIF removed (too large); minimal parameters written into a JPEG COM marker |

When a fallback occurs the `Metadata Fallback: <stage>` marker is appended to the parameters string to aid downstream tooling.

### Troubleshooting / FAQ
**Why is my workflow JSON missing in a JPEG?**  
The save exceeded `max_jpeg_exif_kb` and fell back to `reduced-exif`, `minimal`, or `com-marker`. Use PNG / WebP or lower the workflow size.

**I see `Metadata Fallback: minimal` — did I lose important info?**  
Only non-core keys were trimmed. Prompts, sampler settings, LoRAs, hashes, seed, model & VAE info remain.

**Forced node shows up with empty `{}` in scanner output. Bug?**  
No—`force_include_node_class` guarantees presence even if no heuristic rules match yet; use it as an anchor for manual rules.

**My LoRA summary line disappeared.**  
Either `include_lora_summary=False` in the node or `METADATA_NO_LORA_SUMMARY` env flag was set (UI param takes precedence).

**Parameter string suddenly multiline.**  
Environment variable `METADATA_TEST_MODE=1` was set (intended for tests). Unset it for production single-line mode.

**Why are hashes missing detail JSON?**  
Environment flag `METADATA_NO_HASH_DETAIL` suppresses the extended hash breakdown.

**How do I know which fallback stage occurred programmatically?**  
Parse the tail of the parameters string for `Metadata Fallback:`. (A future explicit key may be added.)

### Design / Future Ideas
See `docs/WORKFLOW_COMPRESSION_DESIGN.md` for deferred workflow compression & adaptive embedding strategy.

## Environment Flags
| Flag | Effect |
| ---- | ------ |
| `METADATA_NO_HASH_DETAIL` | Suppress structured `Hash detail` JSON section. |
| `METADATA_NO_LORA_SUMMARY` | Suppress aggregated `LoRAs:` summary (per-LoRA entries retained). |
| `METADATA_TEST_MODE` | Switch parameter string to multiline deterministic format for tests. |
| `METADATA_DEBUG_PROMPTS` | Enable verbose prompt capture / aliasing debug logs. |
| `METADATA_NO_LORA_SUMMARY` | (UI overrideable) suppress aggregated `LoRAs:` line. |

Additional Support:
* LoRA / model file extension recognition now includes `.st` everywhere `.safetensors` was previously required (hashing, detection, index building).

Precedence for LoRA summary: UI param `include_lora_summary` (explicit) > env flag > default include.

## Parameter String Formatting Modes
* Production: Single-line A1111-compatible string.
* Test: One key per line (stable ordering) when `METADATA_TEST_MODE` is set—facilitates snapshot diffing.

## Ordering Guarantees
Primary ordering and batch field placement are intentionally stable; avoid reordering without updating docs/tests.

## Contributing (Summary)
Run lint & tests before submitting PRs:
```
ruff check .
pytest -q
```
See `CONTRIBUTING.md` for full guidelines.

---
### Filename Token Reference
| Token | Replaced With |
|-------|---------------|
| `%seed%` | Seed value |
| `%width%` | Image width |
| `%height%` | Image height |
| `%pprompt%` | Positive prompt |
| `%pprompt:[n]%` | First n chars of positive prompt |
| `%nprompt%` | Negative prompt |
| `%nprompt:[n]%` | First n chars of negative prompt |
| `%model%` | Checkpoint base name |
| `%model:[n]%` | First n chars of checkpoint name |
| `%date%` | Timestamp (yyyyMMddhhmmss) |
| `%date:[format]%` | Custom pattern (yyyy, MM, dd, hh, mm, ss) |

Date pattern components:
`yyyy` | `MM` | `dd` | `hh` | `mm` | `ss`

For extended sampler selection details and advanced capture behavior, refer to the in-code docstrings (`Trace`, `Capture`) or open an issue if external docs would help.

日本語版READMEは[こちら](README.jp.md)。

