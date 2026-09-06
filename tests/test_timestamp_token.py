"""Tests for the `%timestamp%` filename token (M4 B2)."""
import time

try:  # prefer installed-style path
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image import (
        SaveImageWithMetaDataUniversal,
    )
except ModuleNotFoundError:  # editable checkout fallback
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal


def test_timestamp_token_resolves_to_unix_epoch(monkeypatch):
    """`%timestamp%` resolves to the integer Unix epoch."""
    monkeypatch.setattr(time, "time", lambda: 1757150000)
    out = SaveImageWithMetaDataUniversal.format_filename("img_%timestamp%", {})
    assert out == "img_1757150000"


def test_timestamp_token_truncation(monkeypatch):
    """`%timestamp:N%` truncates like the other tokens."""
    monkeypatch.setattr(time, "time", lambda: 1757150000)
    out = SaveImageWithMetaDataUniversal.format_filename("img_%timestamp:8%", {})
    assert out == "img_17571500"
