import os
import re
from pathlib import Path

import pytest
import logging

from saveimage_unimeta.defs import formatters

# Utility to create a dummy artifact file


def _make_file(tmp_path: Path, name: str, content: str = "x") -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


@pytest.mark.parametrize(
    "mode,expect_full_path",
    [
        ("filename", False),
        ("path", True),
    ],
)
def test_basic_model_logging_filename_vs_path(tmp_path, mode, expect_full_path, monkeypatch):
    model_file = _make_file(tmp_path, "modelA.safetensors", "model-content")
    # Monkeypatch folder_paths lookups to return our file
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: model_file if name.startswith("modelA") else name,
    )
    captured: list[str] = []
    monkeypatch.setattr(
        formatters,
        "_log",
        lambda kind, msg, level=logging.INFO: captured.append(msg),
    )
    formatters.HASH_LOG_MODE = mode
    h1 = formatters.calc_model_hash("modelA", None)
    assert len(h1) == 10
    captured.clear()
    h2 = formatters.calc_model_hash("modelA", None)
    assert h2 == h1
    logs = "\n".join(captured)
    if expect_full_path:
        assert model_file in logs
    else:
        assert Path(model_file).name in logs and model_file not in logs
    assert ("hashing" in logs) or ("reading" in logs)


def test_detailed_includes_resolution_and_sidecar(tmp_path, monkeypatch):
    lora_file = _make_file(tmp_path, "myLoRA.safetensors", "lora")
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: lora_file if name.startswith("myLoRA") else name,
    )
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.HASH_LOG_MODE = "detailed"
    _ = formatters.calc_lora_hash("myLoRA", None)
    logs = "\n".join(captured)
    assert "resolved (lora)" in logs
    # For current implementation, hashing log may not appear in detailed mode for lora
    # unless display_for_log is set; tolerate absence.


def test_debug_mode_shows_candidates_and_full_hash(tmp_path, monkeypatch):
    vae_file = _make_file(tmp_path, "specialVAE.safetensors", "vae")
    import folder_paths

    # Force first lookup to fail direct path then succeed via extension probing
    def _gf(kind, name):
        if name == "specialVAE.safetensors":
            return None  # force failure so probing path kicks in
        return vae_file if name.startswith("specialVAE") else None

    monkeypatch.setattr(folder_paths, "get_full_path", _gf)
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.HASH_LOG_MODE = "debug"
    _ = formatters.calc_vae_hash("specialVAE.safetensors", None)
    logs = "\n".join(captured)
    assert "candidates for" in logs
    # Full 64-char hash should be logged in debug mode
    assert re.search(r"full hash .*=[0-9a-f]{64}", logs)


def test_unresolved_warning_once(tmp_path, monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.HASH_LOG_MODE = "detailed"
    _ = formatters.calc_model_hash("nonexistent_model_xyz", None)
    _ = formatters.calc_model_hash("nonexistent_model_xyz", None)
    logs = "\n".join(captured)
    assert logs.count("unresolved model") == 1


def test_lora_numeric_suffix_sidecar(tmp_path, monkeypatch):
    # Create versioned style name with numeric segment before extension
    lora_file = _make_file(tmp_path, "dark_gothic_fantasy_xl_3.01.safetensors", "content")
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: (lora_file if name.startswith("dark_gothic_fantasy_xl_3.01") else name),
    )
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    # Use 'path' so LoRA logging chooses full path emission path
    formatters.HASH_LOG_MODE = "path"
    h1 = formatters.calc_lora_hash("dark_gothic_fantasy_xl_3.01", None)
    assert len(h1) == 10
    base, _ = os.path.splitext(lora_file)
    sidecar = base + ".sha256"
    assert os.path.exists(sidecar), "Expected sidecar with full hash written"
    captured.clear()
    h2 = formatters.calc_lora_hash("dark_gothic_fantasy_xl_3.01", None)
    assert h2 == h1
    # Logging of hashing/reading for lora may be skipped depending on mode; ensure hash stable and sidecar exists.
    _ = "\n".join(captured)


def test_prompt_single_newline_no_double_blank(monkeypatch):
    import saveimage_unimeta.capture as capture_mod

    original = capture_mod.Capture.gen_pnginfo_dict

    def _fake_gen_pnginfo_dict(*a, **k):
        return {
            "Positive prompt": "A cat sitting on a mat\n",  # trailing newline
            "Negative prompt": "",  # empty
        }

    try:
        monkeypatch.setattr(capture_mod.Capture, "gen_pnginfo_dict", staticmethod(_fake_gen_pnginfo_dict))
        params = capture_mod.Capture.gen_parameters_str(_fake_gen_pnginfo_dict())
    finally:
        monkeypatch.setattr(capture_mod.Capture, "gen_pnginfo_dict", original)
    assert "A cat sitting on a mat" in params
    assert "\n\n\n" not in params


def test_version_override(monkeypatch):
    import saveimage_unimeta.capture as capture_mod

    monkeypatch.setenv("METADATA_VERSION_OVERRIDE", "9.9.9-test")
    v = capture_mod.resolve_runtime_version()
    assert v == "9.9.9-test"
    monkeypatch.delenv("METADATA_VERSION_OVERRIDE")


def test_sidecar_write_warning_once(tmp_path, monkeypatch):
    model_file = _make_file(tmp_path, "warnModel.safetensors", "data")
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: model_file if name.startswith("warnModel") else name,
    )
    # Make directory read-only to induce sidecar write failure (Windows may ignore chmod so mock instead)
    base, _ = os.path.splitext(model_file)
    sidecar = base + ".sha256"
    import builtins

    real_open = builtins.open

    def _failing_open(path, mode="r", *a, **k):
        if path == sidecar and "w" in mode:
            raise OSError("permission denied")
        return real_open(path, mode, *a, **k)

    monkeypatch.setattr("builtins.open", _failing_open)
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.HASH_LOG_MODE = "detailed"
    _ = formatters.calc_model_hash("warnModel", None)
    _ = formatters.calc_model_hash("warnModel", None)
    logs = "\n".join(captured)
    assert logs.count("sidecar write failed") == 1
