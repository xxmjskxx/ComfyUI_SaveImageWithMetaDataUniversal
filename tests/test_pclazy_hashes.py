import importlib

import pytest


def test_pclazy_hashes_use_raw_names(monkeypatch):
    mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.PCLazyLoraLoader")

    # Ensure cache is clean
    mod._NODE_DATA_CACHE.clear()

    # Simulate parser returning raw identifiers and strength lists
    raw = ["rawA", "rawB"]
    ms = [0.7, 0.3]
    cs = [0.5, 0.2]

    monkeypatch.setattr(mod, "parse_lora_syntax", lambda text: (raw, ms, cs))
    # Return different display names to ensure we don't accidentally use them for hashing
    monkeypatch.setattr(mod, "resolve_lora_display_names", lambda names: [f"DISPLAY({n})" for n in names])

    seen = []

    def fake_hash(name, input_data):  # name must be from raw
        seen.append(name)
        return f"hash({name})"

    monkeypatch.setattr(mod, "calc_lora_hash", fake_hash)

    # Build minimal input_data shape expected by the selector
    input_data = [{"text": "ignored by patched parser"}]

    hashes = mod.get_lora_model_hashes(123, None, input_data)

    # Validate we called hashing with raw names, not display names
    assert seen == raw
    # Validate returned hashes match fake hashing of raw names
    assert hashes == ["hash(rawA)", "hash(rawB)"]


def test_pclazy_loader_reports_clip_strengths(monkeypatch):
    mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.PCLazyLoraLoader")
    mod._NODE_DATA_CACHE.clear()
    monkeypatch.setattr(mod, "resolve_lora_display_names", lambda names: names)
    monkeypatch.setattr(mod, "calc_lora_hash", lambda name, _input: f"hash::{name}")

    input_data = [{"text": "<lora:Foo:0.8:0.3> <lora:Bar:0.25>"}]
    model_strengths = mod.get_lora_strengths(1, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths(1, None, input_data)
    assert model_strengths == [0.8, 0.25]
    assert clip_strengths == [0.3, 0.25]
