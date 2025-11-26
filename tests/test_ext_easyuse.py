"""Tests for defs/ext/easyuse_nodes.py Easy-Use custom node selectors."""

import pytest

import folder_paths


@pytest.fixture(autouse=True)
def reset_lora_index():
    """Reset the LoRA index between tests."""
    from saveimage_unimeta.utils import lora

    lora._LORA_INDEX = None
    lora._LORA_INDEX_BUILT = False
    yield


@pytest.fixture
def mock_lora_index(monkeypatch, tmp_path):
    """Set up a mock LoRA index for testing."""
    lora_dir = tmp_path / "loras"
    lora_dir.mkdir()
    (lora_dir / "LoRA_One.safetensors").write_text("dummy")
    (lora_dir / "LoRA_Two.safetensors").write_text("dummy")
    monkeypatch.setattr(folder_paths, "get_folder_paths", lambda kind: [str(lora_dir)])
    return lora_dir


# --- get_lora_data_stack tests ---


def test_get_lora_data_stack_extracts_names():
    """get_lora_data_stack should extract LoRA names matching pattern."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_data_stack

    input_data = [
        {
            "num_loras": [3],
            "lora_1_name": ["LoRA_One.safetensors"],
            "lora_2_name": ["LoRA_Two.safetensors"],
            "lora_3_name": ["None"],  # Should be filtered
            "other_key": ["ignored"],
        }
    ]

    result = get_lora_data_stack(input_data, r"lora_\d_name")
    assert result == ["LoRA_One.safetensors", "LoRA_Two.safetensors"]


def test_get_lora_data_stack_extracts_strengths():
    """get_lora_data_stack should extract LoRA strengths matching pattern."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_data_stack

    input_data = [
        {
            "num_loras": [2],
            "lora_1_strength": [0.8],
            "lora_2_strength": [0.5],
            "lora_3_strength": [0.3],  # Beyond num_loras limit
        }
    ]

    result = get_lora_data_stack(input_data, r"lora_\d_strength")
    assert result == [0.8, 0.5]


def test_get_lora_data_stack_limits_to_num_loras():
    """get_lora_data_stack should respect num_loras limit."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_data_stack

    input_data = [
        {
            "num_loras": [1],
            "lora_1_name": ["First.safetensors"],
            "lora_2_name": ["Second.safetensors"],
            "lora_3_name": ["Third.safetensors"],
        }
    ]

    result = get_lora_data_stack(input_data, r"lora_\d_name")
    assert len(result) == 1
    assert result[0] == "First.safetensors"


def test_get_lora_data_stack_filters_none():
    """get_lora_data_stack should filter out 'None' values."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_data_stack

    input_data = [
        {
            "num_loras": [3],
            "lora_1_name": ["Active.safetensors"],
            "lora_2_name": ["None"],
            "lora_3_name": ["Another.safetensors"],
        }
    ]

    result = get_lora_data_stack(input_data, r"lora_\d_name")
    assert "None" not in result
    assert "Active.safetensors" in result


# --- get_lora_model_name_stack tests ---


def test_get_lora_model_name_stack_when_toggled_on():
    """get_lora_model_name_stack should return names when toggle is on."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_model_name_stack

    input_data = [
        {
            "toggle": [True],
            "num_loras": [2],
            "lora_1_name": ["MyLoRA.safetensors"],
            "lora_2_name": ["YourLoRA.safetensors"],
        }
    ]

    result = get_lora_model_name_stack(1, {}, {}, {}, {}, input_data)
    assert result == ["MyLoRA.safetensors", "YourLoRA.safetensors"]


def test_get_lora_model_name_stack_when_toggled_off():
    """get_lora_model_name_stack should return empty list when toggle is off."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_model_name_stack

    input_data = [
        {
            "toggle": [False],
            "num_loras": [2],
            "lora_1_name": ["MyLoRA.safetensors"],
            "lora_2_name": ["YourLoRA.safetensors"],
        }
    ]

    result = get_lora_model_name_stack(1, {}, {}, {}, {}, input_data)
    assert result == []


# --- get_lora_model_hash_stack tests ---


def test_get_lora_model_hash_stack_returns_hashes():
    """get_lora_model_hash_stack should compute hashes for each LoRA."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_model_hash_stack

    input_data = [
        {
            "num_loras": [2],
            "lora_1_name": ["LoRA_A.safetensors"],
            "lora_2_name": ["LoRA_B.safetensors"],
        }
    ]

    result = get_lora_model_hash_stack(1, {}, {}, {}, {}, input_data)
    assert len(result) == 2
    assert all(isinstance(h, str) for h in result)


# --- get_lora_strength_model_stack tests ---


def test_get_lora_strength_model_stack_simple_mode():
    """get_lora_strength_model_stack should use strength in simple mode."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_strength_model_stack

    input_data = [
        {
            "mode": ["simple"],
            "num_loras": [2],
            "lora_1_strength": [0.8],
            "lora_2_strength": [0.6],
        }
    ]

    result = get_lora_strength_model_stack(1, {}, {}, {}, {}, input_data)
    assert result == [0.8, 0.6]


def test_get_lora_strength_model_stack_advanced_mode():
    """get_lora_strength_model_stack should use model_strength in advanced mode."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_strength_model_stack

    input_data = [
        {
            "mode": ["advanced"],
            "num_loras": [2],
            "lora_1_model_strength": [0.9],
            "lora_2_model_strength": [0.7],
            "lora_1_strength": [0.5],  # Should not be used in advanced mode
            "lora_2_strength": [0.4],
        }
    ]

    result = get_lora_strength_model_stack(1, {}, {}, {}, {}, input_data)
    assert result == [0.9, 0.7]


# --- get_lora_strength_clip_stack tests ---


def test_get_lora_strength_clip_stack_simple_mode():
    """get_lora_strength_clip_stack should use strength in simple mode."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_strength_clip_stack

    input_data = [
        {
            "mode": ["simple"],
            "num_loras": [2],
            "lora_1_strength": [0.7],
            "lora_2_strength": [0.5],
        }
    ]

    result = get_lora_strength_clip_stack(1, {}, {}, {}, {}, input_data)
    assert result == [0.7, 0.5]


def test_get_lora_strength_clip_stack_advanced_mode():
    """get_lora_strength_clip_stack should use clip_strength in advanced mode."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_strength_clip_stack

    input_data = [
        {
            "mode": ["advanced"],
            "num_loras": [2],
            "lora_1_clip_strength": [0.6],
            "lora_2_clip_strength": [0.4],
            "lora_1_strength": [0.9],  # Should not be used in advanced mode
            "lora_2_strength": [0.8],
        }
    ]

    result = get_lora_strength_clip_stack(1, {}, {}, {}, {}, input_data)
    assert result == [0.6, 0.4]


# --- get_lora_model_hash tests ---


def test_get_lora_model_hash_returns_hash_for_valid_lora():
    """get_lora_model_hash should return hash when LoRA is not None."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_model_hash

    input_data = [{"lora_name": ["TestLoRA.safetensors"]}]

    result = get_lora_model_hash(1, {}, {}, {}, {}, input_data)
    assert isinstance(result, str)
    assert result != ""


def test_get_lora_model_hash_returns_empty_for_none():
    """get_lora_model_hash should return empty string when LoRA is None."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import get_lora_model_hash

    input_data = [{"lora_name": ["None"]}]

    result = get_lora_model_hash(1, {}, {}, {}, {}, input_data)
    assert result == ""


# --- CAPTURE_FIELD_LIST structure tests ---


def test_capture_field_list_contains_easy_lorastack():
    """CAPTURE_FIELD_LIST should contain easy loraStack node definition."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import CAPTURE_FIELD_LIST
    from saveimage_unimeta.defs.meta import MetaField

    assert "easy loraStack" in CAPTURE_FIELD_LIST

    lora_stack_config = CAPTURE_FIELD_LIST["easy loraStack"]
    assert MetaField.LORA_MODEL_NAME in lora_stack_config
    assert MetaField.LORA_MODEL_HASH in lora_stack_config
    assert MetaField.LORA_STRENGTH_MODEL in lora_stack_config
    assert MetaField.LORA_STRENGTH_CLIP in lora_stack_config


def test_capture_field_list_contains_easy_fullloader():
    """CAPTURE_FIELD_LIST should contain easy fullLoader node definition."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import CAPTURE_FIELD_LIST
    from saveimage_unimeta.defs.meta import MetaField

    assert "easy fullLoader" in CAPTURE_FIELD_LIST

    loader_config = CAPTURE_FIELD_LIST["easy fullLoader"]
    assert MetaField.MODEL_NAME in loader_config
    assert MetaField.MODEL_HASH in loader_config
    assert MetaField.CLIP_SKIP in loader_config


def test_capture_field_list_contains_samplers():
    """CAPTURE_FIELD_LIST should contain sampler node definitions."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import CAPTURE_FIELD_LIST
    from saveimage_unimeta.defs.meta import MetaField

    assert "easy fullkSampler" in CAPTURE_FIELD_LIST
    assert "easy preSampling" in CAPTURE_FIELD_LIST

    sampler_config = CAPTURE_FIELD_LIST["easy fullkSampler"]
    assert MetaField.SEED in sampler_config
    assert MetaField.STEPS in sampler_config
    assert MetaField.CFG in sampler_config


def test_samplers_dict_contains_expected_nodes():
    """SAMPLERS dict should contain expected sampler nodes."""
    from saveimage_unimeta.defs.ext.easyuse_nodes import SAMPLERS

    assert "easy fullkSampler" in SAMPLERS
    assert "easy preSampling" in SAMPLERS
    assert "easy preSamplingAdvanced" in SAMPLERS
