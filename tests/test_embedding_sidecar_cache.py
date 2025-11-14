"""Test that embedding hash collection uses .sha256 sidecar caching."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def test_embedding_hash_uses_sidecar_cache(monkeypatch, tmp_path):
    """Verify that extract_embedding_hashes uses load_or_calc_hash with sidecar support."""
    # Import the module
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import formatters

    # Create a fake embedding file
    embedding_file = tmp_path / "test_embedding.safetensors"
    embedding_file.write_bytes(b"fake embedding content")

    # Create a .sha256 sidecar with a known hash
    # Sidecar path is based on file path without extension
    sidecar_file = tmp_path / "test_embedding.sha256"
    test_hash = "1234567890abcdef" * 4  # 64 char hash
    sidecar_file.write_text(test_hash)

    # Mock _extract_embedding_candidates to return our test path
    def mock_extract(text, input_data):
        return ["test_embedding.safetensors"], None, [str(embedding_file)]

    monkeypatch.setattr(formatters, "_extract_embedding_candidates", mock_extract)

    # Call extract_embedding_hashes
    hashes = formatters.extract_embedding_hashes("embedding:test_embedding", {})

    # Should return the hash from the sidecar (truncated to 10 chars)
    assert len(hashes) == 1
    assert hashes[0] == test_hash[:10]


def test_embedding_hash_creates_sidecar_on_compute(monkeypatch, tmp_path):
    """Verify that extract_embedding_hashes creates .sha256 sidecar when computing new hash."""
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import formatters

    # Create a fake embedding file
    embedding_file = tmp_path / "new_embedding.safetensors"
    embedding_file.write_bytes(b"new fake embedding content for hashing")

    # Mock _extract_embedding_candidates to return our test path
    def mock_extract(text, input_data):
        return ["new_embedding.safetensors"], None, [str(embedding_file)]

    monkeypatch.setattr(formatters, "_extract_embedding_candidates", mock_extract)

    # Ensure no sidecar exists initially (sidecar is based on path without extension)
    sidecar_file = tmp_path / "new_embedding.sha256"
    assert not sidecar_file.exists()

    # Call extract_embedding_hashes
    hashes = formatters.extract_embedding_hashes("embedding:new_embedding", {})

    # Should return a computed hash
    assert len(hashes) == 1
    assert isinstance(hashes[0], str)
    assert len(hashes[0]) == 10  # truncated hash

    # Sidecar should now exist with full 64-char hash
    assert sidecar_file.exists()
    sidecar_content = sidecar_file.read_text().strip()
    assert len(sidecar_content) == 64
    assert sidecar_content.startswith(hashes[0])


def test_embedding_hash_handles_missing_file(monkeypatch):
    """Verify that extract_embedding_hashes handles missing files gracefully."""
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import formatters

    # Mock _extract_embedding_candidates to return a non-existent path
    def mock_extract(text, input_data):
        return ["missing_embedding.safetensors"], None, ["/nonexistent/path/missing_embedding.safetensors"]

    monkeypatch.setattr(formatters, "_extract_embedding_candidates", mock_extract)

    # Call extract_embedding_hashes
    hashes = formatters.extract_embedding_hashes("embedding:missing_embedding", {})

    # Should return N/A for missing file
    assert len(hashes) == 1
    assert hashes[0] == "N/A"
