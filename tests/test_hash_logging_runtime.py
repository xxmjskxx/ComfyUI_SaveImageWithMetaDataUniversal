import os
import logging
from pathlib import Path

import pytest

from saveimage_unimeta.defs import formatters


@pytest.fixture(autouse=True)
def reset_mode():
    formatters.set_hash_log_mode("none")
    yield
    formatters.set_hash_log_mode("none")


def _mk(tmp_path: Path, name: str, content: str = "data") -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_logging_initialization_and_hash_source(tmp_path, monkeypatch):
    model_file = _mk(tmp_path, "anonymodel.safetensors", "AAAA")
    # folder_paths stub
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: model_file if name.startswith("anonymodel") else None,
    )
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.set_hash_log_mode("debug")
    h1 = formatters.calc_model_hash("anonymodel", None)
    assert len(h1) == 10
    # Should include initialization banner via logger (not captured by _log) and our custom _log messages
    assert any("resolved (model)" in msg or "hash source=" in msg for msg in captured)
    # Second call should mark sidecar path reuse
    captured.clear()
    h2 = formatters.calc_model_hash("anonymodel", None)
    assert h2 == h1
    assert any("hash source=sidecar" in msg for msg in captured)


def test_lora_numeric_suffix_debug_logging(tmp_path, monkeypatch):
    lora_file = _mk(tmp_path, "obscure_theme_pack_7.05.safetensors", "BBBB")
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: (lora_file if name.startswith("obscure_theme_pack_7.05") else None),
    )
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.set_hash_log_mode("debug")
    h = formatters.calc_lora_hash("obscure_theme_pack_7.05", None)
    assert len(h) == 10
    joined = "\n".join(captured)
    assert "resolved (lora)" in joined
    assert "hash source=" in joined
    assert "full hash" in joined  # debug full hash line


def test_force_rehash_env(tmp_path, monkeypatch):
    model_file = _mk(tmp_path, "anothermodel.safetensors", "CCCC")
    import folder_paths

    monkeypatch.setattr(
        folder_paths,
        "get_full_path",
        lambda kind, name: model_file if name.startswith("anothermodel") else None,
    )
    # Capture log messages
    recorded = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: recorded.append(m))
    formatters.set_hash_log_mode("path")
    # First call writes sidecar
    h1 = formatters.calc_model_hash("anothermodel", None)
    assert len(h1) == 10
    # Capture full old hash from sidecar
    sidecar = os.path.splitext(model_file)[0] + ".sha256"
    assert os.path.exists(sidecar)
    with open(sidecar, encoding="utf-8") as f:
        _ = f.read().strip()
    # Modify file content significantly to ensure hash changes
    Path(model_file).write_text("DDDD-CHANGED-CONTENT-LONGER", encoding="utf-8")
    # Without force flag we still read old sidecar (same truncated hash)
    h2 = formatters.calc_model_hash("anothermodel", None)
    assert h2 == h1
    # Force rehash via env (should log source=computed even though sidecar exists)
    monkeypatch.setenv("METADATA_FORCE_REHASH", "1")
    formatters.calc_model_hash("anothermodel", None)
    # Verify a recompute occurred (presence of 'hash source=computed' after force env)
    assert any("hash source=computed" in m for m in recorded), recorded
    monkeypatch.delenv("METADATA_FORCE_REHASH")


def test_unresolved_model_resolution_logging(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.set_hash_log_mode("detailed")
    h = formatters.calc_model_hash("nonexistent_foo_bar_baz", None)
    assert h == "N/A"
    # Resolution failure warning logged only in detailed/debug via _warn_unresolved_once -> "unresolved model"
    assert any("unresolved model" in m for m in captured)
