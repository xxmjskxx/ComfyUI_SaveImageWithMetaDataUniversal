"""Provides the `CreateExtraMetaDataUniversal` node for ComfyUI.

This module contains the implementation of a node that allows users to manually
add key-value pairs to the metadata of a saved image. This is useful for
adding information that is not automatically captured by the metadata scanner.
"""


from collections.abc import Mapping
from typing import Any


class CreateExtraMetaDataUniversal:
    """A node to collect key/value pairs and emit an EXTRA_METADATA payload.

    This node allows users to manually input up to
    ``EXTRA_METADATA_PAIR_COUNT`` key-value pairs, which are then merged with
    an optional incoming ``extra_metadata`` mapping. This enables the
    injection of custom data into the metadata pipeline without modifying any
    configuration files.
    """

    EXTRA_METADATA_PAIR_COUNT = 4

    @classmethod
    def _validated_pair_count(cls) -> int:
        """Return the configured pair count after enforcing a valid minimum."""
        pair_count = cls.EXTRA_METADATA_PAIR_COUNT
        if not isinstance(pair_count, int) or isinstance(pair_count, bool):
            raise TypeError(
                "CreateExtraMetaDataUniversal.EXTRA_METADATA_PAIR_COUNT must be an integer, "
                f"got {type(pair_count).__name__}"
            )
        if pair_count < 1:
            raise ValueError(
                f"CreateExtraMetaDataUniversal.EXTRA_METADATA_PAIR_COUNT must be >= 1, got {pair_count}"
            )
        return pair_count

    @classmethod
    def _build_pair_inputs(cls, start_index: int, end_index: int) -> dict[str, tuple[str, dict[str, Any]]]:
        """Build the repeated key/value string inputs for the node schema."""
        cls._validated_pair_count()
        pair_inputs = {}
        for index in range(start_index, end_index + 1):
            pair_inputs[f"key{index}"] = ("STRING", {"default": "", "multiline": False})
            pair_inputs[f"value{index}"] = ("STRING", {"default": "", "multiline": False})
        return pair_inputs

    @classmethod
    def _pair_field_names(cls) -> tuple[str, ...]:
        """Return the ordered field names matching the declared key/value inputs."""
        field_names = []
        for index in range(1, cls._validated_pair_count() + 1):
            field_names.extend((f"key{index}", f"value{index}"))
        return tuple(field_names)

    @classmethod
    def _normalize_pair_arguments(cls, pair_args: tuple[Any, ...], pair_kwargs: dict[str, Any]) -> dict[str, Any]:
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
        including a configurable number of key-value pairs plus an optional
        ``extra_metadata`` input.

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
        "Keys and values are expected to be strings.\nPairs with empty keys or values equal to None or '' are ignored."
    )

    def create_extra_metadata(
        self,
        extra_metadata: Mapping[Any, Any] | None = None,
        *pair_args: Any,
        **kwargs: Any,
    ) -> tuple[dict[Any, Any]]:
        """Merge provided key/value pairs into a metadata dictionary.

        This method combines the input key-value pairs with an optional existing
        metadata dictionary and returns the result as a tuple, which is the
        standard format for ComfyUI node outputs.

        Args:
            extra_metadata (Mapping[Any, Any] | None, optional): An existing
                metadata mapping. If None, a new dictionary is created.
                Defaults to None.
            *pair_args: Positional ``keyN``/``valueN`` pairs for direct Python
                callers after the optional ``extra_metadata`` argument.
            **kwargs: Dynamic ``keyN``/``valueN`` pairs aligned with ``INPUT_TYPES``.

        Returns:
            tuple[dict[Any, Any]]: A tuple containing the updated metadata dictionary.
        """
        # Create a fresh dictionary so incoming metadata mappings are copied
        # rather than mutated in place.
        result: dict[Any, Any] = {}
        # Copy existing metadata if provided
        if extra_metadata is not None:
            if not isinstance(extra_metadata, Mapping):
                raise TypeError(
                    "CreateExtraMetaDataUniversal.extra_metadata must be a mapping, "
                    f"got {type(extra_metadata).__name__}"
                )
            result.update(extra_metadata)
        normalized_pairs = self._normalize_pair_arguments(pair_args, kwargs)
        pair_count = self._validated_pair_count()
        # Add key/value pairs only when the key is truthy and the value is neither None nor an empty string.
        for index in range(1, pair_count + 1):
            key = normalized_pairs.get(f"key{index}", "")
            value = normalized_pairs.get(f"value{index}", "")
            if key and value is not None and value != "":
                result[key] = value
        return (result,)
