"""Test SaveImageWithMetaDataUniversal for lora_strengths_in_prompt.

Test the SaveImageWithMetaDataUniversal (Save Image w/ Metadata Universal) node
for the behaviors of lora_strengths_in_prompt-related functions.
It runs the node's EXECUTE method (save_images()) to actually save an image file
and investigates the saved image file.
"""

import pytest
import copy
import torch
import piexif
from PIL import Image
from PIL.ImageFile import ImageFile

import folder_paths

from saveimage_unimeta.capture import Capture
from saveimage_unimeta.defs.combo import SAMPLER_SELECTION_METHOD
from saveimage_unimeta.defs.meta import MetaField
from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal, hook

def _create_stub_prompt(loras: int) -> dict[str, dict[str, dict[str, object] | str]]:
    """Create and return a prompt for this test.

    Args:
        loras: number of LoRAs in the returned prompt.
    """

    # Base prompt data containing two LoRAs.
    # The dictionary may be modified later, so we should create a new object everytime.
    # The content needs to be consistent with _get_inputs_stub() below.
    prompt = {
        "1": {
            "inputs": {"ckpt_name": "base.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "2": {
            "inputs": {"text": "1girl", "clip": ["9", 1]},
            "class_type": "CLIPTextEncode",
        },
        "3": {
            "inputs": {"text": "nsfw", "clip": ["9", 1]},
            "class_type": "CLIPTextEncode",
        },
        "4": {
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 4.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["9", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "5": {
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "6": {
            "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
            "class_type": "VAEDecode",
        },
        "7": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "sampler_selection_method": "Farthest",
                "sampler_selection_node_id": 0,
                "file_format": "png",
                "lossless_webp": True,
                "quality": 100,
                "max_jpeg_exif_kb": 60,
                "save_workflow_json": False,
                "add_counter_to_filename": True,
                "civitai_sampler": False,
                "guidance_as_cfg": False,
                "save_workflow_image": True,
                "include_lora_summary": False,
                "suppress_missing_class_log": True,
                "model_hash_log": "none",
                "images": ["6", 0],
            },
            "class_type": "SaveImageWithMetaDataUniversal",
        },
        "8": {
            "inputs": {
                "lora_name": "lora-8.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.8,
                "model": ["1", 0],
                "clip": ["1", 1],
            },
            "class_type": "LoraLoader",
        },
        "9": {
            "inputs": {
                "lora_name": "lora-9.safetensors",
                "strength_model": 0.9,
                "strength_clip": 0.9,
                "model": ["8", 0],
                "clip": ["8", 1],
            },
            "class_type": "LoraLoader",
        },
    }

    count = sum(v["class_type"] == "LoraLoader" for v in prompt.values())
    if loras < 0 or loras > count:
        raise IndexError(f"argument 'loras' must be in 0 to {count} (inclusive).")

    # Remove the excess LoraLoader nodes from the base prompt.
    for _ in range(count - loras):
        # Remove the first LoraLoader in the current prompt.
        lora_loader_id = _find_node_id_by_class_type(prompt, "LoraLoader")
        lora_loader_node = prompt.pop(lora_loader_id)
        # Relink inputs that were connected to the removed node.
        # Note that the following relinkage technique works
        # only when removing some particular types of nodes,
        # including LoraLoader (of course.)
        # Be careful if you are reusing this code
        for node in prompt.values():
            for input_name, value in node["inputs"].items():
                if isinstance(value, list) and value[0] == lora_loader_id:
                    node["inputs"][input_name] = copy.deepcopy(lora_loader_node["inputs"][input_name])

    return prompt

def _find_node_id_by_class_type(prompt: dict[str, dict[str, object]], class_type: str) -> str:
    """Find the first node of the specified class type in the prompt and return its id."""
    id = next((id for id, node in prompt.items() if node.get("class_type") == class_type), None)
    if id is None:
        raise ValueError(f"{class_type} not found in the prompt.")
    return id

def _get_inputs_stub(cls):
    """Return a fixed inputs data for testing to substitute the Capture.get_inputs()."""
    # The inputs data.
    # The dictionary might be modified, so we create a new object everytime.
    # The content should be consistent with _get_inputs_stub() above,
    # but inputs may contain any excess information,
    # because it is always _filtered_ before use by our prompt.
    return {
        MetaField.MODEL_NAME: [("1", "base.safetensors", "ckpt_name")],
        MetaField.MODEL_HASH: [("1", "1111111111", "ckpt_name")],
        MetaField.POSITIVE_PROMPT: [("2", "1girl", "text")],
        MetaField.EMBEDDING_NAME: [],
        MetaField.EMBEDDING_HASH: [],
        MetaField.NEGATIVE_PROMPT: [("3", "nsfw", "text")],
        MetaField.SEED: [("4", 0, "seed")],
        MetaField.STEPS: [("4", 20, "steps")],
        MetaField.CFG: [("4", 4.0, "cfg")],
        MetaField.SAMPLER_NAME: [("4", "euler", "sampler_name")],
        MetaField.SCHEDULER: [("4", "normal", "scheduler")],
        MetaField.IMAGE_WIDTH: [("5", 1024, "width")],
        MetaField.IMAGE_HEIGHT: [("5", 1024, "height")],
        MetaField.LORA_MODEL_NAME: [
            ("8", "lora-8.safetensors", "lora_name"),
            ("9", "lora-9.safetensors", "lora_name"),
        ],
        MetaField.LORA_MODEL_HASH: [
            ("8", "8888888888", "lora_name"),
            ("9", "9999999999", "lora_name"),
        ],
        MetaField.LORA_STRENGTH_MODEL: [
            ("8", 0.8, "strength_model"),
            ("9", 0.9, "strength_model"),
        ],
        MetaField.LORA_STRENGTH_CLIP: [
            ("8", 0.8, "strength_clip"),
            ("9", 0.9, "strength_clip"),
        ],
    }

def _create_stub_images():
    """Create a ComfyUI IMAGE data of 1 batch of 16x16 of zeros (black.)"""
    return torch.zeros(1, 16, 16, 3, dtype=torch.float32, device='cpu')

def _get_parameters(imagefile: ImageFile) -> str:
    """Get the Parameters string out of an image file."""

    if imagefile.format.lower() == "png":
        parameters = imagefile.info.get("parameters")
        assert parameters is not None
    else:
        exif0 = imagefile.info.get("exif")
        assert exif0 is not None
        exif1 = piexif.load(exif0)
        assert exif1 is not None
        exif2 = exif1.get("Exif")
        assert exif2 is not None
        user_comment = exif2.get(piexif.ExifIFD.UserComment)
        assert user_comment is not None
        parameters = piexif.helper.UserComment.load(user_comment)
        assert parameters is not None
    return parameters

# Strings expected in the saved image files.

_1GIRL_0LORA  = "1girl"
_1GIRL_1LORA  = "1girl <lora:lora-9:0.9>"
_1GIRL_2LORAS = "1girl <lora:lora-9:0.9> <lora:lora-8:0.8>"

_LORA_HASHES_1 = ', Lora hashes: "lora-9: 9999999999", '
_LORA_HASHES_2 = ', Lora hashes: "lora-9: 9999999999, lora-8: 8888888888", '

@pytest.mark.parametrize(
    "lora_strengths_in_prompt, loras, expected_positive_prompt, expected_lora_hashes",
    [
        pytest.param(True,  0, _1GIRL_0LORA,  None,           id="T0"),
        pytest.param(True,  1, _1GIRL_1LORA,  _LORA_HASHES_1, id="T1"),
        pytest.param(True,  2, _1GIRL_2LORAS, _LORA_HASHES_2, id="T2"),
        pytest.param(False, 0, _1GIRL_0LORA,  None,           id="F0"),
        pytest.param(False, 1, _1GIRL_0LORA,  None,           id="F1"),
        pytest.param(False, 2, _1GIRL_0LORA,  None,           id="F2"),
    ]
)
@pytest.mark.parametrize("format", ("png", "jpeg", "webp"))
def test_save_images_for_lora_strengths_in_prompt(monkeypatch, tmp_path,
        format, lora_strengths_in_prompt, loras, expected_positive_prompt, expected_lora_hashes):
    """Test SaveImageWithMetaDataUnivesal.save_images handles lora_strengths_in_prompt."""

    # SaveImageWithMetaDataUniversal enters the _test mode_ when invoked in pytest,
    # and it behaves differently from the production environment.
    # We want to test the behaviors in the _real_ environment, so try to disable it.
    # setenv'ing at this timing is too late to disable all such test mode behaviors,
    # but the following seems enough for our test.
    monkeypatch.setenv("METADATA_TEST_MODE", "")

    node = SaveImageWithMetaDataUniversal()
    prompt = _create_stub_prompt(loras)

    # We don't executed the workflow/prompt, so stub the hook.
    current_save_image_node_id = _find_node_id_by_class_type(prompt, "SaveImageWithMetaDataUniversal")
    monkeypatch.setattr(hook, "current_prompt", prompt)
    monkeypatch.setattr(hook, "current_save_image_node_id", current_save_image_node_id)

    # We don't provide the workflow, so stub the Capture.get_inputs() to provide our inputs.
    monkeypatch.setattr(Capture, "get_inputs", classmethod(_get_inputs_stub))

    # Save images in a temporary directory by stubbing the save path generation method.
    node.output_dir = str(tmp_path)
    monkeypatch.setattr(folder_paths, "get_save_image_path",
        lambda prefix, dir, w, h: (node.output_dir, "test_img", 0, "", prefix))

    node.save_images(
        images=_create_stub_images(),
        file_format=format,
        sampler_selection_method=SAMPLER_SELECTION_METHOD[2], # "By node ID"
        sampler_selection_node_id=_find_node_id_by_class_type(prompt, "KSampler"),
        lora_strengths_in_prompt=lora_strengths_in_prompt)

    files = list(tmp_path.iterdir())
    assert len(files) == 1, "More than one file is created."
    with Image.open(files[0]) as imagefile:
        assert imagefile.format.lower() == format
        parameters = _get_parameters(imagefile)

    # Our stub prompt/inputs contain no newlines in either prompt texts,
    # so the parameters string should consist of exactly three lines.
    lines = parameters.splitlines()
    assert len(lines) == 3

    # The first line should be the positive prompt
    # followed by an appropriate number of LoRA designations.
    assert lines[0] == expected_positive_prompt

    # The last single line should contain all other metadata,
    # including the "Lora hashes:" if present.
    if expected_lora_hashes is None:
        assert 'Lora hashes:' not in lines[2]
    else:
        assert expected_lora_hashes in lines[2]

    # and in no case "Lora strength:" should be included in the save file.
    assert 'lora strengths:' not in lines[2]
