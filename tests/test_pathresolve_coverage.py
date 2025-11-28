
import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from saveimage_unimeta.utils import pathresolve
from saveimage_unimeta.utils.pathresolve import (
    sanitize_candidate,
    try_resolve_artifact,
    _probe_folder,
    _iter_container_candidates,
    load_or_calc_hash,
)
import folder_paths

def test_sanitize_candidate_edge_cases():
    # Test defensive check
    assert sanitize_candidate(123) == "123"
    assert sanitize_candidate(None) == "None"

    # Test trim_trailing_punct logic
    assert sanitize_candidate("test. ", trim_trailing_punct=True) == "test"
    assert sanitize_candidate("test. ", trim_trailing_punct=False) == "test."

    # Test mixed quotes
    assert sanitize_candidate("'test\"") == "'test\"" # asymmetric
    assert sanitize_candidate('"test\'') == '"test\'' # asymmetric

    # Test empty result after stripping
    assert sanitize_candidate("  .  ") == ""
    assert sanitize_candidate("  .  ", trim_trailing_punct=False) == "."

def test_iter_container_candidates_exceptions():
    # Test error handling in iter_container_candidates
    # The traceback shows that `hasattr(container, attr)` accesses the property and RAISES exception if it is a property.
    # The code expects `hasattr` to be safe, but with properties it executes code.
    # The `except Exception` block wraps `getattr`, not `hasattr`.

    class Evil:
        @property
        def model_name(self):
            raise ValueError("Evil")

    # If hasattr raises, then it's not caught.
    # We should catch it if the source code intended to cover this.
    # Source:
    #         for attr in RESOLUTION_ATTR_KEYS:
    #            if hasattr(container, attr):
    #                try:
    #                    val = getattr(container, attr)
    #                except Exception:  # pragma: no cover
    #                    continue

    # So `hasattr` is outside the try block.
    # So if we want to exercise the `except` block, we need `hasattr` to return True, but `getattr` to raise exception.
    # This happens if the property works the first time (or we Mock `hasattr`?)
    # `hasattr` basically calls `getattr` and catches AttributeError.
    # If the property raises ValueError, `hasattr` will let it propagate (in newer python versions? or always?).
    # Actually `hasattr` catches exceptions in older python, but catching generic Exception is discouraged.

    # Let's try to make `hasattr` return True, but `getattr` fail.
    # We can't easily do that with a property on same object unless it has state.

    class Flaky:
        def __init__(self):
            self.calls = 0
        @property
        def model_name(self):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("Fail on second access")
            return "ok"

    # hasattr(obj, 'model_name') -> calls property -> calls=1, returns "ok" (True)
    # getattr(obj, 'model_name') -> calls property -> calls=2, raises RuntimeError

    # But wait, `hasattr` swallows exceptions?
    # "The result is True if the string is the name of one of the object’s attributes, False if not. (This is implemented by calling getattr(object, name) and seeing whether it raises an AttributeError or not.)"
    # It only swallows AttributeError. Other exceptions propagate.

    # So if we raise AttributeError in the property, hasattr returns False.
    # If we raise RuntimeError, hasattr propagates it.

    # So to trigger the `except Exception` block around `getattr`:
    # We need `hasattr` to return True.
    # And `getattr` to raise Exception.

    f = Flaky()
    # verify logic
    # hasattr(f, "model_name") # calls=1. Returns True.
    # getattr(f, "model_name") # calls=2. Raises RuntimeError.

    # But does `hasattr` really call the property? Yes.

    # Let's use this Flaky class.

    candidates = list(_iter_container_candidates(Flaky()))
    # It should yield nothing if exception is caught and continue is executed.
    assert candidates == []


def test_probe_folder_extensions(monkeypatch):
    # Mock folder_paths.get_full_path

    def mock_get_full_path(kind, name):
        if name == "exists.safetensors":
            return "/path/to/exists.safetensors"
        if name == "base.safetensors":
            return "/path/to/base.safetensors"
        if name == "base.01.safetensors":
             return "/path/to/base.01.safetensors"
        return None

    # We need os.path.exists to match
    monkeypatch.setattr(folder_paths, "get_full_path", mock_get_full_path)
    monkeypatch.setattr(os.path, "exists", lambda p: True if p else False)

    # Test direct match
    assert _probe_folder("ckpt", "exists.safetensors") == "/path/to/exists.safetensors"

    # Test extension probing
    # If we ask for "base", it should find "base.safetensors"
    assert _probe_folder("ckpt", "base") == "/path/to/base.safetensors"

    # Test unknown extension fallback
    # "base.01" -> extension is ".01", not in supported.
    # Should treat "base.01" as stem and append known extensions -> "base.01.safetensors"
    assert _probe_folder("ckpt", "base.01") == "/path/to/base.01.safetensors"

def test_try_resolve_artifact_max_depth():
    # Create a recursive structure
    recursive_list = []
    recursive_list.append(recursive_list)

    res = try_resolve_artifact("ckpt", recursive_list, max_depth=2)
    assert res.full_path is None
    # visited_ids logic should also prevent infinite recursion even if max_depth was high

def test_try_resolve_artifact_pathlike():
    import pathlib
    p = pathlib.Path("test.safetensors")

    with patch("saveimage_unimeta.utils.pathresolve._probe_folder", return_value="/resolved/path"):
        res = try_resolve_artifact("ckpt", p)
        assert res.full_path == "/resolved/path"

def test_try_resolve_artifact_post_resolver_exception():
    def exploding_resolver(name):
        raise ValueError("Boom")

    res = try_resolve_artifact("ckpt", "missing", post_resolvers=[exploding_resolver])
    assert res.full_path is None

def test_load_or_calc_hash_sidecar_write_failure(tmp_path):
    # Create a file to hash
    f = tmp_path / "test.txt"
    f.write_text("content")

    # Mock calc_hash to return a valid hash
    valid_hash = "a" * 64

    with patch("saveimage_unimeta.utils.pathresolve.calc_hash", return_value=valid_hash):
        # Use builtins.open patch carefully
        real_open = open
        def mock_open(file, mode="r", *args, **kwargs):
            if str(file).endswith(".sha256") and "w" in mode:
                raise OSError("Write failed")
            return real_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            error_cb = MagicMock()
            res = load_or_calc_hash(str(f), sidecar_error_cb=error_cb)

        assert res == valid_hash[:10]
        error_cb.assert_called_once()

def test_load_or_calc_hash_read_failure(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("content")
    sidecar = tmp_path / "test.sha256"
    sidecar.touch()

    # Mock reading sidecar failing
    real_open = open
    def mock_open(file, mode="r", *args, **kwargs):
        if str(file).endswith(".sha256") and "r" in mode:
             raise OSError("Read failed")
        return real_open(file, mode, *args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        with patch("saveimage_unimeta.utils.pathresolve.calc_hash", return_value="b"*64):
             res = load_or_calc_hash(str(f))
             assert res == ("b"*64)[:10]

def test_load_or_calc_hash_rehash_env(tmp_path, monkeypatch):
    f = tmp_path / "test.txt"
    f.write_text("content")
    sidecar = tmp_path / "test.sha256"
    sidecar.write_text("a"*64)

    monkeypatch.setenv("METADATA_FORCE_REHASH", "1")

    with patch("saveimage_unimeta.utils.pathresolve.calc_hash", return_value="b"*64):
        res = load_or_calc_hash(str(f))
        assert res == ("b"*64)[:10]
        # Should have updated sidecar
        assert sidecar.read_text() == "b"*64
