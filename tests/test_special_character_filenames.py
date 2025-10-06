#!/usr/bin/env python3
"""Filename resolution & hashing robustness tests (pytest).

Covers hashing for model / LoRA / VAE / UNet plus embedding resolution across a
wide variety of Windows-valid filenames (excluding reserved characters).

Focus: ensure name→path resolution logic tolerates punctuation, multiple dots,
unicode, spaces, and trailing punctuation segments before extension.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:  # runtime import (skip gracefully if minimal env)
    from saveimage_unimeta.defs.formatters import (
        calc_lora_hash,
        calc_model_hash,
        calc_vae_hash,
        calc_unet_hash,
    )
    from saveimage_unimeta.utils.embedding import get_embedding_file_path
    FORMATTERS_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:  # narrow expected import failures
    logging.warning("Could not import formatters: %s", e)
    FORMATTERS_AVAILABLE = False


FILENAME_VARIANTS = [
    # Basic
    "normal_file.safetensors",
    "file-with-dashes.safetensors",
    "file_with_underscores.safetensors",
    "file with spaces.safetensors",
    # Dots / versions / multi-dot numeric segments
    "model.v1.2.3.safetensors",
    "lora.with.dots.safetensors",
    "dark_gothic_fantasy_xl_3.01.safetensors",
    "version.1.2.3.final.safetensors",
    # Unicode + extended
    "unicode_ñ_ü_ß_model.safetensors",
    "japanese_日本語_model.safetensors",
    "emoji_😀_model.safetensors",
    "extended_àáâãäåæçèéêë.safetensors",
    "symbols_£¥€§©®™.safetensors",
    # Punctuation
    "file(with)parentheses.safetensors",
    "file[with]brackets.safetensors",
    "file{with}braces.safetensors",
    "file'with'apostrophes.safetensors",
    "file,with,commas.safetensors",
    "file;with;semicolons.safetensors",
    "file=with=equals.safetensors",
    "file+with+plus.safetensors",
    "file!with!exclamation.safetensors",
    "file@with@at.safetensors",
    "file#with#hash.safetensors",
    "file$with$dollar.safetensors",
    "file%with%percent.safetensors",
    "file^with^caret.safetensors",
    "file&with&ampersand.safetensors",
    "file~with~tilde.safetensors",
    "file`with`backtick.safetensors",
    # Trailing punctuation (Windows strips trailing dot/space in UI but underlying APIs handle pattern)
    "file.ending.with.dot..safetensors",
    "file ending with space .safetensors",
    # Complex combo
    "complex-file_name.with.many[special](chars)&symbols.v1.2.3.safetensors",
]


def _mock_folder_paths(base_dir: str):
    """Create minimal folder_paths stub covering extension fallback logic."""
    m = MagicMock()

    def _get_full_path(folder_type: str, name: str):  # mirrors usage pattern in formatters
        root = os.path.join(base_dir, folder_type)
        candidate = os.path.join(root, name)
        if os.path.exists(candidate):
            return candidate
        for ext in [".safetensors", ".st", ".pt", ".bin", ".ckpt"]:
            c2 = os.path.join(root, name + ext)
            if os.path.exists(c2):
                return c2
        raise FileNotFoundError(name)

    m.get_full_path = _get_full_path  # type: ignore[attr-defined]
    m.get_folder_paths = lambda ft: [os.path.join(base_dir, ft)]  # type: ignore[attr-defined]
    return m


# -------------------- Parametrized Hash Tests --------------------


# Helper fixture to reduce repeated patch boilerplate
@pytest.fixture
def patch_folder_paths():
    def _apply(base_dir: str):
        mfp = _mock_folder_paths(base_dir)
        return patch("saveimage_unimeta.defs.formatters.folder_paths", mfp)
    return _apply


if FORMATTERS_AVAILABLE:
    HASH_FUNCS = [
        ("lora", calc_lora_hash),
        ("model", calc_model_hash),
        ("vae", calc_vae_hash),
        ("unet", calc_unet_hash),
    ]
else:  # pragma: no cover - skipped when formatters unavailable
    HASH_FUNCS = []


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
@pytest.mark.parametrize("filename", FILENAME_VARIANTS)
def test_lora_hash_variants(filename, mock_file_content, create_test_files, patch_folder_paths):
    with tempfile.TemporaryDirectory() as td:
        create_test_files(td, "loras", [filename], mock_file_content["lora"])
        with patch_folder_paths(td):
            base = os.path.splitext(filename)[0]
            result = calc_lora_hash(base, [])
            assert result != "N/A" and len(result) == 10


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
@pytest.mark.parametrize("filename", FILENAME_VARIANTS)
def test_model_hash_variants(filename, mock_file_content, create_test_files, patch_folder_paths):
    with tempfile.TemporaryDirectory() as td:
        create_test_files(td, "checkpoints", [filename], mock_file_content["model"])
        with patch_folder_paths(td):
            base = os.path.splitext(filename)[0]
            result = calc_model_hash(base, [])
            assert result != "N/A" and len(result) == 10


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
@pytest.mark.parametrize("filename", FILENAME_VARIANTS)
def test_vae_hash_variants(filename, mock_file_content, create_test_files, patch_folder_paths):
    with tempfile.TemporaryDirectory() as td:
        create_test_files(td, "vae", [filename], mock_file_content["vae"])
        with patch_folder_paths(td):
            base = os.path.splitext(filename)[0]
            result = calc_vae_hash(base, [])
            assert result != "N/A" and len(result) == 10


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
@pytest.mark.parametrize("filename", FILENAME_VARIANTS)
def test_unet_hash_variants(filename, mock_file_content, create_test_files, patch_folder_paths):
    with tempfile.TemporaryDirectory() as td:
        create_test_files(td, "unet", [filename], mock_file_content["unet"])
        with patch_folder_paths(td):
            base = os.path.splitext(filename)[0]
            result = calc_unet_hash(base, [])
            assert result != "N/A" and len(result) == 10


# -------------------- Embedding Resolution --------------------


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
def test_embedding_resolution(mock_file_content):
    subset = FILENAME_VARIANTS[:12]  # keep runtime reasonable
    with tempfile.TemporaryDirectory() as td:
        embed_dir = os.path.join(td, "embeddings")
        os.makedirs(embed_dir, exist_ok=True)
        exts = [".safetensors", ".pt", ".bin"]
        for i, fn in enumerate(subset):
            base = os.path.splitext(fn)[0]
            target = base + exts[i % len(exts)]
            with open(os.path.join(embed_dir, target), "w", encoding="utf-8") as f:
                f.write(mock_file_content["embedding"])

        class _Clip:  # minimal stub
            embedding_directory = embed_dir

        for fn in subset:
            base = os.path.splitext(fn)[0]
            resolved = get_embedding_file_path(base, _Clip())
            assert resolved and os.path.exists(resolved)


# -------------------- Negative / Edge Cases --------------------


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
@pytest.mark.parametrize("hash_name,func", HASH_FUNCS)
def test_reserved_characters_return_na(hash_name, func):
    reserved = '<>:"/\\|?*'
    for ch in reserved:
        name = f"file{ch}bad"
        assert func(name, []) == "N/A", f"Expected N/A for reserved char {ch} via {hash_name}"


def test_splitext_edge_case_documentation():
    """Document (not assert semantics of) how splitext behaves on tricky names."""
    cases = [
        "model.name.v1.2.3",
        "file.ending.with.dot.",
        "file.with..double.dots",
        "file name with spaces",
        "file.01",
        "file.123.456",
    ]
    for c in cases:
        base, ext = os.path.splitext(c)
        # Both parts should always be strings (may be empty for ext)
        assert isinstance(base, str)
        assert isinstance(ext, str)


if __name__ == "__main__":  # allow ad‑hoc local run
    import pytest as _pytest

    raise SystemExit(_pytest.main([__file__]))
