import importlib

import pytest

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def _install_prompt_environment(monkeypatch: pytest.MonkeyPatch, capture_mod, prompt: dict[str, dict]) -> None:
    """Install a deterministic hook/prompt environment for capture tests."""

    class DummyPromptExecuter:
        class Caches:
            outputs = {}

        caches = Caches()

    class DummyHook:
        current_prompt = prompt
        current_extra_data = {}
        prompt_executer = DummyPromptExecuter()

    monkeypatch.setattr(capture_mod, "hook", DummyHook)

    node_classes = {}
    for node in prompt.values():
        class_type = node["class_type"]
        if class_type not in node_classes:
            node_classes[class_type] = type(f"{class_type}Stub", (), {})
    monkeypatch.setattr(capture_mod, "NODE_CLASS_MAPPINGS", node_classes)

    def fake_get_input_data(node_inputs, obj_class, node_id, outputs, dyn_prompt, extra):
        del obj_class, node_id, outputs, dyn_prompt, extra
        return (node_inputs,)

    monkeypatch.setattr(capture_mod, "get_input_data", fake_get_input_data)


def test_get_inputs_supports_fields_and_prefix_rules(monkeypatch: pytest.MonkeyPatch):
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "10": {
            "class_type": "MultiFieldNode",
            "inputs": {
                "alpha": ["StyleA"],
                "beta": ["stacked"],
                "clip_name1": ["CLIP-A"],
                "clip_name2": ["None"],
                "clip_name3": ["CLIP-C"],
            },
        }
    }
    _install_prompt_environment(monkeypatch, capture_mod, prompt)

    def multi_formatter(value, _input_data):
        return [value.upper(), f"tagged:{value}"]

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "MultiFieldNode": {
                MetaField.MODEL_NAME: {
                    "fields": ["alpha", "beta"],
                    "format": multi_formatter,
                    "source_tag": "multi-fields",
                },
                MetaField.CLIP_MODEL_NAME: {
                    "prefix": "clip_name",
                },
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()

    model_entries = inputs[MetaField.MODEL_NAME]
    collected_values = [entry[1] for entry in model_entries]
    assert collected_values.count("STYLEA") == 1
    assert any(val == "tagged:StyleA" for val in collected_values)
    assert collected_values.count("STACKED") == 1
    assert any(val == "tagged:stacked" for val in collected_values)
    assert all(entry[2] == "multi-fields" for entry in model_entries)

    clip_entries = inputs[MetaField.CLIP_MODEL_NAME]
    assert [(entry[1], entry[2]) for entry in clip_entries] == [
        ("CLIP-A", "prefix:clip_name"),
        ("CLIP-C", "prefix:clip_name"),
    ]


def test_model_name_hash_formatters_are_skipped(monkeypatch: pytest.MonkeyPatch):
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "20": {
            "class_type": "HashyNode",
            "inputs": {"model_field": ["TinyModel"]},
        }
    }
    _install_prompt_environment(monkeypatch, capture_mod, prompt)

    call_count = 0

    def fake_calc_model_hash(value, _input_data):
        nonlocal call_count
        call_count += 1
        return f"hashed:{value}"

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "HashyNode": {
                MetaField.MODEL_NAME: {
                    "field_name": "model_field",
                    "format": fake_calc_model_hash,
                }
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()

    assert call_count == 0, "hash formatter must be skipped for model name fields"
    assert inputs[MetaField.MODEL_NAME][0][1] == "TinyModel"


def test_model_hash_formatter_requires_path_like_values(monkeypatch: pytest.MonkeyPatch):
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "plain": {
            "class_type": "HashyNode",
            "inputs": {"model_path": ["TokenOnly"]},
        },
        "pathy": {
            "class_type": "HashyNode",
            "inputs": {"model_path": ["C:/models/fluxXl.safetensors"]},
        },
    }
    _install_prompt_environment(monkeypatch, capture_mod, prompt)

    called_values: list[str] = []

    def fake_model_hash(value, _input_data):
        called_values.append(value)
        return "HASHED"

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "HashyNode": {
                MetaField.MODEL_HASH: {
                    "field_name": "model_path",
                    "format": fake_model_hash,
                }
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()

    # Only the path-like input should invoke the formatter
    assert called_values == ["C:/models/fluxXl.safetensors"]

    hash_entries = inputs[MetaField.MODEL_HASH]
    values = [entry[1] for entry in hash_entries]
    assert values == ["TokenOnly", "HASHED"]
