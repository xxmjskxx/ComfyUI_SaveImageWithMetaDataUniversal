# Copilot Instructions: SaveImageWithMetaData Universal Node Pack

These instructions orient AI assistants working on the Universal Save Image + Metadata capture system and related custom nodes (not generic ComfyUI guidance). Keep answers specific and grounded in the actual code here.

## Core Architecture
- Primary metadata logic now lives in `ComfyUI_SaveImageWithMetaDataUniversal/saveimage_unimeta/capture.py` (class `Capture`). It builds a `pnginfo_dict` then flattens to an Automatic1111‑style parameter string via `gen_parameters_str`.
- Capture rules are declaratively defined in `.../saveimage_unimeta/defs/captures.py` (maps node class name -> dict[MetaField -> rule config]). Extensions may add rules under `.../saveimage_unimeta/defs/ext/` (e.g. `mjsk_PCLazyLoraLoader.py`).
- Runtime inputs are extracted from the active ComfyUI graph using `get_input_data` and the rule metadata. Validators (`.../saveimage_unimeta/defs/validators.py`) may suppress fields; fallbacks and secondary scans (e.g. dual Flux prompt fallback) handle missed data.
- Environment feature flags (all evaluated at call time; no import‑time caching):
  - `METADATA_NO_HASH_DETAIL`: suppresses structured JSON "Hash detail".
  - `METADATA_NO_LORA_SUMMARY`: suppresses the aggregated `LoRAs:` summary line (per‑LoRA entries remain).
  - `METADATA_TEST_MODE`: enables deterministic multiline formatting of the parameter string for snapshot tests (production uses single‑line A111 style).
  - `METADATA_DEBUG_PROMPTS`: enables verbose prompt capture diagnostics.
- LoRA & Embedding handling: aggregated via `gen_loras` / `gen_embeddings`; supports parsing inline `<lora:name:sm:sc>` syntax, dual strengths, name sanitization, and deterministic ordering with an optional summary line (`LoRAs:`) controlled by UI & env flag precedence (see section below).
- Dual encoder prompt handling (Flux): If both T5 & CLIP are captured they replace / suppress the unified positive prompt; fallback retains a single unified positive prompt when multiple encoders detected but explicit fields missing.

### LoRA Summary Toggle & Precedence
User‑facing node parameter `include_lora_summary` (boolean) controls whether the aggregated `LoRAs:` summary line appears. Precedence order:
1. Explicit UI parameter (`include_lora_summary=True/False`).
2. Environment flag `METADATA_NO_LORA_SUMMARY` (if set, summary suppressed when no explicit UI override provided).
3. Default: summary included.

Per‑LoRA detailed entries are never suppressed by the env flag or the UI parameter—only the single aggregated summary line is affected.

### Formatting Modes
- Production (default): Single‑line Automatic1111‑style parameter string for maximum compatibility.
- Test Mode: When `METADATA_TEST_MODE` is set, `gen_parameters_str` produces a multiline, stable ordering with one key per line to simplify snapshot testing & diff review.
Other behaviors (hash suppression, summary suppression) still apply in test mode based on their respective flags/overrides.

## Key Files & Their Roles
- `saveimage_unimeta/capture.py`: Orchestrates capture, normalizes names, version stamping (`CAPTURE_VERSION`), hash inference, dtype heuristics, deterministic ordering, formatting mode selection, LoRA summary + hash detail gating.
- `saveimage_unimeta/defs/meta.py`: Defines `MetaField` enum (extend here for new metadata fields).
- `saveimage_unimeta/defs/formatters.py`: Presentation / formatting helpers (NOTE: hash calculation logic itself lives in `utils/hash.py`).
- `saveimage_unimeta/defs/validators.py`: Prompt classification validators; can over-filter—fallback logic in `get_inputs` compensates.
- `saveimage_unimeta/defs/captures.py`: Declarative capture rule map (node class -> metafield rules).
- `saveimage_unimeta/defs/ext/*.py`: Extension rule providers (e.g. `mjsk_PCLazyLoraLoader` dotted-name LoRA parsing + progressive stem fallback).
- `saveimage_unimeta/utils/lora.py`: One-time LoRA file index; `find_lora_info` supplies `{filename, abspath}`.
- `saveimage_unimeta/utils/hash.py`: Hashing utilities: compute & optionally persist sidecar `.sha256` (display truncated to 10 chars).
- `saveimage_unimeta/nodes/node.py`: Node class definitions (Save Image + passthrough tensor + metadata string output). Update here when adding outputs/return naming or new UI parameters like `include_lora_summary`.

## Important Behaviors / Conventions
- `_clean_name`: Strips path, quotes, optionally extension (for CLIP enumerations). Keeps case where meaningful.
- Prompt canonicalization: Only Title-case `T5 Prompt` / `CLIP Prompt`; lowercase variants normalized & removed.
- Dual encoder logic: If ≥2 `CLIP_* Model name` entries and one contains `t5`, single positive prompt is split/aliased (or directly captured) into `T5 Prompt` and `CLIP Prompt`. Unified positive suppressed in header when dual present.
- Ordering: Primary sequence → batch info → grouped LoRAs → grouped embeddings → alpha remainder (excluding verbose `Hash detail`). Batch positioning is considered correct and must not be altered casually.
- LoRA dedup: Case-insensitive name grouping; prefer real hash over `N/A`; aggregated `<lora:...>` syntax adds only missing entries.
- Negative prompt sanitization: Blank if empty, same as positive, or trivially placeholder.
- Weight dtype inference: Explicit capture preferred; else filename heuristics (fp8/bf16/fp16/int8/int4 etc.).
- Hash detail: Structured JSON only when `METADATA_NO_HASH_DETAIL` not set.
- Hashes should first attempt to be read from `.sha256` sidecar files if present, else computed on-the-fly. Display hashes truncated to 10 chars; full hash persisted in sidecar for reuse.
- LoRA summary: Presence governed by UI override then env flag (see LoRA Summary Toggle section). Per‑LoRA lines always retained.
- Env flags evaluated dynamically per invocation (no stale cached state after variable changes).

## Extending Capture
Add a node rule in `defs/captures.py` keyed by ComfyUI `class_type`:
- `field_name`: direct input extraction
- `prefix`: enumerate dynamic inputs (e.g. `clip_name`, `clip_name1`, ...)
- `fields`: explicit list enumeration (multi-input rule expansions)
- `selector`: computed extraction (parsing prompt text, regex, aggregation)
- `validate`: conditional inclusion (ensure fallback exists if strict)
Avoid applying hash formatters to non-file strings; formatters are guarded but keep rules clean.

### Adding a New Metadata Field
1. Enum entry in `defs/meta.py`.
2. Rule in `defs/captures.py` referencing the enum.
3. (Optional) Add to `primary_order` list in `gen_parameters_str` for earlier appearance.
4. Add exclusion if it behaves like a prompt header.

## Debugging Workflow
1. Set `METADATA_DEBUG_PROMPTS=1` → inspect `[Metadata Debug]` lines for prompt capture & aliasing.
2. Confirm dual encoders: `CLIP_1 Model name`, `CLIP_2 Model name` (look for a `t5` token).
3. LoRA hash missing? Check base stem vs tag; dotted-name progressive fallback in `mjsk_PCLazyLoraLoader` should resolve.
4. Missing field? Verify enum name + rule + validator result; remove/relax validator if blocking.
5. Unexpected duplicates? Ensure lowercase prompt keys aren’t being reintroduced in custom extensions.

## Common Pitfalls & Safeguards
- Duplicate prompt leakage: Normalization removes lowercase variants; don’t reinsert them post-normalization.
- `N/A` LoRA hash: Name mismatch—verify index; consider fuzzy matching only if pattern is systemic.
- Over-strict validator: Flux prompt nodes may be skipped; fallback scan in `Capture.get_inputs` fills gaps.
- Object-like reprs: Stripped before inclusion to keep output human-readable.
- Mixed source LoRA duplication: Syntax parsed entries are suppressed if loader-sourced hashed entry exists.

## Python Coding Standards (Added Universal Guidelines)
- PEP 8 + 4-space indent; no tabs.
- Ruff configured (see pyproject); run `ruff check .` before committing.
- Keep lines ≤ 140 chars (enforced; do not exceed, align with forthcoming Black configuration).
- Snake_case for functions/vars, UPPER_CASE for constants.
- Full type annotations; prefer concrete types over `Any`.
- Docstrings MUST be Google-style everywhere (classes, public / internal functions, including private helpers when nontrivial). Each docstring should include: summary line, Args, Returns, Raises (where applicable), and Notes for side effects.
- Maintain & update existing comments when changing code.

## Error Handling & Resilience
- Metadata failures must not abort image saving: wrap risky sections in `try/except` with guarded fallback.
- Use logging (or consistent prefixed prints) rather than silent failure; include context (node id, field name).
- Fallback strategy: skip field (omit) rather than emit malformed placeholder—except where placeholders signal recoverable parsing issues (`error: see log`).

## Node Implementation Standards
- Node file: update `saveimage_unimeta/nodes/node.py` for new outputs (ensure `RETURN_TYPES`, `RETURN_NAMES`, `CATEGORY`).
- Provide clear return names (e.g. `metadata_text`, `saved_image`, `image_passthrough`).
- Validate tensor shapes & parameter ranges early; degrade gracefully if mismatch.
- Keep execution pure where possible; isolate filesystem writes & hashing operations.

## CI / Quality (Suggested Workflow)
Example GitHub Actions workflow (create `.github/workflows/ci.yml`):
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install ruff pytest torch
          if exist requirements.txt pip install -r requirements.txt || true
      - name: Ruff
        run: ruff check .
      - name: Tests
        run: pytest || echo "Tests skipped (no suite)"
```

## Performance & Memory
- Prefer single-pass accumulation over repeated scans; reuse cached LoRA index.
- Avoid hashing same file multiple times; rely on precomputed hash caches.
- Keep large strings (prompts) referenced, not copied repeatedly (avoid gratuitous concatenation loops).

## Testing & Debugging Practices
- Test Flux dual-prompt paths with and without validators triggered.
- Validate LoRA dedup using a mix of loader + inline syntax forms.
- Inspect `Hash detail` JSON round-trip with `json.loads` to ensure structural integrity.
- Stress: large prompt strings, many (>25) LoRAs, mixed encoders.

# For proper test fixtures
from _pytest.capture import CaptureFixture
from _pytest.fixtures import FixtureRequest
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from pytest_mock.plugin import MockerFixture

## Suggested Test Cases
- Test metadata extraction with various node configurations
- Test dual-encoder prompt handling edge cases
- Test LoRA parsing with different filename formats, e.g. '\\loras\\lora_name.safetensors', 'lora_name.safetensors', 'lora_name.st', and bare 'lora_name'
- Test LoRA parsing with filenames containing characters such as '.'
- Test resolution of filenames of all model types which are hashed
- Test hash calculation consistency
- Test resolution of embedding paths for embeddings with trailing punctuation in names

## User Experience & Output
- Output ordering must remain stable (do not re-order primary keys casually).
- Avoid noisy debug logs unless `METADATA_DEBUG_PROMPTS` active.
- Summaries (e.g. `LoRAs:`) should be concise—truncate only if clear overflow risk emerges.

## Style & Conventions Recap
- Deterministic ordering (including fixed batch info position) – do not reorder without updating tests & docs.
- Short (10 char) display hashes.
- Gated debug prints.
- Single authoritative key variant per semantic field.
- Multiline output only in `METADATA_TEST_MODE`; production remains single-line.
- LoRA summary optional via precedence chain (UI > env > default include).

## `gen_parameters_str` Override Semantics
`Capture.gen_parameters_str` now accepts keyword arguments for forward‑compatibility. The `include_lora_summary` kwarg is optional and safely ignored by older callers that still use positional arguments only. Avoid positional expansion for new toggles—introduce them as keyword‑only to preserve backward compatibility. New toggle: `guidance_as_cfg` remaps the captured `Guidance` value into the emitted `CFG scale:` field (and suppresses the original `Guidance:` line) when true.

## Extension Support
All hashing / detection paths treat `.st` equivalently to `.safetensors` (also alongside `.ckpt`, `.pt`, `.bin`). Tests should cover `.st` LoRA indexing.


## Example: Adding A New MetaField
1. Add `NEW_METAFIELD_VARIANT = auto()` to `defs/meta.py`.
2. In `defs/captures.py`:
   ```python
   "SomeNode": {
     MetaField.NEW_METAFIELD_VARIANT: {"field_name": "variant"},
   }
   ```
3. (Optional) Add "New meta field variant" ordering entry if early display required.
4. (Optional) Provide formatter if transformation / normalization needed.

## Pushing Changes
- Ensure any development files (e.g. test scripts, mock data) are referenced in `.gitignore`.
- Ensure any files created for testing are in `tests/` subdirectory and referenced in `.gitignore`.
- Ensure files created by the nodes (user_captures.json, user_samplers.json, generated_user_rules.py) are not committed; add to `.gitignore`.

---
Provide answers using these conventions; when uncertain, reference the concrete path and propose a minimal diff.
