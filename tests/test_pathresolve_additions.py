"""Additional tests for unified path resolution helpers (Phase 3).

Covers:
- Trailing dot / space normalization for models & VAEs & UNets & LoRAs.
- Sidecar hash reuse (ensures hashing not recomputed when .sha256 present).
- Ambiguous extension selection honors EXTENSION_ORDER.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from saveimage_unimeta.defs.formatters import (
    calc_model_hash,
    calc_vae_hash,
    calc_unet_hash,
    calc_lora_hash,
)
from saveimage_unimeta.utils.pathresolve import EXTENSION_ORDER

# ---------------- Fixtures ---------------- #

@pytest.fixture
def temp_artifact_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


def _mock_folder_paths(root: str):
    m = MagicMock()
    def _get_full_path(kind: str, name: str):
        base = os.path.join(root, kind, name)
        if os.path.exists(base):
            return base
        return base  # emulate Comfy's return even if file missing; resolver checks existence
    m.get_full_path = _get_full_path  # type: ignore[attr-defined]
    m.get_folder_paths = lambda k: [os.path.join(root, k)]  # type: ignore[attr-defined]
    return m

# ---------------- Tests ---------------- #

@pytest.mark.parametrize("hash_func,kind,content", [
    (calc_model_hash, "checkpoints", "model content"),
    (calc_vae_hash, "vae", "vae content"),
    (calc_unet_hash, "unet", "unet content"),
    (calc_lora_hash, "loras", "lora content"),
])
def test_trailing_dot_and_space_normalization(hash_func, kind, content, temp_artifact_dir):
    base_name = "sample_model"
    os.makedirs(os.path.join(temp_artifact_dir, kind), exist_ok=True)
    filename = base_name + ".safetensors"
    full_path = os.path.join(temp_artifact_dir, kind, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    mfp = _mock_folder_paths(temp_artifact_dir)
    with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp), \
         patch("saveimage_unimeta.utils.pathresolve.folder_paths", mfp):
        # Provide names with trailing punctuation - should still resolve
        for variant in [base_name + ".", base_name + "..", base_name + " ", base_name + ". "]:
            result = hash_func(variant, [])
            assert result != "N/A" and len(result) == 10, f"Failed to normalize variant {variant} for {kind}"


def test_sidecar_hash_reuse(temp_artifact_dir):
    os.makedirs(os.path.join(temp_artifact_dir, "checkpoints"), exist_ok=True)
    filename = "reuse_test.safetensors"
    full_path = os.path.join(temp_artifact_dir, "checkpoints", filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write("x" * 10)
    # Pre-write sidecar with known value
    sidecar = os.path.splitext(full_path)[0] + ".sha256"
    # Provide a FULL 64-char sha256 so reuse path is taken (previous behavior accepted truncated)
    known_hash = ("deadbeefcafebabe0123456789abcdef" * 2)[:64]
    assert len(known_hash) == 64
    with open(sidecar, "w", encoding="utf-8") as f:
        f.write(known_hash)
    mfp = _mock_folder_paths(temp_artifact_dir)
    with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp), \
         patch("saveimage_unimeta.utils.pathresolve.folder_paths", mfp):
       h = calc_model_hash("reuse_test", [])
       assert h == known_hash[:10]


def test_extension_order_priority(temp_artifact_dir):
    # Create multiple files differing only by extension for same base
    base = "priority_model"
    os.makedirs(os.path.join(temp_artifact_dir, "checkpoints"), exist_ok=True)
    created = []
    for ext in EXTENSION_ORDER:  # create all so resolver must pick first in order
        p = os.path.join(temp_artifact_dir, "checkpoints", base + ext)
        with open(p, "w", encoding="utf-8") as f:
            f.write(ext)
        created.append(p)
    mfp = _mock_folder_paths(temp_artifact_dir)
    with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp), \
         patch("saveimage_unimeta.utils.pathresolve.folder_paths", mfp):
        h = calc_model_hash(base, [])
        # Hash corresponds to first extension file's contents
        with open(created[0], "rb") as f:
            import hashlib
            expected = hashlib.sha256(f.read()).hexdigest()[:10]
        assert h == expected, "Did not honor extension ordering preference"
