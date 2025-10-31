# Complete end-to-end plan

## 1. Scope Boundaries

In scope:
- Multi-sampler enumeration (cap 4, farthest-first path ordering already accepted).
- Sampler detection using ONLY:
  - Tier A: Explicit known sampler node classes / type IDs (existing `SAMPLERS` list).
  - Tier B: Nodes that have capture rules emitting BOTH `SAMPLER_NAME` (or equivalent) and at least one step indicator (`STEPS` or `START_STEP` + `END_STEP` pair).
- Per-sampler segment metadata (range aware).
- Structured metadata block (key: `Samplers detail`) only when >1 sampler.
- Parameter string augmentation with appended per-sampler mini spec.
- Primary sampler selection logic (range precedence).
- Fallback stage compatibility (structured block suppressed in reduced/minimal fallback stages per existing trimming rules; parameters retain appended summary unless trimmed entirely).
- Start/end segment-aware rendering (for wrappers providing partial ranges).

Out of scope (explicitly deferred for later):
- Experimental heuristic scanning (Tier C).
- Any inference from single `STEPS` alone without rule + sampler name.
- WAN-specific separate extension file (fold into existing rule file).
- Workflow gzip placeholder implementation (already noted as future).

## 2. Definitions & Data Contracts

New internal sampler entry structure (in-memory, not all fields serialized directly):
```
SamplerEntry = {
  "node_id": int,
  "tier": Literal["A","B"],
  "sampler_name": str,
  "steps": int | None,          # Total steps if node provides singular
  "start_step": int | None,     # Segment start (0-based)
  "end_step": int | None,       # Segment end (exclusive or inclusive? -> Use inclusive internally, display human-friendly)
  "range_len": int,             # Derived: (end_step - start_step + 1) where both present
  "is_segment": bool,           # True if start/end present
  "source_rule_ids": list[str], # Optional: for debugging/troubleshooting
}
```

Primary sampler selection metric:
1. Prefer Tier A over Tier B.
2. Within same tier:
   - If any segment samplers present: choose widest `range_len`.
   - Else fall back to largest `steps`.
3. Tie-breaker: farthest-first traversal order (already determined in existing trace path list).
4. Last tie: lowest `node_id`.

Structured metadata key `Samplers detail` (only if length > 1):
Each sampler rendered as one JSON-ish flat object inside a list-like textual representation OR retained as dict (depending on existing formatting style). Example textual value (single line unless multiline mode active):
```
[ {Name: Euler a, Steps: 30}, {Name: DPM++ 2M, Start: 31, End: 50}, {Name: Heun, Start: 51, End: 60} ]
```
Rules:
- Include `Steps` only if sampler supplies a whole-run count and no start/end.
- Include `Start`/`End` only if segment.
- Omit absent fields (no placeholders).
- Preserve listing order = primary first, then remaining in descending range length, tie by insertion order (trace order).

Parameter string augmentation (when >1 sampler):
Append after main line:
```
, Samplers: Euler a (0-30) | DPM++ 2M (31-50) | Heun (51-60)
```
Formatting rules:
- Use `(start-end)` where segment; if only steps and it's the primary full-run sampler, optionally omit range if redundant; decision: KEEP `(0-<steps-1>)` only if there are segments after it for clarity.
- Separator: ` | ` (distinct from metadata’s comma semantics).
- If multiline mode (test mode): put on its own line prefixed: `Samplers:` without leading comma.

Fallback trimming:
- `reduced-exif`: parameters preserved (includes appended `Samplers:` line), structured `Samplers detail` dropped.
- `minimal`: both structured block and appended Samplers line trimmed unless allowlist includes it. (Decision: DO NOT add new allowlist entry; keep lean.)
- `com-marker`: nothing but fallback marker as already established.

## 3. File-Level Changes

1. trace.py
   - Add function `enumerate_samplers(trace_result, capture_rules_index, max_multi)` returning ordered `list[SamplerEntry]`.
   - Refactor existing single-sampler detection into extraction of Tier A candidate list (explicit).
   - Add rule-backed sampler detection:
     - For each node encountered in farthest-first traversal:
       - Check if capture rules include both sampler name field (MetaField.SAMPLER_NAME) and either STEPS or START/END pair.
       - Validate it produces a latent or consumes model (reuse existing connection analysis logic).
   - Compose final candidate list, deduplicate by node id (explicit takes precedence).
   - Derive segment ranges:
     - If node supplies START/END, record.
     - If only STEPS and no others give global steps range: interpret range as (0 .. steps-1) if this sampler becomes primary and no segments otherwise; segments always rely on their explicit start/end.

2. node.py (or whichever orchestrates metadata assembly)
   - Integrate multi-sampler enumeration before existing parameter construction.
   - Determine primary sampler id using selection rules.
   - Store sampler entries in capture context for later formatting.
   - Adjust parameters string builder: append multi-sampler summary when >1.

3. Formatting/utility (possible new file `saveimage_unimeta/multisampler.py` if separation preferred)
   - Pure helpers: `format_samplers_detail(entries, multiline: bool)` and `format_samplers_parameter_tail(entries, multiline: bool)`.

4. Existing Wan wrapper rule file
   - Ensure it adds START_STEP / END_STEP fields (and SAMPLER_NAME). If already outputs those fields, no change other than confirming they appear together.

5. `captures.py` / rule index (only if needed)
   - No reordering of existing stable keys.
   - Confirm new fields already enumerated via MetaField; no further enum changes required.

6. Tests directory (create if absent): e.g. `tests/test_multi_samplers.py`
   - Add synthetic graph fixtures:
     - Case A: Single explicit sampler → no `Samplers detail`.
     - Case B: Explicit + one rule-backed segment → structured list length 2; ordering + primary detection.
     - Case C: One full-run explicit + two segment wrappers (Tier B) → ordering by widest range after primary.
     - Case D: Two rule-backed (no explicit) → primary by widest range then node id.
     - Case E: Rule-backed sampler without CFG but with STEPS + SAMPLER_NAME accepted.
     - Fallback scenario: Force small EXIF size; assert structured key missing in reduced/minimal; appended line present only in reduced.

## 4. Algorithm Details

Enumeration pseudocode:
```
def enumerate_samplers(graph, path_order, rules, max_multi):
    explicit = []
    rule_backed = []
    seen = set()

    for node_id in path_order:   # farthest-first already
        if node_is_explicit_sampler(node_id):
            entry = build_entry(node_id, tier="A")
            explicit.append(entry)
            seen.add(node_id)
        else:
            fields = rules.get(node_id, set())
            if has_sampler_name(fields) and (has_steps(fields) or has_start_end(fields)):
                if qualifies_by_io(graph, node_id):
                    if node_id not in seen:
                        entry = build_entry(node_id, tier="B")
                        rule_backed.append(entry)
                        seen.add(node_id)

    candidates = explicit + rule_backed
    # Derive range_len
    for c in candidates:
        if c.start_step is not None and c.end_step is not None:
            c.range_len = c.end_step - c.start_step + 1
        elif c.steps is not None:
            c.range_len = c.steps  # provisional
        else:
            c.range_len = 0

    primary = select_primary(candidates)
    ordered = order_remaining(primary, candidates)
    return ordered[:max_multi], primary
```

Selection:
```
def select_primary(candidates):
    tier_groups = {"A": [], "B": []}
    for c in candidates: tier_groups[c.tier].append(c)
    for tier in ["A","B"]:
        if tier_groups[tier]:
            # prefer segment with largest range_len else largest steps
            sorted_candidates = sorted(tier_groups[tier],
                key=lambda c: (c.range_len, -c.node_id), reverse=True)
            return sorted_candidates[0]
    return None
```

Ordering of remaining:
- Primary first.
- Remaining sorted by:
  - Desc `range_len`
  - Original path index (stable)
  - Node id as tertiary

## 5. Edge Cases & Handling

- No candidates: Behavior unchanged (legacy single-sampler path sets parameters as before).
- Multiple full-run samplers (no segments, all with steps): primary largest steps, rest listed (still qualifies for multi-sampler output because count >1).
- Mixed segments overlapping ranges: No normalization; we simply report declared ranges. (Future improvement could validate overlap; for now just log a warning if overlap >0.)
- Segment with missing end/start parity: If only one of START/END appears → ignore node (log warning).
- Steps + Start/End both present: Prefer explicit start/end; ignore steps for range (still keep Steps out of the structured object to avoid redundancy).
- Max cap (< number of enumerated): Truncate after ordering; log truncation with count of omitted.

## 6. Logging & Diagnostics

- Introduce logger debug lines prefix: `[multi-sampler]`.
- Warnings:
  - Segment missing counterpart START/END.
  - Overlapping segment ranges (include pair node ids and ranges).
  - Truncation due to cap.
- Debug:
  - Candidate list before selection.
  - Chosen primary node id + tier.

No INFO-level spam unless fallback stage modifications occur (existing pattern honored).

## 7. Performance Considerations

- Single pass over traversal path; O(N) where N = nodes in traced path.
- Rule lookup: Pre-index capture rules once (dict node_id -> set of MetaFields).
- No additional graph traversals; reuse existing BFS result.

## 8. Fallback Integration

- Structured `Samplers detail` added at same level as other metadata dict entries (after existing stable keys; appended to avoid reordering).
- For minimal fallback trimming: Do NOT add `Samplers detail` key to allowlist; thus dropped.
- Parameter augmentation line considered part of parameters string; existing logic that reduces parameters to minimal subset will strip it indirectly when parameters are rebuilt—ensure logic that constructs minimal parameters does not parse appended Samplers line as a core field (i.e., appended only after minimal filtering stage OR conditional on reduced stage presence). Implementation detail: build base parameters first, then append sampler tail only if stage == full.

Stages:
- full: structured + tail
- reduced-exif: tail only
- minimal: neither
- com-marker: neither

## 9. Testing Plan (Detailed)

Unit tests (pure logic):
- `test_select_primary_tier_priority()`
- `test_segment_range_wins_over_steps()`
- `test_rule_backed_sampler_without_cfg_is_detected()`
- `test_missing_end_ignored()`
- `test_overlap_warning_emitted()` (can mock logger)

Integration tests:
- Construct synthetic capture output with 3 sampler nodes; verify ordering + structured value string exact match.
- Fallback size test: set artificially low `max_jpeg_exif_kb` to trigger reduced/minimal; assert presence/absence states.

Golden output sample for multi-sampler case saved to fixture for regression.

## 10. Documentation Updates

Files to update:
- README: Section “Multi-sampler Metadata” (new) with:
  - When it appears.
  - How to add custom samplers (add capture rule with name + steps or start/end).
  - Primary selection rules.
  - Fallback behavior matrix.
- WAN22_SUPPORT.md: Add “Implemented Alternative Approach – A+B Only” note replacing provisional design statements.
- CHANGELOG (Unreleased):
  - Added: Multi-sampler metadata (Samplers detail) + parameter augmentation.
  - Added: START_STEP / END_STEP integration live.
  - Note: Only explicit & rule-backed detection (no heuristic inference).

## 11. Risk Mitigation

Potential regressions:
- Existing single-sampler parameters mutated inadvertently.
  - Mitigation: Preserve pre-augmentation parameter string; only append tail when >1 sampler.
- Ordering instability:
  - Mitigation: Deterministic sort chain + test fixture.
- EXIF size inflation:
  - Mitigation: Keep structured block concise; no redundant fields; fallback test ensures trimming path.

## 12. Rollout / Guard Rails

- No new env flag needed (keeping surface minimal).
- If future heuristic tier desired, can introduce `METADATA_EXPERIMENTAL_SAMPLER_SCAN` later without breaking current logic.
- Provide debug toggle via existing `METADATA_DEBUG_PROMPTS` to surface sampler enumeration details if set.

## 13. Implementation Sequence (Step-by-Step)

1. Create helper in `trace.py` (enumeration + selection).
2. Integrate into node save pipeline before parameters string creation.
3. Add formatting helpers.
4. Add logic for fallback stage filtering of structured key + tail.
5. Add tests (unit first, then integration).
6. Run lint + tests.
7. Update docs & changelog.
8. Final verification: generate sample with multi-sampler; confirm outputs.

## 14. Acceptance Criteria Checklist

- When exactly one sampler: No `Samplers detail`, no appended line changes from prior behavior.
- When >1 sampler: Structured key present (except reduced/minimal), appended tail present (full, reduced).
- Correct omission of absent fields per sampler.
- Ordering deterministic and matches rules.
- Fallback trimming behavior matches matrix.
- No reordering or mutation of pre-existing metadata keys besides appending new one.
- Tests passing; lint clean.
