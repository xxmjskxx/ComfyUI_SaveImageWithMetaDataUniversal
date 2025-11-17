"""Provides metadata definitions for the ComfyUI-SizeFromPresets custom nodes.

This module is designed to integrate with the `ComfyUI-SizeFromPresets` custom nodes,
which can be found at: https://github.com/nkchocoai/ComfyUI-SizeFromPresets

The primary function of this module is to parse the `preset` string (e.g., "1024 x 768")
from the `EmptyLatentImageFromPresets` nodes to extract the image width and height.
It defines two formatter functions, `get_width` and `get_height`, to perform this parsing.

Attributes:
    CAPTURE_FIELD_LIST (dict): A dictionary that maps the `EmptyLatentImageFromPresetsSD15`
                               and `EmptyLatentImageFromPresetsSDXL` nodes to their
                               metadata capture configurations, using the custom
                               formatters to extract image dimensions.
"""
# https://github.com/nkchocoai/ComfyUI-SizeFromPresets/
from ..meta import MetaField


def get_width(preset, input_data):
    """Formatter function to extract the width from a preset string.

    Args:
        preset (str): The preset string, e.g., "1024 x 768".
        input_data (dict): The input data for the node.

    Returns:
        str: The extracted width as a string.
    """
    return preset.split("x")[0].strip()


def get_height(preset, input_data):
    """Formatter function to extract the height from a preset string.

    Args:
        preset (str): The preset string, e.g., "1024 x 768".
        input_data (dict): The input data for the node.

    Returns:
        str: The extracted height as a string.
    """
    return preset.split("x")[1].strip()


CAPTURE_FIELD_LIST = {
    "EmptyLatentImageFromPresetsSD15": {
        MetaField.IMAGE_WIDTH: {"field_name": "preset", "format": get_width},
        MetaField.IMAGE_HEIGHT: {"field_name": "preset", "format": get_height},
    },
    "EmptyLatentImageFromPresetsSDXL": {
        MetaField.IMAGE_WIDTH: {"field_name": "preset", "format": get_width},
        MetaField.IMAGE_HEIGHT: {"field_name": "preset", "format": get_height},
    },
    # TODO RandomEmptyLatentImageFromPresetsSD..
}
