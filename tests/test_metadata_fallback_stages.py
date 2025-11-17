import types
import numpy as np
import importlib
import pytest
from .fixtures_piexif import build_piexif_stub


def make_dummy_image():
    # shape: batch=1, h=8, w=8, c=3  -> Comfy style list/array
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


def _reset_node_module():
    # Allow re-import if we monkeypatch piexif in different ways between tests
    import sys

    mod_name = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node"
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])
    else:
        import importlib as _il

        _il.import_module(mod_name)
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
    node_cls = getattr(mod, "SaveImageWithMetaDataUniversal")
    node = node_cls()

    long_params = "Sampler: test, Steps: 30, CFG scale: 7," + ", ".join([f"K{i}:{i}" for i in range(120)])
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture import Capture as RealCapture

    monkeypatch.setattr(RealCapture, "gen_parameters_str", staticmethod(lambda *_, **__: long_params))

    # Build stub per scenario leveraging shared factory semantics
    if scenario == "reduced-exif":
        # adaptive behaves like reduced-exif path with differential sizes
        monkeypatch.setattr(mod, "piexif", build_piexif_stub("adaptive"))
    elif scenario == "minimal":
        # Force minimal by making full EXIF large but parameters-only smaller than limit progression
        monkeypatch.setattr(mod, "piexif", build_piexif_stub("huge"))
    elif scenario == "com-marker":
        monkeypatch.setattr(mod, "piexif", build_piexif_stub("huge"))
    if scenario == "com-marker":
        monkeypatch.setattr(node, "_build_minimal_parameters", lambda p: p)

    images = make_dummy_image()
    # Use empty prompt to force zeroth_ifd population for reduced-exif scenario
    prompt = {} if scenario == "reduced-exif" else None
    node.save_images(images=images, file_format="jpeg", max_jpeg_exif_kb=limit_kb, prompt=prompt)
    assert node._last_fallback_stages, "No fallback recorded"
    assert node._last_fallback_stages[0] in expectations
