import os
import sys
from pathlib import Path
import importlib
import re
import json

PKG_PARENT = os.path.dirname(os.path.dirname(__file__))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

nodes_mod = importlib.import_module("saveimage_unimeta.nodes.node")
SaveNode = nodes_mod.SaveImageWithMetaDataUniversal

class DummyImage:
    def __init__(self, w=8, h=8):
        import numpy as np
        self._arr = (np.random.rand(h, w, 3)).astype("float32")
    def cpu(self):
        return self
    def numpy(self):
        return self._arr


def _large_metadata_dict():
    d = {"Positive prompt": "x" * 1500, "Negative prompt": "y" * 1500}
    for i in range(80):
        d[f"Key{i}"] = "z" * 40
    return d


def test_batch_multiple_images_fallback_tracking(monkeypatch, tmp_path):
    monkeypatch.setenv("METADATA_JPEG_EXIF_SEGMENT_LIMIT", "6000")
    node = SaveNode()
    node.output_dir = str(tmp_path)

    def fake_gen(method, node_id, civitai):
        return _large_metadata_dict()
    monkeypatch.setattr(SaveNode, "gen_pnginfo", classmethod(lambda cls, a, b, c: fake_gen(a, b, c)))

    images = [DummyImage() for _ in range(3)]
    node.save_images(images, file_format="jpeg", max_jpeg_exif_kb=4, include_lora_summary=False)
    assert len(node._last_fallback_stages) == 3
    assert all(stage in {"reduced-exif", "minimal", "com-marker"} for stage in node._last_fallback_stages)


def test_no_duplicate_metadata_fallback_marker(monkeypatch, tmp_path):
    monkeypatch.setenv("METADATA_JPEG_EXIF_SEGMENT_LIMIT", "6000")
    node = SaveNode()
    node.output_dir = str(tmp_path)

    # Force path where COM marker is written
    def fake_gen(method, node_id, civitai):
        return _large_metadata_dict()
    monkeypatch.setattr(SaveNode, "gen_pnginfo", classmethod(lambda cls, a, b, c: fake_gen(a, b, c)))

    img = DummyImage()
    result = node.save_images([img], file_format="jpeg", max_jpeg_exif_kb=4, include_lora_summary=False)
    saved = result["ui"]["images"][0]["filename"]
    path = Path(node.output_dir) / saved
    # Read raw bytes and look for multiple occurrences of the marker phrase in UTF-8 decode best-effort
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8", "ignore")
    except Exception:
        text = ""
    occurrences = text.count("Metadata Fallback:")
    assert occurrences <= 1

