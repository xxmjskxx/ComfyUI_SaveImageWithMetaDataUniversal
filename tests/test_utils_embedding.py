import os
import sys
from pathlib import Path

import pytest

try:  # Allow both editable installs and repo checkouts
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils import embedding as embedding_mod
except ModuleNotFoundError:  # pragma: no cover - fallback path for pytest
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils import embedding as embedding_mod


class DummyClip:
    def __init__(self, directories):
        self.embedding_directory = directories


def test_get_embedding_file_path_found_with_extension(tmp_path):
    embed_dir = tmp_path / "embeds"
    embed_dir.mkdir()
    target = embed_dir / "lion.pt"
    target.write_bytes(b"bin")

    clip = DummyClip(str(embed_dir))
    resolved = embedding_mod.get_embedding_file_path("lion", clip)

    assert resolved == str(target)


def test_get_embedding_file_path_checks_multiple_dirs(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    target = second / "fox.safetensors"
    target.write_bytes(b"data")

    clip = DummyClip([str(first), str(second)])
    resolved = embedding_mod.get_embedding_file_path("fox", clip)

    assert resolved == str(target)


def test_get_embedding_file_path_rejects_traversal(tmp_path):
    embed_dir = tmp_path / "safe"
    embed_dir.mkdir()
    sneaky_path = os.path.abspath(tmp_path.parent / "outside.bin")
    Path(sneaky_path).write_bytes(b"bad")

    clip = DummyClip(str(embed_dir))
    resolved = embedding_mod.get_embedding_file_path("../outside.bin", clip)

    assert resolved is None


def test_get_embedding_file_path_errors_on_missing_directory():
    clip = DummyClip("")
    with pytest.raises(ValueError):
        embedding_mod.get_embedding_file_path("lion", clip)


def test_get_embedding_file_path_handles_expand_errors(monkeypatch):
    clip = DummyClip("/tmp/fake")

    def boom(_paths):  # pragma: no cover - ensures ValueError path executed
        raise TypeError("explode")

    monkeypatch.setattr(embedding_mod, "expand_directory_list", boom)

    with pytest.raises(ValueError) as exc:
        embedding_mod.get_embedding_file_path("lion", clip)

    assert "expand" in str(exc.value)


def test_get_embedding_file_path_errors_when_no_valid_dirs(monkeypatch):
    clip = DummyClip("/tmp/fake")
    monkeypatch.setattr(embedding_mod, "expand_directory_list", lambda paths: [])

    with pytest.raises(ValueError):
        embedding_mod.get_embedding_file_path("lion", clip)
