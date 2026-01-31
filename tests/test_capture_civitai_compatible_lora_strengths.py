import re
import pytest

from saveimage_unimeta.defs.meta import MetaField
from saveimage_unimeta.capture import Capture

def _inputs0():
    """Create and return a new stub inputs with no LoRA."""
    return {
        MetaField.MODEL_NAME: [('n1', 'model.safetensors', 2)],
        MetaField.MODEL_HASH: [('n1', '1111111111', 2)],

        MetaField.POSITIVE_PROMPT: [('n2', '1girl', 1)],
        MetaField.NEGATIVE_PROMPT: [('n3', 'nsfw', 1)],

        MetaField.SEED: [('n4', 0, 0)],
        MetaField.STEPS: [('n4', 30, 0)],
        MetaField.CFG: [('n4', 4.0, 0)],
        MetaField.SAMPLER_NAME: [('n4', 'euler', 0)],
        MetaField.SCHEDULER: [('n4', 'normal', 0)],
    }

def _inputs1():
    """Create and return a new stub inputs with one LoRA."""
    inputs = _inputs0()
    inputs.update({
        MetaField.LORA_MODEL_NAME: [('n5', 'lora-5.safetensors', 1)],
        MetaField.LORA_MODEL_HASH: [('n5', '5555555555', 1)],
        MetaField.LORA_STRENGTH_MODEL: [('n5', 0.9, 1)],
        MetaField.LORA_STRENGTH_CLIP: [('n5', 0.7, 1)],
    })
    return inputs

def _inputs2():
    """Create and return a new stub inputs with two LoRAs."""
    inputs = _inputs1()
    inputs.update({
        MetaField.LORA_MODEL_NAME: [
            ('n5', 'lora-5.safetensors', 1),
            ('n6', 'lora-6.safetensors', 1)
        ],
        MetaField.LORA_MODEL_HASH: [
            ('n5', '5555555555', 1),
            ('n6', '6666666666', 1),
        ],
        MetaField.LORA_STRENGTH_MODEL: [
            ('n5', 0.9, 1),
            ('n6', 0.8, 1),
        ],
        MetaField.LORA_STRENGTH_CLIP: [
            ('n5', 0.7, 1),
            ('n5', 0.6, 1),
        ],
    })
    return inputs

# TODO: add tests for gen_pnginfo_dict when its behavior is determined.

@pytest.mark.parametrize(
    "inputs, lora_hashes",
    [
        (_inputs0(), []),
        (_inputs1(), ['"lora-5: 5555555555"']),
        (_inputs2(), ['"lora-5: 5555555555, lora-6: 6666666666"']),
    ]
)
def test_gen_parameters_str_creates_lora_hashes(inputs, lora_hashes):
    pnginfo = Capture.gen_pnginfo_dict(inputs, inputs, True)
    parameters = Capture.gen_parameters_str(pnginfo)
    # "Steps:" comes first in the _other_ metadata.
    # "Lora hashes:" should be somewhere after it.
    p = parameters.find('Steps:')
    assert p >= 0, "'Steps:' not found"
    found = re.findall(', *Lora hashes: *("[^"]*") *(?:,|$)', parameters[p:])
    assert found == lora_hashes

@pytest.mark.parametrize(
    "inputs, lora_designations",
    [
        (_inputs0(), []),
        (_inputs1(), ["<lora:lora-5:0.9>"]),
        (_inputs2(), ["<lora:lora-5:0.9>", "<lora:lora-6:0.8>"]),
    ]
)
def test_gen_parameters_str_creates_lora_designations(inputs, lora_designations):
    pnginfo = Capture.gen_pnginfo_dict(inputs, inputs, True)
    parameters = Capture.gen_parameters_str(pnginfo)
    # "Negative prompt:" terminates the positive prompt text.
    p = parameters.find('Negative prompt:')
    assert p >= 0, "'Negative prompt:' not found"
    found = re.findall('<(?:lora|hypernet):[a-zA-Z0-9_.-]+:[0-9.]+>', parameters[:p])
    assert found == lora_designations
