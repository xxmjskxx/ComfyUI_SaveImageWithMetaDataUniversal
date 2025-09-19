# ComfyUI-SaveImageWithMetaDataUniversal
![SaveImageWithMetaData Preview](img/save_image_with_metadata.png)  

> Enhanced Automatic1111‑style metadata capture with dual-encoder prompt support, LoRA & embedding hashing, optional aggregated summaries, and test-friendly deterministic formatting.

## Quick Feature Overview (Added / Extended)
* Automatic1111‑style parameter string generation (single-line in production; multiline when `METADATA_TEST_MODE=1`).
* Dual Flux encoder prompt handling: captures / aliases T5 + CLIP prompts, suppressing unified positive when both present.
* LoRA handling:
  * Loader + inline `<lora:name:sm[:sc]>` syntax parsing (dual strengths supported).
  * Aggregated summary line `LoRAs: name(strength_model/strength_clip), ...` (UI & env toggles).
  * Per-LoRA model name, hash, strengths always retained.
* Embedding resolution with secure path normalization and hashing.
* Hash detail (structured JSON) optionally included (suppressed via `METADATA_NO_HASH_DETAIL`).
* Batch fields (`Batch index`, `Batch size`) inserted at stable position—ordering is intentionally fixed.
* Sampler normalization limited to specific cases (e.g. `euler_karras`) to avoid unwanted renames.
* Dynamic (call-time) evaluation of all environment flags—changes take effect without restart.
* Google-style docstrings and Ruff-enforced style (line length 140) across core modules.

### Design / Future Ideas
See `docs/WORKFLOW_COMPRESSION_DESIGN.md` for deferred workflow compression & adaptive embedding strategy.

## Nodes Provided
| Node | Purpose |
| ---- | ------- |
| `SaveImageWithMetaDataUniversal` | Save images + produce enriched metadata (PNGInfo / EXIF) & parameter string. |
| `Create Extra MetaData` | Inject additional custom key-value metadata pairs. |

## Node UI Parameters (Key Additions)
`include_lora_summary` (BOOLEAN, default True): Controls aggregated `LoRAs:` line. When False, only individual `Lora_X` entries appear. Overrides env flag precedence (see below).
`guidance_as_cfg` (BOOLEAN, default False): When enabled the recorded `CFG scale:` value is replaced with the captured `Guidance` value (if present) and the original `Guidance:` field is omitted. This is useful when workflows report guidance separately but you want the traditional Automatic1111 single `CFG scale:` line.
`max_jpeg_exif_kb` (INT, default 60, min 4, max 256): Maximum EXIF segment size (in kilobytes) the node will attempt to embed in JPEG files. If the full metadata (parameters + workflow JSON + hashes, etc.) exceeds this limit the node automatically falls back to: (1) a parameters‑only reduced EXIF block (still A1111 compatible). If that also exceeds the limit or the encoder rejects it, it finally falls back to inserting the full parameter string in a JPEG COM marker. WebP is unaffected (it stores extended metadata separately). Lower this if you encounter viewers that choke on large EXIF blocks; raise cautiously (JPEG hard limit ~64KB for a single APP1 segment, practical safe ceiling kept below 256KB to avoid fragmentation / viewer issues).
 `force_include_node_class` (STRING, optional): Comma separated list of node class names to force include in metadata rule scanning even if heuristics would normally exclude them.

### Fallback Stages & Indicator
JPEG saves now record a `Metadata Fallback:` stage when size constraints trigger progressive trimming:

| Stage | Meaning |
| ----- | ------- |
| `none` | Full EXIF (workflow + parameters) written within limit (stage not emitted) |
| `reduced-exif` | EXIF shrunk to parameters-only UserComment |
| `minimal` | Parameters string trimmed to minimal allowlist (prompt, negative prompt, core generation fields, LoRA entries, hashes) and embedded as EXIF |
| `com-marker` | All EXIF removed (too large); minimal parameters written into a JPEG COM marker |

When a fallback occurs the `Metadata Fallback: <stage>` marker is appended to the parameters string to aid downstream tooling.

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
Original README continues below.
日本語版READMEは[こちら](README.jp.md)。

- Custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).
- Add a node to save images with metadata (PNGInfo) extracted from the input values of each node.
- Since the values are extracted dynamically, values output by various extension nodes can be added to metadata.

## Installation
```
cd <ComfyUI directory>/custom_nodes
git clone https://github.com/nkchocoai/ComfyUI-SaveImageWithMetaData.git
```

## Nodes
### Save Image With Metadata
- Saves the `images` received as input as an image with metadata (PNGInfo).
- Metadata is extracted from the input of the KSampler node found by `sampler_selection_method` and the input of the previously executed node.
  - Target KSampler nodes are the key of `SAMPLERS` in the file [py/defs/samplers.py](py/defs/samplers.py) and the file in [py/defs/ext/](py/defs/ext/).

#### filename_prefix
- The string (Key) specified in `filename_prefix` will be replaced with the retrieved information.

| Key             | Information to be replaced            |
| --------------- | ------------------------------------- |
| %seed%          | seed value                            |
| %width%         | Image width                           |
| %height%        | Image height                          |
| %pprompt%       | Positive Prompt                       |
| %pprompt:[n]%   | first n characters of Positive Prompt |
| %nprompt%       | Negative Prompt                       |
| %nprompt:[n]%   | First n characters of Negative Prompt |
| %model%         | Checkpoint name                       |
| %model:[n]%     | First n characters of Checkpoint name |
| %date%          | Date of generation(yyyyMMddhhmmss)    |
| %date:[format]% | Date of generation                    |

- See the following table for the identifier specified by `[format]` in `%date:[format]%`.

| Identifier | Description |
| ---------- | ----------- |
| yyyy       | year        |
| MM         | month       |
| dd         | day         |
| hh         | hour        |
| mm         | minute      |
| ss         | second      |

#### sampler_selection_method
- Specifies how to select a KSampler node that has been executed before this node.

##### Farthest
- Selects the farthest KSampler node from this node.
- Example: In [everywhere_prompt_utilities.png](examples/everywhere_prompt_utilities.png), select the upper KSampler node (seed=12345).

##### Nearest
- Select the nearest KSampler node to this node.
- Example: In [everywhere_prompt_utilities.png](examples/everywhere_prompt_utilities.png), select the bottom KSampler node (seed=67890).

##### By node ID
- Select the KSampler node whose node ID is `sampler_selection_node_id`.

### Create Extra MetaData
- Specifies metadata to be added to the image to be saved.
- Example: In [extra_metadata.png](examples/extra_metadata.png).

## Metadata to be given
- Positive prompt
- Negative prompt
- Steps
- Sampler
- CFG Scale
- Seed
- Clip skip
- Size
- Model
- Model hash
- VAE
  - It is referenced from the input of SaveImageWithMetadata node, not KSampler node.
- VAE hash
  - It is referenced from the input of SaveImageWithMetadata node, not KSampler node.
- Loras
  - Model name
  - Model hash
  - Strength model
  - Strength clip
- Embeddings
  - Name
  - Hash
- If batch size >= 2 :
  - Batch index
  - Batch size
- Hashes
  - Model, Loras, Embeddings
  - For [Civitai](https://civitai.com/)

## Supported nodes and extensions
- Please check the following file for supported nodes.
  - [py/defs/captures.py](py/defs/captures.py)
  - [py/defs/samplers.py](py/defs/samplers.py)
- Please check the following directories for supported extensions.
  - [py/defs/ext/](py/defs/ext/)

## CI & Development

![CI](https://github.com/jags111/efficiency-nodes-comfyui/actions/workflows/ci.yml/badge.svg)

The project includes a GitHub Actions workflow (`ci.yml`) that runs on pushes and pull requests to `main`:

- Ruff lint (`ruff check .`)
- Pytest with coverage (`coverage run -m pytest -q` / `coverage xml`)
- Dependency vulnerability scan (`pip-audit`, non-fatal)

### Local Development
```
pip install -e .[dev]
ruff check .
coverage run -m pytest -q
coverage report -m
```

### Environment Flags
| Variable | Purpose |
| -------- | ------- |
| `METADATA_DEBUG_PROMPTS` | Verbose prompt capture logging. |
| `METADATA_DEBUG_LORA` | Detailed LoRA parsing diagnostics. |
| `METADATA_NO_HASH_DETAIL` | Suppress verbose Hash detail JSON block. |
| `METADATA_DEBUG` | General debug enablement. |

### Extending CI
Potential enhancements you can add:
1. Coverage upload to Codecov.
2. Pre-commit hook enforcement.
3. Wheel/sdist packaging on tag.
4. Selective path triggers to speed runs.

### Pre-commit Hooks
This repository includes a `.pre-commit-config.yaml` with:
- Ruff lint & format (`ruff`, `ruff-format` with auto-fix)
- Trailing whitespace / end-of-file fixes
- Mixed line ending normalization (LF)
- Large file guard & private key detector

Enable locally:
```
pip install -e .[dev]
pre-commit install
# Run on all files initially
pre-commit run --all-files
```

Optional (manual stage) quick test hook can be enabled by uncommenting the local section inside `.pre-commit-config.yaml`.

