import os
import json
import sys
import types
from pathlib import Path

import importlib

# Add package parent path
PKG_PARENT = os.path.dirname(os.path.dirname(__file__))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

# Imports from package
Capture = importlib.import_module("saveimage_unimeta.capture").Capture
nodes_mod = importlib.import_module("saveimage_unimeta.nodes.node")
SaveNode = nodes_mod.SaveImageWithMetaDataUniversal
MetaField = importlib.import_module("saveimage_unimeta.defs.meta").MetaField


class DummyImage:
    """Minimal image-like object to satisfy save_images expectations (numpy array)."""

    def __init__(self, w=8, h=8):
        import numpy as np

        self._arr = (np.random.rand(h, w, 3)).astype("float32")

    def cpu(self):
        return self

    def numpy(self):
        return self._arr


def build_minimal_prompt_graph():
    # Provide bare minimum for Trace.trace usage: current_save_image_node_id referenced internally.
    return {}


def test_guidance_as_cfg_parameter_line(monkeypatch, tmp_path):
    # Arrange: craft pnginfo dict with Guidance and CFG scale
    pnginfo = {
        "Seed": 123,
        "Steps": 20,
        "Guidance": 7.5,
        "CFG scale": 12.0,  # Raw CFG scale that should be overridden when guidance_as_cfg=True
        "Model": "model.safetensors",
        "Model hash": "abcdef1234",
    }
    # Generate parameters with guidance_as_cfg=True
    params_guidance = Capture.gen_parameters_str(pnginfo, include_lora_summary=False, guidance_as_cfg=True)
    assert "CFG scale: 7.5" in params_guidance
    assert "Guidance:" not in params_guidance
    # With guidance_as_cfg=False original CFG scale should remain and Guidance shown
    params_no_guidance = Capture.gen_parameters_str(pnginfo, include_lora_summary=False, guidance_as_cfg=False)
    assert "CFG scale: 12" in params_no_guidance or "CFG scale: 12.0" in params_no_guidance
    assert "Guidance: 7.5" in params_no_guidance


def test_jpeg_exif_fallback_stages(monkeypatch, tmp_path):
    # Force very low EXIF size limit to trigger staged fallbacks
    monkeypatch.setenv("METADATA_JPEG_EXIF_SEGMENT_LIMIT", "6000")  # small but > header
    # Reduce hard max so user limit remains effective
    monkeypatch.setenv("METADATA_JPEG_EXIF_HARD_MAX_KB", "32")

    node = SaveNode()

    # Patch output directory
    node.output_dir = str(tmp_path)

    # Build artificially large parameters by injecting many keys in pnginfo
    big_pnginfo = {
        "Positive prompt": "a" * 2000,
        "Negative prompt": "b" * 2000,
    }
    for i in range(120):
        big_pnginfo[f"ExtraKey{i}"] = "x" * 50

    # Monkeypatch gen_pnginfo to return our large dict
    def fake_gen_pnginfo(method, node_id, civitai):
        return big_pnginfo

    monkeypatch.setattr(SaveNode, "gen_pnginfo", classmethod(lambda cls, a, b, c: fake_gen_pnginfo(a, b, c)))

    # Prepare dummy image batch
    images = [DummyImage()]

    # Case 1: Start with tiny limit (max_jpeg_exif_kb=4) to force fallback quickly
    result = node.save_images(
        images,
        file_format="jpeg",
        max_jpeg_exif_kb=4,
        civitai_sampler=False,
        include_lora_summary=False,
    )
    # Ensure we recorded one fallback stage
    assert len(node._last_fallback_stages) == 1
    stage = node._last_fallback_stages[0]
    assert stage in {"reduced-exif", "minimal", "com-marker"}

    # Inspect file parameters presence (COM marker path) if com-marker stage selected
    saved = result["ui"]["images"][0]["filename"]
    img_path = Path(node.output_dir) / saved
    assert img_path.exists()

    # Case 2: Raise limit to something larger to attempt earlier stage capture
    node._last_fallback_stages.clear()
    node.save_images(
        images,
        file_format="jpeg",
        max_jpeg_exif_kb=32,
        civitai_sampler=False,
        include_lora_summary=False,
    )
    assert len(node._last_fallback_stages) == 1
    # Stage may be 'none' if EXIF fits
    stage2 = node._last_fallback_stages[0]
    assert stage2 in {"none", "reduced-exif", "minimal", "com-marker"}
