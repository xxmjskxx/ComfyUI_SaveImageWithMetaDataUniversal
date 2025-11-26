"""Tests for version module.

This module tests:
- saveimage_unimeta/version.py

Tests cover:
- resolve_runtime_version function
- Version override via environment variable
- Fallback behavior
"""

from __future__ import annotations

from saveimage_unimeta.version import resolve_runtime_version, _read_pyproject_version


class TestResolveRuntimeVersion:
    """Tests for the resolve_runtime_version function."""

    def test_returns_string(self):
        """Should return a string."""
        result = resolve_runtime_version()
        assert isinstance(result, str)

    def test_returns_non_empty(self):
        """Should return non-empty string."""
        result = resolve_runtime_version()
        assert len(result) > 0

    def test_override_via_env_var(self, monkeypatch):
        """Should use METADATA_VERSION_OVERRIDE if set."""
        monkeypatch.setenv("METADATA_VERSION_OVERRIDE", "1.2.3-test")
        result = resolve_runtime_version()
        assert result == "1.2.3-test"

    def test_override_strips_whitespace(self, monkeypatch):
        """Should strip whitespace from override."""
        monkeypatch.setenv("METADATA_VERSION_OVERRIDE", "  1.0.0  ")
        result = resolve_runtime_version()
        assert result == "1.0.0"

    def test_empty_override_uses_resolved(self, monkeypatch):
        """Should use resolved version if override is empty."""
        monkeypatch.setenv("METADATA_VERSION_OVERRIDE", "")
        result = resolve_runtime_version()
        # Should not be empty string
        assert result != ""

    def test_whitespace_only_override_uses_resolved(self, monkeypatch):
        """Should use resolved version if override is whitespace."""
        monkeypatch.setenv("METADATA_VERSION_OVERRIDE", "   ")
        result = resolve_runtime_version()
        # Should not be whitespace
        assert result.strip() == result

    def test_no_override_returns_resolved(self, monkeypatch):
        """Should return resolved version without override."""
        monkeypatch.delenv("METADATA_VERSION_OVERRIDE", raising=False)
        result = resolve_runtime_version()
        assert result is not None
        assert len(result) > 0


class TestReadPyprojectVersion:
    """Tests for the _read_pyproject_version function."""

    def test_returns_version_or_none(self):
        """Should return a version string or None."""
        result = _read_pyproject_version()
        assert result is None or isinstance(result, str)

    def test_reads_from_pyproject(self):
        """Should read version from pyproject.toml if it exists."""
        result = _read_pyproject_version()
        # In this repo, pyproject.toml exists, so should get a version
        if result is not None:
            assert len(result) > 0
            # Version should look like a semver
            assert "." in result or result == "unknown"
