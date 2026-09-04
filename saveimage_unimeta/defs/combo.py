"""Defines the selection-method lists for use in ComfyUI nodes.

This module provides the `SAMPLER_SELECTION_METHOD` list (for choosing which
upstream sampler node is authoritative) and the `MODEL_SELECTION_METHOD` list
(for choosing which base-model loader is the primary model).
"""
SAMPLER_SELECTION_METHOD = ["Farthest", "Auto (Nearest)", "By node ID"]
MODEL_SELECTION_METHOD = ["Auto", "By node ID"]
