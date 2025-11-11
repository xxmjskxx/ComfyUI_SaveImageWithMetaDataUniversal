import importlib
from .fixtures_piexif import build_piexif_stub

def test_no_fallback_when_under_limit(monkeypatch, node_instance, dummy_image):
    node = node_instance

    # Monkeypatch piexif to return small EXIF always
    mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
    monkeypatch.setattr(mod, 'piexif', build_piexif_stub('small'))

    images = dummy_image
    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=64)
    assert node._last_fallback_stages, 'Stage list empty'
    assert node._last_fallback_stages[0] == 'none'
