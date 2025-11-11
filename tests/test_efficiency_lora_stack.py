import pytest

from saveimage_unimeta.defs.ext import efficiency_nodes as eff
from saveimage_unimeta.defs.formatters import calc_lora_hash


@pytest.fixture(name="simple_input_data")
def fixture_simple_input_data():
    return [
        {
            "input_mode": ["simple"],
            "lora_count": [3],
            "lora_name_1": ["enabled_lora.safetensors"],
            "lora_name_2": ["disabled_lora.safetensors"],
            "lora_name_3": ["None"],
            "lora_wt_1": [1.0],
            "lora_wt_2": [0.0],
            "lora_wt_3": [0.0],
        }
    ]


def test_efficiency_stack_prefers_outputs(simple_input_data):
    node_id = 42
    outputs = {
        node_id: ([
            ("enabled_lora.safetensors", 0.75, 0.5),
            ("disabled_lora.safetensors", 0.0, 0.0),
            ("another_disabled", "0", "0.0"),
        ],)
    }

    names = eff.get_lora_model_name_stack(node_id, None, None, None, outputs, simple_input_data)
    model_strengths = eff.get_lora_strength_model_stack(node_id, None, None, None, outputs, simple_input_data)
    clip_strengths = eff.get_lora_strength_clip_stack(node_id, None, None, None, outputs, simple_input_data)
    hashes = eff.get_lora_model_hash_stack(node_id, None, None, None, outputs, simple_input_data)

    assert names == [
        "enabled_lora.safetensors",
        "disabled_lora.safetensors",
        "another_disabled",
    ]
    assert model_strengths == [0.75, 0.0, "0"]
    assert clip_strengths == [0.5, 0.0, "0.0"]
    assert hashes == [
        calc_lora_hash("enabled_lora.safetensors", simple_input_data),
        calc_lora_hash("disabled_lora.safetensors", simple_input_data),
        calc_lora_hash("another_disabled", simple_input_data),
    ]


def test_efficiency_stack_falls_back_without_outputs(simple_input_data):
    node_id = 101
    outputs = {}

    names = eff.get_lora_model_name_stack(node_id, None, None, None, outputs, simple_input_data)
    model_strengths = eff.get_lora_strength_model_stack(node_id, None, None, None, outputs, simple_input_data)
    clip_strengths = eff.get_lora_strength_clip_stack(node_id, None, None, None, outputs, simple_input_data)

    assert names == ["enabled_lora.safetensors", "disabled_lora.safetensors"]
    assert model_strengths == [1.0, 0.0]
    assert clip_strengths == [1.0, 0.0]


def test_efficiency_stack_reports_empty_when_only_disabled_outputs(simple_input_data):
    node_id = 7
    outputs = {
        node_id: ([
            ("disabled_lora.safetensors", 0.0, 0.0),
        ],)
    }

    names = eff.get_lora_model_name_stack(node_id, None, None, None, outputs, simple_input_data)
    assert names == ["disabled_lora.safetensors"]
    assert eff.get_lora_model_hash_stack(node_id, None, None, None, outputs, simple_input_data) == [
        calc_lora_hash("disabled_lora.safetensors", simple_input_data)
    ]
    assert eff.get_lora_strength_model_stack(node_id, None, None, None, outputs, simple_input_data) == [0.0]
    assert eff.get_lora_strength_clip_stack(node_id, None, None, None, outputs, simple_input_data) == [0.0]
