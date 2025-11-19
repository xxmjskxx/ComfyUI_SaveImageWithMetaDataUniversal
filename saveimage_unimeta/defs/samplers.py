"""A dictionary mapping sampler names to their positive and negative conditioning text inputs.

This module provides a comprehensive mapping of various sampler implementations used within the ComfyUI ecosystem
to their corresponding positive and negative conditioning inputs. The dictionary `SAMPLERS` is the core component,
where each key is a string representing the name of a sampler, and its value is another dictionary specifying
the names of the positive and negative text conditioning inputs for that sampler.

This mapping is crucial for dynamically identifying and accessing the correct conditioning inputs when a sampler
is used in a ComfyUI workflow. For example, the standard "KSampler" uses "positive" and "negative" as its
conditioning inputs, while a more specialized sampler like "SeargeSDXLSampler" might use "base_positive" and
"base_negative". By centralizing this information, the system can abstract away these differences and handle
various samplers in a unified manner.

The dictionary is designed to be easily extensible. To add support for a new sampler, one simply needs to add
a new entry to the `SAMPLERS` dictionary with the sampler's name and the names of its conditioning inputs.

Attributes:
    SAMPLERS (dict): A dictionary where keys are sampler names (str) and values are dictionaries
                     mapping conditioning type (e.g., "positive", "negative") to the corresponding
                     input name (str).
"""
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
