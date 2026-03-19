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
