"""Mappings of sampler and guider nodes to their conditioning text inputs.

This module provides two companion dictionaries used by the validator BFS
(``_get_node_id_list``) to resolve positive and negative prompt connections
in a ComfyUI workflow.

``SAMPLERS`` maps sampler class names to the input fields that carry their
positive and negative conditioning.  For example, ``KSampler`` uses
``"positive"`` and ``"negative"``, while ``SeargeSDXLSampler`` uses
``"base_positive"`` and ``"base_negative"``.  ``SamplerCustomAdvanced``
routes both through a single ``"guider"`` input — the downstream guider
node determines how conditioning is split.

``GUIDERS`` maps class names of guider and conditioning-modifier nodes
(e.g. ``CFGGuider``, ``BasicGuider``, ``ControlNetApplyAdvanced``) to the
conditioning inputs they expose.  When the BFS encounters one of these
nodes it follows only the input that matches the requested field
(positive or negative) instead of blindly exploring all inputs.

Both dictionaries are easily extensible: add a new entry keyed by the
node's class name with a sub-dictionary of conditioning mappings.

Attributes:
    GUIDERS (dict): A dictionary where keys are guider or conditioning-
                    modifier class names (str) and values map conditioning
                    type to the corresponding input name (str).
    SAMPLERS (dict): A dictionary where keys are sampler class names (str)
                     and values map conditioning type to the corresponding
                     input name (str).
"""
GUIDERS: dict[str, dict[str, str]] = {
    "CFGGuider": {
        "positive": "positive",
        "negative": "negative",
    },
    "PerpNegGuider": {
        "positive": "positive",
        "negative": "negative",
    },
    "Scheduled CFGGuider (Inspire)": {
        "positive": "positive",
        "negative": "negative",
    },
    "Scheduled PerpNeg CFGGuider (Inspire)": {
        "positive": "positive",
        "negative": "negative",
    },
    "DualCFGGuider": {
        "positive": "cond1",
        "negative": "negative",
    },
    "BasicGuider": {
        "positive": "conditioning",
    },
    # Conditioning-modifier nodes that pass-through separate positive/negative
    # conditioning paths and must not be traversed blindly.
    "ControlNetApplyAdvanced": {
        "positive": "positive",
        "negative": "negative",
    },
}
# Guider and conditioning-modifier nodes that route conditioning between
# text encoders and samplers.
# When the BFS in _get_node_id_list encounters one of these nodes while tracing
# from a SamplerCustomAdvanced node, it follows only the conditioning input that
# matches the requested field (positive/negative) instead of blindly exploring
# all inputs.  This ensures the negative prompt connected to a CFGGuider's
# *negative* input — or passed through ControlNetApplyAdvanced's *negative*
# input — is correctly detected.

SAMPLERS = {
    "KSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerAdvanced": {
        "positive": "positive",
        "negative": "negative",
    },
    # Flux - https://comfyanonymous.github.io/ComfyUI_examples/flux/
    "SamplerCustomAdvanced": {
        "positive": "guider",
        "negative": "guider",
    },
    # --- Add other common samplers here ---
    "SamplerCustom": {
        "positive": "positive",
        "negative": "negative",
    },
    "ClownsharKSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "ClownsharKSampler_Beta": {
        "positive": "positive",
        "negative": "negative",
    },
    "Legacy_SharkSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "UltraSharkSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "UnsamplerHookProvider": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSampler //Inspire": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerAdvanced //Inspire": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerProgress //Inspire": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerAdvancedProgress //Inspire": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerWithNAG": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerWithNAG (Advanced)": {
        "positive": "positive",
        "negative": "negative",
    },
    "SamplerCustomWithNAG": {
        "positive": "positive",
        "negative": "negative",
    },
    "KRestartSamplerCustomNoise": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerVariationsStochastic+": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerVariationsWithNoise+": {
        "positive": "positive",
        "negative": "negative",
    },
    "FL_KsamplerPlus": {
        "positive": "positive",
        "negative": "negative",
    },
    "FL_KsamplerPlusV2": {
        "positive": "positive",
        "negative": "negative",
    },
    "FL_KsamplerBasic": {
        "positive": "positive",
        "negative": "negative",
    },
    "FL_FractalKSampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "BNK_Unsampler": {
        "positive": "positive",
        "negative": "negative",
    },
    "UltraSharkSampler Tiled": {
        "positive": "positive",
        "negative": "negative",
    },
    "SeargeSDXLSampler": {
        "positive": "base_positive",
        "negative": "base_negative",
    },
    "SeargeSDXLSampler2": {
        "positive": "base_positive",
        "negative": "base_negative",
    },
    "SeargeSDXLSamplerV3": {
        "positive": "base_positive",
        "negative": "base_negative",
    },
    "SeargeSDXLImage2ImageSampler": {
        "positive": "base_positive",
        "negative": "base_negative",
    },
    "SeargeSDXLImage2ImageSampler2": {
        "positive": "base_positive",
        "negative": "base_negative",
    },
    "KSampler (WAS)": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSampler Cycle": {
        "positive": "positive",
        "negative": "negative",
    },
    "KSamplerAdvanced (WLSH)": {
        "positive": "positive",
        "negative": "negative",
    },
}
