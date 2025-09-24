class CreateExtraMetaDataUniversal:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
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
        extra_metadata={},
        key1="",
        value1="",
        key2="",
        value2="",
        key3="",
        value3="",
        key4="",
        value4="",
    ):
        extra_metadata.update(
            {
                key1: value1,
                key2: value2,
                key3: value3,
                key4: value4,
            }
        )
        return (extra_metadata,)
