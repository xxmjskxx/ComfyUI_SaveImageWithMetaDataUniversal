"""Tests for the WebP `method=6` encoder setting (M4 B3)."""
from PIL import Image

try:  # prefer installed-style path
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image import (
        SaveImageWithMetaDataUniversal,
    )
except ModuleNotFoundError:  # editable checkout fallback
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal


def test_webp_save_uses_method_6(monkeypatch, node_instance, dummy_image):
    """The WebP save passes method=6 for best compression."""
    captured = {}
    original_save = Image.Image.save

    def spy_save(self, fp, *args, **kwargs):
        captured["kwargs"] = kwargs
        return original_save(self, fp, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "save", spy_save)
    node_instance.save_images(images=dummy_image, file_format="webp", prompt=None, extra_pnginfo=None)
    assert captured.get("kwargs", {}).get("method") == 6
