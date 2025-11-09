"""Graph tracing utilities for locating upstream sampler and related nodes.

Provides BFS-based traversal to build a distance map from a starting node
and helper heuristics to identify sampler-like nodes when not explicitly
declared in the sampler definitions.
"""

import logging
import os
from collections import deque

from .defs import CAPTURE_FIELD_LIST

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
                pass  # Logging failure should not break trace tree building
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
                pass  # Logging failure should not break sampler node finding
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
                pass  # Logging failure should not break input filtering
        return filtered_inputs
