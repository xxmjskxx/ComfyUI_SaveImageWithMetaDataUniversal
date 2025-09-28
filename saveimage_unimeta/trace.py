"""Graph tracing utilities for locating upstream sampler and related nodes.

Provides BFS-based traversal to build a distance map from a starting node
and helper heuristics to identify sampler-like nodes when not explicitly
declared in the sampler definitions.
"""

import logging
import os
from collections import deque

from .defs.captures import CAPTURE_FIELD_LIST

# from . import SAMPLERS
from .defs.combo import SAMPLER_SELECTION_METHOD
from .defs.meta import MetaField
from .defs.samplers import SAMPLERS

from .utils.color import cstr

logger = logging.getLogger(__name__)

def _trace_debug_enabled() -> bool:
    # Reuse the same flag as capture for prompt/sampler tracing verbosity.
    return os.environ.get("METADATA_DEBUG_PROMPTS", "").strip() != ""


class Trace:
    @classmethod
    def trace(cls, start_node_id, prompt):
    # logger.debug("[Trace] Attempting to trace node ID: %s", start_node_id)
        if start_node_id not in prompt:
            # This check prevents the KeyError: -1
            logger.warning(
                "[Trace] start_node_id %s not found in prompt graph. Returning empty trace tree.",
                start_node_id,
            )
            return {}
        class_type = prompt[start_node_id]["class_type"]
        if _trace_debug_enabled():
            logger.debug(cstr("[Trace] Found class_type: %s").msg, class_type)
        Q = deque()  # noqa: N806 (algorithm queue conventional uppercase)
        Q.append((start_node_id, 0))
        visited = set()  # Keep track of visited nodes
        visited.add(start_node_id)
        trace_tree = {start_node_id: (0, class_type)}
        while len(Q) > 0:
            current_node_id, distance = Q.popleft()
            input_fields = prompt[current_node_id]["inputs"]
            for value in input_fields.values():
                if isinstance(value, list):
                    nid = value[0]
                    if nid not in visited and nid in prompt:  # Ensure the node is not visited and exists
                        class_type = prompt[nid]["class_type"]
                        trace_tree[nid] = (distance + 1, class_type)
                        Q.append((nid, distance + 1))
                        visited.add(nid)  # Mark the node as visited
        if _trace_debug_enabled():
            try:
                logger.debug(
                    cstr("[Trace] Built trace tree (size=%d) from start=%s").msg,
                    len(trace_tree),
                    start_node_id,
                )
            except Exception:
                pass
        return trace_tree

    @classmethod
    def find_sampler_node_id(cls, trace_tree, sampler_selection_method, node_id):
        # Rely on the caller to have called the definitions loader with the
        # appropriate merge order and coverage. Do not reload here to avoid
        # overriding conditional merge decisions.

        def is_sampler_like(class_type: str) -> bool:
            """
            Heuristic to identify a sampler node when it isn't explicitly listed in SAMPLERS.
            Priority:
              1) Explicitly in SAMPLERS
              2) Node capture rules include MetaField.SAMPLER_NAME
              3) Node capture rules include both MetaField.STEPS and MetaField.CFG
            """
            if class_type in SAMPLERS.keys():
                return True
            rules = CAPTURE_FIELD_LIST.get(class_type)
            if not rules:
                return False
            # Case 2: explicit sampler name capture exists
            if MetaField.SAMPLER_NAME in rules:
                return True
            # Case 3: has steps and cfg together (typical sampler signature)
            if MetaField.STEPS in rules and MetaField.CFG in rules:
                return True
            return False

        if sampler_selection_method == SAMPLER_SELECTION_METHOD[2]:
            node_id = str(node_id)
            _, class_type = trace_tree.get(node_id, (-1, None))
            if class_type is None:
                return -1
            # Accept either explicit sampler mapping or heuristic sampler-like nodes
            if is_sampler_like(class_type):
                return node_id
            return -1

        sorted_by_distance_trace_tree = sorted(
            [(k, v[0], v[1]) for k, v in trace_tree.items()],
            key=lambda x: x[1],
            reverse=(sampler_selection_method == SAMPLER_SELECTION_METHOD[0]),
        )
        if _trace_debug_enabled():
            try:
                logger.debug(
                    cstr("[Trace] Candidate nodes by distance (reversed=%s): %s").msg,
                    sampler_selection_method == SAMPLER_SELECTION_METHOD[0],
                    [f"{nid}:{dist}/{ctype}" for nid, dist, ctype in sorted_by_distance_trace_tree],
                )
            except Exception:
                pass
        # Pass 1: exact matches defined in SAMPLERS
        for nid, _, class_type in sorted_by_distance_trace_tree:
            if class_type in SAMPLERS.keys():
                if _trace_debug_enabled():
                    logger.debug(cstr("[Trace] Exact SAMPLERS match: %s").msg, nid)
                return nid

        # Pass 2: heuristic sampler-like detection via CAPTURE_FIELD_LIST
        for nid, _, class_type in sorted_by_distance_trace_tree:
            if is_sampler_like(class_type):
                if _trace_debug_enabled():
                    logger.debug(cstr("[Trace] Heuristic sampler-like match: %s").msg, nid)
                return nid
        return -1

    # --- Multi-sampler (Tier A + B) enumeration helpers ---
    @classmethod
    def enumerate_samplers(cls, trace_tree: dict, max_multi: int = 4) -> list[dict]:
        """Return ordered sampler candidate entries (Tier A explicit + Tier B rule-backed).

        Each entry structure:
            {
              'node_id': <str>,
              'tier': 'A' | 'B',
              'class_type': <str>,
              'sampler_name': <str|None>,
              'steps': <int|None>,
              'start_step': <int|None>,
              'end_step': <int|None>,
              'range_len': <int>,
              'is_segment': <bool>,
            }

        Ordering rules applied after collection:
            1. Primary first (tier priority A over B, then widest range_len, then steps, then farthest distance).
            2. Remaining by (range_len desc, original farthest distance, node id asc).

        Note: trace_tree values are (distance, class_type). Distance larger => farther upstream.
        """
        try:
            # Build distance-sorted list (farthest-first) for deterministic ordering base.
            nodes = [
                (nid, info[0], info[1])
                for nid, info in trace_tree.items()
                if isinstance(info, tuple) and len(info) >= 2
            ]
        except Exception:
            return []
        # Sort farthest-first (higher distance earlier)
        nodes.sort(key=lambda x: x[1], reverse=True)

        candidates: list[dict] = []
        seen_ids: set[str] = set()

        for nid, dist, class_type in nodes:
            if class_type in SAMPLERS and nid not in seen_ids:
                entry = cls._build_sampler_entry(nid, class_type, tier="A")
                candidates.append(entry)
                seen_ids.add(nid)
                continue
            # Tier B evaluation: rule-backed (must have sampler name + (steps or start+end))
            rules = CAPTURE_FIELD_LIST.get(class_type)
            if not rules or nid in seen_ids:
                continue
            meta_keys = set(m for m in rules.keys() if hasattr(m, "name"))
            has_name = any(getattr(m, "name", "") == MetaField.SAMPLER_NAME.name for m in meta_keys)
            has_steps = any(getattr(m, "name", "") == MetaField.STEPS.name for m in meta_keys)
            has_start = any(getattr(m, "name", "") == MetaField.START_STEP.name for m in meta_keys)
            has_end = any(getattr(m, "name", "") == MetaField.END_STEP.name for m in meta_keys)
            segment_ok = has_start and has_end
            if (has_start != has_end) and _trace_debug_enabled():  # mismatched segment definitions
                try:
                    logger.warning(
                        cstr("[Trace] Incomplete segment rule for class %s (start=%s end=%s) - ignoring segment").msg,
                        class_type,
                        has_start,
                        has_end,
                    )
                except Exception:
                    pass
            if has_name and (has_steps or segment_ok):
                entry = cls._build_sampler_entry(nid, class_type, tier="B", segment=segment_ok)
                candidates.append(entry)
                seen_ids.add(nid)

        if not candidates:
            return []

        # Compute primary
        primary = cls._select_primary(candidates, trace_tree)
        # Order remaining
        ordered: list[dict] = []
        if primary:
            ordered.append(primary)
        for c in candidates:
            if primary and c["node_id"] == primary["node_id"]:
                continue
            ordered.append(c)
        # Secondary ordering for non-primary
        if len(ordered) > 1:
            head, tail = ordered[0], ordered[1:]
            tail.sort(
                key=lambda e: (
                    -(e.get("range_len", 0) or 0),  # desc range
                    -trace_tree.get(e["node_id"], (0, ""))[0],  # farther distance first
                    e["node_id"],
                )
            )
            ordered = [head] + tail

        if len(ordered) > max_multi:
            if _trace_debug_enabled():
                logger.debug(cstr("[Trace] Truncating multi-sampler list %d -> %d").msg, len(ordered), max_multi)
            ordered = ordered[:max_multi]
        if _trace_debug_enabled():
            try:
                logger.debug(
                    cstr("[Trace] Multi-sampler candidates: %s").msg,
                    [f"{e['tier']}:{e['class_type']}#{e['node_id']}" for e in ordered],
                )
            except Exception:
                pass
        return ordered

    @classmethod
    def _build_sampler_entry(cls, node_id: str, class_type: str, tier: str, segment: bool = False) -> dict:
        # We only know start/end placeholders later once capture dictionary is built; store None now.
        entry = {
            "node_id": node_id,
            "tier": tier,
            "class_type": class_type,
            "sampler_name": None,
            "steps": None,
            "start_step": None,
            "end_step": None,
            "range_len": 0,
            "is_segment": segment,
        }
        return entry

    @classmethod
    def _select_primary(cls, candidates: list[dict], trace_tree: dict):
        # Separate by tier
        tierA = [c for c in candidates if c.get("tier") == "A"]
        tierB = [c for c in candidates if c.get("tier") == "B"]
        for group in (tierA, tierB):
            if not group:
                continue
            # Choose by widest range_len then steps then farthest distance then node id
            group.sort(
                key=lambda e: (
                    e.get("range_len", 0) or 0,
                    e.get("steps", 0) or 0,
                    trace_tree.get(e["node_id"], (0, ""))[0],
                    -int(e["node_id"]) if str(e["node_id"]).isdigit() else 0,
                ),
                reverse=True,
            )
            return group[0]
        return None

    @classmethod
    def filter_inputs_by_trace_tree(cls, inputs, trace_tree):
        filtered_inputs = {}
        for meta, inputs_list in inputs.items():
            for entry in inputs_list:
                # Support tuples of forms:
                #  (node_id, value)
                #  (node_id, value, field_name)
                #  (node_id, value, field_name, other...)
                # Existing downstream only needs node_id/value and distance from trace tree.
                try:
                    # Accept list or tuple entries (UP038 compliant union syntax)
                    if not isinstance(entry, list | tuple):  # noqa: UP038 - explicit modern union usage
                        continue
                    if len(entry) < 2:
                        continue
                    node_id = entry[0]
                    input_value = entry[1]
                except Exception:
                    continue
                trace = trace_tree.get(node_id)
                if trace is None:
                    continue
                distance = trace[0]
                filtered_inputs.setdefault(meta, []).append((node_id, input_value, distance))

        # sort by distance
        for k, v in filtered_inputs.items():
            filtered_inputs[k] = sorted(v, key=lambda x: x[2])
        if _trace_debug_enabled():
            try:
                logger.debug(
                    cstr("[Trace] Filtered inputs by distance: %s").msg,
                    {getattr(meta, 'name', str(meta)): v for meta, v in filtered_inputs.items()},
                )
            except Exception:
                pass
        return filtered_inputs
