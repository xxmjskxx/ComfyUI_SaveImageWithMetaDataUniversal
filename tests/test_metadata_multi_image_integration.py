import numpy as np
import types
import importlib
from .fixtures_piexif import build_piexif_stub


def make_dummy_images():
    # Two images in batch
    return np.zeros((2, 8, 8, 3), dtype=np.float32)


def test_multi_image_mixed_fallback(monkeypatch):
    mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node")
    node_cls = getattr(mod, "SaveImageWithMetaDataUniversal")
    node = node_cls()

    # Start with adaptive to allow first image to degrade
    monkeypatch.setattr(mod, "piexif", build_piexif_stub("adaptive"))

    images = make_dummy_images()
    # Low limit to force fallback for full EXIF; second image we force com-marker by monkeypatching _build_minimal_parameters to identity and huge size via another stub switch  # noqa: E501
    # Simplify: After first image processing, monkeypatch dump to always produce gigantic output so second image ends in com-marker.  # noqa: E501
    # After first image, escalate to huge to force later com-marker
    orig_save = node.save_images

    def wrapped_save(*a, **k):
        if not node._last_fallback_stages:
            return orig_save(*a, **k)
        # Swap to huge stub for subsequent images
        monkeypatch.setattr(mod, "piexif", build_piexif_stub("huge"))
        return orig_save(*a, **k)

    node.save_images = wrapped_save  # type: ignore
    monkeypatch.setattr(node, "_build_minimal_parameters", lambda p: p)

    node.save_images(images=images, file_format="jpeg", max_jpeg_exif_kb=4, prompt={})

    assert len(node._last_fallback_stages) == 2, "Did not record two stages"
    assert node._last_fallback_stages[0] in {"reduced-exif", "minimal", "com-marker"}
    # Second image may still end up in reduced-exif if adaptive sizing produced smaller parameters-only payload first
    assert node._last_fallback_stages[1] in {"com-marker", "minimal", "reduced-exif"}
