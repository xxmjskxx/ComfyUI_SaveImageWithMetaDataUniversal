# Release Notes — v1.4.4

**Release Date:** 2026-09-03
**Commits:** 1 merged PR since v1.4.3
**Tag:** [`v1.4.4`](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/releases/tag/v1.4.4)

## Overview

Version 1.4.4 is a patch release that fixes a metadata capture crash. When a list-of-dicts widget value
(such as a LoRA stack) sits upstream of the save node, the tracer raised `TypeError: unhashable type: 'dict'`
and aborted the save. The fix is backward-compatible with no migration required.

## Highlights

### Crash Fix: List-of-Dicts Widget Values in the Tracer

- `Trace.trace` treated every list-valued input as a graph link and hashed its first element. For a
  list-of-dicts widget value (e.g. `[{"name": "...", "strength": ...}]`), the first element is a dict and
  hashing it raised `TypeError: unhashable type: 'dict'`. (#145)
- `Trace.trace` now uses the shared `_is_link_input` predicate, and `_get_node_id_list` in `validators.py`
  guards its initial conditioning link, so non-link list values are skipped instead of hashed. This also
  fixes a latent `IndexError` on empty-list inputs and aligns the two tracers. (#145)

### Testing and Validation

- Added regression tests that feed a bare list-of-dicts input through the tracer and assert it is skipped
  without crashing.
- `python -m pytest -q`: 1164 passed, 1 skipped; `python -m ruff check .` passes cleanly.

## Breaking Changes

None.

## Upgrade Notes

No migration is required. Update the node pack and restart ComfyUI — the change only affects graph
traversal during metadata capture and is fully backward-compatible.

## What's Changed
* Fix trace crash on list-of-dicts widget values by @EnragedAntelope in https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/pull/145

**Full Changelog**: https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/compare/v1.4.3...v1.4.4
