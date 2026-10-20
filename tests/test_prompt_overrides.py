"""Tests for positive/negative prompt overrides on the save node."""

import numpy as np
import pytest
from PIL import Image

import folder_paths

from saveimage_unimeta.capture import Capture
from saveimage_unimeta.defs.combo import SAMPLER_SELECTION_METHOD
from saveimage_unimeta.defs.meta import MetaField
from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal, hook


def _create_stub_prompt():
    """Return a minimal txt2img prompt graph whose node IDs match the inputs stub."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "base.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "1girl", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "nsfw", "clip": ["1", 1]}},
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 4.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["5", 0],
            },
        },
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["4", 0], "vae": ["1", 2]}},
        "7": {
            "class_type": "SaveImageWithMetaDataUniversal",
            "inputs": {"images": ["6", 0], "filename_prefix": "ComfyUI"},
        },
    }


def _find_node_id_by_class_type(prompt, class_type):
    return next((nid for nid, node in prompt.items() if node.get("class_type") == class_type), None)


def _get_inputs_stub(cls):
    """Return fixed captured inputs consistent with _create_stub_prompt."""
    return {
        MetaField.MODEL_NAME: [("1", "base.safetensors", "ckpt_name")],
        MetaField.POSITIVE_PROMPT: [("2", "1girl", "text")],
        MetaField.NEGATIVE_PROMPT: [("3", "nsfw", "text")],
        MetaField.SEED: [("4", 0, "seed")],
        MetaField.STEPS: [("4", 20, "steps")],
        MetaField.CFG: [("4", 4.0, "cfg")],
        MetaField.SAMPLER_NAME: [("4", "euler", "sampler_name")],
        MetaField.SCHEDULER: [("4", "normal", "scheduler")],
        MetaField.IMAGE_WIDTH: [("5", 512, "width")],
        MetaField.IMAGE_HEIGHT: [("5", 512, "height")],
    }


def _create_stub_images():
    return np.zeros((1, 16, 16, 3), dtype=np.float32)


def _run_save(monkeypatch, tmp_path, **save_kwargs):
    """Execute the save node against the stub workflow and return saved files."""
    node = SaveImageWithMetaDataUniversal()
    prompt = _create_stub_prompt()

    current_save_image_node_id = _find_node_id_by_class_type(prompt, "SaveImageWithMetaDataUniversal")
    monkeypatch.setattr(hook, "current_prompt", prompt)
    monkeypatch.setattr(hook, "current_save_image_node_id", current_save_image_node_id)
    monkeypatch.setattr(Capture, "get_inputs", classmethod(_get_inputs_stub))

    node.output_dir = str(tmp_path)
    monkeypatch.setattr(
        folder_paths,
        "get_save_image_path",
        lambda prefix, dir, w, h: (node.output_dir, prefix, 0, "", prefix),
    )

    node.save_images(
        images=_create_stub_images(),
        file_format="png",
        sampler_selection_method=SAMPLER_SELECTION_METHOD[2],  # "By node ID"
        sampler_selection_node_id=_find_node_id_by_class_type(prompt, "KSampler"),
        rules_mode="Off",
        **save_kwargs,
    )

    files = list(tmp_path.iterdir())
    assert len(files) == 1, "Exactly one image file should be saved."
    return files[0]


def test_override_replaces_prompt_in_parameters(monkeypatch, tmp_path):
    """A non-empty override replaces the captured prompt; the original is gone."""
    file_path = _run_save(
        monkeypatch,
        tmp_path,
        positive_prompt_override="masterpiece quality",
        negative_prompt_override="lowres blurry",
    )
    with Image.open(file_path) as imagefile:
        parameters = imagefile.info["parameters"]

    lines = parameters.splitlines()
    assert lines[0] == "masterpiece quality"
    assert "Negative prompt: lowres blurry" in parameters
    assert "1girl" not in parameters
    assert "nsfw" not in parameters


def test_empty_override_leaves_capture_untouched(monkeypatch, tmp_path):
    """An empty override leaves the captured prompts intact."""
    file_path = _run_save(monkeypatch, tmp_path)
    with Image.open(file_path) as imagefile:
        parameters = imagefile.info["parameters"]

    lines = parameters.splitlines()
    assert lines[0] == "1girl"
    assert "Negative prompt: nsfw" in parameters


def test_pprompt_nprompt_tokens_follow_override(monkeypatch, tmp_path):
    """The %pprompt%/%nprompt% filename tokens resolve against the override."""
    file_path = _run_save(
        monkeypatch,
        tmp_path,
        filename_prefix="pp_%pprompt%_np_%nprompt%",
        positive_prompt_override="masterpiece",
        negative_prompt_override="lowres",
    )
    assert "pp_masterpiece_np_lowres" in file_path.name
