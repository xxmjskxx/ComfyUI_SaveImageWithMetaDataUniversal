"""Provides metadata definitions for the ComfyUI-Miaoshouai-Tagger custom node.

This module contains configurations for integrating the `ComfyUI-Miaoshouai-Tagger`,
which can be found at: https://github.com/miaoshouai/ComfyUI-Miaoshouai-Tagger

It defines the necessary mappings for metadata capture fields, allowing
the `saveimage_unimeta` node to correctly interpret and record data from workflows
that utilize this custom node.

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary that specifies how to capture metadata
                               fields from the `Miaoshouai_Flux_CLIPTextEncode` node.
                               Each entry maps a standard metadata field (e.g.,
                               `MetaField.POSITIVE_PROMPT`) to the corresponding
                               field name within the node's widget values.
"""
# https://github.com/miaoshouai/ComfyUI-Miaoshouai-Tagger
from ..meta import MetaField


CAPTURE_FIELD_LIST = {
    "Miaoshouai_Flux_CLIPTextEncode": {
        MetaField.POSITIVE_PROMPT: {"field_name": "caption"},
        MetaField.GUIDANCE: {"field_name": "guidance"},
    },
}
