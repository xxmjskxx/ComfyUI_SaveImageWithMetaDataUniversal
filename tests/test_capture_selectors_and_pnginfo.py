"""Tests for capture.py selector error handling and gen_pnginfo_dict edge cases."""

import importlib

import pytest

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField
from tests.test_helpers import install_prompt_environment

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


# --- Selector error handling ---


def test_selector_raises_key_error_gracefully(monkeypatch: pytest.MonkeyPatch):
    """When a selector raises KeyError, capture should skip the entry and continue."""
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "1": {"class_type": "SelectorNode", "inputs": {"field_a": ["hello"]}},
    }
    install_prompt_environment(monkeypatch, capture_mod, prompt)

    def bad_selector(node_id, obj, prompt, extra_data, outputs, input_data):
        raise KeyError("missing_field")

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "SelectorNode": {
                MetaField.MODEL_NAME: {"selector": bad_selector},
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()
    # Entry should be skipped; MODEL_NAME list will be empty or absent
    assert MetaField.MODEL_NAME not in inputs or inputs[MetaField.MODEL_NAME] == []


def test_selector_raises_type_error_gracefully(monkeypatch: pytest.MonkeyPatch):
    """When a selector raises TypeError, capture should skip the entry and continue."""
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "2": {"class_type": "TypeSelectorNode", "inputs": {}},
    }
    install_prompt_environment(monkeypatch, capture_mod, prompt)

    def bad_selector(*args, **kwargs):
        raise TypeError("bad call")

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "TypeSelectorNode": {
                MetaField.VAE_NAME: {"selector": bad_selector},
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()
    assert MetaField.VAE_NAME not in inputs or inputs[MetaField.VAE_NAME] == []


def test_selector_returns_list_of_values(monkeypatch: pytest.MonkeyPatch):
    """A selector that returns a list should expand into multiple capture entries."""
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "3": {"class_type": "MultiSelector", "inputs": {}},
    }
    install_prompt_environment(monkeypatch, capture_mod, prompt)

    def multi_selector(*args, **kwargs):
        return ["val_a", "val_b", "val_c"]

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "MultiSelector": {
                MetaField.EMBEDDING_NAME: {"selector": multi_selector, "source_tag": "multi"},
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()
    entries = inputs[MetaField.EMBEDDING_NAME]
    assert len(entries) == 3
    assert [e[1] for e in entries] == ["val_a", "val_b", "val_c"]
    assert all(e[2] == "multi" for e in entries)


def test_validation_skips_node_when_false(monkeypatch: pytest.MonkeyPatch):
    """Entries with validate=False should be skipped entirely."""
    capture_mod = importlib.import_module(MODULE_PATH)

    prompt = {
        "4": {"class_type": "ValidatedNode", "inputs": {"data": ["captured"]}},
    }
    install_prompt_environment(monkeypatch, capture_mod, prompt)

    def always_false(*args, **kwargs):
        return False

    monkeypatch.setattr(
        capture_mod,
        "CAPTURE_FIELD_LIST",
        {
            "ValidatedNode": {
                MetaField.SEED: {
                    "field_name": "data",
                    "validate": always_false,
                },
            }
        },
    )

    inputs = capture_mod.Capture.get_inputs()
    assert MetaField.SEED not in inputs


# --- gen_pnginfo_dict tests ---


def test_weight_dtype_sanitizes_known_tokens():
    """Weight dtype key should sanitize and accept known dtype tokens."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.WEIGHT_DTYPE: [("node", "fp16", "field")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert pnginfo.get("Weight dtype") == "fp16"


def test_weight_dtype_rejects_path_like_values():
    """Weight dtype key should reject path-like strings."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.WEIGHT_DTYPE: [("node", "C:/models/something.safetensors", "field")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert "Weight dtype" not in pnginfo


def test_weight_dtype_rejects_pure_numeric():
    """Weight dtype should reject purely numeric values."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.WEIGHT_DTYPE: [("node", "1024", "field")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert "Weight dtype" not in pnginfo


def test_negative_prompt_blanked_when_none_literal():
    """Negative prompt should be blanked when set to 'none'."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.POSITIVE_PROMPT: [("1", "a beautiful sunset", "text")],
        MetaField.NEGATIVE_PROMPT: [("1", "none", "text")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert pnginfo.get("Negative prompt") == ""


def test_guidance_normalized_to_float():
    """Guidance values should be normalized to float."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.GUIDANCE: [("1", 7, "field")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert pnginfo.get("Guidance") == 7.0
    assert isinstance(pnginfo.get("Guidance"), float)


def test_cfg_scale_normalized_to_float():
    """CFG scale values should be normalized to float."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.CFG: [("1", "7.5", "cfg")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert pnginfo.get("CFG scale") == 7.5


def test_sampler_fallback_from_this_node_inputs(monkeypatch: pytest.MonkeyPatch):
    """If sampler_name missing before sampler, fallback to inputs_before_this_node."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    before_sampler = {}
    before_this = {
        MetaField.SAMPLER_NAME: [("5", "euler_ancestral", "sampler_name")],
    }
    pnginfo = Capture.gen_pnginfo_dict(before_sampler, before_this, False)
    assert pnginfo.get("Sampler") == "euler_ancestral"


def test_steps_rejects_negative_values():
    """Steps should not be written when value is negative."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.STEPS: [("1", -1, "steps")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert "Steps" not in pnginfo


def test_steps_accepts_zero():
    """Steps value of 0 should be accepted (edge case)."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.STEPS: [("1", 0, "steps")],
    }
    pnginfo = Capture.gen_pnginfo_dict(inputs, {}, False)
    assert pnginfo.get("Steps") == 0


# --- LoRA record edge cases ---


def test_lora_aggregate_text_filtered():
    """Aggregated text entries (multiple <lora:...>) should be filtered out."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.LORA_MODEL_NAME: [
            ("1", "<lora:a:0.5> <lora:b:0.5>", "aggregated"),
            ("2", "SingleLoRA", "single"),
        ],
    }
    records, _ = Capture._collect_lora_records(inputs)
    names = [r.name for r in records]
    assert "SingleLoRA" in names
    # Aggregated entry should have been filtered
    assert not any("<lora:" in n for n in names)


def test_lora_invalid_name_rejected():
    """LoRA names that are empty, 'none', or purely numeric should be rejected."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    inputs = {
        MetaField.LORA_MODEL_NAME: [
            ("1", "", "empty"),
            ("2", "none", "none_literal"),
            ("3", "123.45", "numeric"),
            ("4", "ValidLoRA", "valid"),
        ],
    }
    records, _ = Capture._collect_lora_records(inputs)
    names = [r.name for r in records]
    assert names == ["ValidLoRA"]


def test_looks_like_hex_hash_valid_cases():
    """_looks_like_hex_hash should accept valid truncated and full hashes."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    assert Capture._looks_like_hex_hash("abc123def0") is True
    assert Capture._looks_like_hex_hash("A" * 64) is True
    assert Capture._looks_like_hex_hash("  abcdef12  ") is True


def test_looks_like_hex_hash_invalid_cases():
    """_looks_like_hex_hash should reject non-hex or out-of-range strings."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    assert Capture._looks_like_hex_hash("short") is False
    assert Capture._looks_like_hex_hash("A" * 65) is False
    assert Capture._looks_like_hex_hash("ghijklmn") is False
    assert Capture._looks_like_hex_hash(12345) is False
    assert Capture._looks_like_hex_hash(None) is False


# --- gen_parameters_str edge cases ---


def test_gen_parameters_str_guidance_as_cfg():
    """guidance_as_cfg kwarg should copy Guidance into CFG scale and remove Guidance."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    pnginfo = {
        "Positive prompt": "test",
        "Negative prompt": "",
        "Guidance": 5.5,
        "Metadata generator version": "1.0",
    }
    result = Capture.gen_parameters_str(pnginfo, guidance_as_cfg=True)
    assert "CFG scale: 5.5" in result
    assert "Guidance:" not in result


def test_gen_parameters_str_dual_prompts():
    """When both T5 Prompt and CLIP Prompt exist, output should label them."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    pnginfo = {
        "Positive prompt": "ignored",
        "Negative prompt": "bad things",
        "T5 Prompt": "T5 text here",
        "CLIP Prompt": "CLIP text here",
        "Metadata generator version": "1.0",
    }
    result = Capture.gen_parameters_str(pnginfo)
    assert "T5 Prompt: T5 text here" in result
    assert "CLIP Prompt: CLIP text here" in result
    # Positive prompt should not appear as a standalone line
    assert result.count("ignored") == 0


def test_gen_parameters_str_include_lora_summary_override(monkeypatch: pytest.MonkeyPatch):
    """include_lora_summary kwarg should override env flag."""
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture

    # Ensure env flag would suppress summary
    monkeypatch.setenv("METADATA_NO_LORA_SUMMARY", "1")

    pnginfo = {
        "Positive prompt": "test",
        "Negative prompt": "",
        "Lora_0 Model name": "TestLoRA",
        "Lora_0 Strength model": 0.8,
        "Metadata generator version": "1.0",
    }
    # With override=True, summary should appear
    result = Capture.gen_parameters_str(pnginfo, include_lora_summary=True)
    assert "LoRAs:" in result or "Lora_0" in result
