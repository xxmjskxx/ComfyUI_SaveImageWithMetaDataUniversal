"""Defines the selection-method lists for use in ComfyUI nodes.

This module provides the `SAMPLER_SELECTION_METHOD` list (for choosing which
upstream sampler node is authoritative) and the `MODEL_SELECTION_METHOD` list
(for choosing which base-model loader is the primary model).
"""
# "Nearest" is retained as a legacy value: workflows serialized before the
# rename stored the literal "Nearest", and ComfyUI may reset an out-of-list
# combo value on UI load/re-save. Trace.find_sampler_node_id aliases "Nearest"
# to "Auto (Nearest)", so both select the nearest sampler.
SAMPLER_SELECTION_METHOD = ["Farthest", "Auto (Nearest)", "By node ID", "Nearest"]
MODEL_SELECTION_METHOD = ["Auto", "By node ID"]
