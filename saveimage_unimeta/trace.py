"""Provides graph tracing utilities for for locating upstream sampler and related nodes.

This module contains the `Trace` class, which is used to traverse the workflow
graph, build a distance map from a starting node, and identify sampler nodes
based on a set of heuristics when not explicitly declared in the sampler definitions. This is crucial for correctly identifying the
source of various metadata attributes in the workflow.
"""

import logging
import os
from collections import deque
from typing import NamedTuple

from .defs import CAPTURE_FIELD_LIST

# from . import SAMPLERS
from .defs.combo import MODEL_SELECTION_METHOD, SAMPLER_SELECTION_METHOD
from .defs.meta import MetaField
from .defs.samplers import SAMPLERS
from .defs.validators import _is_link_input

from .utils.color import cstr

logger = logging.getLogger(__name__)

# Priority ranking for model-input names used to break ties when a loader
# exposes multiple model fields (e.g. base vs. refiner checkpoints).
_PRIMARY_INPUT_PRIORITY = {
    "base_ckpt_name": 0,
    "model_name": 0,
    "gguf_name": 1,
    "unet_name": 2,
    "diffusion_model_name": 3,
    "ckpt_name": 4,
    "checkpoint_name": 5,
    "checkpoint": 6,
    "stage_c": 7,
    "stage_b": 8,
    "extra_model_name": 9,
    "model_path": 10,
    "refiner_ckpt_name": 11,
}

# Sampler input names that may carry the base model, in lookup order.
_SAMPLER_MODEL_INPUTS = (
    "model",
    "base_model",
    "base_pipe",
    "base_sampler",
    "basic_pipe",
    "detailer_pipe",
    "guider",
    "model_input",
    "diffusion_model",
    "pipe",
    "refiner_model",
    "sampler_inputs",
)


class TraceEntry(NamedTuple):
    """Distance/class pair describing how far a node sits upstream."""

    distance: int
    class_type: str


def _trace_debug_enabled() -> bool:
    """Check if verbose tracing debug logging is enabled.

    This function checks the `METADATA_DEBUG_PROMPTS` environment variable to
    determine whether detailed logging for graph tracing should be activated.

    Returns:
        bool: True if debug logging is enabled, False otherwise.
    """
    # Reuse the same flag as capture for prompt/sampler tracing verbosity.
    return os.environ.get("METADATA_DEBUG_PROMPTS", "").strip() != ""


class Trace:
    """A class for tracing and analyzing ComfyUI workflow graphs."""

    @classmethod
    def trace(cls, start_node_id, prompt):
        """Perform a breadth-first search (BFS) traversal of the workflow graph.

        Starting from a given node, this method traverses the graph backwards
        (upstream) to build a "trace tree". This tree is a dictionary that maps
        each node ID to a tuple containing its distance from the start node and
        its class type.

        Args:
            start_node_id (str): The ID of the node to start the trace from.
            prompt (dict): The workflow prompt dictionary.

        Returns:
            dict: The trace tree, mapping node IDs to (distance, class_type)
                tuples.
        """
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
        node_queue: deque[tuple[str, int]] = deque()
        node_queue.append((start_node_id, 0))
        visited = {start_node_id}
        trace_tree: dict[str, TraceEntry] = {start_node_id: TraceEntry(0, class_type)}
        while node_queue:
            current_node_id, distance = node_queue.popleft()
            input_fields = prompt[current_node_id]["inputs"]
            for value in input_fields.values():
                if _is_link_input(value):
                    nid = value[0]
                    if nid not in visited and nid in prompt:  # Ensure the node is not visited and exists
                        class_type = prompt[nid]["class_type"]
                        trace_tree[nid] = TraceEntry(distance + 1, class_type)
                        node_queue.append((nid, distance + 1))
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
        """Find the ID of the sampler node in the trace tree.

        This method identifies the sampler node based on the specified selection
        method ('Farthest', 'Nearest', or 'By node ID'). It uses a set of
        heuristics to determine if a node is "sampler-like", which includes
        checking if it is explicitly listed in `SAMPLERS` or if its capture
        rules contain common sampler-related `MetaField`s.

        Args:
            trace_tree (dict): The trace tree generated by the `trace` method.
            sampler_selection_method (str): The method to use for selecting the
                sampler node.
            node_id (str): The node ID to use when the selection method is
                'By node ID'.

        Returns:
            str: The ID of the found sampler node, or -1 if no sampler is found.
        """
        # Legacy alias: workflows saved before the rename stored "Nearest".
        if sampler_selection_method == "Nearest":
            sampler_selection_method = SAMPLER_SELECTION_METHOD[1]

        # Rely on the caller to have called the definitions loader with the
        # appropriate merge order and coverage. Do not reload here to avoid
        # overriding conditional merge decisions.

        def is_sampler_like(class_type: str) -> bool:
            """Determine if a node is sampler-like based on heuristics.

            This helper function checks if a node's class type is present in the
            `SAMPLERS` dictionary or if its capture rules in `CAPTURE_FIELD_LIST`
            indicate that it is a sampler.

            Heuristic to identify a sampler node when it isn't explicitly listed in SAMPLERS.
            Priority:
              1) Explicitly in SAMPLERS
              2) Node capture rules include MetaField.SAMPLER_NAME
              3) Node capture rules include both MetaField.STEPS and MetaField.CFG

            Args:
                class_type (str): The class type of the node.

            Returns:
                bool: True if the node is sampler-like, False otherwise.
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
            entry = trace_tree.get(node_id)
            if entry is None:
                return -1
            # Accept either explicit sampler mapping or heuristic sampler-like nodes
            if is_sampler_like(entry.class_type):
                return node_id
            return -1

        reverse = sampler_selection_method == SAMPLER_SELECTION_METHOD[0]
        sorted_by_distance_trace_tree = sorted(
            [(node_id, entry.distance, entry.class_type) for node_id, entry in trace_tree.items()],
            key=lambda x: x[1],
            reverse=reverse,
        )
        if _trace_debug_enabled():
            try:
                logger.debug(
                    cstr("[Trace] Candidate nodes by distance (reversed=%s): %s").msg,
                    reverse,
                    [f"{nid}:{dist}/{ctype}" for nid, dist, ctype in sorted_by_distance_trace_tree],
                )
            except Exception:
                pass  # Logging failure should not break sampler node finding
        # Prefer exact matches defined in SAMPLERS; fall back to heuristics.
        exact = [c for c in sorted_by_distance_trace_tree if c[2] in SAMPLERS]
        candidates = exact or [c for c in sorted_by_distance_trace_tree if is_sampler_like(c[2])]
        if not candidates:
            return -1
        best_distance = candidates[0][1]
        tied = [c for c in candidates if c[1] == best_distance]
        if len(tied) > 1:
            logger.warning(
                "[Trace] Sampler selection (%s) is ambiguous among %s; choosing the first deterministically.",
                sampler_selection_method,
                [f"{nid}:{ctype}" for nid, _, ctype in tied],
            )
            tied.sort(key=lambda c: str(c[0]))
        return tied[0][0]

    @classmethod
    def _model_field_name(cls, class_type: str) -> str | None:
        """Return the model field/prefix a class captures, or ``None``."""
        rules = CAPTURE_FIELD_LIST.get(class_type)
        if not rules:
            return None
        model_rule = rules.get(MetaField.MODEL_NAME) or rules.get(MetaField.MODEL_HASH)
        if not model_rule:
            return None
        return model_rule.get("field_name") or model_rule.get("prefix")

    @classmethod
    def _primary_model_input_names(cls, sampler_node: dict) -> tuple[str, ...]:
        """Return the sampler input names that carry the base model."""
        inputs = sampler_node.get("inputs", {}) if isinstance(sampler_node, dict) else {}
        for input_name in _SAMPLER_MODEL_INPUTS:
            if input_name in inputs:
                return (input_name,)
        return _SAMPLER_MODEL_INPUTS

    @classmethod
    def _walk_upstream_from_inputs(cls, start_node_id, prompt, first_hop_inputs):
        """BFS upstream from selected inputs of ``start_node_id``.

        Only the first hop is constrained to ``first_hop_inputs``; subsequent
        hops follow every link so intermediate nodes (model patches, LoRA
        loaders) are traversed through to the actual model loader.
        """
        if start_node_id not in prompt:
            return {}
        start_inputs = prompt[start_node_id].get("inputs", {})
        queue: deque[tuple[str, int]] = deque()
        for input_name in first_hop_inputs:
            value = start_inputs.get(input_name)
            if _is_link_input(value) and value[0] in prompt:
                queue.append((value[0], 1))
        distances: dict[str, int] = {}
        while queue:
            node_id, distance = queue.popleft()
            known = distances.get(node_id)
            if known is not None and known <= distance:
                continue
            distances[node_id] = distance
            for value in prompt[node_id].get("inputs", {}).values():
                if _is_link_input(value) and value[0] in prompt:
                    queue.append((value[0], distance + 1))
        return distances

    @classmethod
    def find_model_node_id(
        cls,
        sampler_node_id,
        prompt,
        selection_method=MODEL_SELECTION_METHOD[0],
        node_id=0,
    ):
        """Find the primary base-model loader node feeding ``sampler_node_id``.

        With ``MODEL_SELECTION_METHOD[1]`` ("By node ID") the explicit
        ``node_id`` is returned when it is a known model loader. Otherwise the
        nearest loader reached by walking upstream from the sampler's model
        inputs is selected, with ties broken by ``_PRIMARY_INPUT_PRIORITY`` and
        a deterministic fallback.
        """
        if sampler_node_id not in prompt:
            return -1
        if selection_method == MODEL_SELECTION_METHOD[1]:
            nid = str(node_id)
            if nid in prompt and cls._model_field_name(prompt[nid].get("class_type", "")) is not None:
                return nid
            return -1
        sampler_node = prompt[sampler_node_id]
        model_inputs = cls._primary_model_input_names(sampler_node)
        distances = cls._walk_upstream_from_inputs(sampler_node_id, prompt, model_inputs)
        candidates = []
        for nid, distance in distances.items():
            field_name = cls._model_field_name(prompt[nid].get("class_type", ""))
            if field_name is None:
                continue
            priority = _PRIMARY_INPUT_PRIORITY.get(field_name, 999)
            candidates.append((distance, priority, str(nid)))
        if not candidates:
            if _trace_debug_enabled():
                logger.warning("[Trace] No model loader found upstream of sampler %s", sampler_node_id)
            return -1
        candidates.sort(key=lambda c: (c[0], c[1]))
        best = [c for c in candidates if c[0] == candidates[0][0] and c[1] == candidates[0][1]]
        if len(best) > 1:
            logger.warning(
                "[Trace] Primary model selection is ambiguous among %s; choosing deterministically.",
                [c[2] for c in best],
            )
            best.sort(key=lambda c: c[2])
        return best[0][2]

    @classmethod
    def filter_inputs_by_trace_tree(cls, inputs, trace_tree):
        """Filter and sort captured inputs based on a trace tree.

        This method filters the captured `inputs` to include only those that
        originate from nodes present in the `trace_tree`. It also augments the
        input entries with their distance from the start of the trace and sorts
        them by this distance.

        Args:
            inputs (dict): The dictionary of captured inputs.
            trace_tree (dict): The trace tree to filter by.

        Returns:
            dict: The filtered and sorted dictionary of inputs.
        """
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
                filtered_inputs.setdefault(meta, []).append((node_id, input_value, trace.distance))

        # sort by distance
        for k, v in filtered_inputs.items():
            filtered_inputs[k] = sorted(v, key=lambda x: x[2])
        if _trace_debug_enabled():
            try:
                logger.debug(
                    cstr("[Trace] Filtered inputs by distance: %s").msg,
                    {getattr(meta, "name", str(meta)): v for meta, v in filtered_inputs.items()},
                )
            except Exception:
                pass  # Logging failure should not break input filtering
        return filtered_inputs
