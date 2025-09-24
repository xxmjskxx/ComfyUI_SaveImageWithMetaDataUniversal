import importlib

def test_no_fallback_when_under_limit(monkeypatch, node_instance, dummy_image):
    node = node_instance

    # Monkeypatch piexif to return small EXIF always
    try:
        import piexif as real_piexif
    except Exception:
        import importlib
        mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
        real_piexif = getattr(mod, 'piexif')

    class PStub:
        ImageIFD = getattr(real_piexif, 'ImageIFD', type('ImageIFD', (), {'Model': 0x0110, 'Make': 0x010F}))
        ExifIFD = getattr(real_piexif, 'ExifIFD', type('ExifIFD', (), {'UserComment': 0x9286}))
        _UserComment = type(
            'UC',
            (),
            {
                'dump': staticmethod(
                    lambda v, encoding="unicode": v.encode('utf-8') if isinstance(v, str) else b''
                )
            },
        )
        helper = getattr(real_piexif, 'helper', type('H', (), {'UserComment': _UserComment}))
        @staticmethod
        def dump(d):
            return b'SMALL'
        @staticmethod
        def insert(exif_bytes, path):
            return None

    import importlib
    mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
    monkeypatch.setattr(mod, 'piexif', PStub)

    images = dummy_image
    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=64)
    assert node._last_fallback_stages, 'Stage list empty'
    assert node._last_fallback_stages[0] == 'none'
