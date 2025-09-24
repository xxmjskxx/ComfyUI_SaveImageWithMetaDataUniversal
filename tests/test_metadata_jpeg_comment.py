import os
import importlib
import numpy as np
from PIL import Image

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal
import folder_paths as real_folder_paths  # type: ignore


def make_dummy_image():
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


def test_jpeg_com_marker_contains_fallback(monkeypatch, tmp_path):
    node = SaveImageWithMetaDataUniversal()
    # Redirect output directory to tmp_path
    node.output_dir = str(tmp_path)

    # Monkeypatch output path generator so we know exact location
    monkeypatch.setattr(real_folder_paths, 'get_save_image_path', lambda prefix, outdir, w, h: (node.output_dir, 'test_img', 0, ''))

    # Monkeypatch piexif to always produce huge EXIF to force com-marker fallback
    try:  # Standard runtime import
        import piexif as real_piexif  # type: ignore
    except Exception:  # Access stubbed instance from module if real piexif unavailable
        mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
        real_piexif = getattr(mod, 'piexif')

    class PStub:
        ImageIFD = getattr(real_piexif, 'ImageIFD', type('ImageIFD', (), {'Model': 0x0110, 'Make': 0x010F}))
        ExifIFD = getattr(real_piexif, 'ExifIFD', type('ExifIFD', (), {'UserComment': 0x9286}))
        helper = getattr(real_piexif, 'helper', type('H', (), {'UserComment': type('UC', (), {'dump': staticmethod(lambda v, encoding="unicode": v.encode("utf-8") if isinstance(v, str) else b"" )})}) )

        @staticmethod
        def dump(d):
            return b'Z' * (128 * 1024)

        @staticmethod
        def insert(exif_bytes, path):
            return None

    mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
    monkeypatch.setattr(mod, 'piexif', PStub)

    images = make_dummy_image()
    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=4)

    # Find saved JPEG
    saved_files = [f for f in os.listdir(node.output_dir) if f.lower().endswith('.jpeg') or f.lower().endswith('.jpg')]
    assert saved_files, 'No JPEG saved'
    img_path = os.path.join(node.output_dir, saved_files[0])

    with Image.open(img_path) as im:
        # PIL stores comment in info.get('comment') for JPEG
        comment = im.info.get('comment', b'')
    assert b'Metadata Fallback: com-marker' in comment or b'Metadata Fallback: minimal' in comment or b'Metadata Fallback: reduced-exif' in comment, 'Fallback indicator missing from JPEG comment'
