import os
import importlib
import numpy as np
from PIL import Image
from .fixtures_piexif import build_piexif_stub

try:
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal  # type: ignore
import folder_paths as real_folder_paths  # type: ignore


def make_dummy_image():
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


def test_jpeg_com_marker_contains_fallback(monkeypatch, tmp_path):
    node = SaveImageWithMetaDataUniversal()
    # Redirect output directory to tmp_path
    node.output_dir = str(tmp_path)

    # Monkeypatch output path generator so we know exact location
    def _save_path(prefix, outdir, w, h):
        return (node.output_dir, 'test_img', 0, '')
    monkeypatch.setattr(real_folder_paths, 'get_save_image_path', _save_path)

    # Force huge EXIF dump to trigger fallback
    mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
    monkeypatch.setattr(mod, 'piexif', build_piexif_stub('huge'))

    images = make_dummy_image()
    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=4)

    # Find saved JPEG
    saved_files = [f for f in os.listdir(node.output_dir) if f.lower().endswith('.jpeg') or f.lower().endswith('.jpg')]
    assert saved_files, 'No JPEG saved'
    img_path = os.path.join(node.output_dir, saved_files[0])

    with Image.open(img_path) as im:
        # PIL stores comment in info.get('comment') for JPEG
        comment = im.info.get('comment', b'')
    fallback_markers = (
        b'Metadata Fallback: com-marker',
        b'Metadata Fallback: minimal',
        b'Metadata Fallback: reduced-exif',
    )
    assert any(m in comment for m in fallback_markers), 'Fallback indicator missing from JPEG comment'
