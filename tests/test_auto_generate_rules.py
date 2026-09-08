"""Tests for auto-generating capture rules with the rules_mode selector (E)."""
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


def _stub_scan_save(monkeypatch, scan_json='{"nodes": {"SomeNode": {"SomeField": {"field_name": "x"}}}}'):
    """Stub the scanner and writer nodes and return a call-count dict."""
    calls = {"scan": 0, "save": 0, "save_kwargs": None}

    def fake_scan(self):
        calls["scan"] += 1
        return (scan_json, "diff")

    def fake_save(self, rules_json, **kwargs):
        calls["save"] += 1
        calls["save_kwargs"] = kwargs
        return ("ok",)

    monkeypatch.setattr(scanner_mod.MetadataRuleScanner, "scan_for_rules", fake_scan)
    monkeypatch.setattr(rules_writer_mod.SaveCustomMetadataRules, "save_rules", fake_save)
    return calls


def _set_rules(monkeypatch, version):
    """Stub the disk-based rules-version read and the runtime version."""
    monkeypatch.setattr(save_image_mod, "_read_rules_version", lambda: version)
    monkeypatch.setattr(save_image_mod, "resolve_runtime_version", lambda: "1.4.4")


def test_off_mode_never_runs(monkeypatch):
    """Off mode never scans or saves, even with no rules."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, None)
    save_image_mod._maybe_auto_generate_rules("Off")
    save_image_mod._maybe_auto_generate_rules("Off")
    assert calls["scan"] == 0
    assert calls["save"] == 0


def test_unknown_mode_is_ignored(monkeypatch):
    """An unknown rules_mode value is rejected instead of being treated as Auto."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, None)
    save_image_mod._maybe_auto_generate_rules("Garbage")
    assert calls["scan"] == 0
    assert calls["save"] == 0


def test_auto_no_rules_generates_once(monkeypatch):
    """Auto with no rules generates once (overwrite), then the flag suppresses it."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, None)
    save_image_mod._maybe_auto_generate_rules("Auto")
    save_image_mod._maybe_auto_generate_rules("Auto")
    assert calls["scan"] == 1
    assert calls["save"] == 1
    assert calls["save_kwargs"]["save_mode"] == "overwrite"


def test_auto_current_rules_noop(monkeypatch):
    """Auto with current rules does nothing."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, "1.4.4")
    save_image_mod._maybe_auto_generate_rules("Auto")
    assert calls["scan"] == 0
    assert calls["save"] == 0


def test_auto_outdated_rules_appends_once(monkeypatch):
    """Auto with outdated rules appends new rules once (preserving existing)."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, "1.4.3")
    save_image_mod._maybe_auto_generate_rules("Auto")
    save_image_mod._maybe_auto_generate_rules("Auto")
    assert calls["scan"] == 1
    assert calls["save"] == 1
    assert calls["save_kwargs"]["save_mode"] == "append_new"


def test_overwrite_runs_once_then_suppressed(monkeypatch):
    """Overwrite regenerates once per session, with overwrite mode and a backup."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, "1.4.4")
    save_image_mod._maybe_auto_generate_rules("Overwrite")
    save_image_mod._maybe_auto_generate_rules("Overwrite")
    assert calls["scan"] == 1
    assert calls["save"] == 1
    assert calls["save_kwargs"]["save_mode"] == "overwrite"
    assert calls["save_kwargs"]["backup_before_save"] is True


def test_save_images_auto_generates_rules_once(monkeypatch, node_instance):
    """The save node triggers auto-generation once across multiple saves."""
    calls = _stub_scan_save(monkeypatch)
    _set_rules(monkeypatch, None)
    node_instance.save_images(images=[], rules_mode="Auto")
    node_instance.save_images(images=[], rules_mode="Auto")
    assert calls["scan"] == 1
    assert calls["save"] == 1


def test_empty_scan_skips_save_rules(monkeypatch):
    """An empty scan (nothing new) never calls save_rules and is checked once."""
    calls = _stub_scan_save(monkeypatch, scan_json='{"nodes": {}, "samplers": {}}')
    _set_rules(monkeypatch, None)
    save_image_mod._maybe_auto_generate_rules("Auto")
    save_image_mod._maybe_auto_generate_rules("Auto")
    assert calls["scan"] == 1
    assert calls["save"] == 0


def test_empty_scan_overwrite_is_suppressed(monkeypatch):
    """An empty scan under Overwrite is also suppressed after the first try."""
    calls = _stub_scan_save(monkeypatch, scan_json='{"nodes": {}, "samplers": {}}')
    _set_rules(monkeypatch, "1.4.4")
    save_image_mod._maybe_auto_generate_rules("Overwrite")
    save_image_mod._maybe_auto_generate_rules("Overwrite")
    assert calls["scan"] == 1
    assert calls["save"] == 0


def test_missing_scan_result_marks_checked(monkeypatch):
    """A falsy scan result sets the checked flag so it does not re-scan forever."""
    calls = _stub_scan_save(monkeypatch, scan_json="")
    _set_rules(monkeypatch, None)
    save_image_mod._maybe_auto_generate_rules("Auto")
    save_image_mod._maybe_auto_generate_rules("Auto")
    assert calls["scan"] == 1
    assert calls["save"] == 0


def test_read_rules_version_finds_version_beyond_4096(monkeypatch, tmp_path):
    """_read_rules_version reads the whole file, not just the first 4096 bytes."""
    ext_dir = tmp_path / "ext"
    ext_dir.mkdir()
    gen = ext_dir / "generated_user_rules.py"
    gen.write_text(("x" * 5000) + "\n" + 'RULES_VERSION = "1.4.4"\n', encoding="utf-8")
    monkeypatch.setattr(defs_mod, "__file__", str(tmp_path / "__init__.py"))
    assert save_image_mod._read_rules_version() == "1.4.4"


def test_read_rules_version_returns_none_when_absent(monkeypatch, tmp_path):
    ext_dir = tmp_path / "ext"
    ext_dir.mkdir()
    (ext_dir / "generated_user_rules.py").write_text("# no version here\n", encoding="utf-8")
    monkeypatch.setattr(defs_mod, "__file__", str(tmp_path / "__init__.py"))
    assert save_image_mod._read_rules_version() is None


def test_read_rules_version_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(defs_mod, "__file__", str(tmp_path / "__init__.py"))
    assert save_image_mod._read_rules_version() is None
