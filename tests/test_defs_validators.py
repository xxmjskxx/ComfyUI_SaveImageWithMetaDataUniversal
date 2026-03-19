import sys
from pathlib import Path

import pytest

try:  # Allow execution both inside editable installs and custom_nodes checkouts
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import validators as validators_mod
except ModuleNotFoundError:  # pragma: no cover - repo-local fallback for pytest
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import validators as validators_mod


@pytest.fixture(autouse=True)
def reset_connection_cache(monkeypatch):
    """Ensure each test observes a clean connection cache."""

    monkeypatch.setattr(validators_mod, "_CONNECTION_CACHE", {}, raising=False)


# Positive prompt validator should identify direct CLIPTextEncode connections.
def test_is_positive_prompt_detects_known_text_encoder():
    prompt = {
        "1": {
            "class_type": "KSampler",
            "inputs": {
                "positive": ["clip_node", 0],
            },
        },
        "clip_node": {
            "class_type": "CLIPTextEncode",
            "inputs": {},
        },
    }

    assert validators_mod.is_positive_prompt("clip_node", None, prompt, None, None, None)
    assert not validators_mod.is_positive_prompt("1", None, prompt, None, None, None)


# Negative prompt validator must traverse intermediate nodes and match regex-based encoders.
def test_is_negative_prompt_handles_regex_encoder_and_chains():
    prompt = {
        "1": {
            "class_type": "KSampler",
            "inputs": {
                "negative": ["pre_node", 0],
            },
        },
        "pre_node": {
            "class_type": "PromptAdapter",
            "inputs": {"source": ["regex_encode", 0]},
        },
        "regex_encode": {
            "class_type": "Prompt Encode Deluxe",
            "inputs": {},
        },
    }

    assert validators_mod.is_negative_prompt("regex_encode", None, prompt, None, None, None)
    assert not validators_mod.is_positive_prompt("regex_encode", None, prompt, None, None, None)


# Connection validator should cache positive lookups and skip nodes lacking an inputs key.
def test_is_node_connected_caches_results(monkeypatch):
    prompt = {
        "encoder": {"class_type": "CLIPTextEncode", "inputs": {}},
        "consumer": {"class_type": "ShowText", "inputs": {"text": ["encoder", 0]}},
        "no_inputs": {"class_type": "StatelessNode"},
    }

    assert validators_mod.is_node_connected("encoder", prompt)
    assert validators_mod._CONNECTION_CACHE.get("encoder") is True

    # Remove the edge; cached result should still report True without accessing the missing input.
    prompt["consumer"]["inputs"] = {}
    assert validators_mod.is_node_connected("encoder", prompt)


# Connection validator should memoize negative lookups as well.
def test_is_node_connected_records_disconnected_nodes():
    prompt = {
        "isolated": {"class_type": "CLIPTextEncode", "inputs": {}},
        "other": {"class_type": "KSampler", "inputs": {"positive": ["shadow", 0]}},
    }

    assert not validators_mod.is_node_connected("isolated", prompt)
    assert validators_mod._CONNECTION_CACHE.get("isolated") is False


# --- CFGGuider / SamplerCustomAdvanced guider-aware traversal ---


def _cfg_guider_prompt():
    """Build a prompt mimicking SamplerCustomAdvanced → CFGGuider → two CLIPTextEncode nodes."""
    return {
        "sampler": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["noise_node", 0],
                "guider": ["cfg_guider", 0],
                "sampler": ["sampler_select", 0],
                "sigmas": ["scheduler", 0],
                "latent_image": ["latent", 0],
            },
        },
        "cfg_guider": {
            "class_type": "CFGGuider",
            "inputs": {
                "model": ["checkpoint", 0],
                "positive": ["pos_clip", 0],
                "negative": ["neg_clip", 0],
                "cfg": 8.0,
            },
        },
        "pos_clip": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "a white horse", "clip": ["checkpoint", 1]},
        },
        "neg_clip": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "human", "clip": ["checkpoint", 1]},
        },
        "checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"},
        },
        "noise_node": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": 1},
        },
        "sampler_select": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler"},
        },
        "scheduler": {
            "class_type": "BasicScheduler",
            "inputs": {"model": ["checkpoint", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0},
        },
        "latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
    }


def test_cfg_guider_positive_prompt_detected():
    """Positive CLIPTextEncode connected to CFGGuider's positive input must be identified."""
    prompt = _cfg_guider_prompt()
    assert validators_mod.is_positive_prompt("pos_clip", None, prompt, None, None, None)
    assert not validators_mod.is_positive_prompt("neg_clip", None, prompt, None, None, None)


def test_cfg_guider_negative_prompt_detected():
    """Negative CLIPTextEncode connected to CFGGuider's negative input must be identified."""
    prompt = _cfg_guider_prompt()
    assert validators_mod.is_negative_prompt("neg_clip", None, prompt, None, None, None)
    assert not validators_mod.is_negative_prompt("pos_clip", None, prompt, None, None, None)


def test_dual_cfg_guider_negative_prompt_detected():
    """DualCFGGuider exposes negative conditioning via its 'negative' input."""
    prompt = {
        "sampler": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {"guider": ["dual_guider", 0]},
        },
        "dual_guider": {
            "class_type": "DualCFGGuider",
            "inputs": {
                "model": ["ckpt", 0],
                "cond1": ["pos_clip", 0],
                "cond2": ["style_clip", 0],
                "negative": ["neg_clip", 0],
                "cfg_conds": 7.0,
                "cfg_cond2_negative": 1.0,
            },
        },
        "pos_clip": {"class_type": "CLIPTextEncode", "inputs": {"text": "a cat", "clip": ["ckpt", 1]}},
        "style_clip": {"class_type": "CLIPTextEncode", "inputs": {"text": "anime style", "clip": ["ckpt", 1]}},
        "neg_clip": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad quality", "clip": ["ckpt", 1]}},
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {}},
    }
    assert validators_mod.is_negative_prompt("neg_clip", None, prompt, None, None, None)
    assert not validators_mod.is_negative_prompt("pos_clip", None, prompt, None, None, None)
    assert not validators_mod.is_negative_prompt("style_clip", None, prompt, None, None, None)


def test_basic_guider_no_false_negative_detection():
    """BasicGuider has no negative input; the positive encoder must not be misidentified as negative."""
    prompt = {
        "sampler": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {"guider": ["basic_guider", 0]},
        },
        "basic_guider": {
            "class_type": "BasicGuider",
            "inputs": {
                "model": ["ckpt", 0],
                "conditioning": ["pos_clip", 0],
            },
        },
        "pos_clip": {"class_type": "CLIPTextEncode", "inputs": {"text": "a sunset", "clip": ["ckpt", 1]}},
        "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
    }
    assert validators_mod.is_positive_prompt("pos_clip", None, prompt, None, None, None)
    assert not validators_mod.is_negative_prompt("pos_clip", None, prompt, None, None, None)


# --- ControlNetApplyAdvanced conditioning-modifier traversal ---


def _controlnet_apply_advanced_prompt():
    """Build a prompt mimicking CLIPTextEncode → ControlNetApplyAdvanced → KSampler.

    This reproduces the workflow from issue #96 where Apply ControlNet
    (ControlNetApplyAdvanced) sits between the text encoders and the sampler.
    """
    return {
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["ckpt", 0],
                "positive": ["controlnet", 0],
                "negative": ["controlnet", 1],
                "latent_image": ["latent", 0],
                "seed": 1,
                "steps": 20,
                "cfg": 8.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "controlnet": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["pos_clip", 0],
                "negative": ["neg_clip", 0],
                "control_net": ["cn_loader", 0],
                "image": ["load_image", 0],
                "strength": 1.0,
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        "pos_clip": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "girl character, fox ears, blonde, sky, clouds, standing, flower garden,",
                "clip": ["ckpt", 1],
            },
        },
        "neg_clip": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "text, error, cropped, bad hands, extra legs,",
                "clip": ["ckpt", 1],
            },
        },
        "ckpt": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        },
        "cn_loader": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "t2i-adapter_xl_sketch.safetensors"},
        },
        "load_image": {
            "class_type": "LoadImage",
            "inputs": {"image": "input_scribble_example.png"},
        },
        "latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
    }


def test_controlnet_apply_advanced_positive_prompt_detected():
    """Positive CLIPTextEncode routed through ControlNetApplyAdvanced must be identified."""
    prompt = _controlnet_apply_advanced_prompt()
    assert validators_mod.is_positive_prompt("pos_clip", None, prompt, None, None, None)
    assert not validators_mod.is_positive_prompt("neg_clip", None, prompt, None, None, None)


def test_controlnet_apply_advanced_negative_prompt_detected():
    """Negative CLIPTextEncode routed through ControlNetApplyAdvanced must be identified."""
    prompt = _controlnet_apply_advanced_prompt()
    assert validators_mod.is_negative_prompt("neg_clip", None, prompt, None, None, None)
    assert not validators_mod.is_negative_prompt("pos_clip", None, prompt, None, None, None)
# and correctly routed as positive/negative prompt based on KSampler connections.
def test_qwen_image_edit_plus_prompt_detection():
    prompt = {
        "1": {
            "class_type": "KSampler",
            "inputs": {
                "positive": ["pos_enc", 0],
                "negative": ["neg_enc", 0],
            },
        },
        "pos_enc": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {"prompt": "Draw the text Hello in white."},
        },
        "neg_enc": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {"prompt": "blurry text, landscape"},
        },
    }

    assert validators_mod.is_positive_prompt("pos_enc", None, prompt, None, None, None)
    assert not validators_mod.is_negative_prompt("pos_enc", None, prompt, None, None, None)

    assert validators_mod.is_negative_prompt("neg_enc", None, prompt, None, None, None)
    assert not validators_mod.is_positive_prompt("neg_enc", None, prompt, None, None, None)


# --- Extension-registered text encoders (e.g., LoraManager Prompt) ---


_SENTINEL = object()


def test_has_prompt_capture_rules_true_for_registered_node():
    """_has_prompt_capture_rules should return True when CAPTURE_FIELD_LIST contains prompt rules."""
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import meta as meta_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import (
        CAPTURE_FIELD_LIST,
    )

    prev = CAPTURE_FIELD_LIST.get("TestPromptNode", _SENTINEL)
    CAPTURE_FIELD_LIST["TestPromptNode"] = {
        meta_mod.MetaField.POSITIVE_PROMPT: {"field_name": "text"},
    }
    try:
        assert validators_mod._has_prompt_capture_rules("TestPromptNode")
    finally:
        if prev is _SENTINEL:
            CAPTURE_FIELD_LIST.pop("TestPromptNode", None)
        else:
            CAPTURE_FIELD_LIST["TestPromptNode"] = prev


def test_has_prompt_capture_rules_false_for_unregistered_node():
    """_has_prompt_capture_rules should return False for unknown classes."""
    assert not validators_mod._has_prompt_capture_rules("SomeUnknownNode")


def test_has_prompt_capture_rules_false_for_non_prompt_rules():
    """_has_prompt_capture_rules should return False when rules exist but have no prompt fields."""
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import meta as meta_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import (
        CAPTURE_FIELD_LIST,
    )

    prev = CAPTURE_FIELD_LIST.get("LoraOnlyNode", _SENTINEL)
    CAPTURE_FIELD_LIST["LoraOnlyNode"] = {
        meta_mod.MetaField.LORA_MODEL_NAME: {"selector": lambda *a: []},
    }
    try:
        assert not validators_mod._has_prompt_capture_rules("LoraOnlyNode")
    finally:
        if prev is _SENTINEL:
            CAPTURE_FIELD_LIST.pop("LoraOnlyNode", None)
        else:
            CAPTURE_FIELD_LIST["LoraOnlyNode"] = prev


def test_prompt_loramanager_positive_detected():
    """Prompt (LoraManager) node connected to KSampler positive input should be identified as positive prompt.

    This test simulates the workflow from issue #92 where Prompt (LoraManager) nodes
    replace CLIPTextEncode nodes. The validator must recognise these nodes via the
    extension-registered capture rules rather than the hardcoded whitelist.
    """
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import meta as meta_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs import (
        CAPTURE_FIELD_LIST,
    )

    prev = CAPTURE_FIELD_LIST.get("Prompt (LoraManager)", _SENTINEL)
    # In test mode CAPTURE_FIELD_LIST is empty so we inject the same rules that
    # lora_manager.py registers at runtime.  This verifies the validator path
    # without depending on ext module import ordering.
    CAPTURE_FIELD_LIST.setdefault("Prompt (LoraManager)", {}).update({
        meta_mod.MetaField.POSITIVE_PROMPT: {"field_name": "text", "validate": validators_mod.is_positive_prompt},
        meta_mod.MetaField.NEGATIVE_PROMPT: {"field_name": "text", "validate": validators_mod.is_negative_prompt},
    })

    prompt = {
        "1": {
            "class_type": "KSampler",
            "inputs": {
                "positive": ["pos_prompt", 0],
                "negative": ["neg_prompt", 0],
            },
        },
        "pos_prompt": {
            "class_type": "Prompt (LoraManager)",
            "inputs": {"text": "photo of a woman in full color.", "clip": ["lora_loader", 1]},
        },
        "neg_prompt": {
            "class_type": "Prompt (LoraManager)",
            "inputs": {"text": "nude, kid, child,", "clip": ["lora_loader", 1]},
        },
        "lora_loader": {
            "class_type": "Lora Loader (LoraManager)",
            "inputs": {"model": ["ckpt", 0], "clip": ["ckpt", 1]},
        },
        "ckpt": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        },
    }

    try:
        assert validators_mod.is_positive_prompt("pos_prompt", None, prompt, None, None, None)
        assert not validators_mod.is_positive_prompt("neg_prompt", None, prompt, None, None, None)
        assert validators_mod.is_negative_prompt("neg_prompt", None, prompt, None, None, None)
        assert not validators_mod.is_negative_prompt("pos_prompt", None, prompt, None, None, None)
    finally:
        if prev is _SENTINEL:
            CAPTURE_FIELD_LIST.pop("Prompt (LoraManager)", None)
        else:
            CAPTURE_FIELD_LIST["Prompt (LoraManager)"] = prev
