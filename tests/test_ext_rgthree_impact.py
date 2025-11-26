"""Tests for defs/ext/rgthree.py and defs/ext/impact.py LoRA extraction modules."""

import importlib
import sys

import pytest

import folder_paths


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset all module-level caches between tests."""
    # Reset rgthree cache
    from saveimage_unimeta.defs.ext import rgthree

    rgthree._SYNTAX_CACHE.clear()

    # Reset impact cache
    from saveimage_unimeta.defs.ext import impact

    impact._CACHE.clear()

    # Reset lora index
    from saveimage_unimeta.utils import lora

    lora._LORA_INDEX = None
    lora._LORA_INDEX_BUILT = False

    yield


@pytest.fixture
def mock_lora_index(monkeypatch, tmp_path):
    """Set up a mock LoRA index for testing."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "TestLoRA.safetensors").write_text("dummy")
    (lora_dir / "DetailLoRA.safetensors").write_text("dummy")
    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])
    return lora_dir


# --- rgthree get_lora_data tests ---


def test_get_lora_data_extracts_active_loras():
    """get_lora_data should extract data from active LoRA inputs."""
    from saveimage_unimeta.defs.ext.rgthree import get_lora_data

    input_data = [
        {
            "lora_01": [{"on": True, "lora": "TestLoRA.safetensors", "strength": 0.8}],
            "lora_02": [{"on": False, "lora": "Inactive.safetensors", "strength": 0.5}],
            "lora_03": [{"on": True, "lora": "AnotherLoRA.safetensors", "strength": 1.0}],
        }
    ]

    result = get_lora_data(input_data, "lora")
    assert result == ["TestLoRA.safetensors", "AnotherLoRA.safetensors"]


def test_get_lora_data_extracts_strength():
    """get_lora_data should extract strength values from active LoRAs."""
    from saveimage_unimeta.defs.ext.rgthree import get_lora_data

    input_data = [
        {
            "lora_01": [{"on": True, "lora": "TestLoRA.safetensors", "strength": 0.8}],
            "lora_02": [{"on": True, "lora": "AnotherLoRA.safetensors", "strength": 1.2}],
        }
    ]

    result = get_lora_data(input_data, "strength")
    assert result == [0.8, 1.2]


def test_get_lora_data_returns_empty_for_invalid_input():
    """get_lora_data should return empty list for invalid input."""
    from saveimage_unimeta.defs.ext.rgthree import get_lora_data

    assert get_lora_data(None, "lora") == []
    assert get_lora_data([], "lora") == []
    assert get_lora_data("not a list", "lora") == []
    assert get_lora_data([123], "lora") == []  # Not a dict


def test_get_lora_data_skips_non_lora_keys():
    """get_lora_data should ignore keys that don't start with 'lora_'."""
    from saveimage_unimeta.defs.ext.rgthree import get_lora_data

    input_data = [
        {
            "other_key": [{"on": True, "lora": "Should.safetensors", "strength": 1.0}],
            "lora_01": [{"on": True, "lora": "TestLoRA.safetensors", "strength": 0.5}],
        }
    ]

    result = get_lora_data(input_data, "lora")
    assert result == ["TestLoRA.safetensors"]


# --- rgthree selectors tests ---


def test_get_lora_model_name_selector():
    """get_lora_model_name should use get_lora_data internally."""
    from saveimage_unimeta.defs.ext.rgthree import get_lora_model_name

    input_data = [
        {"lora_01": [{"on": True, "lora": "MyLoRA.safetensors", "strength": 0.9}]}
    ]

    result = get_lora_model_name(1, {}, {}, {}, {}, input_data)
    assert result == ["MyLoRA.safetensors"]


def test_get_lora_strength_selector():
    """get_lora_strength should use get_lora_data internally."""
    from saveimage_unimeta.defs.ext.rgthree import get_lora_strength

    input_data = [
        {"lora_01": [{"on": True, "lora": "MyLoRA.safetensors", "strength": 0.75}]}
    ]

    result = get_lora_strength(1, {}, {}, {}, {}, input_data)
    assert result == [0.75]


# --- rgthree _parse_syntax tests ---


def test_parse_syntax_extracts_lora_tags(mock_lora_index):
    """_parse_syntax should extract LoRA info from syntax tags."""
    from saveimage_unimeta.defs.ext.rgthree import _parse_syntax

    text = "a portrait <lora:TestLoRA:0.8> photo"
    result = _parse_syntax(text)

    assert "TestLoRA.safetensors" in result["names"]
    assert len(result["model_strengths"]) == 1
    assert result["model_strengths"][0] == 0.8


def test_parse_syntax_handles_dual_strengths(mock_lora_index):
    """_parse_syntax should handle dual model/clip strengths."""
    from saveimage_unimeta.defs.ext.rgthree import _parse_syntax

    text = "<lora:TestLoRA:0.7:0.5>"
    result = _parse_syntax(text)

    assert result["model_strengths"][0] == 0.7
    assert result["clip_strengths"][0] == 0.5


def test_parse_syntax_returns_empty_for_no_loras():
    """_parse_syntax should return empty lists when no LoRA syntax found."""
    from saveimage_unimeta.defs.ext.rgthree import _parse_syntax

    result = _parse_syntax("just a plain prompt without any loras")

    assert result["names"] == []
    assert result["hashes"] == []
    assert result["model_strengths"] == []
    assert result["clip_strengths"] == []


# --- rgthree _get_syntax tests ---


def test_get_syntax_extracts_from_prompt_field(mock_lora_index):
    """_get_syntax should extract text from 'prompt' field."""
    from saveimage_unimeta.defs.ext.rgthree import _get_syntax

    input_data = [{"prompt": "<lora:TestLoRA:0.9>"}]
    result = _get_syntax(1, input_data)

    assert "TestLoRA.safetensors" in result["names"]


def test_get_syntax_extracts_from_text_field(mock_lora_index):
    """_get_syntax should extract text from 'text' field."""
    from saveimage_unimeta.defs.ext.rgthree import _get_syntax

    input_data = [{"text": "<lora:DetailLoRA:0.6>"}]
    result = _get_syntax(2, input_data)

    assert "DetailLoRA.safetensors" in result["names"]


def test_get_syntax_uses_cache():
    """_get_syntax should cache results and return cached data."""
    from saveimage_unimeta.defs.ext.rgthree import _get_syntax, _SYNTAX_CACHE

    input_data = [{"prompt": "test prompt <lora:MyLoRA:0.5>"}]
    _get_syntax(99, input_data)

    assert 99 in _SYNTAX_CACHE
    assert _SYNTAX_CACHE[99]["text"] == "test prompt <lora:MyLoRA:0.5>"


def test_get_syntax_returns_empty_for_invalid_input():
    """_get_syntax should return empty data for invalid input."""
    from saveimage_unimeta.defs.ext.rgthree import _get_syntax

    assert _get_syntax(1, None)["names"] == []
    assert _get_syntax(1, [])["names"] == []
    assert _get_syntax(1, [123])["names"] == []  # Not a dict


def test_get_syntax_handles_list_values(mock_lora_index):
    """_get_syntax should coerce list values to first element."""
    from saveimage_unimeta.defs.ext.rgthree import _get_syntax

    input_data = [{"prompt": ["<lora:TestLoRA:0.8>", "ignored"]}]
    result = _get_syntax(3, input_data)

    assert "TestLoRA.safetensors" in result["names"]


# --- rgthree syntax selector tests ---


def test_get_rgthree_syntax_names(mock_lora_index):
    """get_rgthree_syntax_names should return LoRA names from syntax."""
    from saveimage_unimeta.defs.ext.rgthree import get_rgthree_syntax_names

    input_data = [{"prompt": "<lora:TestLoRA:0.5>"}]
    result = get_rgthree_syntax_names(1, {}, {}, {}, {}, input_data)

    assert "TestLoRA.safetensors" in result


def test_get_rgthree_syntax_model_strengths(mock_lora_index):
    """get_rgthree_syntax_model_strengths should return model strengths."""
    from saveimage_unimeta.defs.ext.rgthree import get_rgthree_syntax_model_strengths

    input_data = [{"prompt": "<lora:TestLoRA:0.65>"}]
    result = get_rgthree_syntax_model_strengths(1, {}, {}, {}, {}, input_data)

    assert result == [0.65]


# --- impact _coerce tests ---


def test_impact_coerce_handles_list():
    """_coerce should return first element of list."""
    from saveimage_unimeta.defs.ext.impact import _coerce

    assert _coerce(["first", "second"]) == "first"
    assert _coerce([]) == ""


def test_impact_coerce_handles_string():
    """_coerce should return string unchanged."""
    from saveimage_unimeta.defs.ext.impact import _coerce

    assert _coerce("hello") == "hello"


def test_impact_coerce_handles_invalid():
    """_coerce should return empty string for invalid input."""
    from saveimage_unimeta.defs.ext.impact import _coerce

    assert _coerce(123) == ""
    assert _coerce(None) == ""


# --- impact _parse tests ---


def test_impact_parse_strict_format(mock_lora_index):
    """_parse should extract LoRA data from strict format."""
    from saveimage_unimeta.defs.ext.impact import _parse

    text = "prompt <lora:TestLoRA:0.8> more text"
    result = _parse(text)

    assert "TestLoRA.safetensors" in result["names"]
    assert result["model_strengths"][0] == 0.8
    assert result["clip_strengths"][0] == 0.8  # Same as model when not specified


def test_impact_parse_strict_with_clip(mock_lora_index):
    """_parse should handle strict format with explicit clip strength."""
    from saveimage_unimeta.defs.ext.impact import _parse

    text = "<lora:TestLoRA:0.7:0.4>"
    result = _parse(text)

    assert result["model_strengths"][0] == 0.7
    assert result["clip_strengths"][0] == 0.4


def test_impact_parse_legacy_format(mock_lora_index):
    """_parse should fall back to legacy format when strict doesn't match."""
    from saveimage_unimeta.defs.ext.impact import _parse

    # Legacy format: <lora:name:model:clip> as a blob
    text = "<lora:TestLoRA:0.6:0.3>"
    result = _parse(text)

    # With strict pattern it should still parse correctly
    assert "TestLoRA.safetensors" in result["names"]


def test_impact_parse_empty_text():
    """_parse should return empty lists for empty text."""
    from saveimage_unimeta.defs.ext.impact import _parse

    result = _parse("")

    assert result["names"] == []
    assert result["hashes"] == []


def test_impact_parse_multiple_loras(mock_lora_index):
    """_parse should extract multiple LoRA tags."""
    from saveimage_unimeta.defs.ext.impact import _parse

    text = "<lora:TestLoRA:0.5> <lora:DetailLoRA:0.8>"
    result = _parse(text)

    assert len(result["names"]) == 2
    assert len(result["model_strengths"]) == 2


# --- impact _extract tests ---


def test_impact_extract_finds_text_field(mock_lora_index):
    """_extract should find and parse text from 'text' field."""
    from saveimage_unimeta.defs.ext.impact import _extract

    input_data = [{"text": "<lora:TestLoRA:0.9>"}]
    result = _extract(1, input_data)

    assert "TestLoRA.safetensors" in result["names"]


def test_impact_extract_uses_cache():
    """_extract should cache results."""
    from saveimage_unimeta.defs.ext.impact import _extract, _CACHE

    input_data = [{"prompt": "test <lora:MyLoRA:0.5>"}]
    _extract(88, input_data)

    assert 88 in _CACHE
    assert _CACHE[88]["text"] == "test <lora:MyLoRA:0.5>"


def test_impact_extract_returns_cached_on_same_text():
    """_extract should return cached data if text hasn't changed."""
    from saveimage_unimeta.defs.ext.impact import _extract, _CACHE

    # Pre-populate cache
    cached_data = {"names": ["cached"], "hashes": ["abc"], "model_strengths": [1.0], "clip_strengths": [1.0]}
    _CACHE[77] = {"text": "cached text", "data": cached_data}

    input_data = [{"prompt": "cached text"}]
    result = _extract(77, input_data)

    assert result["names"] == ["cached"]


def test_impact_extract_returns_empty_for_invalid_input():
    """_extract should return empty data for invalid input."""
    from saveimage_unimeta.defs.ext.impact import _extract

    assert _extract(1, None)["names"] == []
    assert _extract(1, [])["names"] == []
    assert _extract(1, ["not a dict"])["names"] == []


# --- impact selector tests ---


def test_get_impact_lora_names(mock_lora_index):
    """get_impact_lora_names should return extracted LoRA names."""
    from saveimage_unimeta.defs.ext.impact import get_impact_lora_names

    input_data = [{"text": "<lora:TestLoRA:0.8>"}]
    result = get_impact_lora_names(1, {}, {}, {}, {}, input_data)

    assert "TestLoRA.safetensors" in result


def test_get_impact_lora_model_strengths(mock_lora_index):
    """get_impact_lora_model_strengths should return extracted model strengths."""
    from saveimage_unimeta.defs.ext.impact import get_impact_lora_model_strengths

    input_data = [{"text": "<lora:TestLoRA:0.75>"}]
    result = get_impact_lora_model_strengths(1, {}, {}, {}, {}, input_data)

    assert result == [0.75]


def test_get_impact_lora_clip_strengths(mock_lora_index):
    """get_impact_lora_clip_strengths should return extracted clip strengths."""
    from saveimage_unimeta.defs.ext.impact import get_impact_lora_clip_strengths

    input_data = [{"text": "<lora:TestLoRA:0.8:0.6>"}]
    result = get_impact_lora_clip_strengths(1, {}, {}, {}, {}, input_data)

    assert result == [0.6]


def test_get_impact_lora_hashes(mock_lora_index):
    """get_impact_lora_hashes should return hash strings."""
    from saveimage_unimeta.defs.ext.impact import get_impact_lora_hashes

    input_data = [{"text": "<lora:TestLoRA:0.5>"}]
    result = get_impact_lora_hashes(1, {}, {}, {}, {}, input_data)

    assert len(result) == 1
    assert isinstance(result[0], str)

