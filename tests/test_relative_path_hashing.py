import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

try:
    from saveimage_unimeta.defs import formatters

    HAVE_FMT = True
except Exception:
    HAVE_FMT = False


def _mock_folder_paths(temp_dir: str):
    mfp = MagicMock()

    def _get_full_path(kind: str, name: str):
        # emulate Comfy's models/<kind> roots with subfolders allowed
        root = os.path.join(temp_dir, kind)
        direct = os.path.join(root, name)
        if os.path.exists(direct):
            return direct
        # also allow when name has backslashes (Windows-style)
        direct_win = os.path.join(root, *name.split("\\"))
        if os.path.exists(direct_win):
            return direct_win
        raise FileNotFoundError(name)

    mfp.get_full_path = _get_full_path
    return mfp


@pytest.mark.skipif(not HAVE_FMT, reason="formatters not available")
def test_lora_hash_from_relative_subpath_with_backslashes():
    with tempfile.TemporaryDirectory() as td:
        loras_root = os.path.join(td, "loras")
        subdir = os.path.join(loras_root, "flux", "artstyle", "style")
        os.makedirs(subdir, exist_ok=True)
        file_path = os.path.join(subdir, "sample_lora.safetensors")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("content")
        rel = "flux\\artstyle\\style\\sample_lora.safetensors"
        mfp = _mock_folder_paths(td)
        with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp):
            h = formatters.calc_lora_hash(rel, [])
            assert isinstance(h, str) and len(h) == 10 and h != "N/A"


@pytest.mark.skipif(not HAVE_FMT, reason="formatters not available")
def test_unet_hash_from_relative_subpath_with_backslashes():
    with tempfile.TemporaryDirectory() as td:
        unet_root = os.path.join(td, "unet")
        subdir = os.path.join(unet_root, "flux", "models")
        os.makedirs(subdir, exist_ok=True)
        file_path = os.path.join(subdir, "unet_x.safetensors")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("unet")
        rel = "flux\\models\\unet_x.safetensors"
        mfp = _mock_folder_paths(td)
        with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp):
            h = formatters.calc_unet_hash(rel, [])
            assert isinstance(h, str) and len(h) == 10 and h != "N/A"


@pytest.mark.skipif(not HAVE_FMT, reason="formatters not available")
def test_vae_hash_from_relative_subpath_with_backslashes():
    with tempfile.TemporaryDirectory() as td:
        vae_root = os.path.join(td, "vae")
        subdir = os.path.join(vae_root, "ae")
        os.makedirs(subdir, exist_ok=True)
        file_path = os.path.join(subdir, "ae.safetensors")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("vae")
        rel = "ae\\ae.safetensors"
        mfp = _mock_folder_paths(td)
        with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp):
            h = formatters.calc_vae_hash(rel, [])
            assert isinstance(h, str) and len(h) == 10 and h != "N/A"


@pytest.mark.skipif(not HAVE_FMT, reason="formatters not available")
def test_logger_reinit_on_mode_change_only(monkeypatch, capsys):
    # Start with mode 'none'
    monkeypatch.setenv("METADATA_HASH_LOG_MODE", "none")
    from importlib import reload

    fmt = reload(formatters)
    # Switch to 'debug' via API and ensure it prints the init banner once
    fmt.set_hash_log_mode("debug")
    # Trigger a log action (harmless call)
    _ = fmt.calc_model_hash("dummy_missing_model", [])
    io = capsys.readouterr()
    stream = io.err + io.out
    assert "[Hash] logging initialized" in stream
    # Calling again without changing mode should not reinitialize
    capsys.readouterr()
    _ = fmt.calc_model_hash("dummy_missing_model", [])
    io2 = capsys.readouterr()
    stream2 = io2.err + io2.out
    assert "[Hash] logging initialized" not in stream2
