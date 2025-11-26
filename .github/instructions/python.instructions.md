---
description: 'Python coding conventions and guidelines'
applyTo: '**/*.py'
---

# Python Coding Standards and Guidelines

> **Related guidance:** Use `.github/instructions/comfy.instructions.md` for ComfyUI protocol/manifest requirements and `.github/copilot-instructions.md` for the project tour, env flags, and build/test commands. This file is the single source of truth for Python style, metadata ordering, hashing, logging, and JPEG fallback behavior.

## Core Principles

- Follow **PEP 8**: 4-space indents, descriptive names, and idiomatic constructs.
- Prioritize clarity. Explain heuristics or cross-module side effects with short comments so future agents understand intent.
- Favor deterministic flows over clever tricks; ComfyUI nodes stay resident for long sessions and benefit from predictable code.
- Match the repo’s configured limits: keep lines ≤140 characters as enforced by `ruff.toml`.

## Ruff Compliance & Formatting

- Treat `ruff check .` as the authority for linting, import order, and formatting. Run it locally before sending a PR.
- Accept Ruff’s auto-fixes only after reviewing the diff so semantics stay intact.
- Group imports as standard library → third-party → first-party, and prefer absolute imports for project modules.
- Target Python 3.12 semantics (per `ruff.toml`) when using new syntax.

## Type Hinting & Documentation

- Add modern type hints to every new function, method, and significant variable. Use `typing` / `collections.abc` protocols (`Iterable`, `Mapping`, `Iterator`) to describe behavior rather than concrete containers.
- Follow the **ComfyUI type duality** pattern: keep protocol constants (`RETURN_TYPES`, `FUNCTION`, etc.) as strings, while method signatures use precise hints (`torch.Tensor`, TypedDicts) for runtime logic.
- Write PEP 257 docstrings that cover purpose, inputs, outputs, and any `METADATA_*` flags or UI settings influencing behavior.
- Mention external dependencies (Pillow, `folder_paths`, `execution`, etc.) inside the docstring or an inline comment so readers know why the import exists.

## Structure & Modules

- Break capture traversal, hashing, and JPEG fallback orchestration into focused helpers instead of embedding everything in node classes like `saveimage_unimeta/nodes/save_image.py`.
- Prefer pure functions. When mutating shared structures (prompt caches, metadata dicts), document the expected state change in code or docstrings.
- Use guard clauses and early returns to keep nesting shallow.
- Keep modules scoped to a single concern (`capture.py`, `trace.py`, `defs/formatters.py`, etc.) and keep package `__init__.py` files minimal (exports/metadata only).

## Logging & Diagnostics

- Never call `print`. Create a module-level logger (`logging.getLogger(__name__)`).
- Wrap user-facing fragments with `saveimage_unimeta/utils/color.cstr` when highlighting filenames, tokens, or hashes so CLI logs remain readable.
- Gate verbose logging behind env flags (`METADATA_DEBUG_PROMPTS`, `METADATA_HASH_LOG_MODE`, `METADATA_HASH_LOG_PROPAGATE`) to avoid noisy production runs.
- Include actionable context (node IDs, sampler names, filenames) when logging capture failures.

## Runtime Imports & Testability

- Guard ComfyUI-only imports (`folder_paths`, `execution`, `comfy_execution.graph`) in `try/except ImportError` blocks so `pytest` can run outside the runtime.
- Mirror the `_TEST_MODE = bool(os.environ.get("METADATA_TEST_MODE"))` pattern throughout the codebase: when `_TEST_MODE` is true, load the lightweight stubs provided in `saveimage_unimeta/piexif_alias.py` and `hook.py`.
- Access prompt caches through `saveimage_unimeta/hook.py` instead of global variables; tests patch this surface to keep capture deterministic.
- Document every environment flag a function reads inside its docstring so test authors know how to toggle behavior.

## Metadata & Capture Contracts

- Pull metadata definitions from `saveimage_unimeta/defs` (`MetaField`, `CAPTURE_FIELD_LIST`, `FORCED_INCLUDE_CLASSES`) rather than hard-coding field names.
- Preserve insertion order: append new keys at the tail of metadata dicts and keep `"Metadata generator version"` last for PNGInfo and EXIF stability.
- JPEG fallback is fixed (`full → reduced-exif → minimal → com-marker`). `_build_minimal_parameters` may only include prompts, sampler core (Steps/Sampler/CFG), seeds, sizes, hashes, `Lora_*`, and the metadata version; adding fields requires product sign-off plus updated docs/tests.
- Use `Trace.filter_inputs_by_trace_tree` from `saveimage_unimeta/trace.py` when you need deterministic upstream ordering. Do not invent ad-hoc traversals.
- Keep filename tokens in `saveimage_unimeta/nodes/save_image.py` backward compatible (`%seed%`, `%width%`, `%pprompt%[:n]`, `%date:<pattern>`, etc.) and update README/tooltips anytime you add tokens.
- `_format_filename` and `_build_minimal_parameters` inside `saveimage_unimeta/nodes/save_image.py` are the canonical implementations for token substitution and minimal metadata trimming. Touching either requires coordinated doc/test updates so JPEG fallback behavior stays deterministic.
- UI overrides (e.g., the `include_lora_summary` checkbox) must take precedence over related environment flags; treat UI state as canonical when both exist.

## Helper Utilities & Hashing

- Reuse `saveimage_unimeta/defs/formatters.py` helpers (`calc_model_hash`, `calc_lora_hash`, `display_model_name`, etc.) for hashing and labeling—never introduce ad-hoc routines.
- Hash primitives (sidecar read/write, SHA truncation) live in `saveimage_unimeta/utils/hash.py`, while metadata-facing wrappers sit in `saveimage_unimeta/defs/formatters.py`. Depend on that split instead of adding ad-hoc caches; `METADATA_FORCE_REHASH=1` invalidates `.sha256` sidecars.
- Use `saveimage_unimeta/utils/pathresolve` for filesystem work so relative paths resolve consistently across platforms.

## Error Handling & Node Safety

- Handle edge cases and write clear, documented exception handling.
- Metadata failures must never prevent an image from saving. Wrap risky sections in `try/except`, log via the module logger, and still return success to the caller.
- Emit `"error: see log"` placeholders only when a metadata field would otherwise be blank, and ensure the corresponding log explains the issue.
- Sanitize user-provided metadata exactly like `saveimage_unimeta/nodes/extra_metadata.py` (replace commas with `/`, trim whitespace) to keep downstream CSV consumers stable.
- Keep UI-facing strings (labels, tooltips) ≤140 characters so they fit within ComfyUI’s limits.

## Edge Cases, Testing & Artifacts

- Validate inputs early (empty prompts, invalid tensors, oversized metadata) and raise descriptive errors when necessary.
- Update or add unit tests whenever capture logic, hashing, fallback behavior, or filename tokens change. Focus on suites such as `tests/test_capture_core.py`, `tests/test_guidance_and_exif_fallback.py`, `tests/test_hash_logging.py`, and related files.
- Run `pytest -q` (or `coverage run -m pytest -q`) with `METADATA_TEST_MODE=1` before submitting changes to mirror CI behavior.
- Store generated fixtures, workflow dumps, or hash logs under `tests/_test_outputs/` or `tests/_artifacts/` so git history stays clean.

## Example: Project Docstrings & Type Duality

```python
import torch
from comfy.cli_args import args


class SaveImageWithMetaDataUniversal:
    """Implement the ComfyUI saver protocol for UniMeta outputs."""

    CATEGORY = "image/metadata"
    RETURN_TYPES: tuple[str, ...] = ()
    FUNCTION = "save_images"

    @classmethod
    def INPUT_TYPES(cls):
        """Describe required/optional/hidden inputs returned to ComfyUI."""
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
            },
            "optional": {
                "extra_metadata": ("UNIMETA_METADATA",),
                "metadata_rules": ("UNIMETA_RULES",),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def save_images(
        self,
        images: torch.Tensor,
        filename_prefix: str,
        extra_metadata: dict | None = None,
        metadata_rules: dict | None = None,
        prompt: dict | None = None,
        extra_pnginfo: dict | None = None,
    ) -> tuple:
        """Save the incoming images with workflow metadata extracted from ComfyUI.

        Args:
            images: Batch of images to persist.
            filename_prefix: Prefix applied to output filenames.
            extra_metadata: Optional user-supplied metadata block.
            metadata_rules: Optional capture overrides.
            prompt: Serialized ComfyUI workflow (hidden input).
            extra_pnginfo: Additional PNG metadata (hidden input).
        """

        if args.dont_save_previews:
            return ()

        # ... full implementation logic ...

        return ()
```
