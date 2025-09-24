import types
import numpy as np
import importlib
import pytest


def make_dummy_image():
    # shape: batch=1, h=8, w=8, c=3  -> Comfy style list/array
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


def _reset_node_module():
    # Allow re-import if we monkeypatch piexif in different ways between tests
    import sys
    mod_name = 'ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node'
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])
    return sys.modules[mod_name]


@pytest.mark.parametrize(
    "scenario,limit_kb,expectations",
    [
        ("reduced-exif", 8, {"reduced-exif"}),
        ("minimal", 4, {"minimal", "com-marker"}),
        ("com-marker", 4, {"com-marker"}),
    ],
)
def test_fallback_parametrized(monkeypatch, scenario, limit_kb, expectations):
    mod = _reset_node_module()
    node_cls = getattr(mod, 'SaveImageWithMetaDataUniversal')
    node = node_cls()
    real_piexif = getattr(mod, 'piexif')

    long_params = 'Sampler: test, Steps: 30, CFG scale: 7,' + ', '.join([f'K{i}:{i}' for i in range(120)])
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture import Capture as RealCapture
    monkeypatch.setattr(RealCapture, 'gen_parameters_str', staticmethod(lambda *_, **__: long_params))

    class PStub(types.SimpleNamespace):
        ImageIFD = real_piexif.ImageIFD
        ExifIFD = real_piexif.ExifIFD
        helper = real_piexif.helper

        @staticmethod
        def dump(d):
            if scenario == 'reduced-exif':
                if '0th' in d and d['0th']:
                    return b'A' * (32 * 1024)
                return b'B' * (2 * 1024)
            if scenario == 'minimal':
                return b'A' * (40 * 1024)
            if scenario == 'com-marker':
                return b'Z' * (128 * 1024)
            return b'X' * 1024

        @staticmethod
        def insert(exif_bytes, path):
            return None

    monkeypatch.setattr(mod, 'piexif', PStub)
    if scenario == 'com-marker':
        monkeypatch.setattr(node, '_build_minimal_parameters', lambda p: p)

    images = make_dummy_image()
    # Use empty prompt to force zeroth_ifd population for reduced-exif scenario
    prompt = {} if scenario == 'reduced-exif' else None
    node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=limit_kb, prompt=prompt)
    assert node._last_fallback_stages, 'No fallback recorded'
    assert node._last_fallback_stages[0] in expectations
