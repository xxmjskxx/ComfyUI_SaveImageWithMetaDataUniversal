import numpy as np
import types
import importlib


def make_dummy_images():
    # Two images in batch
    return np.zeros((2, 8, 8, 3), dtype=np.float32)


def test_multi_image_mixed_fallback(monkeypatch):
    mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
    node_cls = getattr(mod, 'SaveImageWithMetaDataUniversal')
    node = node_cls()

    real_piexif = getattr(mod, 'piexif')

    class PStub(types.SimpleNamespace):
        ImageIFD = real_piexif.ImageIFD
        ExifIFD = real_piexif.ExifIFD
        helper = real_piexif.helper
        counter = 0

        @staticmethod
        def dump(d):
            # First image: simulate moderately large full EXIF but small parameters-only (reduced-exif)
            # Second image: always huge forcing com-marker
            if '0th' in d and d['0th']:
                # Full EXIF path
                size = 40 * 1024
            else:
                size = 2 * 1024
            # Use internal counter heuristic: second call (parameters-only fallback attempt for image 1?) size small; later calls large
            payload = b'A' * size
            return payload

        @staticmethod
        def insert(exif_bytes, path):
            return None

    monkeypatch.setattr(mod, 'piexif', PStub)

    images = make_dummy_images()
    # Low limit to force fallback for full EXIF; second image we force com-marker by monkeypatching _build_minimal_parameters to identity and huge size via another stub switch
    # Simplify: After first image processing, monkeypatch dump to always produce gigantic output so second image ends in com-marker.
    original_dump = PStub.dump
    def selective_dump(d):
        if len(node._last_fallback_stages) == 0:
            return original_dump(d)  # first image logic
        return b'Z' * (128 * 1024)  # subsequent attempts enormous
    monkeypatch.setattr(PStub, 'dump', staticmethod(selective_dump))
    monkeypatch.setattr(node, '_build_minimal_parameters', lambda p: p)

    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=4, prompt={})

    assert len(node._last_fallback_stages) == 2, 'Did not record two stages'
    assert node._last_fallback_stages[0] in {'reduced-exif', 'minimal', 'com-marker'}
    assert node._last_fallback_stages[1] in {'com-marker', 'minimal'}
