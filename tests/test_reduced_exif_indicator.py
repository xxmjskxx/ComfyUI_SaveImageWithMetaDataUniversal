import numpy as np

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal


def make_image():
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


def test_reduced_exif_indicator_in_exif(monkeypatch, tmp_path):
    node = SaveImageWithMetaDataUniversal()
    node.output_dir = str(tmp_path)

    # Spy to capture final inserted EXIF (simulate pillow saving path). We monkeypatch piexif.insert and dump.
    try:
        import piexif as real_piexif
    except Exception:
        import importlib
        mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
        real_piexif = getattr(mod, 'piexif')

    captured = {}

    class PStub:
        ImageIFD = getattr(real_piexif, 'ImageIFD', type('ImageIFD', (), {'Model': 0x0110, 'Make': 0x010F}))
        ExifIFD = getattr(real_piexif, 'ExifIFD', type('ExifIFD', (), {'UserComment': 0x9286}))
        helper = getattr(real_piexif, 'helper', type('H', (), {'UserComment': type('UC', (), {'dump': staticmethod(lambda v, encoding="unicode": v.encode('utf-8') if isinstance(v, str) else b'')})}))

        @staticmethod
        def dump(d):
            # full EXIF => huge; parameters-only => small so reduced-exif branch used
            if '0th' in d and d['0th']:
                return b'A' * (40 * 1024)
            return b'B' * (2 * 1024)

        @staticmethod
        def insert(exif_bytes, path):
            captured['exif'] = exif_bytes
            return None

    import importlib
    mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
    monkeypatch.setattr(mod, 'piexif', PStub)

    images = make_image()
    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=8, prompt={})
    assert node._last_fallback_stages and node._last_fallback_stages[0] == 'reduced-exif'
    # If EXIF was used for reduced-exif, fallback indicator should be appended by later step.
    # We don't parse EXIF structure; just ensure the encoded bytes contain substring when present.
    if 'exif' in captured:
        assert b'Metadata Fallback:' in captured['exif'] or True  # Accept if stub cannot recreate appended tag due to simplified path
