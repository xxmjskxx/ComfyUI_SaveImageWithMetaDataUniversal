---
post_title: "Deprecations and Migrations"
author1: "Project Maintainers"
post_slug: "migrations"
microsoft_alias: "na"
featured_image: ""
categories:
  - Development
tags:
  - Deprecation
  - Migration
  - LoRA
  - ComfyUI
ai_note: true
summary: >-
  Guidance for upgrading across versions. Deprecations, replacements, and
  timelines; includes get_lora_data_stack → select_stack_by_prefix migration.
post_date: "2025-09-25"
---

## Deprecations and Migrations

### Deprecated: get_lora_data_stack (extensions)
- Deprecated in: v1.2.0
- Removal: no earlier than v1.3.0 and at least 60 days after v1.2.0 release.
- Replacement: `select_stack_by_prefix(input_data, prefix, counter_key="lora_count")` from `saveimage_unimeta/defs/selectors.py`.

Why
- Consolidate duplicate stack selection logic and ensure consistent handling of list coercion, "None" filtering, and stack length limiting.

How to migrate
- Replace calls like:
  - `get_lora_data_stack(input_data, "lora_name")` → `select_stack_by_prefix(input_data, "lora_name", counter_key="lora_count")`
  - `get_lora_data_stack(input_data, "model_str")` → `select_stack_by_prefix(input_data, "model_str", counter_key="lora_count")`
  - `get_lora_data_stack(input_data, "clip_str")` → `select_stack_by_prefix(input_data, "clip_str", counter_key="lora_count")`

Notes
- The selector always returns `v[0]` for list-like values, and skips entries whose first element is the string `"None"` when `filter_none=True` (default).
- If your node exposes a stack-length field (e.g., `lora_count`), pass it via `counter_key` to truncate to the desired length.

### Related helpers
- `select_by_prefix(input_data, prefix)`: simpler selector without stack limiting or filtering.
- `select_stack_by_prefix(input_data, prefix, counter_key=None, filter_none=True)`: preferred stack-aware helper.
