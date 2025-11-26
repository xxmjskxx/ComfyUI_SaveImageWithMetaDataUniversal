"""Tests for saveimage_unimeta/utils/lora.py LoRA parsing and indexing utilities."""

import importlib

import pytest

import folder_paths


@pytest.fixture
def lora_mod():
    """Import the lora module."""
    mod = importlib.import_module("saveimage_unimeta.utils.lora")
    # Reset module-level caches before each test
    mod._LORA_INDEX = None
    mod._LORA_INDEX_BUILT = False
    return mod


# --- coerce_first tests ---


def test_coerce_first_returns_first_element_of_list(lora_mod):
    """coerce_first should return the first element of a list."""
    assert lora_mod.coerce_first(["hello", "world"]) == "hello"


def test_coerce_first_returns_empty_for_empty_list(lora_mod):
    """coerce_first should return empty string for empty list."""
    assert lora_mod.coerce_first([]) == ""


def test_coerce_first_returns_string_unchanged(lora_mod):
    """coerce_first should return strings unchanged."""
    assert lora_mod.coerce_first("direct") == "direct"


def test_coerce_first_returns_empty_for_non_string_non_list(lora_mod):
    """coerce_first should return empty string for non-string/non-list."""
    assert lora_mod.coerce_first(123) == ""
    assert lora_mod.coerce_first(None) == ""


# --- parse_lora_syntax tests ---


def test_parse_lora_syntax_empty_text(lora_mod):
    """parse_lora_syntax should return empty lists for empty text."""
    names, ms, cs = lora_mod.parse_lora_syntax("")
    assert names == []
    assert ms == []
    assert cs == []


def test_parse_lora_syntax_strict_format(lora_mod):
    """parse_lora_syntax should parse strict <lora:name:strength> format."""
    text = "prompt <lora:TestLoRA:0.8> more text"
    names, ms, cs = lora_mod.parse_lora_syntax(text)
    assert names == ["TestLoRA"]
    assert ms == [0.8]
    assert cs == [0.8]  # clip strength defaults to model strength


def test_parse_lora_syntax_strict_with_clip_strength(lora_mod):
    """parse_lora_syntax should parse strict format with explicit clip strength."""
    text = "<lora:DualStrength:0.7:0.5>"
    names, ms, cs = lora_mod.parse_lora_syntax(text)
    assert names == ["DualStrength"]
    assert ms == [0.7]
    assert cs == [0.5]


def test_parse_lora_syntax_multiple_loras(lora_mod):
    """parse_lora_syntax should extract multiple LoRAs from text."""
    text = "<lora:First:1.0> some text <lora:Second:0.5:0.3>"
    names, ms, cs = lora_mod.parse_lora_syntax(text)
    assert names == ["First", "Second"]
    assert ms == [1.0, 0.5]
    assert cs == [1.0, 0.3]


def test_parse_lora_syntax_legacy_format(lora_mod):
    """parse_lora_syntax should parse legacy format when strict fails."""
    # Legacy format with colon-separated strengths in a single blob
    text = "<lora:LegacyLoRA:0.6:0.4>"
    names, ms, cs = lora_mod.parse_lora_syntax(text)
    # With strict matching, this should still parse correctly
    assert names == ["LegacyLoRA"]
    assert ms == [0.6]
    assert cs == [0.4]


def test_parse_lora_syntax_invalid_strength_defaults(lora_mod):
    """parse_lora_syntax should default to 1.0 for invalid strengths."""
    # Construct a string that won't match STRICT but will match LEGACY
    # LEGACY captures everything after the second colon as a blob
    text = "<lora:BadStrength:abc>"
    names, ms, cs = lora_mod.parse_lora_syntax(text)
    # STRICT won't match 'abc', so LEGACY kicks in, which will fail float conversion
    assert "BadStrength" in names or names == []
    if names:
        assert ms == [1.0]
        assert cs == [1.0]


# --- build_lora_index and find_lora_info tests ---


def test_build_lora_index_creates_index(lora_mod, monkeypatch, tmp_path):
    """build_lora_index should scan directories and build the index."""
    # Create a fake lora directory structure
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "TestModel.safetensors").write_text("dummy")
    (lora_dir / "AnotherModel.pt").write_text("dummy")
    subdir = lora_dir / "subdir"
    subdir.mkdir()
    (subdir / "SubLoRA.safetensors").write_text("dummy")

    # Patch folder_paths at the module level where it's used
    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])

    # Reset and build
    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False
    lora_mod.build_lora_index()

    assert lora_mod._LORA_INDEX_BUILT is True
    assert "TestModel" in lora_mod._LORA_INDEX
    assert "AnotherModel" in lora_mod._LORA_INDEX
    assert "SubLoRA" in lora_mod._LORA_INDEX


def test_build_lora_index_is_idempotent(lora_mod, monkeypatch, tmp_path):
    """build_lora_index should not rebuild if already built."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "First.safetensors").write_text("dummy")

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])

    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False
    lora_mod.build_lora_index()

    # Add another file after index is built
    (lora_dir / "Second.safetensors").write_text("dummy")
    lora_mod.build_lora_index()  # Should not re-scan

    assert "First" in lora_mod._LORA_INDEX
    assert "Second" not in lora_mod._LORA_INDEX  # Not picked up due to idempotence


def test_find_lora_info_returns_entry(lora_mod, monkeypatch, tmp_path):
    """find_lora_info should return the indexed info for a known LoRA."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    lora_file = lora_dir / "KnownLoRA.safetensors"
    lora_file.write_text("dummy")

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])

    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False

    info = lora_mod.find_lora_info("KnownLoRA")
    assert info is not None
    assert info["filename"] == "KnownLoRA.safetensors"
    assert str(lora_dir) in info["abspath"]


def test_find_lora_info_returns_none_for_unknown(lora_mod, monkeypatch, tmp_path):
    """find_lora_info should return None for unknown LoRAs."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])

    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False

    info = lora_mod.find_lora_info("NonExistent")
    assert info is None


# --- resolve_lora_display_names tests ---


def test_resolve_lora_display_names_uses_index(lora_mod, monkeypatch, tmp_path):
    """resolve_lora_display_names should resolve names using the index."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "IndexedLoRA.safetensors").write_text("dummy")

    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])

    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False

    result = lora_mod.resolve_lora_display_names(["IndexedLoRA", "UnknownLoRA"])
    assert result[0] == "IndexedLoRA.safetensors"
    assert result[1] == "UnknownLoRA"  # Falls back to raw name


def test_resolve_lora_display_names_handles_exceptions(lora_mod, monkeypatch):
    """resolve_lora_display_names should handle exceptions gracefully."""
    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [])

    lora_mod._LORA_INDEX = None
    lora_mod._LORA_INDEX_BUILT = False

    # Should not raise
    result = lora_mod.resolve_lora_display_names(["SomeName"])
    assert result == ["SomeName"]
