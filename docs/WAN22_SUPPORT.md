---
post_title: "Wan2.2 MoE Per-Sampler Metadata: Design and Prototype Plan"
author1: "Project Maintainers"
post_slug: "wan22-moe-per-sampler-metadata"
microsoft_alias: "na"
featured_image: ""
categories:
  - Planning
  - ComfyUI
  - Metadata
tags:
  - WanVideoWrapper
  - MoE
  - ComfyUI
  - Metadata
  - EXIF
  - PNGInfo
ai_note: true
summary: >-
  Design for capturing per-sampler details in Wan2.2 MoE workflows while preserving
  compatibility and JPEG fallback semantics; staged rollout and tests documented.
post_date: "2025-09-24"
---

## Goals and Non-Goals
- Capture complete, per-sampler metadata for Wan2.2 MoE workflows (high/low models).
- Preserve current single-model behavior and output shape for non-MoE graphs.
- Maintain JPEG fallback semantics and size caps; avoid regressions.
- Non-goals: Implement CLIP hashes; change existing allowlist ordering.

## Background
- Wan2.2 is a Mixture-of-Experts style setup: typical graphs have two
  `WanVideoModelLoader` nodes (high/low) and two or more `WanVideo Sampler` nodes.
- Each `WanVideo Sampler` includes `steps` and also `start_step` and `end_step` to
  define a subrange of the total steps.
- Wan2.1 workflows are single-model and are already covered by current logic.

## Detection Strategy (MoE vs Single-Model)
- Detect MoE conservatively to avoid disrupting stable single-model flows:
  - True when traced subgraph contains ≥ 2 `WanVideoModelLoader` and
    either ≥ 2 `WanVideo Sampler` or any sampler exposes `start_step`/`end_step`.
    - Should use something more future-proof and adaptable to other workflows and models than just `WanVideoModelLoader` or `WanVideo Sampler`
    - Something more general like when traced subgraph contains ≥ 2 Samplers; or when traced subgraph contains ≥ 2 model loaders
    - Maybe something like, when saving image with `Save Image w/ Metadata Universal`:
      - Trace up to x samplers, set in UI widget (default 1), but fallback to as few as 1 if trace fails to detect multiple samplers (or to 0 with an error log message, if no samplers are found)
      - If samplers is set to 1 use current behaviour
      - Run trace as usual
      - If a second sampler is found, workflow has at least 2 samplers, else fallback to current behaviour
      - If workflow has at least 2 samplers, continue trace (if samplers is set to > 2), and if an additional sampler is hit workflow has at least 3 samplers
      - Continue for up to x samplers
      - Multi-sampler metadata will have sections (e.g. 'Sampler_1:\n') for each sampler.
      - Sampler numbers will be set to reverse order of proximity to `Save Image w/ Metadata Universal` node (so, 3 is closest, 1 is furthest).
      - Multi-sampler trace should write parameters from nodes connected directly or indirectly to each sampler to that sampler's section in the metadata (similar to current behaviour).
      - Exceptions: any node(s) connected indirectly through another sampler; any node(s) which are executed after a sampler.
        - Example 1: node_1⟶node_2⟶sampler_1⟶sampler_2
          - node_1 and node_2 are recorded to sampler_1's metadata (if they contain relevant captured information), but they are not recorded to sampler_2's metadata because they are connected to sampler_2 indirectly through sampler_1
        - Example 2: node_1⟶sampler_1⟶node_2⟶sampler_2⟶node_3⟶sampler_3
          - node_1 is recorded to sampler_1's metadata (if it contains relevant captured information), but it is not recorded to sampler_2's or sampler_3's metadata because they are both connected to node_1 indirectly through 1 or more samplers.
          - node_2 is recorded to sampler_2's metadata (if it contains relevant captured information); node_2 is not recorded to sampler_1's metadata because it is executed after sampler_1; node_2 is not recorded to sampler_3's metadata because it is connected to node_2 indirectly through sampler_2. 
          - node_3 is recorded to sampler_3's metadata (if it contains relevant captured information), but it is not recorded to sampler_1's or sampler_2's metadata because node_3 is executed after both sampler_1 and sampler_2
        - Example 3: node_1⟶sampler_1⟶node_2⟶sampler_2 and node_1⟶sampler_2
          - node_1 is recorded to both sampler_1's and sampler_2's metadata (if it contains relevant captured information) because they are both connected to it directly
          - node_2 is recorded to sampler_2's metadata (if it contains relevant captured information), but it is not recorded to sampler_1's metadata because it it occurs after sampler_1's execution in the graph
      - As the multi-sampler trace is run, it should follow the above pathing logic to attribute the extracted metadata to the correct sampler(s).
- Add an environment override:
  - `METADATA_WAN_MOE_FORCE=1` forces MoE path.
  - Optional: `METADATA_WAN_MOE_DISABLE=1` disables MoE path.

## New Fields
- Add metadata enums (to be appended without reordering existing keys):
  - `START_STEP` (per sampler)
  - `END_STEP` (per sampler)
- Extend `WanVideo Sampler` capture with:
  - `seed`, `steps`, `cfg`, `shift`, `denoise`
  - `start_step`, `end_step`
  - `sampler`, `scheduler` parsed from the combined `scheduler` input
    (supports dict, list/tuple, and string formats like `Euler (Karras)`).

## Capture Rules Adjustments
- `saveimage_unimeta/defs/ext/wan_video_wrapper.py`:
  - Keep existing rules.
  - Add `start_step` and `end_step` mappings for `WanVideo Sampler`.
  - Keep the robust `scheduler` parser used to split into `sampler` and `scheduler`.

## Trace and Association (MoE Path Only)
- Implement a new helper `collect_sampler_contexts_moe` (name tentative):
  - Enumerate all `WanVideo Sampler` nodes which are traced and part of the executed graph in a deterministic order.
  - For each sampler, walk upstream to find the nearest `WanVideoModelLoader`.
  - Collect associated VAE, LoRAs (names/hashes/strengths) along the same path.
  - Record sampler settings: `steps`, `start_step`, `end_step`, `cfg`, `shift`,
    `seed`, `denoise`, `sampler`, `scheduler`.
- Heuristics:
  - If multiple model loaders are reachable, pick the closest by hop count.
  - If LoRAs fan-in, keep those on the sampler → model path; otherwise omit.

## Output Schema
- Backward-compatible flat fields remain unchanged for non-MoE workflows.
- When MoE is detected:
  - Continue emitting today’s flat fields derived from a single “primary” sampler
    (e.g., largest `end_step` or last in order). This preserves downstream expectations.
  - Add a structured array field `Samplers detail` (name tentative) containing objects:
    - `node_id`, `model`, `model_hash`, `vae`, `vae_hash`
    - `sampler`, `scheduler`, `steps`, `start_step`, `end_step`, `cfg`, `shift`, `denoise`
    - `loras`: array of `{ name, hash, strength }`

### Example (PNGInfo JSON field)
```json
{
  "Samplers detail": [
    {
      "node_id": 42,
      "model": "wan2.2-high.safetensors",
      "model_hash": "a1b2c3d4e5",
      "vae": "wan-vae.safetensors",
      "vae_hash": "f6g7h8i9j0",
      "sampler": "Euler a",
      "scheduler": "Karras",
      "steps": 30,
      "start_step": 0,
      "end_step": 20,
      "cfg": 3.5,
      "shift": 0.0,
      "denoise": 1.0,
      "loras": [
        { "name": "detailer", "hash": "1111111111", "strength": 0.5 }
      ]
    },
    {
      "node_id": 51,
      "model": "wan2.2-low.safetensors",
      "model_hash": "1122334455",
      "vae": "wan-vae.safetensors",
      "vae_hash": "f6g7h8i9j0",
      "sampler": "DPM++ 2M",
      "scheduler": "Exponential",
      "steps": 30,
      "start_step": 20,
      "end_step": 30,
      "cfg": 3.0,
      "shift": 0.0,
      "denoise": 1.0,
      "loras": []
    }
  ]
}
```

## Parameters String Rendering
- Normal mode: single-line summary such as `Samplers: High[0–20] Euler a/Karras; Low[20–30] DPM++ 2M/Exponential`.
- Test/multiline mode: a readable block enumerating each sampler with key fields.

## JPEG Fallback Integration
- No changes to 64KB EXIF cap or stages. We keep the staged fallback:
  - full → reduced-exif → minimal → com-marker.
- The `Samplers detail` block is not added to the minimal allowlist. It will be trimmed in reduced/minimal stages to protect size budgets.
- We preserve the `Metadata Fallback: <stage>` marker semantics.

## Error Handling
- Wrap per-field extraction in `try/except`. Omit failing fields rather than injecting placeholders, except where placeholders are already defined in the project.
- Log context (node id, field name) at debug level for troubleshooting.

## Tests
- Unit tests for capture rules:
  - `WanVideo Sampler` captures `start_step` and `end_step`.
  - Scheduler parser variants (dict, tuple/list, string in multiple formats).
- Integration tests for MoE graphs:
  - Two model loaders + two samplers with distinct ranges and LoRAs.
  - Verify per-sampler associations and that flat fields are still present.
- JPEG fallback tests:
  - Lower `max_jpeg_exif_kb` and verify trimming of the detailed block.

## Documentation
- README: add a short “Wan2.2 (MoE) support” section when implemented.
- Environment Flags: document `METADATA_WAN_MOE_FORCE` and optional disable flag.

## Phased Rollout
1. Add `START_STEP`/`END_STEP` enums and extend Wan sampler rules.
2. Implement MoE detector (no behavior change) + unit tests.
3. Implement per-sampler collector and structured output, guarded behind detector.
4. Add parameters rendering; update tests.
5. Update README; validate fallback; ship.

## Risks and Mitigations
- Mis-association of models/LoRAs in complex graphs:
  - Use nearest-upstream heuristic and path-based filtering; expand tests.
- Output size in PNGInfo:
  - Struct stays in PNGInfo; trimmed during JPEG fallback stages.
- Node variants with different field names:
  - Add small selector aliases as discovered (`start`, `end`, etc.).


# Alternative Approach (better)
## More Modular, Versatile, and Future Proof
- Should implement multi-model / multi-sampler strategy adaptable to other workflows and models than just `WanVideoModelLoader` or `WanVideo Sampler`
- Something more general like when traced subgraph contains ≥ 2 Samplers; or when traced subgraph contains ≥ 2 model loaders. (of the two options, ≥ 2 Samplers is probably the only thing we need to consider).
- Should still add [new fields](#new-fields), but may have some additional fields from other samplers to add.
- Maybe something like, when saving image with `Save Image w/ Metadata Universal`:
  - Trace up to x samplers, set in a new UI widget (default 1), but fallback to as few as 1 (and current behaviour) if trace fails to detect multiple samplers (or to 0 with an error log message, if no samplers are found)
  - If samplers is set to 1 use current behaviour
  - If samplers >1, run multi-sampler trace
  - If a second sampler is found, workflow has at least 2 samplers, else fallback to current behaviour
  - If workflow has at least 2 samplers, continue trace (if samplers is set to > 2), and if an additional sampler is hit workflow has at least 3 samplers
  - Continue for up to x samplers
  - Multi-sampler metadata will have sections (e.g. 'Sampler_1:\n') for each sampler.
  - Sampler numbers will be set to reverse order of proximity to `Save Image w/ Metadata Universal` node (so, 3 is closest, 1 is furthest).
  - Multi-sampler trace should write parameters from nodes connected directly or indirectly to each sampler to that sampler's section in the metadata (similar to current behaviour).
  - Exceptions: any node(s) connected indirectly through another sampler; any node(s) which are executed after a sampler.
    - Example 1: node_1⟶node_2⟶sampler_1⟶sampler_2
      - node_1 and node_2 are recorded to sampler_1's metadata (if they contain relevant captured information), but they are not recorded to sampler_2's metadata because they are connected to sampler_2 indirectly through sampler_1
    - Example 2: node_1⟶sampler_1⟶node_2⟶sampler_2⟶node_3⟶sampler_3
      - node_1 is recorded to sampler_1's metadata (if it contains relevant captured information), but it is not recorded to sampler_2's or sampler_3's metadata because they are both connected to node_1 indirectly through 1 or more samplers.
      - node_2 is recorded to sampler_2's metadata (if it contains relevant captured information); node_2 is not recorded to sampler_1's metadata because it is executed after sampler_1; node_2 is not recorded to sampler_3's metadata because it is connected to node_2 indirectly through sampler_2. 
      - node_3 is recorded to sampler_3's metadata (if it contains relevant captured information), but it is not recorded to sampler_1's or sampler_2's metadata because node_3 is executed after both sampler_1 and sampler_2
    - Example 3: node_1⟶sampler_1⟶node_2⟶sampler_2 and node_1⟶sampler_2
      - node_1 is recorded to both sampler_1's and sampler_2's metadata (if it contains relevant captured information) because they are both connected to it directly
      - node_2 is recorded to sampler_2's metadata (if it contains relevant captured information), but it is not recorded to sampler_1's metadata because it it occurs after sampler_1's execution in the graph
  - As the multi-sampler trace is run, it should follow the above pathing logic to attribute the extracted metadata to the correct sampler(s).
