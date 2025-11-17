# AI Assistant Project Instructions
Authoritative onboarding for `ComfyUI_SaveImageWithMetaDataUniversal`. This repo is a Python custom-node pack (~220 tracked files excluding local-only `.venv`/outputs) targeting the ComfyUI runtime; edits usually run inside ComfyUI but must stay testable via pure Python.

## Overview & Tech Stack
- Purpose: `saveimage_unimeta/nodes/node.py` saves images with rich Automatic1111/Civitai-compatible metadata, hashes, workflow JSON, and filename tokens while degrading gracefully on JPEG limits.
- Languages & tooling: Python 3.9+ (CI runs 3.10–3.13), Pillow/Numpy/Piexif, ComfyUI APIs (`folder_paths`, `nodes`, `execution`). Browser assets under `web/` use HTML/JavaScript for optional UI helpers. Linting via Ruff (`ruff.toml`), testing via Pytest (`tests/`), coverage tracked by `.coveragerc`.
- Dependencies live in `requirements.txt` (runtime) and `requirements-test.txt` (adds pytest, ruff, coverage). Installing editable dev extras: `pip install -e .[dev]` (see `pyproject.toml`).

## Repository Layout (edit here before searching)
- Root: `saveimage_unimeta/` (core package), `tests/` (unit suites hitting public APIs), `docs/` (JPEG fallback, workflow compression, futures), `example_workflows/`, `user_rules/` (shipped examples), `.github/workflows/*.yml` (CI/publish), `web/` (static JS/CSS helpers referenced by ComfyUI UI), `ruff.toml`, `.pre-commit-config.yaml`.
- `saveimage_unimeta/defs/`: canonical capture metadata definitions, sampler heuristics, combo helpers, plus `ext/` for shipped extensions. Never bypass these when adding fields.
- `saveimage_unimeta/nodes/`: save node + supporting UI tooling (scanner, rule writers, extra metadata nodes, test stubs). Each node must keep tooltip text ≤140 chars (see `pyproject` metadata for copy text).
- `saveimage_unimeta/capture.py`: merges defs + `user_rules` + `FORCED_INCLUDE_CLASSES`, normalizes prompts, ensures `Metadata generator version` is always last. Relies on `saveimage_unimeta/hook.py` to read the active ComfyUI prompt cache (tests shim this when `METADATA_TEST_MODE=1`).
- `saveimage_unimeta/trace.py`: BFS graph traversal + sampler selection heuristics (exact match in `defs/samplers.py`, else `MetaField.SAMPLER_NAME` or `{STEPS, CFG_SCALE}` hint). `Trace.filter_inputs_by_trace_tree` guarantees deterministic ordering upstream of capture.
- `saveimage_unimeta/utils/`: hashing (`formatters.py`), LoRA/embed utilities, logging helpers (`color.py`). Always use these helpers—no ad-hoc hashing/log formatting, and prefer `pathresolve` for filesystem work.
- `web/`: static TypeScript/JavaScript snippets for optional UI affordances (see `web/js/`); keep them aligned with node parameter expectations when changing UI-visible behavior.

## Data Flow & Runtime Contracts
1. `Trace.trace` builds a distance map from the save node back through executed nodes; `sampler_selection_method` (UI) controls farthest/nearest/explicit traversal.
2. `Capture.gen_pnginfo_dict` / `.gen_parameters_str` iterate that ordering, apply rule merges, sanitize prompts, and append deterministic fields (metadata generator version last).
3. `saveimage_unimeta/nodes/save_image.py` writes PNGInfo or EXIF/WebP metadata, attempts JPEG EXIF up to `max_jpeg_exif_kb` (≤64 KB enforced). `_last_fallback_stages` mirrors whichever fallback stage fired.
4. JPEG fallback follows the multi-stage pipeline documented in `.github/instructions/python.instructions.md`; `_last_fallback_stages` mirrors whichever stage triggered so downstream tests can assert the markers.
5. Hashing: `saveimage_unimeta/utils/formatters.py` caches full SHA256 hashes in `.sha256` sidecars which are truncated to 10-chars when written to metadata; `METADATA_FORCE_REHASH=1` invalidates caches. Hash log verbosity controlled via `METADATA_HASH_LOG_MODE` and `METADATA_HASH_LOG_PROPAGATE`.

## Runtime Integration & Environment Flags
- Runs embedded in ComfyUI; expect access to `folder_paths`, sampler nodes, and numerous other `comfy.` imports, and PIL. When unit testing, `saveimage_unimeta/piexif_alias.py` and `hook.py` provide safe stubs—only extend the stub surface actually required.
- Runtime feature flags (read at execution time, no restart needed) include: `METADATA_TEST_MODE`, `METADATA_NO_HASH_DETAIL`, `METADATA_NO_LORA_SUMMARY`, `METADATA_FORCE_REHASH`, `METADATA_HASH_LOG_MODE`, `METADATA_HASH_LOG_PROPAGATE`, `METADATA_DUMP_LORA_INDEX`, `METADATA_ENABLE_TEST_NODES`, `METADATA_DEBUG_PROMPTS`. UI checkbox `include_lora_summary` overrides the env flag.
- JPEG/env documentation source of truth: `docs/JPEG_METADATA_FALLBACK.md`, `docs/WORKFLOW_COMPRESSION_DESIGN.md`, `docs/FUTURE_AND_PROTOTYPES.md`. Update both docs + this file when behavior changes.

## Build, Lint, Test (validated locally and mirrored by CI)
1. **Bootstrap** (from repo root, Python ≥3.9):
	```cmd
	python -m venv .venv
	.venv\Scripts\activate
	python -m pip install --upgrade pip
	pip install -e .[dev]
	```
	(Alternatively, `pip install -r requirements.txt -r requirements-test.txt`.)
2. **Lint**: `ruff check .` (configured by `ruff.toml`; CI fails on lint). Optional: `pre-commit run --all-files` (hooks defined in `.pre-commit-config.yaml`).
3. **Unit tests**: `pytest -q` (Pytest auto-discovers under `tests/`). Set `METADATA_TEST_MODE=1` to match CI matrix determinism. Coverage is gathered in CI via `coverage run -m pytest -q`; run locally when touching core pipeline.
4. **Workflow/CLI tests**: optional but recommended before shipping metadata format changes. Use `python tests/tools/run_dev_workflows.py --comfyui-path "<your ComfyUI root>" [--workflow-dir ...]` (see `tests/comfyui_cli_tests/DEV_WORKFLOW_TESTING.md` + `ignore/DEV_WORKFLOW_TESTING.md`). Always ensure workflows are in API format and clean outputs with `--temp-dir` or manual deletion.
5. **Integration sanity**: when touching JPEG fallback, temporarily set `max_jpeg_exif_kb=8` via the node UI or JSON to coerce fallback coverage; inspect `_last_fallback_stages` and resulting metadata strings to confirm markers append exactly once.
6. **CI awareness**: `.github/workflows/ci.yml` runs Ruff + Pytest across Python 3.10–3.13 and toggles `METADATA_TEST_MODE`. `unimeta-ci.yml` covers packaging/comfy-registry smoke tests; `publish_action.yml` handles release packaging. Match local tooling to avoid failures.

## Rules, Scanner & User Overrides
- `saveimage_unimeta/nodes/scanner.py` inspects installed node classes and suggests capture rules. `rules_save.py` + `rules_view.py` manage JSON/Python persistence (`saveimage_unimeta/user_rules/generated_user_rules.py`). After editing `defs/captures.py`, re-run scanner + saver so automated tests (`tests/test_generated_user_rules.py`) stay in sync.
- `rules_writer.py` stamps a `RULES_VERSION` constant into generated modules; `defs.load_user_definitions` caches it as `LOADED_RULES_VERSION`. `save_image.py` logs a one-time warning when the saved rules are missing or outdated—ask users to re-run `Metadata Rule Scanner` + `Save Custom Metadata Rules` or execute `example_workflows/refresh-rules.json` after updates.
- `Metadata Force Include` node feeds `FORCED_INCLUDE_CLASSES` used during capture merge; keep manual overrides inside `saveimage_unimeta/user_rules/` so merges remain deterministic.
- Manual capture additions must update: `defs/captures.py`, `_build_minimal_parameters` (only if the field must survive minimal fallback), docs (README + `docs/...`), targeted tests (e.g., `tests/test_capture_core.py`, `tests/test_guidance_and_exif_fallback.py`).

## Conventions & Safety Nets
- `.github/instructions/python.instructions.md` is the authoritative source for coding conventions, logging patterns, runtime import guards, metadata ordering, JPEG fallback behavior, filename token safety, helper usage, UI override precedence, sanitization rules, and artifact locations. Follow it whenever editing `.py` files.
- `.github/instructions/comfy.instructions.md` documents the ComfyUI manifest contract (`__init__.py` exports, `NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`) and protocol expectations (`CATEGORY`, `RETURN_TYPES`, `INPUT_TYPES`, `FUNCTION`, tuple returns). Reference it when adding or modifying nodes.

## Integration Resources & Troubleshooting
- **Docs**: `docs/JPEG_METADATA_FALLBACK.md`, `docs/MIGRATIONS.md`, `docs/V3_SCHEMA_MIGRATION.md` (for future migration to V3; no specific timeline for implementing this yet), `docs/WAN22_SUPPORT.md`, `docs/FUTURE_AND_PROTOTYPES.md` (historical context). Keep them synchronized with behavior changes.
- **Workflow samples**: `example_workflows/*.json` showcase Force Include, extra metadata, LoRA stacks, WAN/FLUX flows. Use them to reproduce bugs quickly.
- **Testing aids**: `saveimage_unimeta/nodes/testing_stubs.py` exposes lightweight sampler nodes when `METADATA_ENABLE_TEST_NODES=1`; `tests/` contains stub fixtures demonstrating how to patch ComfyUI APIs.
- **Troubleshooting tips**: enable `METADATA_DEBUG_PROMPTS=1` to log prompt aliasing, drop `max_jpeg_exif_kb` to 8 to hit fallback paths, set `METADATA_NO_HASH_DETAIL=1` or `METADATA_NO_LORA_SUMMARY=1` to verify UI overrides. Hash mismatches? delete `.sha256` sidecars or set `METADATA_FORCE_REHASH=1`.

## Working Style & Search Discipline
- Start from this file: it summarizes architecture, commands, and directory hotspots—search the codebase only if something here is missing or inaccurate. When in doubt, inspect `saveimage_unimeta/` modules referenced above before global greps.
- Keep diffs surgical: modify only the modules relevant to your change, maintain doc parity (README + docs + this file), and update/extend tests covering the touched behavior. CI enforces Ruff + Pytest; aim to replicate locally before pushing.
- Document new env flags, workflow parameters, or fallback behaviors immediately here and in the README/doc section they affect. Avoid conflicting guidance—the coding agent will obey the strictest rule present.
- Trust these instructions. Only run exploratory searches if the required information isn’t covered or appears outdated, and if you discover drift, update this file as part of your change.