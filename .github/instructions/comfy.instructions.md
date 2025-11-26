---
description: "ComfyUI protocol guarantees and manifest/registration contract."
applyTo: "**/*.py"
---

# GitHub Copilot Instructions for `ComfyUI_SaveImageWithMetaDataUniversal`

## How This File Fits With Other Instructions

- Use `.github/copilot-instructions.md` for the full repo tour (layout, data flow, build/test commands, env flags).
- Use `.github/instructions/python.instructions.md` for every Python-convention question (ruff expectations, logging, metadata ordering, JPEG fallback, helper usage). That file is the authority on code style and testing rules.
- This document focuses solely on **ComfyUI protocol guarantees** and the **manifest/registration contract** that every node must respect.

## Architecture Layers (ComfyUI View)

1. **Registration Layer (`__init__.py`)** – Treat this as the manifest. It should primarily import concrete node classes, declare `NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`, optional `WEB_DIRECTORY`, and export the curated `__all__`. Controlled side effects (e.g., gating test nodes on `METADATA_ENABLE_TEST_NODES` or logging a one-time startup banner) are acceptable, but keep them lightweight and well-documented.
2. **Logic Layer (`saveimage_unimeta/`)** – All node behavior, utilities, capture/trace helpers, and metadata plumbing live inside this package. New functionality must be implemented here and tested via `pytest` as described in the Python instructions.
3. **Presentation Layer (`web/`)** – Houses any optional ComfyUI frontend extensions. Keep the JS aligned with node INPUT_TYPES and update the manifest’s `WEB_DIRECTORY` when shipping UI assets.

## ComfyUI Protocol Requirements

When writing or modifying nodes, enforce these protocol rules to stay compatible with ComfyUI and downstream forks:

- Define the static protocol fields on every node class: `CATEGORY`, `RETURN_TYPES`, `FUNCTION`, and, when applicable, `OUTPUT_NODE` or `OUTPUT_IS_LIST`.
- Implement `@classmethod INPUT_TYPES(cls)` returning a dict with `"required"`, `"optional"`, and `"hidden"` keys. Ensure magic strings (e.g., `"IMAGE"`, `"STRING"`, `"UNIMETA_METADATA"`) match the runtime’s expectations.
- The method referenced by `FUNCTION` must accept parameters that line up exactly with `INPUT_TYPES` and always return a tuple. Saver nodes typically `return ()` to signal “work complete, no tensors produced.”
- Hidden inputs for prompt/workflow/state (`"PROMPT"`, `"EXTRA_PNGINFO"`, etc.) must be threaded through to capture utilities rather than reinventing workflow parsing.

## Registration Checklist

Whenever a new node class is introduced under `saveimage_unimeta/nodes/`:

1. Import the class inside the root `__init__.py` without triggering runtime-only dependencies during import.
2. Add the class to `NODE_CLASS_MAPPINGS` using the ComfyUI identifier as the key.
3. Provide a concise (<140 char) entry in `NODE_DISPLAY_NAME_MAPPINGS` so UI menus look polished.
4. Append the class name to `__all__` to keep static analyzers in sync.
5. If the node requires web assets, expose them via `WEB_DIRECTORY` and keep the folder paths stable for ComfyUI.

## Gold-Standard Node Outline

New nodes should resemble the structure below. It highlights the ComfyUI-specific plumbing this document governs; read the Python instructions for broader style and metadata rules.

```python
import torch
from comfy.cli_args import args


class SaveImageWithMetaDataUniversal:
    """Canonical saver node registered via NODE_CLASS_MAPPINGS."""

    CATEGORY = "image/metadata"
    RETURN_TYPES: tuple[str, ...] = ()
    FUNCTION = "save_images"

    @classmethod
    def INPUT_TYPES(cls):
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
        if args.dont_save_previews:
            return ()

        # Business logic defined in saveimage_unimeta/nodes/save_image.py

        return ()
```

Use this outline to validate that protocol attributes, INPUT_TYPES, and return signatures remain aligned whenever you extend the saver or add supporting nodes.