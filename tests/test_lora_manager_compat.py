"""Tests for LoraManager settings-reading helpers and their integration with build_lora_index."""

import json
import os

import folder_paths

from saveimage_unimeta.utils import lora as lora_mod
from saveimage_unimeta.utils.lora import (
    _find_lora_manager_root,
    _get_lora_manager_lora_paths,
    _get_lora_manager_user_config_path,
    _read_lora_manager_settings,
    build_lora_index,
    find_lora_info,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_index():
    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False


def _make_settings(extra_dir: str = "", folder_dir: str = "", portable: bool = False) -> dict:
    """Build a minimal LoraManager settings dict for testing."""
    data: dict = {}
    if portable:
        data["use_portable_settings"] = True
    if extra_dir:
        data["extra_folder_paths"] = {"loras": [extra_dir]}
    if folder_dir:
        data["folder_paths"] = {"loras": [folder_dir]}
    return data


# ---------------------------------------------------------------------------
# _find_lora_manager_root
# ---------------------------------------------------------------------------

def test_find_lora_manager_root_returns_none_when_no_candidates(monkeypatch):
    """Returns None when no recognised LoraManager directory exists under custom_nodes."""
    monkeypatch.setattr(os.path, "isdir", lambda _path: False)
    assert _find_lora_manager_root() is None


def test_find_lora_manager_root_finds_hyphenated_name(monkeypatch, tmp_path):
    """Detects 'comfyui-lora-manager' (the canonical install name)."""
    target = tmp_path / "comfyui-lora-manager"
    target.mkdir()

    real_isdir = os.path.isdir

    def _patched(path):
        if path == str(target):
            return True
        # Return False for all paths EXCEPT the one we fabricated to avoid noise from
        # real filesystem checks in the standard dirname chain.
        return False

    monkeypatch.setattr(os.path, "isdir", _patched)
    # Override "abspath(__file__)" for the module so the dirname chain resolves to tmp_path.
    # lora.py: utils/lora.py → utils → saveimage_unimeta → plugin_root → custom_nodes
    # We need dirname * 4 from __file__ to land on tmp_path.
    fake_file = str(tmp_path / "cn" / "Plug" / "pkg" / "utils" / "lora.py")

    orig_abspath = os.path.abspath

    def _fake_abspath(p):
        if p == lora_mod.__file__:
            return fake_file
        return orig_abspath(p)

    monkeypatch.setattr(os.path, "abspath", _fake_abspath)
    # Rebuild target based on the fake __file__ dirname chain.
    fake_cn_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(fake_file))))
    expected = os.path.join(fake_cn_dir, "comfyui-lora-manager")

    # Make the patched isdir return True for the expected path.
    def _patched2(path):
        return path == expected

    monkeypatch.setattr(os.path, "isdir", _patched2)
    result = _find_lora_manager_root()
    assert result == expected


# ---------------------------------------------------------------------------
# _get_lora_manager_user_config_path
# ---------------------------------------------------------------------------

def test_user_config_path_returns_settings_json_string():
    """Returns a non-empty string ending in settings.json."""
    path = _get_lora_manager_user_config_path()
    assert path is not None
    assert isinstance(path, str)
    assert path.endswith("settings.json")
    assert "ComfyUI-LoRA-Manager" in path


def test_user_config_path_linux_manual_fallback(monkeypatch):
    """Falls back to ~/.config/ComfyUI-LoRA-Manager/settings.json on Linux when no platformdirs."""
    import builtins
    real_import = builtins.__import__

    def _block_platformdirs(name, *args, **kwargs):
        if name == "platformdirs":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_platformdirs)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")

    path = _get_lora_manager_user_config_path()
    assert path == os.path.join("/custom/config", "ComfyUI-LoRA-Manager", "settings.json")


def test_user_config_path_windows_manual_fallback(monkeypatch):
    """Falls back to %APPDATA%\\ComfyUI-LoRA-Manager\\settings.json on Windows."""
    import builtins
    real_import = builtins.__import__

    def _block_platformdirs(name, *args, **kwargs):
        if name == "platformdirs":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_platformdirs)
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", r"C:\Users\Tester\AppData\Roaming")

    path = _get_lora_manager_user_config_path()
    assert path == r"C:\Users\Tester\AppData\Roaming\ComfyUI-LoRA-Manager\settings.json"


# ---------------------------------------------------------------------------
# _read_lora_manager_settings
# ---------------------------------------------------------------------------

def test_read_settings_portable_mode(tmp_path):
    """Reads settings.json from plugin root when use_portable_settings is True."""
    settings = _make_settings(extra_dir="/loras/extra", portable=True)
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    result = _read_lora_manager_settings(str(tmp_path))
    assert result is not None
    assert result["use_portable_settings"] is True
    assert result["extra_folder_paths"]["loras"] == ["/loras/extra"]


def test_read_settings_user_config_mode(tmp_path, monkeypatch):
    """Reads settings.json from user config dir when portable mode is off."""
    cfg_dir = tmp_path / "user_config"
    cfg_dir.mkdir()
    settings = _make_settings(extra_dir="/loras/user")
    (cfg_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    monkeypatch.setattr(lora_mod, "_get_lora_manager_user_config_path", lambda: str(cfg_dir / "settings.json"))

    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()
    # No settings.json in plugin root  → must fall back to user config
    result = _read_lora_manager_settings(str(plugin_root))
    assert result is not None
    assert result["extra_folder_paths"]["loras"] == ["/loras/user"]


def test_read_settings_legacy_fallback(tmp_path, monkeypatch):
    """Falls back to plugin-root settings.json that lacks the portable flag."""
    settings = _make_settings(extra_dir="/loras/legacy")
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    # No user-config file exists
    monkeypatch.setattr(lora_mod, "_get_lora_manager_user_config_path", lambda: str(tmp_path / "nonexistent.json"))

    result = _read_lora_manager_settings(str(tmp_path))
    assert result is not None
    assert result["extra_folder_paths"]["loras"] == ["/loras/legacy"]


def test_read_settings_portable_wins_over_user_config(tmp_path, monkeypatch):
    """Portable mode file takes precedence over user-config file."""
    portable_settings = _make_settings(extra_dir="/loras/portable", portable=True)
    (tmp_path / "settings.json").write_text(json.dumps(portable_settings), encoding="utf-8")

    user_cfg = tmp_path / "user.json"
    user_cfg.write_text(json.dumps(_make_settings(extra_dir="/loras/user")), encoding="utf-8")
    monkeypatch.setattr(lora_mod, "_get_lora_manager_user_config_path", lambda: str(user_cfg))

    result = _read_lora_manager_settings(str(tmp_path))
    assert result["extra_folder_paths"]["loras"] == ["/loras/portable"]


def test_read_settings_returns_none_when_no_files(tmp_path, monkeypatch):
    """Returns None when neither plugin-root nor user-config settings files exist."""
    monkeypatch.setattr(lora_mod, "_get_lora_manager_user_config_path", lambda: str(tmp_path / "nope.json"))
    result = _read_lora_manager_settings(str(tmp_path))
    assert result is None


def test_read_settings_handles_invalid_json_gracefully(tmp_path, monkeypatch):
    """Returns None (rather than raising) on malformed JSON."""
    (tmp_path / "settings.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(lora_mod, "_get_lora_manager_user_config_path", lambda: str(tmp_path / "nope.json"))
    result = _read_lora_manager_settings(str(tmp_path))
    assert result is None


# ---------------------------------------------------------------------------
# _get_lora_manager_lora_paths
# ---------------------------------------------------------------------------

def test_lora_paths_from_extra_folder_paths(tmp_path, monkeypatch):
    """Returns paths from extra_folder_paths.loras."""
    settings = {"extra_folder_paths": {"loras": ["/extra/loras"]}}
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: settings)

    result = _get_lora_manager_lora_paths()
    assert result == ["/extra/loras"]


def test_lora_paths_from_folder_paths(tmp_path, monkeypatch):
    """Returns paths from folder_paths.loras (library-switching case)."""
    settings = {"folder_paths": {"loras": ["/library/loras"]}}
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: settings)

    result = _get_lora_manager_lora_paths()
    assert result == ["/library/loras"]


def test_lora_paths_merges_both_keys(tmp_path, monkeypatch):
    """Returns paths from both extra_folder_paths and folder_paths when both are present."""
    settings = {
        "extra_folder_paths": {"loras": ["/extra/loras"]},
        "folder_paths": {"loras": ["/standard/loras"]},
    }
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: settings)

    result = _get_lora_manager_lora_paths()
    assert "/extra/loras" in result
    assert "/standard/loras" in result
    assert len(result) == 2


def test_lora_paths_deduplicates_same_path(tmp_path, monkeypatch):
    """A path appearing in both keys is returned only once."""
    shared = "/shared/loras"
    settings = {
        "extra_folder_paths": {"loras": [shared]},
        "folder_paths": {"loras": [shared]},
    }
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: settings)

    result = _get_lora_manager_lora_paths()
    assert result == [shared]


def test_lora_paths_returns_empty_when_plugin_not_installed(monkeypatch):
    """Returns [] when LoraManager is not installed (no plugin root found)."""
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: None)
    assert _get_lora_manager_lora_paths() == []


def test_lora_paths_returns_empty_when_no_settings(tmp_path, monkeypatch):
    """Returns [] when plugin root exists but no settings file is found."""
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: None)
    assert _get_lora_manager_lora_paths() == []


def test_lora_paths_ignores_empty_string_entries(tmp_path, monkeypatch):
    """Blank string entries in the paths list are filtered out."""
    settings = {"extra_folder_paths": {"loras": ["   ", "", "/real/path"]}}
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: settings)
    result = _get_lora_manager_lora_paths()
    assert result == ["/real/path"]


def test_lora_paths_tolerates_missing_loras_key(tmp_path, monkeypatch):
    """Settings with extra_folder_paths but no 'loras' sub-key returns []."""
    settings = {"extra_folder_paths": {"checkpoints": ["/checkpoints"]}}
    monkeypatch.setattr(lora_mod, "_find_lora_manager_root", lambda: str(tmp_path))
    monkeypatch.setattr(lora_mod, "_read_lora_manager_settings", lambda _root: settings)
    assert _get_lora_manager_lora_paths() == []


# ---------------------------------------------------------------------------
# build_lora_index integration
# ---------------------------------------------------------------------------

def test_build_lora_index_includes_extra_lora_manager_paths(monkeypatch, tmp_path):
    """Loras stored only in LoraManager extra paths are indexed and findable."""
    # Standard ComfyUI path has no loras.
    standard_dir = tmp_path / "standard_loras"
    standard_dir.mkdir()

    # LoraManager-only extra path contains add-detail-xl.safetensors.
    extra_dir = tmp_path / "extra_loras"
    extra_dir.mkdir()
    lora_file = extra_dir / "add-detail-xl.safetensors"
    lora_file.write_bytes(b"dummy")

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(standard_dir)] if kind == "loras" else [])
    monkeypatch.setattr(lora_mod, "_get_lora_manager_lora_paths", lambda: [str(extra_dir)])
    _reset_index()

    build_lora_index()
    info = find_lora_info("add-detail-xl")
    assert info is not None, "Expected add-detail-xl to be found in the extra path"
    assert info["filename"] == "add-detail-xl.safetensors"
    assert os.path.normcase(info["abspath"]) == os.path.normcase(str(lora_file))


def test_build_lora_index_standard_path_takes_priority_over_extra(monkeypatch, tmp_path):
    """When the same stem exists in both standard and extra paths, the standard path wins."""
    standard_dir = tmp_path / "standard"
    standard_dir.mkdir()
    extra_dir = tmp_path / "extra"
    extra_dir.mkdir()

    std_file = standard_dir / "my-lora.safetensors"
    std_file.write_bytes(b"standard")
    extra_file = extra_dir / "my-lora.safetensors"
    extra_file.write_bytes(b"extra")

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(standard_dir)] if kind == "loras" else [])
    monkeypatch.setattr(lora_mod, "_get_lora_manager_lora_paths", lambda: [str(extra_dir)])
    _reset_index()

    build_lora_index()
    info = find_lora_info("my-lora")
    assert info is not None
    assert os.path.normcase(info["abspath"]) == os.path.normcase(str(std_file))


def test_build_lora_index_no_lora_manager_installed(monkeypatch, tmp_path):
    """build_lora_index works normally when LoraManager returns no extra paths."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "standard-lora.safetensors").write_bytes(b"dummy")

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)] if kind == "loras" else [])
    monkeypatch.setattr(lora_mod, "_get_lora_manager_lora_paths", lambda: [])
    _reset_index()

    build_lora_index()
    assert find_lora_info("standard-lora") is not None


def test_build_lora_index_deduplicates_overlapping_paths(monkeypatch, tmp_path):
    """A path present in both ComfyUI folder_paths and LoraManager extra paths is walked only once."""
    shared_dir = tmp_path / "shared_loras"
    shared_dir.mkdir()
    (shared_dir / "overlap-lora.safetensors").write_bytes(b"dummy")

    walk_calls: list[str] = []
    real_walk = os.walk

    def _counting_walk(path, *args, **kwargs):
        walk_calls.append(str(path))
        return real_walk(path, *args, **kwargs)

    monkeypatch.setattr(lora_mod.os, "walk", _counting_walk)
    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(shared_dir)] if kind == "loras" else [])
    # LoraManager also reports the same directory
    monkeypatch.setattr(lora_mod, "_get_lora_manager_lora_paths", lambda: [str(shared_dir)])
    _reset_index()

    build_lora_index()

    # File must be indexed exactly once
    info = find_lora_info("overlap-lora")
    assert info is not None
    assert info["filename"] == "overlap-lora.safetensors"
    # The directory must have been walked only once
    assert walk_calls.count(str(shared_dir)) == 1
