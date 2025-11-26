"""Tests for utils/pathresolve.py artifact resolution and hashing utilities."""

import os
import tempfile

import pytest

import folder_paths

from saveimage_unimeta.utils.pathresolve import (
    EXTENSION_ORDER,
    SUPPORTED_MODEL_EXTENSIONS,
    ResolutionResult,
    _LAST_PROBE_CANDIDATES,
    _probe_folder,
    has_supported_extension,
    load_or_calc_hash,
    sanitize_candidate,
    try_resolve_artifact,
)


# --- sanitize_candidate tests ---


class TestSanitizeCandidate:
    """Tests for the sanitize_candidate function."""

    def test_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert sanitize_candidate("  test  ") == "test"

    def test_removes_single_quotes(self):
        """Should remove symmetric single quotes."""
        assert sanitize_candidate("'quoted'") == "quoted"

    def test_removes_double_quotes(self):
        """Should remove symmetric double quotes."""
        assert sanitize_candidate('"quoted"') == "quoted"

    def test_trims_trailing_dots(self):
        """Should trim trailing dots when enabled."""
        assert sanitize_candidate("test..") == "test"
        assert sanitize_candidate("test.") == "test"

    def test_trims_trailing_spaces(self):
        """Should trim trailing spaces when enabled."""
        assert sanitize_candidate("test   ", trim_trailing_punct=True) == "test"

    def test_no_trailing_trim_when_disabled(self):
        """Should preserve trailing punct when disabled."""
        assert sanitize_candidate("test.", trim_trailing_punct=False) == "test."

    def test_preserves_internal_dots(self):
        """Should preserve internal dots."""
        assert sanitize_candidate("test.model.safetensors") == "test.model.safetensors"

    def test_handles_non_string_input(self):
        """Should convert non-string to string."""
        assert sanitize_candidate(123) == "123"

    def test_handles_empty_after_trim(self):
        """Should handle edge case of empty string after trimming."""
        assert sanitize_candidate("...") == ""
        assert sanitize_candidate("   ") == ""


# --- has_supported_extension tests ---


class TestHasSupportedExtension:
    """Tests for the has_supported_extension function."""

    def test_safetensors_supported(self):
        """Should recognize .safetensors extension."""
        assert has_supported_extension("model.safetensors") is True

    def test_ckpt_supported(self):
        """Should recognize .ckpt extension."""
        assert has_supported_extension("model.ckpt") is True

    def test_pt_supported(self):
        """Should recognize .pt extension."""
        assert has_supported_extension("model.pt") is True

    def test_bin_supported(self):
        """Should recognize .bin extension."""
        assert has_supported_extension("model.bin") is True

    def test_st_supported(self):
        """Should recognize .st extension."""
        assert has_supported_extension("model.st") is True

    def test_case_insensitive(self):
        """Should be case insensitive."""
        assert has_supported_extension("model.SAFETENSORS") is True
        assert has_supported_extension("model.Ckpt") is True

    def test_unsupported_extension(self):
        """Should return False for unsupported extensions."""
        assert has_supported_extension("model.txt") is False
        assert has_supported_extension("model.json") is False

    def test_no_extension(self):
        """Should return False for no extension."""
        assert has_supported_extension("model") is False


# --- EXTENSION_ORDER constants tests ---


class TestExtensionConstants:
    """Tests for extension-related constants."""

    def test_extension_order_contains_safetensors(self):
        """EXTENSION_ORDER should contain .safetensors."""
        assert ".safetensors" in EXTENSION_ORDER

    def test_extension_order_equals_supported(self):
        """EXTENSION_ORDER should equal SUPPORTED_MODEL_EXTENSIONS."""
        assert EXTENSION_ORDER == SUPPORTED_MODEL_EXTENSIONS

    def test_safetensors_is_first(self):
        """Safetensors should have highest priority."""
        assert EXTENSION_ORDER[0] == ".safetensors"


# --- ResolutionResult tests ---


class TestResolutionResult:
    """Tests for the ResolutionResult dataclass."""

    def test_creation(self):
        """Should create ResolutionResult with attributes."""
        result = ResolutionResult(display_name="test", full_path="/path/to/file")
        assert result.display_name == "test"
        assert result.full_path == "/path/to/file"

    def test_none_full_path(self):
        """Should allow None for full_path."""
        result = ResolutionResult(display_name="test", full_path=None)
        assert result.full_path is None


# --- _probe_folder tests ---


class TestProbeFolder:
    """Tests for the _probe_folder function."""

    def test_clears_and_populates_last_probe_candidates(self, monkeypatch):
        """Should track probe candidates for debugging."""
        monkeypatch.setattr(folder_paths, "get_full_path", lambda kind, name: None)

        _probe_folder("checkpoints", "model.safetensors")

        assert "model.safetensors" in _LAST_PROBE_CANDIDATES

    def test_returns_none_when_not_found(self, monkeypatch):
        """Should return None when file not found."""
        monkeypatch.setattr(folder_paths, "get_full_path", lambda kind, name: None)

        result = _probe_folder("checkpoints", "nonexistent.safetensors")
        assert result is None

    def test_returns_path_when_found(self, monkeypatch, tmp_path):
        """Should return path when file exists."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_text("dummy")

        def mock_get_full_path(kind, name):
            if name == "model.safetensors":
                return str(test_file)
            return None

        monkeypatch.setattr(folder_paths, "get_full_path", mock_get_full_path)
        monkeypatch.setattr(os.path, "exists", lambda p: p == str(test_file))

        result = _probe_folder("checkpoints", "model.safetensors")
        assert result == str(test_file)


# --- try_resolve_artifact tests ---


class TestTryResolveArtifact:
    """Tests for the try_resolve_artifact function."""

    def test_resolves_string_directly(self, monkeypatch, tmp_path):
        """Should resolve a direct string path."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_text("dummy")

        def mock_get_full_path(kind, name):
            if "model" in name:
                return str(test_file)
            return None

        monkeypatch.setattr(folder_paths, "get_full_path", mock_get_full_path)

        result = try_resolve_artifact("checkpoints", "model.safetensors")
        assert result.display_name == "model.safetensors"

    def test_resolves_from_list(self, monkeypatch, tmp_path):
        """Should resolve from a list container."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_text("dummy")

        def mock_get_full_path(kind, name):
            if "model" in name:
                return str(test_file)
            return None

        monkeypatch.setattr(folder_paths, "get_full_path", mock_get_full_path)

        result = try_resolve_artifact("checkpoints", ["model.safetensors", "other"])
        assert "model" in result.display_name

    def test_resolves_from_dict(self, monkeypatch, tmp_path):
        """Should resolve from a dict container."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_text("dummy")

        def mock_get_full_path(kind, name):
            if "model" in name:
                return str(test_file)
            return None

        monkeypatch.setattr(folder_paths, "get_full_path", mock_get_full_path)

        result = try_resolve_artifact("checkpoints", {"ckpt_name": "model.safetensors"})
        assert result.display_name == "model.safetensors"

    def test_respects_max_depth(self, monkeypatch):
        """Should stop recursion at max_depth."""
        monkeypatch.setattr(folder_paths, "get_full_path", lambda kind, name: None)

        # Deeply nested structure
        nested = [[[[["deep"]]]]]
        result = try_resolve_artifact("checkpoints", nested, max_depth=2)
        # Should still return something, just not resolve deeply
        assert result.full_path is None

    def test_uses_post_resolvers(self, monkeypatch, tmp_path):
        """Should try post_resolvers when primary resolution fails."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_text("dummy")

        monkeypatch.setattr(folder_paths, "get_full_path", lambda kind, name: None)

        def custom_resolver(name):
            return str(test_file)

        result = try_resolve_artifact(
            "checkpoints", "model", post_resolvers=[custom_resolver]
        )
        assert result.full_path == str(test_file)

    def test_returns_none_path_when_unresolved(self, monkeypatch):
        """Should return None for full_path when unresolved."""
        monkeypatch.setattr(folder_paths, "get_full_path", lambda kind, name: None)

        result = try_resolve_artifact("checkpoints", "nonexistent")
        assert result.full_path is None
        assert result.display_name == "nonexistent"


# --- load_or_calc_hash tests ---


class TestLoadOrCalcHash:
    """Tests for the load_or_calc_hash function."""

    def test_returns_none_for_nonexistent_file(self):
        """Should return None for nonexistent file."""
        result = load_or_calc_hash("/nonexistent/path/file.safetensors")
        assert result is None

    def test_returns_none_for_empty_filepath(self):
        """Should return None for empty filepath."""
        assert load_or_calc_hash("") is None
        assert load_or_calc_hash(None) is None

    def test_calculates_hash_for_existing_file(self, tmp_path):
        """Should calculate hash for existing file."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")

        result = load_or_calc_hash(str(test_file))

        assert result is not None
        assert len(result) == 10  # Default truncation

    def test_truncate_none_returns_full_hash(self, tmp_path):
        """Should return full hash when truncate=None."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")

        result = load_or_calc_hash(str(test_file), truncate=None)

        assert result is not None
        assert len(result) == 64  # Full SHA256 hash

    def test_reads_from_sidecar_when_exists(self, tmp_path):
        """Should read hash from sidecar file when it exists."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")
        sidecar = tmp_path / "model.sha256"
        valid_hash = "a" * 64  # Valid 64-char hex
        sidecar.write_text(valid_hash)

        result = load_or_calc_hash(str(test_file), truncate=None)

        assert result == valid_hash.lower()

    def test_ignores_invalid_sidecar(self, tmp_path):
        """Should ignore sidecar with invalid content."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")
        sidecar = tmp_path / "model.sha256"
        sidecar.write_text("invalid hash")  # Not 64-char hex

        result = load_or_calc_hash(str(test_file))

        # Should compute actual hash, not use invalid sidecar
        assert result is not None

    def test_creates_sidecar_after_computing(self, tmp_path):
        """Should create sidecar file after computing hash."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")
        sidecar = tmp_path / "model.sha256"

        assert not sidecar.exists()

        load_or_calc_hash(str(test_file))

        assert sidecar.exists()
        content = sidecar.read_text()
        assert len(content) == 64  # Full hash stored

    def test_force_rehash_recomputes(self, tmp_path):
        """Should recompute hash when force_rehash=True."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")
        sidecar = tmp_path / "model.sha256"
        sidecar.write_text("a" * 64)  # Pre-existing sidecar

        result = load_or_calc_hash(str(test_file), truncate=None, force_rehash=True)

        # Should compute new hash, not use sidecar
        assert result != "a" * 64

    def test_on_compute_callback(self, tmp_path):
        """Should call on_compute callback when computing hash."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")

        computed_paths = []

        def track_compute(path):
            computed_paths.append(path)

        load_or_calc_hash(str(test_file), on_compute=track_compute)

        assert str(test_file) in computed_paths

    def test_custom_sidecar_extension(self, tmp_path):
        """Should use custom sidecar extension."""
        test_file = tmp_path / "model.safetensors"
        test_file.write_bytes(b"test content")

        load_or_calc_hash(str(test_file), sidecar_ext=".myhash")

        sidecar = tmp_path / "model.myhash"
        assert sidecar.exists()
