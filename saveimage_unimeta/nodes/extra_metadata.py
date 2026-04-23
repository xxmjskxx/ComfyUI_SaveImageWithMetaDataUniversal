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

    EXTRA_METADATA_PAIR_COUNT = 4

    @classmethod
    def _build_pair_inputs(cls, start_index, end_index):
        """Build the repeated key/value string inputs for the node schema."""
        pair_inputs = {}
        for index in range(start_index, end_index + 1):
            pair_inputs[f"key{index}"] = ("STRING", {"default": "", "multiline": False})
            pair_inputs[f"value{index}"] = ("STRING", {"default": "", "multiline": False})
        return pair_inputs

    @classmethod
    def _pair_field_names(cls):
        """Return the ordered field names matching the declared key/value inputs."""
        field_names = []
        for index in range(1, cls.EXTRA_METADATA_PAIR_COUNT + 1):
            field_names.extend((f"key{index}", f"value{index}"))
        return tuple(field_names)

    @classmethod
    def _normalize_pair_arguments(cls, pair_args, pair_kwargs):
        """Normalize positional and keyword pair inputs into a validated mapping."""
        field_names = cls._pair_field_names()
        if len(pair_args) > len(field_names):
            raise TypeError(f"Expected at most {len(field_names)} pair values, got {len(pair_args)}")

        unexpected_names = set(pair_kwargs) - set(field_names)
        if unexpected_names:
            unexpected_list = ", ".join(sorted(unexpected_names))
            raise TypeError(f"Unexpected metadata arguments: {unexpected_list}")

        normalized_pairs = {}
        for field_name, field_value in zip(field_names, pair_args):
            if field_name in pair_kwargs:
                raise TypeError(f"Got multiple values for argument '{field_name}'")
            normalized_pairs[field_name] = field_value

        normalized_pairs.update(pair_kwargs)
        return normalized_pairs

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
                **cls._build_pair_inputs(start_index=1, end_index=1),
            },
            "optional": {
                **cls._build_pair_inputs(start_index=2, end_index=cls.EXTRA_METADATA_PAIR_COUNT),
                "extra_metadata": ("EXTRA_METADATA",),
            },
        }

    RETURN_TYPES = ("EXTRA_METADATA",)
    FUNCTION = "create_extra_metadata"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    DESCRIPTION = (
        "Manually create extra metadata key-value pairs to include in saved images.\n"
        "Keys and values should be strings.\nKeys without values will be ignored and vice versa."
    )

    def create_extra_metadata(
        self,
        extra_metadata=None,
        *pair_args,
        **kwargs,
    ):
        """Merge provided key/value pairs into a metadata dictionary.

        This method combines the input key-value pairs with an optional existing
        metadata dictionary and returns the result as a tuple, which is the
        standard format for ComfyUI node outputs.

        Args:
            extra_metadata (dict, optional): An existing dictionary of metadata.
                If None, a new dictionary is created. Defaults to None.
            *pair_args: Positional ``keyN``/``valueN`` pairs kept for direct-call compatibility.
            **kwargs: Dynamic ``keyN``/``valueN`` pairs aligned with ``INPUT_TYPES``.

        Returns:
            tuple: A tuple containing the updated metadata dictionary.
        """
        # Create a new dictionary to avoid mutating the input and to prevent
        # stale cache issues from mutable default arguments
        result = {}
        # Copy existing metadata if provided
        if extra_metadata is not None:
            result.update(extra_metadata)
        normalized_pairs = self._normalize_pair_arguments(pair_args, kwargs)
        # Add the new key-value pairs, only if the key is non-empty
        for index in range(1, self.EXTRA_METADATA_PAIR_COUNT + 1):
            key = normalized_pairs.get(f"key{index}", "")
            value = normalized_pairs.get(f"value{index}", "")
            if key:
                result[key] = value
        return (result,)
