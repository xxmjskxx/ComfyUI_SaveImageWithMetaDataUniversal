"""Regression tests for user-rule directory resolution consistency.

The writer (``saveimage_unimeta/nodes/rules_writer.py``) persists user rule JSON
under ``<package>/user_rules/``. The loader and scanner must read from the same
directory — not the stale repository-root ``user_rules/`` location left over from
the old ``py/`` layout. These tests lock that contract in place and verify that
user JSON is loaded even when ``generated_user_rules.py`` is absent.
"""

import json
import os

import pytest


def _package_dir(defs_mod) -> str:
    """Return the package directory containing the loader module."""
    return os.path.dirname(os.path.dirname(os.path.abspath(defs_mod.__file__)))


def test_resolve_user_rules_dir_points_at_package(monkeypatch):
    """Loader must resolve the same ``<package>/user_rules`` dir the writer uses."""
    monkeypatch.delenv("METADATA_TEST_MODE", raising=False)

    import saveimage_unimeta.defs as defs_mod

    package_dir = _package_dir(defs_mod)
    resolved = defs_mod.resolve_user_rules_dir()

    assert resolved == os.path.join(package_dir, "user_rules")
    # It must not fall back to the stale repository-root location.
    repo_root = os.path.dirname(package_dir)
    assert resolved != os.path.join(repo_root, "user_rules")


def test_loads_user_json_without_generated_ext(monkeypatch, tmp_path):
    """User JSON must load even when generated_user_rules.py is absent."""
    monkeypatch.delenv("METADATA_TEST_MODE", raising=False)

    import saveimage_unimeta.defs as defs_mod
    from saveimage_unimeta.defs import CAPTURE_FIELD_LIST, SAMPLERS, load_user_definitions

    # Redirect the resolved user_rules dir to a temp dir with known content.
    monkeypatch.setattr(defs_mod, "resolve_user_rules_dir", lambda: str(tmp_path))
    (tmp_path / "user_captures.json").write_text(
        json.dumps({"UserOnly.Node": {"IMAGE_WIDTH": {"field_name": "width"}}}),
        encoding="utf-8",
    )
    (tmp_path / "user_samplers.json").write_text(
        json.dumps({"UserOnlySampler": {"positive": "positive", "negative": "negative"}}),
        encoding="utf-8",
    )

    # Hide generated_user_rules.py so only JSON is available.
    orig_glob = defs_mod.glob.glob

    def _patched_glob(pattern, *args, **kwargs):
        return [p for p in orig_glob(pattern, *args, **kwargs) if "generated_user_rules" not in p]

    monkeypatch.setattr(defs_mod.glob, "glob", _patched_glob)

    try:
        load_user_definitions(required_classes={"UserOnly.Node", "UserOnlySampler"})
        assert "UserOnly.Node" in CAPTURE_FIELD_LIST
        assert "UserOnlySampler" in SAMPLERS
    finally:
        defs_mod.load_extensions_only()
