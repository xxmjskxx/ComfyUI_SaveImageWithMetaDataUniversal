"""Parametrized fallback scenarios exercising multiple fallback stages in one place.

Purposely broad but coarse so we avoid duplicating focused assertions elsewhere.
"""

from __future__ import annotations

import importlib
import numpy as np
import pytest

from .fixtures_piexif import build_piexif_stub


def _reset_node_module():
    import sys

    mod_name = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node"
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])
    else:  # pragma: no cover
        import importlib as _il

        _il.import_module(mod_name)
    return sys.modules[mod_name]


SCENARIOS = [
    ("huge", 64, 1, {"reduced-exif", "minimal", "com-marker"}),
    ("huge", 8, 1, {"minimal", "com-marker"}),
    ("huge", 4, 1, {"com-marker"}),
    ("huge", 8, 3, {"minimal", "com-marker"}),
    ("huge", 4, 3, {"com-marker"}),
    ("adaptive", 64, 2, {"none", "reduced-exif", "minimal", "com-marker"}),
    # Force adaptive into reduced-exif by lowering limit below full (40KB) but above parameters-only (~2KB)
    ("adaptive", 32, 2, {"reduced-exif"}),
]


@pytest.mark.parametrize("piexif_mode,max_kb,image_count,expected_final_choices", SCENARIOS)
def test_fallback_parametric(monkeypatch, piexif_mode, max_kb, image_count, expected_final_choices):
    mod = _reset_node_module()
    node_cls = getattr(mod, "SaveImageWithMetaDataUniversal")
    node = node_cls()

    long_params = "Sampler: test, Steps: 30, CFG scale: 7," + ", ".join([f"K{i}:{i}" for i in range(120)])
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture import Capture as RealCapture  # type: ignore

    monkeypatch.setattr(RealCapture, "gen_parameters_str", staticmethod(lambda *_, **__: long_params))
    monkeypatch.setattr(mod, "piexif", build_piexif_stub(piexif_mode))

    images = np.zeros((image_count, 8, 8, 3), dtype=np.float32)
    # Provide prompt only for adaptive scenarios with limit < 40KB to inflate initial EXIF for fallback
    prompt_obj = {} if (piexif_mode == "adaptive" and max_kb < 40) else None
    node.save_images(images=images, file_format="jpeg", max_jpeg_exif_kb=max_kb, prompt=prompt_obj)

    stages = node._last_fallback_stages
    assert len(stages) == image_count
    for st in stages:
        assert st in expected_final_choices
    if image_count > 1:
        order = {"full": 0, "reduced-exif": 1, "minimal": 2, "com-marker": 3, "none": 0}
        numeric = [order.get(s, 0) for s in stages]
        assert numeric == sorted(numeric)
