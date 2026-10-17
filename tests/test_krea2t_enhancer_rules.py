import importlib

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.krea2t_enhancer"


def _applied(inputs):
    mod = importlib.import_module(MODULE_PATH)
    return mod.is_lora_applied("1", None, None, None, None, (inputs,))


def test_krea2t_loaders_have_lora_rules():
    mod = importlib.import_module(MODULE_PATH)
    assert set(mod.CAPTURE_FIELD_LIST) == {"Krea2TCharacterLoraImageOnly", "Krea2SelectiveLoraLoaderModelOnlyProjection"}


def test_krea2t_validator_skips_bypassed_loaders():
    assert _applied({"lora_name": ["char.safetensors"], "strength_model": [0.8], "enabled": [True]})
    assert _applied({"lora_name": ["sel.safetensors"], "strength_model": [1.0]})  # selective loader has no `enabled`
    assert not _applied({"lora_name": ["char.safetensors"], "strength_model": [0.8], "enabled": [False]})
    assert not _applied({"lora_name": ["sel.safetensors"], "strength_model": [0.0]})
