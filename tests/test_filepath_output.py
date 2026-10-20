"""Tests for the `filepath` STRING output (M4 B1)."""
import os

try:  # prefer installed-style path
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image import (
        SaveImageWithMetaDataUniversal,
    )
except ModuleNotFoundError:  # editable checkout fallback
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal


def test_return_types_expose_filepath():
    """The node declares an IMAGE + STRING output named images/filepath."""
    assert SaveImageWithMetaDataUniversal.RETURN_TYPES == ("IMAGE", "STRING")
    assert SaveImageWithMetaDataUniversal.RETURN_NAMES == ("images", "filepath")


def test_save_images_returns_filepath(node_instance, dummy_image):
    """save_images returns (images, filepath) with a real path for the last image."""
    result = node_instance.save_images(images=dummy_image, file_format="png")
    assert isinstance(result, dict)
    assert isinstance(result["result"], tuple)
    assert len(result["result"]) == 2
    _images_out, filepath = result["result"]
    assert isinstance(filepath, str) and filepath
    assert os.path.exists(filepath)
    assert filepath.lower().endswith(".png")
    # The returned path matches the saved UI entry's filename.
    ui_entry = result["ui"]["images"][-1]
    assert os.path.basename(filepath) == ui_entry["filename"]
