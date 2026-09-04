"""Integration tests for the `sanitize_metadata` toggle on the save node.

These exercise ``SaveImageWithMetaDataUniversal.save_images`` end-to-end for the
PNG path, verifying that the toggle controls whether embedded workflow JSON is
redacted and that sanitization failures never prevent a save.
"""

from __future__ import annotations

import json
import os

import numpy as np
from PIL import Image

try:
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal
except ModuleNotFoundError:  # pragma: no cover
    from saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal

import folder_paths as real_folder_paths

from saveimage_unimeta.utils import redaction


def _make_image() -> np.ndarray:
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


def _save_png(tmp_path, monkeypatch, **kwargs) -> str:
    node = SaveImageWithMetaDataUniversal()
    node.output_dir = str(tmp_path)
    monkeypatch.setattr(
        real_folder_paths,
        "get_save_image_path",
        lambda prefix, outdir, w, h: (node.output_dir, "test", 0, ""),
    )
    node.save_images(images=_make_image(), file_format="png", **kwargs)
    pngs = [f for f in os.listdir(node.output_dir) if f.lower().endswith(".png")]
    assert pngs, "No PNG saved"
    return os.path.join(node.output_dir, pngs[0])


def _embedded_prompt(img_path: str) -> dict:
    with Image.open(img_path) as im:
        return json.loads(im.text["prompt"])


SECRET_PROMPT = {
    "1": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "a cat", "token": "sk-live-secret-123", "api_key": "sk-api-456"},
    }
}


def test_sanitize_metadata_redacts_embedded_prompt(tmp_path, monkeypatch) -> None:
    img_path = _save_png(tmp_path, monkeypatch, prompt=SECRET_PROMPT, sanitize_metadata=True)
    embedded = _embedded_prompt(img_path)
    assert embedded["1"]["inputs"]["token"] == redaction.REDACTED_SECRET
    assert embedded["1"]["inputs"]["api_key"] == redaction.REDACTED_SECRET
    assert "sk-live-secret-123" not in json.dumps(embedded)


def test_sanitize_metadata_disabled_keeps_raw_prompt(tmp_path, monkeypatch) -> None:
    img_path = _save_png(tmp_path, monkeypatch, prompt=SECRET_PROMPT, sanitize_metadata=False)
    embedded = _embedded_prompt(img_path)
    assert embedded["1"]["inputs"]["token"] == "sk-live-secret-123"


def test_sanitize_metadata_error_falls_back_to_raw(tmp_path, monkeypatch) -> None:
    import sys

    # Patch the module that actually defines the node class (the package may be
    # importable under both "ComfyUI_SaveImageWithMetaDataUniversal" and plain
    # "saveimage_unimeta", which resolve to distinct module trees).
    save_image_mod = sys.modules[SaveImageWithMetaDataUniversal.__module__]
    error_cls = save_image_mod.MetadataSanitizationError

    def _raise(*_args, **_kwargs):
        raise error_cls("test limit")

    monkeypatch.setattr(save_image_mod, "sanitize_metadata_json", _raise)
    img_path = _save_png(tmp_path, monkeypatch, prompt=SECRET_PROMPT, sanitize_metadata=True)
    embedded = _embedded_prompt(img_path)
    assert embedded["1"]["inputs"]["token"] == "sk-live-secret-123"
