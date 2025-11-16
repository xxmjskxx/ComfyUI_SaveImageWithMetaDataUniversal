import importlib

import pytest


def _setup(save_image_module, monkeypatch):
    monkeypatch.setattr(save_image_module, "_RULES_VERSION_WARNING_EMITTED", False, raising=False)


def test_warns_when_rules_version_missing(monkeypatch, caplog):
    save_image = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image"
    )
    defs_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs")
    _setup(save_image, monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", None, raising=False)
    monkeypatch.setattr(save_image, "resolve_runtime_version", lambda: "9.9.9", raising=False)
    with caplog.at_level("WARNING"):
        save_image._maybe_warn_outdated_rules()
    message = " ".join(record.getMessage() for record in caplog.records)
    assert "missing a version stamp" in message
    assert "example_workflows/refresh-rules.json" in message
    caplog.clear()
    save_image._maybe_warn_outdated_rules()
    assert not caplog.records


def test_warns_when_rules_version_mismatch(monkeypatch, caplog):
    save_image = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image"
    )
    defs_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs")
    _setup(save_image, monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", "0.1.0", raising=False)
    monkeypatch.setattr(save_image, "resolve_runtime_version", lambda: "0.2.0", raising=False)
    with caplog.at_level("WARNING"):
        save_image._maybe_warn_outdated_rules()
    message = " ".join(record.getMessage() for record in caplog.records)
    assert "rules=0.1.0" in message
    assert "package=0.2.0" in message


def test_no_warning_when_rules_version_matches(monkeypatch, caplog):
    save_image = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image"
    )
    defs_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs")
    _setup(save_image, monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", "1.0.0", raising=False)
    monkeypatch.setattr(save_image, "resolve_runtime_version", lambda: "1.0.0", raising=False)
    with caplog.at_level("WARNING"):
        save_image._maybe_warn_outdated_rules()
    assert not caplog.records
