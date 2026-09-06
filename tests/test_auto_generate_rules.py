"""Tests for auto-generating capture rules on first save (E)."""
import importlib

import pytest


def _mod(fullname, fallback):
    try:
        return importlib.import_module(fullname)
    except ModuleNotFoundError:  # pragma: no cover
        return importlib.import_module(fallback)


save_image_mod = _mod(
    "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image",
    "saveimage_unimeta.nodes.save_image",
)
scanner_mod = _mod(
    "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.scanner",
    "saveimage_unimeta.nodes.scanner",
)
rules_writer_mod = _mod(
    "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.rules_writer",
    "saveimage_unimeta.nodes.rules_writer",
)
defs_mod = _mod(
    "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs",
    "saveimage_unimeta.defs",
)


@pytest.fixture(autouse=True)
def _reset_flags():
    save_image_mod._AUTO_RULES_CHECKED = False
    save_image_mod._OVERWRITE_RULES_DONE = False
    yield
    save_image_mod._AUTO_RULES_CHECKED = False
    save_image_mod._OVERWRITE_RULES_DONE = False


def _stub_scan_save(monkeypatch):
    """Stub the scanner and writer nodes and return a call-count dict."""
    calls = {"scan": 0, "save": 0, "save_kwargs": None}

    def fake_scan(self):
        calls["scan"] += 1
        return ('{"nodes": {}}', "diff")

    def fake_save(self, rules_json, **kwargs):
        calls["save"] += 1
        calls["save_kwargs"] = kwargs
        return ("ok",)

    monkeypatch.setattr(scanner_mod.MetadataRuleScanner, "scan_for_rules", fake_scan)
    monkeypatch.setattr(rules_writer_mod.SaveCustomMetadataRules, "save_rules", fake_save)
    return calls


def test_auto_generate_runs_exactly_once_when_no_rules(monkeypatch):
    """With no rules, scan+save runs once, then the session flag suppresses it."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", None)
    save_image_mod._maybe_auto_generate_rules(False)
    save_image_mod._maybe_auto_generate_rules(False)
    assert calls["scan"] == 1
    assert calls["save"] == 1


def test_rules_present_never_runs(monkeypatch):
    """With rules present, scan+save never runs."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", "1.4.4")
    save_image_mod._maybe_auto_generate_rules(False)
    assert calls["scan"] == 0
    assert calls["save"] == 0


def test_outdated_rules_not_regenerated(monkeypatch):
    """Outdated-but-present rules are only warned about, never regenerated."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", "0.0.0")
    save_image_mod._maybe_auto_generate_rules(False)
    assert calls["scan"] == 0
    assert calls["save"] == 0


def test_overwrite_rules_runs_once_then_suppressed(monkeypatch):
    """overwrite_rules re-runs scan+save once, then the session flag suppresses it."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", "1.4.4")
    save_image_mod._maybe_auto_generate_rules(True)
    save_image_mod._maybe_auto_generate_rules(True)
    assert calls["scan"] == 1
    assert calls["save"] == 1


def test_overwrite_rules_uses_overwrite_and_backup(monkeypatch):
    """overwrite_rules saves with overwrite mode and a backup."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", "1.4.4")
    save_image_mod._maybe_auto_generate_rules(True)
    assert calls["save_kwargs"]["save_mode"] == "overwrite"
    assert calls["save_kwargs"]["backup_before_save"] is True


def test_overwrite_with_no_rules_runs_once(monkeypatch):
    """overwrite_rules with no rules still runs scan+save exactly once."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", None)
    save_image_mod._maybe_auto_generate_rules(True)
    save_image_mod._maybe_auto_generate_rules(True)
    assert calls["scan"] == 1
    assert calls["save"] == 1


def test_save_images_auto_generates_rules_once(monkeypatch, node_instance):
    """The save node triggers auto-generation once across multiple saves."""
    calls = _stub_scan_save(monkeypatch)
    monkeypatch.setattr(defs_mod, "LOADED_RULES_VERSION", None)
    node_instance.save_images(images=[], overwrite_rules=False)
    node_instance.save_images(images=[], overwrite_rules=False)
    assert calls["scan"] == 1
    assert calls["save"] == 1
