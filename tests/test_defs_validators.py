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
