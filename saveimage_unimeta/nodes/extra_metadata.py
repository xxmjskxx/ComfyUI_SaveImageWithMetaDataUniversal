"""Provides the `CreateExtraMetaDataUniversal` node for ComfyUI.

This module contains the implementation of a node that allows users to manually
add key-value pairs to the metadata of a saved image. This is useful for
adding information that is not automatically captured by the metadata scanner.
"""


class CreateExtraMetaDataUniversal:
    """A node to collect key/value pairs and emit an EXTRA_METADATA payload.

    This node allows users to manually input up to four key-value pairs, which
    are then merged with an optional incoming `extra_metadata` mapping. This
    enables the injection of custom data into the metadata pipeline without
    modifying any configuration files.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `CreateExtraMetaDataUniversal` node.

        This method specifies the required and optional inputs for the node,
        including four key-value pairs and an optional `extra_metadata` input.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
        return {
            "required": {
                "key1": ("STRING", {"default": "", "multiline": False}),
                "value1": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "key2": ("STRING", {"default": "", "multiline": False}),
                "value2": ("STRING", {"default": "", "multiline": False}),
                "key3": ("STRING", {"default": "", "multiline": False}),
                "value3": ("STRING", {"default": "", "multiline": False}),
                "key4": ("STRING", {"default": "", "multiline": False}),
                "value4": ("STRING", {"default": "", "multiline": False}),
                "extra_metadata": ("EXTRA_METADATA",),
            },
        }

    RETURN_TYPES = ("EXTRA_METADATA",)
    FUNCTION = "create_extra_metadata"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    DESCRIPTION = (
        "Manually create extra metadata key-value pairs to include in saved images. "
        "Keys and values should be strings. Commas in values will be replaced with slashes."
    )

    def create_extra_metadata(
        self,
        key1,
        value1,
        extra_metadata=None,
        key2="",
        value2="",
        key3="",
        value3="",
        key4="",
        value4="",
    ):
        """Merge provided key/value pairs into a metadata dictionary.

        This method combines the input key-value pairs with an optional existing
        metadata dictionary and returns the result as a tuple, which is the
        standard format for ComfyUI node outputs.

        Args:
            key1 (str): The first key for the metadata.
            value1 (str): The first value for the metadata.
            extra_metadata (dict, optional): An existing dictionary of metadata.
                If None, a new dictionary is created. Defaults to None.
            key2 (str, optional): The second key for the metadata. Defaults to "".
            value2 (str, optional): The second value for the metadata. Defaults to "".
            key3 (str, optional): The third key for the metadata. Defaults to "".
            value3 (str, optional): The third value for the metadata. Defaults to "".
            key4 (str, optional): The fourth key for the metadata. Defaults to "".
            value4 (str, optional): The fourth value for the metadata. Defaults to "".

        Returns:
            tuple: A tuple containing the updated metadata dictionary.
        """
        if extra_metadata is None:
            extra_metadata = {}
        extra_metadata.update(
            {
                key1: value1,
                key2: value2,
                key3: value3,
                key4: value4,
            }
        )
        return (extra_metadata,)
